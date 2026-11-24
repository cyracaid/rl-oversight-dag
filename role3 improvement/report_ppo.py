"""Turn the PPO evaluation into the pre-registered verdict.

The verdict rules are fixed in ``PREREGISTER_PPO.md``:

| outcome | verdict |
|---|---|
| every seed positive and separated | ``third-loss`` |
| every seed's interval contains zero | ``tie`` |
| every seed negative and separated | ``learned-wins`` |
| the sign flips across seeds | ``unstable`` |

A mixed picture (some separated, some not, same sign) is ``mixed`` and is
reported as cells only, which the pre-registration allows but does not name.
``P2`` is checked against the REINFORCE deltas from ``outputs/v3-learned``,
read from that file rather than typed in here.
"""
import argparse
import csv
import json
from pathlib import Path

SPIKE_GNN = "spike"


def verdict(rows):
    """Rows are dicts with delta_vs_marginal, ci_low, ci_high."""
    signs = {row["delta_vs_marginal"] > 0 for row in rows}
    if len(signs) > 1:
        return "unstable"
    separated = [row["ci_low"] > 0 or row["ci_high"] < 0 for row in rows]
    positive = rows[0]["delta_vs_marginal"] > 0
    if all(separated) and positive:
        return "third-loss"
    if all(separated) and not positive:
        return "learned-wins"
    if not any(separated):
        return "tie"
    return "mixed"


def p2_check(rows, reference):
    """P2: PPO sits between marginal and the REINFORCE GNN it was meant to beat.

    The preregistered bound is the REINFORCE mean delta vs marginal, quoted as
    ``(0, +0.403)``. It is a mean, so it is compared against the PPO mean; the
    per-seed spread is reported separately because three seeds are not a
    distribution to test against.
    """
    bound = sum(r["delta"] for r in reference) / len(reference)
    observed = sum(row["delta_vs_marginal"] for row in rows) / len(rows)
    inside = all(0 < row["delta_vs_marginal"] < bound for row in rows)
    return {"bound": bound, "observed_mean": observed,
            "all_seeds_inside": inside,
            "mean_inside": 0 < observed < bound}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("outputs/ppo-v1"))
    ap.add_argument("--reference",
                    type=Path,
                    default=Path("outputs/v3-learned/learned_vs_marginal.json"))
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.out / "ppo_summary.csv")))
    for row in rows:
        for key in ("mean_sink_errors", "marginal_mean", "delta_vs_marginal",
                    "ci_low", "ci_high"):
            row[key] = float(row[key])
        row["separated"] = row["ci_low"] > 0 or row["ci_high"] < 0
    reference = [r for r in json.loads(args.reference.read_text())
                 if r["family"] == SPIKE_GNN and r["learner"].startswith("gnn_s")]
    result = {"verdict": verdict(rows), "p2": p2_check(rows, reference),
              "reference_deltas": {r["learner"]: r["delta"] for r in reference},
              "cells": rows}
    (args.out / "verdict.json").write_text(json.dumps(result, indent=2))
    (args.out / "ppo_vs_marginal.md").write_text(render(result))
    print(result["verdict"], result["p2"])


def render(result):
    rows = result["cells"]
    lines = [
        "# PPO vs marginal on spike, fresh block 4200-4399",
        "",
        "Pre-registration: `PREREGISTER_PPO.md`. Verdict code: "
        "`report_ppo.py`; the rules were fixed before the trainer existed.",
        "",
        "Paired over 200 graphs, episode seed 20000 + graph seed, budget 16.",
        "Delta is PPO minus `marginal`, so positive means the learner is worse.",
        "",
        "| seed | PPO | marginal | delta | 95% CI | W/T/L |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['policy']} | {row['mean_sink_errors']:.3f} | "
            f"{row['marginal_mean']:.3f} | {row['delta_vs_marginal']:+.3f} | "
            f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}] | "
            f"{row['wins']}/{row['ties']}/{row['losses']} |")
    p2 = result["p2"]
    lines += [
        "",
        f"**Verdict: `{result['verdict']}`.**",
        "",
        f"P2 (PPO between marginal and the REINFORCE GNN, bound "
        f"{p2['bound']:+.3f}): observed mean delta {p2['observed_mean']:+.3f}, "
        f"every seed inside the bound: {p2['all_seeds_inside']}.",
        "",
        "Absolute means are not comparable with `outputs/v3/`: different graph",
        "seed block. Only the paired deltas travel.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
