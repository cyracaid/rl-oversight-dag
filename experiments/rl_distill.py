#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distillation probe: belief greedy as the teacher, GNN + REINFORCE as the student.

Why this exists
---------------
The "observed" GNN variant already receives the belief posterior and still loses
to belief greedy (1.56 vs 1.14, paired +0.42 ± 0.15). Feeding the belief in is
therefore not the open question. This probe asks a different one:

    can the policy represent the teacher's rule at all?

Phase 1 — behaviour cloning (BC): run belief greedy on training graphs, record
(state features, teacher action), and fit the policy by cross-entropy.
Phase 2 — fine-tune (FT): continue the same weights with REINFORCE on the real
objective (sink errors), exactly as rl_gnn_multiseed.py trains.

Reading the result
------------------
  BC alone ≈ 1.14            -> representation is fine; the gap is optimisation/credit.
  BC never gets near 1.14    -> capacity or feature problem.
  BC good but FT makes it worse -> fine-tuning destroys the policy (credit assignment).

Usage
-----
  python3 rl_distill.py --smoke
  python3 rl_distill.py --graphs 800 --bc-epochs 4 --episodes 20000 --seeds 1 2 3 4 5
Writes dist_results.json and dist_table.md next to this file.
"""
import argparse
import json
import math
import random
import statistics

import torch

import spike_active_selection as SP
import rl_gnn_multiseed as M
from rl_cmdp_gnn import GNNPolicy

N, R = M.N, M.R
VARIANT = "observed"
REVIEWED_COL = M.K + 4          # column of the "reviewed" flag inside features()


def masked_scores(policy, F, A):
    s = policy.score(F, A)
    reviewed = F[:, REVIEWED_COL] > 0.5
    return s.masked_fill(reviewed, float("-inf"))


def teacher_episode(rng, belief_seed):
    """Play one episode with belief greedy; return [(features, A, action), ...]."""
    env = M.build_env(rng, belief_seed, with_belief=True)
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    reviewed, flagged = [False] * N, [False] * N
    available = [True] * N
    u = SP.episode_uniforms(rng, N) if SP.CFG["crn"] else None
    rows = []
    for t in range(R):
        F = M.features(env, VARIANT, reviewed, flagged, R - t)
        a = env["belief"].best_action(available)
        rows.append((F, env["A"].clone(), a))
        available[a] = False
        reviewed[a] = True
        f, err = SP.review_step(a, base, err, env["nodes"], env["topo"], env["coins"], rng, u)
        flagged[a] = f
        env["belief"].observe(a, f)
    return rows


def collect(seed, graphs):
    rng = random.Random(seed)
    data = []
    for g in range(graphs):
        data.extend(teacher_episode(rng, seed * 10**6 + g))
    return data


def bc_train(policy, data, epochs, lr, batch):
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    losses = []
    for ep in range(epochs):
        random.shuffle(data)
        tot, n = 0.0, 0
        for i in range(0, len(data), batch):
            chunk = data[i:i + batch]
            loss = 0.0
            for F, A, a in chunk:
                logits = masked_scores(policy, F, A)
                loss = loss + torch.nn.functional.cross_entropy(logits.unsqueeze(0),
                                                                torch.tensor([a]))
            loss = loss / len(chunk)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss.item()) * len(chunk)
            n += len(chunk)
        losses.append(tot / max(n, 1))
        print(f"    BC epoch {ep+1}/{epochs}: loss {losses[-1]:.3f}", flush=True)
    return losses


def finetune(policy, seed, episodes, lr=0.003):
    torch.manual_seed(seed)
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    baseline = 0.0
    rng = random.Random(10**9 + seed)
    curve, window = [], []
    for ep in range(episodes):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        sink_err, logps = M.run_episode(policy, VARIANT, rng,
                                        belief_seed=seed * 10**6 + ep, temp=temp)
        r = -sink_err
        baseline = 0.95 * baseline + 0.05 * r
        loss = -(r - baseline) * torch.stack(logps).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
        window.append(sink_err)
        if len(window) == M.CURVE_EVERY:
            curve.append((ep + 1, sum(window) / len(window)))
            window = []
    return curve


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = statistics.stdev(xs) if n > 1 else 0.0
    t = M.T_975.get(n - 1, 1.96)
    return m, t * sd / math.sqrt(n)


def run_seed(seed, graphs, epochs, episodes, lr_bc, lr_ft, heldout, no_ft):
    print(f"  seed {seed}: collecting teacher data ({graphs} graphs)", flush=True)
    data = collect(seed, graphs)
    policy = GNNPolicy(d=M.DIM[VARIANT])
    torch.manual_seed(seed)
    losses = bc_train(policy, data, epochs, lr_bc, batch=128)
    bc_held = M.eval_gnn(policy, VARIANT, heldout)
    print(f"  seed {seed}: BC-only held-out {sum(bc_held)/len(bc_held):.2f}", flush=True)
    ft_curve = []
    if not no_ft:
        ft_curve = finetune(policy, seed, episodes, lr_ft)
        ft_held = M.eval_gnn(policy, VARIANT, heldout)
        print(f"  seed {seed}: BC+FT  held-out {sum(ft_held)/len(ft_held):.2f}", flush=True)
    else:
        ft_held = bc_held
    return {"seed": seed, "bc_losses": losses, "bc_heldout": bc_held,
            "ft_heldout": ft_held, "ft_curve": ft_curve}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graphs", type=int, default=800)
    ap.add_argument("--bc-epochs", type=int, default=4)
    ap.add_argument("--episodes", type=int, default=20000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--heldout", type=int, default=200)
    ap.add_argument("--lr-bc", type=float, default=1e-3)
    ap.add_argument("--lr-ft", type=float, default=3e-3)
    ap.add_argument("--no-ft", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default="dist_results.json")
    args = ap.parse_args()

    if args.smoke:
        args.graphs, args.bc_epochs, args.episodes = 40, 1, 30
        args.seeds, args.heldout = [1], 20

    torch.set_num_threads(1)
    heldout = M.HELDOUT_SEEDS[:args.heldout]
    base = M.eval_baselines(heldout)
    greedy = base["belief greedy"]
    gm, gci = mean_ci(greedy)
    print(f"belief greedy held-out: {gm:.2f} ± {gci:.2f}")

    results = []
    for seed in args.seeds:
        results.append(run_seed(seed, args.graphs, args.bc_epochs, args.episodes,
                                args.lr_bc, args.lr_ft, heldout, args.no_ft))

    def agg(key):
        per = [sum(r[key]) / len(r[key]) for r in results]
        m, ci = mean_ci(per)
        return m, ci, per

    bc_m, bc_ci, bc_per = agg("bc_heldout")
    ft_m, ft_ci, ft_per = agg("ft_heldout")
    paired = [p - g for p, g in zip(ft_per, [gm] * len(ft_per))]

    lines = [
        f"N={N}, budget={R}, {len(args.seeds)} seed(s) x {args.episodes} FT episodes, "
        f"held-out n={len(heldout)}, teacher = belief greedy",
        "",
        "| policy | held-out mean | 95% CI |",
        "|---|---:|---:|",
        f"| belief greedy (teacher) | {gm:.2f} | ± {gci:.2f} |",
        f"| student, BC only | {bc_m:.2f} | ± {bc_ci:.2f} |",
        f"| student, BC + REINFORCE | {ft_m:.2f} | ± {ft_ci:.2f} |",
        "",
        f"Per-seed BC only: {['%.2f' % x for x in bc_per]}",
        f"Per-seed BC + FT: {['%.2f' % x for x in ft_per]}",
        "",
        ("Reading: BC ≈ teacher means the policy can represent the rule; a large BC gap "
         "means capacity/features; BC good and FT worse means credit assignment."),
    ]
    table = "\n".join(lines)
    print("\n" + table)
    with open(args.out, "w") as f:
        json.dump({"config": vars(args), "teacher": {"mean": gm, "ci95": gci},
                   "bc": {"mean": bc_m, "ci95": bc_ci, "per_seed": bc_per},
                   "ft": {"mean": ft_m, "ci95": ft_ci, "per_seed": ft_per},
                   "results": results}, f, indent=1)
    with open("dist_table.md", "w") as f:
        f.write(table + "\n")


if __name__ == "__main__":
    main()
