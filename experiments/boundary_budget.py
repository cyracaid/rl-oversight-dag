#!/usr/bin/env python3
"""On the real 21-node sleep topology, where does the budget start to matter?

The synthetic phase sweep (`boundary_phase.py`) varies graph shape at a fixed
budget fraction. This one holds the *real* structure fixed (the sleep evidence
DAG) and varies only the review budget, which is the thing we actually control
in the deployment.

Why it is worth doing: the repo has two results on this topology that look
contradictory.
    full-v1, budget 16 / 21 nodes : marginal 1.020 vs confidence 1.440  (win)
    ticket/real, budget 8 / 21    : marginal -0.01 vs confidence        (tie)
18 is not a big difference in absolute reviews, but 8 vs 16 out of 21 is 38% vs
76% of the graph. If the gain is a function of budget fraction, both are
consistent — and the curve says where the crossover is.

Outcome: residual sink errors after the budget (lower is better), plus the
caught fraction `(none - policy) / none`. Graph structure is fixed, so the
resampling unit here is the error realization, not the graph. That is stated in
the output because it makes these intervals narrower than a cross-graph claim
would be.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "role3 improvement"))

from dag_role3 import generate_graph, sample_episode           # noqa: E402
from dag_role3.policies import run_public_policy              # noqa: E402

POLICIES = ("random", "hub", "confidence", "structural", "type_prior", "marginal")
BUDGETS = (2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", default="real", choices=("real", "ticket"))
    ap.add_argument("--budgets", nargs="+", type=int, default=list(BUDGETS))
    ap.add_argument("--draws", type=int, default=400)
    ap.add_argument("--start-seed", type=int, default=90000)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent / "results" / "budget-curve-v1")
    args = ap.parse_args()
    if args.start_seed < 90000:
        ap.error("use held-out seeds >= 90000")

    graph = generate_graph(args.family, 1)
    n = graph.n
    args.out.mkdir(parents=True, exist_ok=True)
    rows, summary = [], []
    t0 = time.time()

    for budget in args.budgets:
        if budget > n:
            continue
        residual: dict[str, list[float]] = {p: [] for p in POLICIES}
        caught: dict[str, list[float]] = {p: [] for p in POLICIES}
        dropped = 0
        for d in range(args.draws):
            seed = args.start_seed + d
            # Same episode-seed convention as role3 improvement/run_benchmark.py, so the
            # budget-8 row of this curve is the published real/ticket row, not a rerun.
            snap = sample_episode(graph, 20000 + seed)
            base = float(run_public_policy(graph, snap, "none", budget)[0])
            for p in POLICIES:
                e = float(run_public_policy(graph, snap, p, budget)[0])
                # Residual is defined for every realization: if the no-review error
                # count is 0 the residual is 0 too. Only the *caught fraction* needs a
                # positive denominator, so only that column is filtered — and the
                # number of filtered draws is reported next to it.
                residual[p].append(e)
                if base > 0:
                    caught[p].append((base - e) / base)
            if base <= 0:
                dropped += 1
        kept = len(caught["marginal"])
        for p in POLICIES:
            rows.append({"family": args.family, "n": n, "budget": budget,
                         "budget_frac": budget / n, "policy": p,
                         "draws": kept, "dropped_no_errors": dropped,
                         "mean_residual": float(np.mean(residual[p])),
                         "mean_caught": float(np.mean(caught[p]))})
        d_conv = np.array(caught["marginal"]) - np.array(caught["confidence"])
        rng = np.random.default_rng(7)
        boot = d_conv[rng.integers(0, len(d_conv), size=(args.reps, len(d_conv)))].mean(axis=1)
        summary.append({
            "family": args.family, "n": n, "budget": budget,
            "budget_frac": budget / n, "draws": kept, "dropped_no_errors": dropped,
            "none_residual": float(np.mean([r for r in residual["confidence"]])),
            "confidence_residual": float(np.mean(residual["confidence"])),
            "marginal_residual": float(np.mean(residual["marginal"])),
            "type_prior_residual": float(np.mean(residual["type_prior"])),
            "confidence": float(np.mean(caught["confidence"])),
            "marginal": float(np.mean(caught["marginal"])),
            "type_prior": float(np.mean(caught["type_prior"])),
            "delta_caught": float(d_conv.mean()),
            "lo": float(np.percentile(boot, 2.5)),
            "hi": float(np.percentile(boot, 97.5)),
            "win": float((d_conv > 1e-12).mean()),
            "tie": float((np.abs(d_conv) <= 1e-12).mean()),
            "loss": float((d_conv < -1e-12).mean()),
        })
        s = summary[-1]
        print(f"{args.family} K={budget:2d} ({budget/n:4.0%})  "
              f"residual conf={s['confidence_residual']:.3f} "
              f"marg={s['marginal_residual']:.3f} prior={s['type_prior_residual']:.3f}  "
              f"Δcaught={s['delta_caught']:+.3f} [{s['lo']:+.3f},{s['hi']:+.3f}]  "
              f"W/T/L={s['win']:.2f}/{s['tie']:.2f}/{s['loss']:.2f}  "
              f"({time.time()-t0:.0f}s)", flush=True)

    with (args.out / "curve.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with (args.out / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    (args.out / "manifest.json").write_text(json.dumps({
        "resampling_unit": "error realization (graph structure is fixed)",
        "family": args.family,
        "n": n,
        "draws": args.draws,
        "start_seed": args.start_seed,
        "p_catch": 0.9,
        "confidence_mode": "normal",
        "policies": list(POLICIES),
        "elapsed_s": round(time.time() - t0, 1),
    }, indent=2) + "\n")
    print(f"\nwrote {args.out}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
