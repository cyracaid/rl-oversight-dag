"""Frozen verdict for the sampled counterfactual value experiment.

Rules come from ``PREREGISTER_EXACT_VALUE.md``:

| recovery 95% interval | verdict |
|---|---|
| lower bound > 0.40 | ``strong`` |
| lower bound > 0 | ``partial`` |
| interval contains 0 | ``null`` |
| upper bound < 0 | ``worse`` |

The interval belongs to the per-graph recovery mean, which is the quantity the
pre-registration named. The aggregate gap-closed share is reported next to it
because the two can disagree: a policy can close a large share of the total gap
while losing on most individual graphs.
"""
import argparse
import csv
import json
from pathlib import Path


def verdict(recovery_ci):
    low, high = recovery_ci
    if low > 0.40:
        return "strong"
    if low > 0:
        return "partial"
    if high < 0:
        return "worse"
    return "null"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("outputs/value-v1"))
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.out / "value_summary.csv")))
    for row in rows:
        low, high = row["recovery_ci"].strip("[]").split(",")
        row["recovery_ci"] = [float(low), float(high)]
        row["verdict"] = verdict(row["recovery_ci"])
        for key in ("marginal_mean", "oracle_mean", "policy_mean", "gap_mean",
                    "graph_recovery_mean", "gap_closed_share_aggregate",
                    "gap_sum", "closed_sum"):
            row[key] = float(row[key])
        for key in ("graphs", "graphs_with_gap", "wins", "ties", "losses",
                    "oracle_ties"):
            row[key] = int(row[key])
    (args.out / "verdict.json").write_text(json.dumps(rows, indent=2))
    (args.out / "value_vs_marginal.md").write_text(render(rows))
    for row in rows:
        print(f"{row['family']:8s} {row['verdict']:8s} "
              f"recovery {row['graph_recovery_mean']:+.3f} "
              f"[{row['recovery_ci'][0]:+.3f}, {row['recovery_ci'][1]:+.3f}]")


def render(rows):
    lines = [
        "# Sampled counterfactual value vs mean-field, block 4400-4599",
        "",
        "Pre-registration: `PREREGISTER_EXACT_VALUE.md`. Verdict code: "
        "`report_value.py`.",
        "",
        "`recovery = (marginal - policy) / (marginal - oracle)` per graph, then",
        "averaged; 1.0 would mean the policy equals the truth-reading reference.",
        "",
        "| family | marginal | oracle | policy | recovery [95% CI] | "
        "aggregate gap closed | W/T/L | verdict |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ]
    for row in rows:
        low, high = row["recovery_ci"]
        lines.append(
            f"| {row['family']} | {row['marginal_mean']:.3f} | "
            f"{row['oracle_mean']:.3f} | {row['policy_mean']:.3f} | "
            f"{row['graph_recovery_mean']:+.3f} [{low:+.3f}, {high:+.3f}] | "
            f"{row['gap_closed_share_aggregate']:+.1%} | "
            f"{row['wins']}/{row['ties']}/{row['losses']} | {row['verdict']} |")
    lines += [
        "",
        "Graphs where `marginal` and `oracle` coincide have no gap to divide by;",
        "they are excluded from the recovery mean and counted here: "
        + ", ".join(f"{r['family']} {r['oracle_ties']}/{r['graphs']}"
                    for r in rows) + ".",
        "",
        "Read the tie column before the means. On `modular` the policy changed the",
        "action on " + str(rows[[r["family"] for r in rows].index("modular")]["wins"]
                          + rows[[r["family"] for r in rows].index("modular")]["losses"])
        + " of 200 graphs and lost more often than it won, so this is not a case of",
        "the estimator being too noisy to move: it moved, and the mean-field",
        "ordering was already the better one at this horizon.",
        "",
        "",
    ]
    disagree = [r for r in rows
                if (r["graph_recovery_mean"] > 0) != (r["gap_closed_share_aggregate"] > 0)]
    if disagree:
        lines += [
            "Where the two columns disagree, say so rather than picking one:",
            "",
        ]
        for row in disagree:
            lines.append(
                f"- `{row['family']}`: ratio mean {row['graph_recovery_mean']:+.3f} but "
                f"aggregate {row['gap_closed_share_aggregate']:+.1%}. The ratio mean is "
                f"carried by graphs with a gap of one or two errors; across all graphs "
                f"the policy closed {row['closed_sum']:+.0f} of a {row['gap_sum']:.0f}-error "
                "total gap.")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
