#!/usr/bin/env python3
"""Put the three published family results on one axis: budget fraction.

The published table reports residual sink errors per family at a fixed budget.
That makes the families look like three separate findings (spike wins, real ties,
ticket ties). They share one axis we never plotted: how much of the graph the
budget covers.

    family   budget   n    budget/n
    spike    16       80   20%
    real      8       21   38%
    ticket    8       21   38%

This script converts the published residuals to the fraction of no-review errors
that each policy removed, so the three points become comparable:

    caught = (none - policy) / none

Input is the committed summary CSV; nothing is re-run, so this cannot drift away
from the published numbers.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE.parent / "role3 improvement" / "outputs" / "v3-baselines" / "benchmark_summary.csv"
# Budgets are fixed in role3 improvement/run_benchmark.py.
BUDGETS = {"spike": 16, "real": 8, "ticket": 8}
NODES = {"spike": 80, "real": 21, "ticket": 21}


def main() -> None:
    with SUMMARY.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    by = {(r["family"], r["policy"]): float(r["mean_sink_errors"]) for r in rows}

    out = []
    for family, budget in BUDGETS.items():
        none = by[(family, "none")]
        conf = by[(family, "confidence")]
        marg = by[(family, "marginal")]
        prior = by[(family, "type_prior")]
        out.append({
            "family": family,
            "n": NODES[family],
            "budget": budget,
            "budget_frac": budget / NODES[family],
            "none_residual": none,
            "confidence_residual": conf,
            "marginal_residual": marg,
            "type_prior_residual": prior,
            "caught_confidence": (none - conf) / none,
            "caught_marginal": (none - marg) / none,
            "delta_caught": (conf - marg) / none,
        })

    print("| family | n | budget | budget/n | `none` residual | `confidence` | `marginal` "
          "| caught conf | caught marg | Δ caught |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(out, key=lambda r: r["budget_frac"]):
        print(f"| {r['family']} | {r['n']} | {r['budget']} | {r['budget_frac']:.0%} "
              f"| {r['none_residual']:.2f} | {r['confidence_residual']:.2f} "
              f"| {r['marginal_residual']:.2f} | {r['caught_confidence']:.3f} "
              f"| {r['caught_marginal']:.3f} | {r['delta_caught']:+.3f} |")

    dest = HERE / "results" / "budget-axis-published.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"source": str(SUMMARY), "rows": out}, indent=2) + "\n")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
