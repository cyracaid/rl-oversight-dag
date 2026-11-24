"""Turn the p_catch sweep into a verdict.

The verdict logic below is fixed by ``PREREGISTER_P_CATCH.md`` and was written
before the sweep ran, so the labels are not chosen after seeing the numbers.
Only the ``spike`` cells enter the verdict; ``real`` is reported descriptively.
"""
import argparse
import json
from pathlib import Path

import numpy as np

PRIMARY = "marginal"
REFERENCE = "confidence"
ORDER = (0.60, 0.75, 0.90, 1.00)


def load(path):
    import csv
    with open(path, newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ("p_catch", "mean_sink_errors", "gain_vs_confidence",
                    "paired_lo", "paired_hi", "zero_error_rate"):
            row[key] = float(row[key]) if row[key] not in ("", None) else None
        for key in ("n_episodes", "wins", "ties", "losses"):
            row[key] = int(row[key])
    return rows


def cell(rows, family, policy, p_catch):
    match = [r for r in rows if r["family"] == family
             and r["policy"] == policy and abs(r["p_catch"] - p_catch) < 1e-9]
    if len(match) != 1:
        raise SystemExit(f"expected exactly one cell for {family}/{policy}/{p_catch}, "
                         f"found {len(match)}")
    return match[0]


def verdict(rows, family="spike"):
    grid = sorted({r["p_catch"] for r in rows if r["family"] == family})
    gains = {p: cell(rows, family, PRIMARY, p) for p in grid}
    # P1: the sign holds on every cell, and at least three intervals exclude zero.
    p1_sign = all(gains[p]["gain_vs_confidence"] > 0 for p in grid)
    p1_separated = sum(gains[p]["paired_lo"] is not None
                       and gains[p]["paired_lo"] > 0 for p in grid) >= 3
    p1 = p1_sign and p1_separated
    # P2: advantage shrinks as the hit rate rises (monotone non-increasing).
    values = [gains[p]["gain_vs_confidence"] for p in grid]
    p2 = all(a > b for a, b in zip(values, values[1:]))
    inverted = all(a < b for a, b in zip(values, values[1:]))
    # P4: any cell where the reference wins with an interval that excludes zero.
    p4 = any(gains[p]["paired_hi"] is not None and gains[p]["paired_hi"] < 0
             for p in grid)
    if p4 or not p1:
        label = "conditional"
    elif p2:
        label = "robust"
    elif inverted:
        label = "inverted"
    else:
        label = "direction-robust"
    return {"label": label, "p1_sign": p1_sign, "p1_separated": p1_separated,
            "p1": p1, "p2_monotone": p2, "p2_inverted": inverted, "p4": p4,
            "grid": grid,
            "gains": {str(p): gains[p]["gain_vs_confidence"] for p in grid}}


LABEL_TEXT = {
    "robust": "Direction holds on every cell and the advantage shrinks as the hit "
              "rate rises. The main conclusion may be described as robust to the "
              "hit rate, with the trend reported as supporting evidence.",
    "direction-robust": "The direction holds on every cell but the advantage is not "
                        "monotone in the hit rate. Report the direction only; do not "
                        "claim or explain a trend.",
    "conditional": "The direction does not hold on every cell. The main conclusion "
                   "must be restated as conditional on the hit rate, and "
                   "BENCHMARK_SPEC.md section 6 has to report the failing cell "
                   "beside the rule.",
    "inverted": "The advantage grows as the hit rate rises, opposite to the "
                "prediction. Report the reversal as a finding and leave the "
                "direction of the main conclusion unchanged.",
}


def table(rows, family, policies):
    lines = ["| policy | " + " | ".join(f"p={p:.2f}" for p in ORDER) + " |",
             "|---|" + "---:|" * len(ORDER)]
    for name in policies:
        cells = []
        for p in ORDER:
            match = [r for r in rows if r["family"] == family
                     and r["policy"] == name and abs(r["p_catch"] - p) < 1e-9]
            cells.append(f"{match[0]['mean_sink_errors']:.3f}" if match else "—")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def gap_table(rows, family, policies):
    lines = ["| policy | " + " | ".join(f"p={p:.2f}" for p in ORDER) + " |",
             "|---|" + "---:|" * len(ORDER)]
    for name in policies:
        cells = []
        for p in ORDER:
            match = [r for r in rows if r["family"] == family
                     and r["policy"] == name and abs(r["p_catch"] - p) < 1e-9]
            if not match:
                cells.append("—")
                continue
            row = match[0]
            cells.append(f"{row['gain_vs_confidence']:+.3f} "
                         f"[{row['paired_lo']:+.3f}, {row['paired_hi']:+.3f}]")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=Path("outputs/p-catch-v1"))
    args = ap.parse_args()
    summary = load(args.dir / "p_catch_summary.csv")
    families = sorted({r["family"] for r in summary})
    spike_policies = ["confidence", PRIMARY, "oracle"]
    learned = sorted({r["policy"] for r in summary
                      if r["family"] == "spike" and r["policy"].startswith("gnn")})
    result = verdict(summary)
    (args.dir / "verdict.json").write_text(json.dumps(result, indent=2))

    lines = [
        "# Reviewer hit rate: `p_catch` sensitivity",
        "",
        "Pre-registered in `PREREGISTER_P_CATCH.md` before the sweep ran; the",
        "verdict code in `report_p_catch.py` was frozen at the same commit.",
        "Graph seeds 4000-4199, paired cells, 200 episodes per cell.",
        "",
        f"**Verdict: `{result['label']}`**", "",
        LABEL_TEXT[result["label"]], "",
        "| test | result |", "|---|---|",
        f"| P1 sign holds on all {len(result['grid'])} spike cells | "
        f"{result['p1_sign']} |",
        f"| P1 at least 3 intervals exclude zero | {result['p1_separated']} |",
        f"| P2 advantage monotone non-increasing in the hit rate | "
        f"{result['p2_monotone']} |",
        f"| P2 reversed | {result['p2_inverted']} |",
        f"| P4 any cell where confidence wins with an interval excluding zero | "
        f"{result['p4']} |",
        "",
        "## Spike: mean remaining conclusion errors", "",
        table(summary, "spike", spike_policies), "",
        "## Spike: learned policies (evaluated out of distribution)", "",
        "Checkpoints were trained at `p_catch = 0.9` and are not retrained, so the",
        "question these rows answer is what a deployed policy does when the true hit",
        "rate differs from the assumed one.", "",
        table(summary, "spike", learned) if learned else "_no learned checkpoints found_",
        "",
        "## Spike: paired difference against `confidence`", "",
        "Positive means fewer remaining errors than `confidence`. Brackets are paired",
        "95% intervals over 200 episodes.", "",
        gap_table(summary, "spike", spike_policies + learned), "",
    ]
    for family in families:
        if family == "spike":
            continue
        found = sorted({r["policy"] for r in summary if r["family"] == family})
        lines += [f"## {family}: descriptive only", "",
                  f"The {family} cells are reported for completeness and do not enter",
                  "the verdict, which the preregistration fixed to `spike`.", "",
                  table(summary, family, found), ""]
    lines += [
        "## What this does not show", "",
        "- It does not show that a learned policy can adapt to a different hit rate;",
        "  no retraining happened, by design.",
        "- It does not license comparing absolute means with `outputs/v3/`; the graph",
        "  seed block is different and only paired differences transfer.",
        "- It does not put a bound on the case where the reviewer is adversarial rather",
        "  than merely less reliable; that is a different model.",
        "",
    ]
    (args.dir / "report.md").write_text("\n".join(lines))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
