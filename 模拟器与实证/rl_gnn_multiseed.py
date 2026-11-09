#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GNN + REINFORCE（固定预算）多种子复现 —— 确认 1.20 的可靠性。

5 个训练种子 × 20000 ep，各自在 16 个评估种子上取均值，报 mean ± 95% CI。
"""
import torch
import random
import spike_active_selection as SP
from rl_cmdp_gnn import GNNPolicy, build_env, compute_err

N = SP.CFG["N"]
R = 16
EVAL_SEEDS = SP.CFG["seeds"]          # 16 个评估种子
TRAIN_SEEDS = [1, 2, 3, 4, 5]         # 5 个训练种子


def train_gnn(seed, n_ep=20000, lr=0.003):
    policy = GNNPolicy()
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    baseline = 0.0
    rng = random.Random(seed)
    for ep in range(n_ep):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        nodes, topo, coins, sinks, base, F, A = build_env(rng)
        base_cur = list(base)
        err = compute_err(base_cur, nodes, topo, coins)
        reviewed = [False] * N
        logps = []
        for _ in range(R):
            s = policy.score(F, A)
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


def evaluate(policy):
    vals = []
    for seed in EVAL_SEEDS:
        rng = random.Random(seed)
        nodes, topo, coins, sinks, base, F, A = build_env(rng)
        base_cur = list(base)
        err = compute_err(base_cur, nodes, topo, coins)
        reviewed = [False] * N
        for _ in range(R):
            s = policy.score(F, A)
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
    results = []
    for seed in TRAIN_SEEDS:
        print(f"[{seed}/5] 训练 seed {seed} ...", flush=True)
        policy = train_gnn(seed)
        m = evaluate(policy)
        results.append(m)
        print(f"      seed {seed}: {m:.2f}", flush=True)

    n = len(results)
    mean = sum(results) / n
    std = (sum((x - mean) ** 2 for x in results) / (n - 1)) ** 0.5
    ci = 2.776 * std / (n ** 0.5)          # t(0.025, df=4) ≈ 2.776

    print("\n" + "=" * 55)
    print("GNN + REINFORCE 多种子复现结果")
    print(f"  各种子 = {[round(x,2) for x in results]}")
    print(f"  mean  = {mean:.2f}")
    print(f"  std   = {std:.2f}")
    print(f"  95% CI = {mean:.2f} ± {ci:.2f}  (即 [{mean-ci:.2f}, {mean+ci:.2f}])")
    print(f"  对比: MLP REINFORCE = 1.40")
    print("=" * 55)

    with open("gnn_multiseed_result.txt", "w") as f:
        f.write(f"seeds={[round(x,2) for x in results]}\n")
        f.write(f"mean={mean:.3f}\nstd={std:.3f}\nci95={ci:.3f}\n")


if __name__ == "__main__":
    main()
