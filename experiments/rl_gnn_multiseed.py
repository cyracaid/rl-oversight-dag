#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-seed GNN + REINFORCE (fixed budget), static vs observed state.

Two state variants share the same GNN, training loop and budget:
  static   : per-node (type one-hot, conf, sink reach), computed once per episode.
             The policy never sees what its reviews found, so it can only learn a
             fixed ranking. This is the original method.
  observed : static features + belief features recomputed after every review:
             P(base error), P(error) from the particle belief (belief.py),
             reviewed?, flagged?, remaining budget fraction.
             Review outcomes now change the next decision.

Evaluation
  legacy   : seeds 1..20 (the graphs every earlier table used)
  held-out : seeds 1000..1199, never used for training; every policy is run on the
             same graph with the same catch-randomness stream, so differences are paired.
Baselines on the same held-out graphs: conf threshold, structural greedy,
belief greedy (deployable adaptive greedy on the same belief).

Writes gnn_multiseed_result.txt and gnn_vs_greedy_table.md.
"""
import math
import random
from concurrent.futures import ProcessPoolExecutor

import torch

import spike_active_selection as SP
from rl_cmdp_gnn import GNNPolicy

N = SP.CFG["N"]
K = SP.CFG["K"]
R = SP.CFG["budget"]
LEGACY_SEEDS = SP.CFG["seeds"]
HELDOUT_SEEDS = list(range(1000, 1200))
TRAIN_SEEDS = [1, 2, 3, 4, 5]
N_EPISODES = 20000
DIM = {"static": K + 2, "observed": K + 7}
T_975 = {4: 2.776, 199: 1.972}


def build_env(rng, belief_seed, with_belief):
    nodes, topo, coins, sinks, sink_reach = SP.build_graph(rng)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(N)]
    conf = SP.make_conf(nodes, base, rng)
    S = torch.zeros(N, K + 2)
    for i in range(N):
        S[i, nodes[i]["type"]] = 1.0
        S[i, K] = conf[i]
        S[i, K + 1] = math.log1p(sink_reach[i]) / math.log1p(N)
    A = torch.zeros(N, N)
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            A[p, i] = 1.0
    deg = A.sum(1, keepdim=True)
    A = torch.where(deg > 0, A / deg.clamp(min=1), A)      # child -> parent mean
    belief = SP.make_belief(nodes, topo, sinks, conf, belief_seed) if with_belief else None
    return dict(nodes=nodes, topo=topo, coins=coins, sinks=sinks, base=base,
                conf=conf, sink_reach=sink_reach, S=S, A=A, belief=belief)


def features(env, variant, reviewed, flagged, budget_left):
    if variant == "static":
        return env["S"]
    b = env["belief"]
    dyn = torch.stack([
        torch.tensor(b.p_base(), dtype=torch.float32),
        torch.tensor(b.p_err(), dtype=torch.float32),
        torch.tensor(reviewed, dtype=torch.float32),
        torch.tensor(flagged, dtype=torch.float32),
        torch.full((N,), budget_left / R),
    ], dim=1)
    return torch.cat([env["S"], dyn], dim=1)


def run_episode(policy, variant, rng, belief_seed, temp=None):
    """temp=None: greedy argmax (evaluation). Otherwise sample (training)."""
    env = build_env(rng, belief_seed, with_belief=(variant == "observed"))
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    reviewed, flagged = [False] * N, [False] * N
    logps = []
    for t in range(R):
        s = policy.score(features(env, variant, reviewed, flagged, R - t), env["A"])
        s = s.masked_fill(torch.tensor(reviewed), float("-inf"))
        if temp is None:
            a = int(torch.argmax(s).item())
        else:
            lp = torch.log_softmax(s / temp, dim=0)
            a = int(torch.multinomial(torch.exp(lp), 1).item())
            logps.append(lp[a])
        f, err = SP.review_step(a, base, err, env["nodes"], env["topo"], env["coins"], rng)
        reviewed[a], flagged[a] = True, f
        if env["belief"] is not None:
            env["belief"].observe(a, f)
    return sum(1 for j in env["sinks"] if err[j]), logps


def train(variant, seed, n_ep=N_EPISODES, lr=0.003):
    torch.manual_seed(seed)
    policy = GNNPolicy(d=DIM[variant])
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    baseline = 0.0
    rng = random.Random(seed)
    for ep in range(n_ep):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        sink_err, logps = run_episode(policy, variant, rng, belief_seed=seed * 10**6 + ep,
                                      temp=temp)
        r = -sink_err
        baseline = 0.95 * baseline + 0.05 * r
        loss = -(r - baseline) * torch.stack(logps).sum()
        opt.zero_grad(); loss.backward(); opt.step()
    return policy


def eval_gnn(policy, variant, seeds):
    with torch.no_grad():
        return [run_episode(policy, variant, random.Random(s), belief_seed=10_000 + s)[0]
                for s in seeds]


def eval_baselines(seeds):
    out = {"conf threshold": [], "structural greedy": [], "belief greedy": []}
    for s in seeds:
        for name in out:
            rng = random.Random(s)
            env = build_env(rng, 10_000 + s, with_belief=(name == "belief greedy"))
            args = (env["base"], env["nodes"], env["topo"], env["coins"], env["sinks"])
            if name == "belief greedy":
                out[name].append(SP.run_belief_greedy(env["belief"], *args, R, rng))
                continue
            if name == "conf threshold":
                order = sorted(range(N), key=lambda i: env["conf"][i])[:R]
            else:
                score = [(1 - env["conf"][i]) * (1 + env["sink_reach"][i]) for i in range(N)]
                order = sorted(range(N), key=lambda i: -score[i])[:R]
            out[name].append(SP.apply_reviews(order, *args, rng))
    return out


def job(variant, seed):
    torch.set_num_threads(1)
    policy = train(variant, seed)
    return variant, seed, eval_gnn(policy, variant, LEGACY_SEEDS), \
        eval_gnn(policy, variant, HELDOUT_SEEDS)


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5
    return m, sd, T_975[n - 1] * sd / n ** 0.5


def main():
    jobs = [(v, s) for v in DIM for s in TRAIN_SEEDS]
    res = {}
    with ProcessPoolExecutor(max_workers=min(len(jobs), 8)) as ex:
        for variant, seed, legacy, held in ex.map(job, *zip(*jobs)):
            res[(variant, seed)] = (legacy, held)
            print(f"  {variant:<9} seed {seed}: legacy {sum(legacy)/len(legacy):.2f}  "
                  f"held-out {sum(held)/len(held):.2f}", flush=True)
    base = eval_baselines(HELDOUT_SEEDS)
    base_legacy = eval_baselines(LEGACY_SEEDS)

    lines = [f"N={N}, budget={R}, {len(TRAIN_SEEDS)} training seeds x {N_EPISODES} "
             f"episodes, held-out graphs {HELDOUT_SEEDS[0]}..{HELDOUT_SEEDS[-1]} "
             f"(n={len(HELDOUT_SEEDS)}), particles={SP.CFG['n_particles']}",
             "",
             "| policy | legacy seeds 1-20 | held-out mean | 95% CI |",
             "|---|---:|---:|---:|"]
    txt = []
    for name in base:
        m, _, ci = mean_ci(base[name])
        lg = sum(base_legacy[name]) / len(LEGACY_SEEDS)
        lines.append(f"| {name} | {lg:.2f} | {m:.2f} | ± {ci:.2f} |")
    per_graph = {}
    for v in DIM:
        legacy_means = [sum(res[(v, s)][0]) / len(LEGACY_SEEDS) for s in TRAIN_SEEDS]
        held_means = [sum(res[(v, s)][1]) / len(HELDOUT_SEEDS) for s in TRAIN_SEEDS]
        lm, _, lci = mean_ci(legacy_means)
        hm, _, hci = mean_ci(held_means)
        lines.append(f"| GNN + REINFORCE ({v} state) | {lm:.2f} ± {lci:.2f} | {hm:.2f} "
                     f"| ± {hci:.2f} (over training seeds) |")
        txt.append(f"{v}: legacy_per_seed={[round(x, 2) for x in legacy_means]} "
                   f"legacy_mean={lm:.3f} ci95={lci:.3f} "
                   f"heldout_per_seed={[round(x, 3) for x in held_means]} heldout_mean={hm:.3f}")
        per_graph[v] = [sum(res[(v, s)][1][g] for s in TRAIN_SEEDS) / len(TRAIN_SEEDS)
                        for g in range(len(HELDOUT_SEEDS))]

    lines += ["", "Paired differences on held-out graphs (per graph, GNN averaged over "
              "training seeds; negative = left side has fewer sink errors):", ""]
    pairs = [("GNN observed", per_graph["observed"], "GNN static", per_graph["static"]),
             ("GNN observed", per_graph["observed"], "belief greedy", base["belief greedy"]),
             ("GNN static", per_graph["static"], "structural greedy",
              base["structural greedy"])]
    for a, xa, b, xb in pairs:
        m, _, ci = mean_ci([p - q for p, q in zip(xa, xb)])
        lines.append(f"- {a} − {b}: {m:+.2f} ± {ci:.2f}")
        txt.append(f"paired {a} - {b}: {m:+.3f} ci95={ci:.3f}")

    with open("gnn_vs_greedy_table.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open("gnn_multiseed_result.txt", "w") as f:
        f.write("\n".join(txt) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
