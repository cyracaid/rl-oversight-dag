#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ablation + failure analysis: is the GNN actually using the confidence signal,
or just the graph structure (fan-out)?

Two conditions, same GNN+REINFORCE training (3 seeds for speed):
  A. Normal: conf encodes (wrong=-1.5, right=+1.5) + type prior + noise
  B. Noisy conf: replace conf with pure noise (break the signal)
  C. Oracle conf: conf = -1.5 if truly wrong else +1.5 (no noise)

If A >> B: the model uses confidence.
If C >> A: the bottleneck is the noisy predictor (like the LLM-scheduler's "predictor is the ceiling").
If A ≈ C: the scheduler is robust to prediction noise.
"""
import torch
import math
import random
import spike_active_selection as SP
from rl_cmdp_gnn import GNNPolicy, compute_err

K = SP.CFG["K"]
N = SP.CFG["N"]
D = K + 2
R = 16
TRAIN_SEEDS = [1, 2, 3]
N_EP = 12000


def feats_with_conf(nodes, conf, sink_reach):
    F = torch.zeros(N, D)
    for i in range(N):
        F[i, nodes[i]["type"]] = 1.0
        F[i, K] = conf[i]
        F[i, K + 1] = math.log1p(sink_reach[i]) / math.log1p(N)
    return F


def build_env_mode(rng, mode):
    """mode: normal | noise | oracle"""
    nodes, topo, coins, sinks, sink_reach = SP.build_graph(rng)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(N)]
    if mode == "noise":
        conf = [rng.random() for _ in range(N)]
    elif mode == "oracle":
        conf = [-1.5 if b else 1.5 for b in base]
    else:
        conf = SP.make_conf(nodes, base, rng)
    F = feats_with_conf(nodes, conf, sink_reach)
    return nodes, topo, coins, sinks, base, F


def train_one(seed, mode, n_ep=N_EP):
    policy = GNNPolicy()
    opt = torch.optim.Adam(policy.parameters(), lr=0.003)
    baseline = 0.0
    rng = random.Random(seed)
    for ep in range(n_ep):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        nodes, topo, coins, sinks, base, F = build_env_mode(rng, mode)
        base_cur = list(base)
        err = compute_err(base_cur, nodes, topo, coins)
        reviewed = [False] * N
        logps = []
        for _ in range(R):
            A0 = torch.zeros(N, N)
            s = policy.score(F, A0)
            mask = torch.full((N,), float("-inf"))
            for i in range(N):
                if not reviewed[i]:
                    mask[i] = 0.0
            lp = torch.log_softmax((s + mask) / temp, dim=0)
            a = int(torch.multinomial(torch.exp(lp), 1).item())
            logps.append(lp[a])
            reviewed[a] = True
            if err[a] and rng.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = compute_err(base_cur, nodes, topo, coins)
        r = -sum(1 for j in sinks if err[j])
        baseline = 0.95 * baseline + 0.05 * r
        adv = r - baseline
        loss = torch.zeros(1)
        for lp in logps:
            loss = loss - adv * lp
        opt.zero_grad(); loss.backward(); opt.step()
    return policy


def eval_one(policy, mode, seeds):
    vals = []
    for seed in seeds:
        rng = random.Random(seed)
        nodes, topo, coins, sinks, base, F = build_env_mode(rng, mode)
        base_cur = list(base)
        err = compute_err(base_cur, nodes, topo, coins)
        reviewed = [False] * N
        A0 = torch.zeros(N, N)
        for _ in range(R):
            s = policy.score(F, A0)
            mask = torch.full((N,), float("-inf"))
            for i in range(N):
                if not reviewed[i]:
                    mask[i] = 0.0
            a = int(torch.argmax(s + mask).item())
            reviewed[a] = True
            if err[a] and rng.random() < SP.CFG["p_catch"]:
                base_cur[a] = False
                err = compute_err(base_cur, nodes, topo, coins)
        vals.append(sum(1 for j in sinks if err[j]))
    return sum(vals) / len(vals)


def main():
    print("Ablation: GNN+REINFORCE under three confidence conditions (3 seeds x 12k ep)")
    print("  normal = learned conf signal (as in main experiments)")
    print("  noise  = conf replaced by uniform noise (signal destroyed)")
    print("  oracle = conf reveals the true error (upper bound of the signal)\n")

    results = {"normal": [], "noise": [], "oracle": []}
    for seed in TRAIN_SEEDS:
        for mode in ["normal", "noise", "oracle"]:
            policy = train_one(seed, mode)
            m = eval_one(policy, mode, SP.CFG["seeds"])
            results[mode].append(m)
            print(f"  seed {seed}  {mode:<7} {m:.2f}", flush=True)

    print("\n" + "=" * 55)
    print(f"{'condition':<10}{'mean':>8}{'per-seed':>28}")
    for mode, vals in results.items():
        mean = sum(vals) / len(vals)
        print(f"{mode:<10}{mean:>8.2f}   {[round(v,2) for v in vals]}")

    n, a, o = (sum(results[k]) / 3 for k in ("noise", "normal", "oracle"))
    print()
    print(f"normal - noise = {a - n:.2f}   (positive → model uses the conf signal)")
    print(f"oracle - normal = {o and (n - o):.2f}   (positive → noisy predictor is the bottleneck)")


if __name__ == "__main__":
    main()
