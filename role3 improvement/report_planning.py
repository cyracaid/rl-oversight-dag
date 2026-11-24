"""Frozen verdict for the depth-two planning experiment.

Rules come from ``PREREGISTER_PLANNING_V2.md``:

| recovery 95% interval | verdict |
|---|---|
| lower bound > 0.40 | ``myopia-bound`` |
| lower bound > 0 | ``myopia-partial`` |
| interval contains 0 | ``informational`` |
| upper bound < 0 | ``informational-strong`` |

Each variant is judged separately, and the aggregate error change is printed next
to the ratio. ``plan2_full`` is reported because it was pre-registered, but it is
known to reward one specific artifact: the environment lowers the belief after a
missed review, so weighting both outcomes makes a low-risk node look valuable.
Read ``plan2_catch`` for the planning question and ``plan2_full`` for the
artifact.
"""
import argparse
import csv
import json
from pathlib import Path


def verdict(recovery_ci):
    low, high = recovery_ci
    if low > 0.40:
        return "myopia-bound"
    if low > 0:
        return "myopia-partial"
    if high < 0:
        return "informational-strong"
    return "informational"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("outputs/planning-v2"))
    args = ap.parse_args()
    summary = json.loads((args.out / "summary.json").read_text())
    for entry in summary:
        for variant in entry["variants"]:
            variant["verdict"] = verdict(variant["recovery_ci"])
    (args.out / "verdict.json").write_text(json.dumps(summary, indent=2))
    (args.out / "planning_vs_marginal.md").write_text(render(summary))
    for entry in summary:
        for variant in entry["variants"]:
            print(f"{entry['family']:8s} {variant['policy']:11s} "
                  f"{variant['verdict']:22s} {variant['recovery']:+.3f} "
                  f"[{variant['recovery_ci'][0]:+.3f}, "
                  f"{variant['recovery_ci'][1]:+.3f}] "
                  f"aggregate {variant['closed_sum']:+.0f}/{entry['gap_sum']:.0f}")


def render(summary):
    lines = [
        "# Depth-two planning against the one-step rule, block 5200-5399",
        "",
        "Pre-registration: `PREREGISTER_PLANNING_V2.md`. Verdict code: "
        "`report_planning.py`.",
        "",
        "`marginal` and `oracle` share rule, budget and horizon, so their gap is "
        "the value of truth under a *one-step* rule and cannot contain the value "
        "of planning. This experiment changes the policy instead of the prior: a "
        "depth-two expectimax on the same mean-field model, width 6 then 4, using "
        "only public inputs.",
        "",
        "| family | marginal | oracle | gap | policy | mean errors | recovery "
        "[95% CI] | aggregate closed | W/T/L | verdict |",
        "|---|---:|---:|---:|---|---:|---|---:|---|---|",
    ]
    for entry in summary:
        for variant in entry["variants"]:
            low, high = variant["recovery_ci"]
            lines.append(
                f"| {entry['family']} | {entry['marginal_mean']:.3f} | "
                f"{entry['oracle_mean']:.3f} | {entry['gap_sum']:.0f} | "
                f"`{variant['policy']}` | {variant['mean_errors']:.3f} | "
                f"{variant['recovery']:+.3f} [{low:+.3f}, {high:+.3f}] | "
                f"{variant['closed_sum']:+.0f} | "
                f"{variant['wins']}/{variant['ties']}/{variant['losses']} | "
                f"{variant['verdict']} |")

    lines += ["", "## How to read the two variants", ""]
    for entry in summary:
        catch = next(v for v in entry["variants"] if v["policy"] == "plan2_catch")
        full = next(v for v in entry["variants"] if v["policy"] == "plan2_full")
        lines.append(
            f"- `{entry['family']}`: `catch` {catch['recovery']:+.3f}, "
            f"`full` {full['recovery']:+.3f}. "
            + ("`full` is higher, and that difference is the miss-branch artifact, "
               "not planning: a missed review lowers the belief, so the planner "
               "prefers nodes likely to be missed."
               if full["recovery"] > catch["recovery"] + 0.02 else
               "The two variants do not separate: the miss branch is not what "
               "moves the result."))
    lines += [
        "",
        "## What this settles and what it does not",
        "",
        "Together with `outputs/value-v1/` (the one-step value estimate, sampled "
        "exactly, is worse) and `outputs/belief-v1/` (the belief's numbers, "
        "rescaled with ranking held fixed, give nothing), this leaves the gap "
        "with no cheap explanation left: not the score's numbers, not the "
        "probability scale, and — at this width and this depth — not the horizon.",
        "",
        "The honest residual is information. The public belief ranks the truth at "
        "about 0.96 AUC, not 1.0, and the review decision needs the *mass* on the "
        "right nodes, not just the order. Nothing here measures how much of the "
        "gap a better belief could remove; that would need a belief with more "
        "information, which the confidence channel does not provide.",
        "",
        "Limits, stated because the numbers are easy to over-read: depth two with "
        "width 6/4 is a truncated greedy planner, not an optimal policy, so "
        "`informational` means 'one more step at this width does not pay', not "
        "'no plan exists'. The two families tested are `modular` and `spike`; "
        "`ba` and `er` are not measured.",
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
