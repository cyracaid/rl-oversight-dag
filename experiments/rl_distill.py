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
  python3 rl_distill.py --smoke --out-dir runs/bc-smoke
  python3 rl_distill.py --graphs 800 --bc-epochs 4 --episodes 20000 --seeds 1 2 3 4 5 --out-dir runs/bc-full
Writes results.json, results.md and checkpoints inside a new output directory.
"""
import argparse
import json
import math
import random
import statistics
from pathlib import Path

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


def bc_train(policy, data, epochs, lr, batch, seed=0):
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    shuffle_rng = random.Random(seed)
    losses = []
    for ep in range(epochs):
        shuffle_rng.shuffle(data)
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


def valid_kl(scores, reference, reviewed, temp):
    """KL(reference || policy) only on available actions; avoid -inf - -inf."""
    lp = torch.log_softmax(scores[~reviewed] / temp, 0)
    with torch.no_grad():
        lp_ref = torch.log_softmax(reference[~reviewed] / temp, 0)
    return (lp_ref.exp() * (lp_ref - lp)).sum()


def rollout_kl(policy, ref, rng, belief_seed, temp):
    """One episode with both the current and the reference (BC) policy scored."""
    env = M.build_env(rng, belief_seed, with_belief=True)
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    reviewed, flagged = [False] * N, [False] * N
    u = SP.episode_uniforms(rng, N) if SP.CFG["crn"] else None
    logps, kls = [], []
    for t in range(R):
        F = M.features(env, VARIANT, reviewed, flagged, R - t)
        s = policy.score(F, env["A"])
        with torch.no_grad():
            s_ref = ref.score(F, env["A"])
        mask = torch.tensor(reviewed)
        kls.append(valid_kl(s, s_ref, mask, temp))
        s = s.masked_fill(mask, float("-inf"))
        s_ref = s_ref.masked_fill(mask, float("-inf"))
        lp = torch.log_softmax(s / temp, 0)
        a = int(torch.multinomial(torch.exp(lp), 1).item())
        logps.append(lp[a])
        f, err = SP.review_step(a, base, err, env["nodes"], env["topo"],
                                env["coins"], rng, u)
        reviewed[a], flagged[a] = True, f
        env["belief"].observe(a, f)
    return sum(1 for j in env["sinks"] if err[j]), logps, kls


def finetune_kl(policy, ref, seed, episodes, lr, beta):
    """REINFORCE with a KL leash to the BC policy."""
    torch.manual_seed(seed)
    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    baseline = 0.0
    rng = random.Random(10**9 + seed)
    curve, window = [], []
    for ep in range(episodes):
        temp = max(0.3, 2.0 * (0.9993 ** ep))
        sink_err, logps, kls = rollout_kl(policy, ref, rng,
                                          belief_seed=seed * 10**6 + ep, temp=temp)
        r = -sink_err
        baseline = 0.95 * baseline + 0.05 * r
        loss = -(r - baseline) * torch.stack(logps).sum() + beta * torch.stack(kls).sum()
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


def run_seed(seed, graphs, epochs, episodes, lr_bc, lr_ft, heldout, no_ft, kl_beta=0.0,
             checkpoint_dir=None):
    print(f"  seed {seed}: collecting teacher data ({graphs} graphs)", flush=True)
    data = collect(seed, graphs)
    torch.manual_seed(seed)
    policy = GNNPolicy(d=M.DIM[VARIANT])
    losses = bc_train(policy, data, epochs, lr_bc, batch=128, seed=seed)
    training_config = dict(graphs=graphs, epochs=epochs, episodes=episodes, lr_bc=lr_bc,
                           lr_ft=lr_ft, kl_beta=kl_beta, no_ft=no_ft)
    if checkpoint_dir is not None:
        from rl_boundary import save_policy
        save_policy(checkpoint_dir / f"bc_{seed}.pt", policy, VARIANT, seed, "bc", training_config)
    bc_held = M.eval_gnn(policy, VARIANT, heldout)
    print(f"  seed {seed}: BC-only held-out {sum(bc_held)/len(bc_held):.2f}", flush=True)
    ft_curve = []
    if not no_ft:
        if kl_beta > 0:
            import copy
            ref = copy.deepcopy(policy)
            ft_curve = finetune_kl(policy, ref, seed, episodes, lr_ft, kl_beta)
        else:
            ft_curve = finetune(policy, seed, episodes, lr_ft)
        ft_held = M.eval_gnn(policy, VARIANT, heldout)
        if checkpoint_dir is not None:
            kind = "bc_kl_ft" if kl_beta > 0 else "bc_ft"
            save_policy(checkpoint_dir / f"{kind}_{seed}.pt", policy, VARIANT, seed, kind, training_config)
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
    ap.add_argument("--kl-beta", type=float, default=0.0,
                    help="KL leash to the BC policy during fine-tuning (0 = off)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=None, help="Legacy JSON path; defaults to out-dir/results.json")
    ap.add_argument("--out-dir", type=Path, default=None, help="New directory; refuses to overwrite")
    ap.add_argument("--bootstrap", type=int, default=10000)
    args = ap.parse_args()

    if args.smoke:
        args.graphs, args.bc_epochs, args.episodes = 40, 1, 30
        args.seeds, args.heldout = [1], 20

    if min(args.graphs, args.bc_epochs, args.heldout, args.bootstrap) < 1:
        ap.error("graphs, bc-epochs, heldout and bootstrap must be positive")
    if args.heldout > len(M.HELDOUT_SEEDS) or len(set(args.seeds)) != len(args.seeds):
        ap.error("heldout must be <= 200 and training seeds must be unique")
    if args.episodes < 0 or args.kl_beta < 0:
        ap.error("episodes and kl-beta must be nonnegative")
    if args.out_dir is None:
        ap.error("--out-dir is required; use a new directory to preserve historical artifacts")
    if args.out is not None:
        ap.error("use --out-dir instead of --out to keep JSON, table and checkpoints together")
    args.out_dir.mkdir(parents=True, exist_ok=False)
    SP.CFG["crn"] = True

    torch.set_num_threads(1)
    heldout = M.HELDOUT_SEEDS[:args.heldout]
    from rl_boundary import evaluate, SCENARIOS, provenance, write_report
    with torch.no_grad():
        greedy = [evaluate(s, SCENARIOS["matched"], "belief greedy")[0] for s in heldout]
    gm, gci = mean_ci(greedy)
    print(f"belief greedy held-out: {gm:.2f} ± {gci:.2f}")

    results = []
    for seed in args.seeds:
        results.append(run_seed(seed, args.graphs, args.bc_epochs, args.episodes,
                                args.lr_bc, args.lr_ft, heldout, args.no_ft, args.kl_beta,
                                args.out_dir))
        # Save completed seeds immediately, before starting the next long training run.
        config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
        conditions = {"belief greedy": greedy,
                      "BC": [r["bc_heldout"] for r in results]}
        if not args.no_ft:
            kind = "BC+KL-FT" if args.kl_beta > 0 else "BC+FT"
            conditions[kind] = [r["ft_heldout"] for r in results]
        write_report(args.out_dir / "results.json", {
            "config": config, "provenance": provenance(), "graph_seeds": heldout,
            "completed_seeds": [r["seed"] for r in results],
            "conditions": {"matched": conditions}, "training": results})
    print(f"Saved {args.out_dir / 'results.json'} and results.md", flush=True)
    return

if __name__ == "__main__":
    main()
