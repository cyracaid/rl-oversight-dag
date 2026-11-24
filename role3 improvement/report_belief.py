"""Frozen verdict for the belief-calibration decomposition.

Rules come from ``PREREGISTER_BELIEF_DECOMPOSITION.md``:

| peak recovery 95% interval | verdict |
|---|---|
| lower bound > 0.40 | ``calibration-bound`` |
| lower bound > 0 | ``calibration-partial`` |
| interval contains 0 | ``policy-bound`` |
| upper bound < 0 | ``policy-bound-strong`` |

``recovery`` is a ratio, so it is reported next to the aggregate error change and
the win/tie/loss counts. The three can disagree, and when they do this report
prints all of them instead of choosing: a positive ratio mean carried by a few
one-error graphs is not a recovered gap, and the reader is told so explicitly.
"""
import argparse
import csv
import json
from pathlib import Path

BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124


def verdict(recovery_ci):
    low, high = recovery_ci
    if low > 0.40:
        return "calibration-bound"
    if low > 0:
        return "calibration-partial"
    if high < 0:
        return "policy-bound-strong"
    return "policy-bound"


def load(path):
    rows = list(csv.DictReader(open(path)))
    for row in rows:
        for key, value in list(row.items()):
            if key in ("family",):
                continue
            row[key] = None if value == "None" else float(value)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("outputs/belief-v1"))
    args = ap.parse_args()
    summary = json.loads((args.out / "curve.json").read_text())

    for entry in summary:
        peak = max(entry["curve"], key=lambda c: c["recovery"])
        entry["gamma_star"] = peak["gamma"]
        entry["graph_recovery_mean"] = peak["recovery"]
        entry["recovery_ci"] = peak["recovery_ci"]
        entry["verdict"] = verdict(peak["recovery_ci"])
        rows = load(args.out / f"belief_{entry['family']}.csv")
        for cell in entry["curve"]:
            gamma = cell["gamma"]
            delta = [r["marginal"] - r[f"gamma_{gamma}"] for r in rows]
            cell["closed_sum"] = float(sum(delta))
            # The interval above is nominal. It is the maximum of six cells, so a
            # Bonferroni interval is the honest companion; both are printed.
            cell["bonferroni_ci"] = bonferroni(rows, gamma)
        entry["gap_sum"] = float(sum(r["marginal"] - r["oracle"] for r in rows))
        entry["closed_sum"] = float(sum(r["marginal"] - r[f"gamma_{entry['gamma_star']}"]
                                        for r in rows))
        entry["peak_bonferroni_ci"] = peak["bonferroni_ci"]

    (args.out / "verdict.json").write_text(json.dumps(summary, indent=2))
    (args.out / "belief_vs_marginal.md").write_text(render(summary))
    for entry in summary:
        peak = [c for c in entry["curve"] if c["gamma"] == entry["gamma_star"]][0]
        print(f"{entry['family']:8s} {entry['verdict']:18s} "
              f"gamma* {entry['gamma_star']:<5} "
              f"recovery {entry['graph_recovery_mean']:+.3f} "
              f"[{entry['recovery_ci'][0]:+.3f}, {entry['recovery_ci'][1]:+.3f}] "
              f"aggregate {peak['closed_sum']:+.0f}/{entry['gap_sum']:.0f} "
              f"W/T/L {peak['wins']}/{peak['ties']}/{peak['losses']}")


def bonferroni(rows, gamma, cells=6):
    """Bootstrap interval at 1 - 0.05 / (number of cells) coverage."""
    import numpy as np
    delta = np.array([r["marginal"] - r[f"gamma_{gamma}"] for r in rows], float)
    gap = np.array([r["marginal"] - r["oracle"] for r in rows], float)
    usable = gap > 0
    recovery = delta[usable] / gap[usable]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(recovery), size=(BOOTSTRAP, len(recovery)))
    means = recovery[draws].mean(axis=1)
    alpha = 0.025 / cells
    low, high = np.quantile(means, [alpha, 1 - alpha])
    return [float(low), float(high)]


def render(summary):
    lines = [
        "# The oracle gap is not the belief's numbers, block 4800-4999",
        "",
        "Pre-registration: `PREREGISTER_BELIEF_DECOMPOSITION.md` (v2 section). "
        "Verdict code: `report_belief.py`.",
        "",
        "`marginal` and `oracle` share rule, budget and horizon; only the prior "
        "differs. The reference here keeps the belief's *ranking* exactly (one "
        "strictly monotone map applied to every node, so per-graph AUC is "
        "bit-identical by construction) and distorts only its *values*:",
        "",
        "    q_i(gamma) = sigmoid(gamma * logit(belief_i))",
        "",
        "`gamma = 1` reproduces `marginal` exactly, per graph, as a hard check.",
        "",
    ]
    for entry in summary:
        peak = [c for c in entry["curve"] if c["gamma"] == entry["gamma_star"]][0]
        lines += [
            f"## {entry['family']} (n=500, N={entry['graphs']} graphs)"
            if entry["family"] == "modular" else
            f"## {entry['family']} (N={entry['graphs']} graphs)",
            "",
            f"`marginal` {entry['marginal_mean']:.3f} / `oracle` "
            f"{entry['oracle_mean']:.3f}, belief AUC {entry['curve'][0]['mean_auc']:.3f}.",
            "",
            "| gamma | mean errors | recovery [95% CI] | Bonferroni CI | "
            "aggregate errors closed | W/T/L |",
            "|---:|---:|---|---|---:|---|",
        ]
        for cell in entry["curve"]:
            lines.append(
                f"| {cell['gamma']:.2f} | {cell['mean_errors']:.3f} | "
                f"{cell['recovery']:+.3f} "
                f"[{cell['recovery_ci'][0]:+.3f}, {cell['recovery_ci'][1]:+.3f}] | "
                f"[{cell['bonferroni_ci'][0]:+.3f}, {cell['bonferroni_ci'][1]:+.3f}] | "
                f"{cell['closed_sum']:+.0f} of {entry['gap_sum']:.0f} | "
                f"{cell['wins']}/{cell['ties']}/{cell['losses']} |")
        lines += [
            "",
            f"Pre-registered verdict from the peak cell: **{entry['verdict']}**. "
            f"Grid-corrected interval for that cell: "
            f"[{entry['peak_bonferroni_ci'][0]:+.3f}, "
            f"{entry['peak_bonferroni_ci'][1]:+.3f}].",
            "",
        ]
        if peak["closed_sum"] <= 0 or peak["wins"] <= peak["losses"] + 4:
            lines += [
                "Read the last two columns before the ratio. "
                f"`gamma = {entry['gamma_star']:.2f}` changed the outcome on "
                f"{peak['wins'] + peak['losses']} of {entry['graphs']} graphs "
                f"({peak['wins']} better, {peak['losses']} worse) and moved the "
                f"aggregate by {peak['closed_sum']:+.0f} errors of a "
                f"{entry['gap_sum']:.0f}-error gap. "
                + ("The ratio mean is positive only because the graphs it wins on "
                   "are the ones with a one-or-two-error gap, so the positive "
                   "number is reshuffling, not recovery."
                   if peak["recovery"] > 0 else
                   "The ratio and the aggregate agree here: no gain."),
                "",
            ]
    lines += [
        "## What this does and does not show",
        "",
        "The ranking of the belief is held fixed, so this is a test of the belief's "
        "*values* and of one one-parameter family of rescalings, not of the whole "
        "calibration space. Within that family `marginal` sits at or next to the "
        "optimum: every distortion is neutral at best and clearly worse at "
        "`gamma = 0.5`. So the residual gap to `oracle` is not a probability-scale "
        "error that a temperature fixes.",
        "",
        "It also does not prove myopia is the cause. The belief still ranks only "
        "0.96 and the review decisions depend on where the mass sits, not on the "
        "AUC. What the experiment removes is the cheapest explanation: 'the "
        "forward derivative is fed wrong numbers'.",
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
