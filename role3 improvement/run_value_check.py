"""Measure whether sampled counterfactual values recover part of the oracle gap.

Pre-registered in ``PREREGISTER_EXACT_VALUE.md``, before this file existed:
graph seeds 4400-4599, 200 per family, particles 256, shortlist 16, hit rate 0.9,
metric ``recovery = (marginal - policy) / (marginal - oracle)`` per graph.

Graphs where ``marginal`` and ``oracle`` agree exactly have no gap to recover;
they are counted and excluded from the recovery mean rather than silently
treated as zero.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.counterfactual import make_policy
from dag_role3.policies import run_public_policy

BLOCK = (4400, 4599)
EPISODE_OFFSET = 20000
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124
BUDGET = {"spike": 16, "modular": 50}


def bootstrap(delta):
    delta = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(delta), size=(BOOTSTRAP, len(delta)))
    means = delta[draws].mean(axis=1)
    return tuple(float(x) for x in np.quantile(means, [0.025, 0.975]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=["modular", "spike"])
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--particles", type=int, default=256)
    ap.add_argument("--shortlist", type=int, default=16)
    ap.add_argument("--p-catch", type=float, default=0.9)
    ap.add_argument("--out", type=Path, default=Path("outputs/value-v1"))
    args = ap.parse_args()
    if args.start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    if (args.particles, args.shortlist, args.p_catch) != (256, 16, 0.9):
        raise SystemExit("particles, shortlist and hit rate are frozen by "
                         "PREREGISTER_EXACT_VALUE.md")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.start, args.end + 1))

    rows, summary = [], []
    for family in args.families:
        budget = BUDGET[family]
        for graph_seed in seeds:
            graph = generate_graph(family, graph_seed)
            snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
            marginal, _ = run_public_policy(graph, snapshot, "marginal", budget)
            oracle, _ = run_public_policy(graph, snapshot, "oracle", budget)
            policy, _ = run_public_policy(
                graph, snapshot,
                make_policy(p_catch=args.p_catch, particles=args.particles,
                            shortlist=args.shortlist, seed=graph_seed),
                budget)
            rows.append({"family": family, "graph_seed": graph_seed,
                         "marginal": marginal, "oracle": oracle,
                         "policy": policy})
        family_rows = [r for r in rows if r["family"] == family]
        with open(args.out / f"value_{family}.csv", "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(family_rows[0]))
            writer.writeheader()
            writer.writerows(family_rows)

        m = np.array([r["marginal"] for r in family_rows], float)
        o = np.array([r["oracle"] for r in family_rows], float)
        p = np.array([r["policy"] for r in family_rows], float)
        gap = m - o
        usable = gap > 0
        recovery = (m - p)[usable] / gap[usable]
        low, high = bootstrap(recovery)
        summary.append({
            "family": family, "graphs": len(m),
            "marginal_mean": float(m.mean()), "oracle_mean": float(o.mean()),
            "policy_mean": float(p.mean()),
            "gap_mean": float(gap.mean()),
            "graph_recovery_mean": float(recovery.mean()),
            "recovery_ci": [low, high],
            "graphs_with_gap": int(usable.sum()),
            "gap_closed_share_aggregate": float(
                (m.sum() - p.sum()) / gap.sum()) if gap.sum() > 0 else 0.0,
            "wins": int((p < m).sum()), "ties": int((p == m).sum()),
            "losses": int((p > m).sum()),
            "oracle_ties": int((o == m).sum()),
        })

    with open(args.out / "value_summary.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (args.out / "manifest.json").write_text(json.dumps({
        "block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
        "particles": args.particles, "shortlist": args.shortlist,
        "p_catch": args.p_catch, "bootstrap_draws": BOOTSTRAP,
        "bootstrap_seed": BOOTSTRAP_SEED, "budget": BUDGET,
        "reference": ["marginal", "oracle"],
    }, indent=2))

    for row in summary:
        print(f"{row['family']:8s} marginal {row['marginal_mean']:.3f}  "
              f"oracle {row['oracle_mean']:.3f}  policy {row['policy_mean']:.3f}  "
              f"recovery {row['graph_recovery_mean']:.3f} "
              f"[{row['recovery_ci'][0]:.3f}, {row['recovery_ci'][1]:.3f}]  "
              f"W/T/L {row['wins']}/{row['ties']}/{row['losses']}")


if __name__ == "__main__":
    main()
