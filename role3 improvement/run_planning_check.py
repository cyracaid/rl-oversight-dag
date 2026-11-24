"""Price the one-step horizon with a depth-two expectimax over the public belief.

Pre-registered in ``PREREGISTER_PLANNING_V2.md``: graph seeds 5200-5399, 200 per
family, width 6 then 4, hit rate 0.9, metric ``recovery = (marginal - policy) /
(marginal - oracle)`` per graph.

Two variants are run on every graph because the environment's miss update is
approximate: ``catch`` follows only the success branch, ``full`` weights both
branches the way ``OversightEnv.step`` does. If ``full`` beats ``catch`` the gain
comes from exploiting that update, not from planning, and the report says so.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.planning import Planner
from dag_role3.policies import run_public_policy

BLOCK = (5200, 5399)
EPISODE_OFFSET = 20000
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124
BUDGET = {"spike": 16, "modular": 50}
WIDTH, SECOND = 6, 4
P_CATCH = 0.9
VARIANTS = {"plan2_catch": ("catch",), "plan2_full": ("catch", "miss")}


def bootstrap(delta):
    delta = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(delta), size=(BOOTSTRAP, len(delta)))
    return tuple(float(x) for x in np.quantile(delta[draws].mean(axis=1),
                                               [0.025, 0.975]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=["modular", "spike"])
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--out", type=Path, default=Path("outputs/planning-v2"))
    args = ap.parse_args()
    if args.start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.start, args.end + 1))

    rows = []
    for family in args.families:
        budget = BUDGET[family]
        for graph_seed in seeds:
            graph = generate_graph(family, graph_seed)
            snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
            marginal, _ = run_public_policy(graph, snapshot, "marginal", budget,
                                            p_catch=P_CATCH)
            oracle, _ = run_public_policy(graph, snapshot, "oracle", budget,
                                          p_catch=P_CATCH)
            row = {"family": family, "graph_seed": graph_seed,
                   "marginal": marginal, "oracle": oracle}
            for name, branches in VARIANTS.items():
                planner = Planner(width=WIDTH, second=SECOND, p_catch=P_CATCH,
                                  branches=branches)
                errors, _ = run_public_policy(graph, snapshot, planner.act, budget,
                                              p_catch=P_CATCH)
                row[name] = errors
            rows.append(row)
            if graph_seed % 20 == 0:
                print(f"  {family} {graph_seed} done", flush=True)

        subset = [r for r in rows if r["family"] == family]
        with open(args.out / f"planning_{family}.csv", "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(subset[0]))
            writer.writeheader()
            writer.writerows(subset)

    summary = []
    for family in args.families:
        subset = [r for r in rows if r["family"] == family]
        gap = np.array([r["marginal"] - r["oracle"] for r in subset], float)
        usable = gap > 0
        entry = {"family": family, "graphs": len(subset),
                 "marginal_mean": float(np.mean([r["marginal"] for r in subset])),
                 "oracle_mean": float(np.mean([r["oracle"] for r in subset])),
                 "gap_mean": float(gap.mean()),
                 "graphs_with_gap": int(usable.sum()),
                 "gap_sum": float(gap.sum()),
                 "variants": []}
        for name in VARIANTS:
            delta = np.array([r["marginal"] - r[name] for r in subset], float)
            recovery = delta[usable] / gap[usable]
            low, high = bootstrap(recovery)
            entry["variants"].append({
                "policy": name,
                "mean_errors": float(np.mean([r[name] for r in subset])),
                "recovery": float(recovery.mean()),
                "recovery_ci": [low, high],
                "closed_sum": float(delta.sum()),
                "wins": int((delta > 0).sum()), "ties": int((delta == 0).sum()),
                "losses": int((delta < 0).sum()),
            })
        summary.append(entry)
        for variant in entry["variants"]:
            print(f"{family:8s} {variant['policy']:11s} "
                  f"{variant['mean_errors']:.3f} "
                  f"recovery {variant['recovery']:+.3f} "
                  f"[{variant['recovery_ci'][0]:+.3f}, "
                  f"{variant['recovery_ci'][1]:+.3f}] "
                  f"aggregate {variant['closed_sum']:+.0f}/{entry['gap_sum']:.0f} "
                  f"W/T/L {variant['wins']}/{variant['ties']}/{variant['losses']}",
                  flush=True)

    with open(args.out / "planning_summary.csv", "w", newline="") as stream:
        flat = [{k: v for k, v in s.items() if k != "variants"} for s in summary]
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    (args.out / "manifest.json").write_text(json.dumps({
        "block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
        "width": WIDTH, "second": SECOND, "p_catch": P_CATCH,
        "variants": {k: list(v) for k, v in VARIANTS.items()},
        "bootstrap_draws": BOOTSTRAP, "bootstrap_seed": BOOTSTRAP_SEED,
        "budget": BUDGET,
    }, indent=2))
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
