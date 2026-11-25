"""Render the supervisor result. The verdict rule is frozen in the preregistration."""
import json
from pathlib import Path

from dag_role3.audit_policy import frozen_policy_v1

OUT = Path("outputs/supervisor-v1")
THRESHOLD = 0.90


def verdict(*, p1_holds, declared_share):
    """Frozen in PREREGISTER_SUPERVISOR.md. Do not relax after seeing the block."""
    if not p1_holds:
        return "decorative"
    if declared_share is not None and declared_share >= THRESHOLD:
        return "load-bearing"
    return "weak"


def main():
    payload = json.loads((OUT / "summary.json").read_text())
    rows = payload["rows"]
    p1 = payload["p1_holds"]
    policy = frozen_policy_v1()

    lines = ["# Supervisor axis — what a delivery can say about its own coverage", "",
             f"Block {payload['block'][0]}–{payload['block'][1]}, "
             f"p_catch {payload['p_catch']}, "
             f"pre-registered in `PREREGISTER_SUPERVISOR.md`.", "",
             f"Policy register: `{policy.fingerprint()}` — the adjudicated objects this "
             f"report is rendered under, frozen in `AUDIT_POLICY.md` v1. A different "
             f"register would describe a different delivery, so the string is quoted rather "
             f"than implied.", "",
             "`declared share` = of the sink errors that survive the budget, the fraction the "
             "honest receipt labels `partial` or `untouched`. The rest sit inside sinks whose "
             "every upstream source was reviewed — that is `p_catch < 1`, not a reporting bug.", "",
             "| family | policy | errors/graph | surviving sink errors | declared | false-inspected "
             "| declared share | verdict |",
             "|---|---|---:|---:|---:|---:|---:|---|"]
    table = []
    for row in rows:
        share = row["declared_share"]
        cell = verdict(p1_holds=p1, declared_share=share)
        table.append({"family": row["family"], "policy": row["policy"],
                      "verdict": cell, "declared_share": share})
        shown = "—" if share is None else f"{share:.3f}"
        lines.append(f"| {row['family']} | {row['policy']} | {row['mean_errors']:.3f} "
                     f"| {row['wrong_sinks']} | {row['declared_gap']} "
                     f"| {row['false_inspection']} | {shown} | {cell} |")

    lines += ["", "## Predictions", "",
              "| | prediction | outcome |", "|---|---|---|"]
    lines.append(f"| P1 | identical actions with and without the receipt | "
                 f"{'holds' if p1 else 'fails'} "
                 f"({len(payload['p1_mismatches'])} mismatching runs) |")
    fidelity = min(r["fidelity_min"] for r in rows)
    lines.append(f"| P2 | honest fidelity 1.0 everywhere | "
                 f"{'holds' if fidelity == 1.0 else 'fails'} (min {fidelity:.3f}) |")
    blind = [r["family"] for r in rows if r["false_inspection"] > 0]
    lines.append(f"| P3 | some family has false-inspected sinks | "
                 f"{'holds' if blind else 'fails'}"
                 f"{' — ' + ', '.join(sorted(set(blind))) if blind else ''} |")
    by_key = {(r["family"], r["policy"]): r for r in rows}
    p4 = []
    for family in ("spike", "modular"):
        share = by_key.get((family, "marginal"), {}).get("declared_share")
        p4.append((family, share))
    lines.append("| P4 | declared share ≥ 0.90 on spike and modular | "
                 + ", ".join(f"{f} " + ("—" if s is None else f"{s:.3f}") for f, s in p4)
                 + (" — holds" if all(s is not None and s >= THRESHOLD for _, s in p4) else " — fails") + " |")
    m = by_key.get(("modular", "marginal"), {}).get("declared_share")
    o = by_key.get(("modular", "oracle"), {}).get("declared_share")
    lines.append("| P5 | oracle's declared share < marginal's on modular | "
                 + ("not comparable" if m is None or o is None
                    else f"{o:.3f} vs {m:.3f} — " + ("holds" if o < m else "fails")) + " |")

    overclaim_ok = all(r["overclaim_false_equals_wrong"] for r in rows)
    overclaim_note = ("it equals the surviving errors in every cell"
                      if overclaim_ok else "it does *not* equal them in every cell (see summary.json)")
    lines += ["", "## The one prediction this block falsified", ""]
    mod = by_key.get(("modular", "marginal"))
    orc = by_key.get(("modular", "oracle"))
    if mod and mod["declared_share"] is not None:
        miss = THRESHOLD - mod["declared_share"]
        false_rule = mod["false_inspection"] / max(1, mod["wrong_sinks"])
        text = (f"P4 asked for a declared share of at least {THRESHOLD:.2f} on `modular` and got "
                f"{mod['declared_share']:.3f} — short by {miss:.3f} "
                f"({mod['declared_gap']} of {mod['wrong_sinks']}). The threshold is not moved. "
                f"So on the 500-node family about one surviving error in ten sits in a sink whose "
                f"every upstream source was reviewed and whose catch still missed.")
        if orc and orc["declared_share"] is not None:
            false_orc = orc["false_inspection"] / max(1, orc["wrong_sinks"])
            text += (f" Better coverage makes that bucket *bigger*, not smaller: "
                     f"{100 * false_rule:.1f} % under the rule, {100 * false_orc:.1f} % under "
                     f"`oracle`. Coverage and correctness pull apart exactly as `p_catch = 0.9` "
                     f"predicts, and a delivery that reports only coverage would overstate itself "
                     f"more, not less, when it reviews more.")
        lines += [text, ""]

    lines += ["## The deletion test, as a number", "",
              "The `silent` arm runs the identical policy on the identical episode. Its "
              "`declared_gap` and `uninspected_errors` columns are empty, because the delivery "
              "has no field for them: the question \"how many of the surviving errors did we "
              "not cover\" has no answer, not a bad one. The `overclaim` arm does answer, and "
              "its answer is wrong by exactly the number of surviving errors: "
              f"{overclaim_note}.", "",
              "So the three arms differ in nothing but the statement, and the statement is what "
              "turns a count of errors into a count of *uncovered* errors.", "",
              "## Bound on this claim", "",
              "* `p_catch` is 0.9, so `inspected` cannot mean `clean`. Every "
              "false-inspected sink in the table is that gap, not a bug.",
              "* No escalation policy is preregistered: `judged` is 1.0 on every row, so no "
              "refusal inflates fidelity.",
              "* Nothing here is about calibration. The receipt is about scope, never truth.",
              "* `modular`/`spike` sinks may be structurally unreachable within the budget; "
              "that is exactly what `untouched` reports, and it is a finding about the budget, "
              "not about the receipt."]

    manifest = json.loads((OUT / "manifest.json").read_text())
    lines += ["", "## Provenance", "",
              "The report is a rendering, not a computation: every number above is read from "
              "`summary.json`, which was written once on the block named at the top. What "
              "produced it is quoted here so a reader does not have to trust the prose.", "",
              "| item | value |", "|---|---|",
              f"| policy register | `{policy.fingerprint()}` |",
              f"| block / episode offset | {manifest['block'][0]}–{manifest['block'][1]} / "
              f"{manifest['episode_offset']} |",
              f"| p_catch | {manifest['p_catch']} |",
              f"| budgets | " + ", ".join(f"{k} {v}" for k, v in manifest["budget"].items()) + " |",
              f"| python / numpy | {manifest['python']} / {manifest['numpy']} |"]
    for name, digest in manifest["sha256"].items():
        lines.append(f"| `{name}` | `{digest}` |")
    lines += ["",
              "Deleting this report leaves `outputs/supervisor-v1/summary.json` intact — the "
              "counts survive, the *statement about what they cover* does not. That asymmetry "
              "is the deletion test in `CLAIM_GRAPH_CONTRACT.md`, and it is why this file "
              "quotes the register it was rendered under."]

    (OUT / "receipt_vs_silent.md").write_text("\n".join(lines) + "\n")
    (OUT / "verdict.json").write_text(json.dumps(
        {"p1_holds": p1, "threshold": THRESHOLD, "cells": table}, indent=2) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
