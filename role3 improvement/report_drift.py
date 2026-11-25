"""Render the drift result. The verdict rule is frozen in PREREGISTER_DRIFT.md."""
import json
from pathlib import Path

OUT = Path("outputs/drift-v1")
NON_MODULAR = ("spike", "real", "ticket")
FAMILIES = ("spike", "modular", "real", "ticket")
BUCKETS = (("1–2", 1, 2), ("3–5", 3, 5), ("6–10", 6, 10), ("11+", 11, 10**6))


def verdict(*, p1_holds, p3_all, inert):
    """Frozen in PREREGISTER_DRIFT.md §4. Do not relax after seeing the block."""
    if inert:
        return "inert"
    if p1_holds and p3_all:
        return "load-bearing"
    if p3_all:
        return "weak"
    return "inert"


def holds(row):
    """An interval excludes zero in the predicted direction."""
    return row["lo"] > 0


def main():
    payload = json.loads((OUT / "summary.json").read_text())
    summary = {r["family"]: r for r in payload["summary"]}
    paired = {(r["family"], r["metric"]): r for r in payload["paired"]}
    depth_rows = payload["depth"]
    block = payload["block"]

    p1_n = sum(1 for f in NON_MODULAR if holds(paired[(f, "errors")]))
    p1 = p1_n >= 2
    p3_all = all(holds(paired[(f, "untouched")]) for f in FAMILIES)
    p4_n = sum(1 for f in FAMILIES if holds(paired[(f, "declared_gap")]))
    p4 = p4_n >= 3
    p2_all = all(
        summary[f]["closed"]["inspected"] <= 0.5 * summary[f]["open"]["inspected"]
        for f in FAMILIES
    )
    p5 = all(
        (summary[f]["closed"]["declared_share"] or 1.0) >= (summary[f]["open"]["declared_share"] or 1.0)
        for f in FAMILIES
    ) and all(
        (summary[f]["closed"]["declared_share"] or 1.0) > (summary[f]["open"]["declared_share"] or 1.0)
        for f in ("spike", "modular")
    )
    inert = all(summary[f]["closed"]["identical_actions"] == summary[f]["closed"]["graphs"]
                for f in FAMILIES)
    v = verdict(p1_holds=p1, p3_all=p3_all, inert=inert)

    lines = ["# The prohibited loop — drift, measured", "",
             f"Block {block[0]}–{block[1]}, p_catch {payload['p_catch']}, "
             f"policy `{payload['policy']}`, pre-registered in `PREREGISTER_DRIFT.md`.", "",
             f"**Verdict: `{v}`.** 100 graphs per family, paired, closed − open, "
             f"{payload['bootstrap']['draws']} bootstrap draws "
             f"(seed {payload['bootstrap']['seed']}).", "",
             "`closed` is the mapping `AUDIT_POLICY.md` v1 forbids: an unreviewed source feeding a "
             "`partial` sink is read as \"the reviewers found nothing here\", so its belief is multiplied "
             "by `1 − p_catch` once per decision, compounding. Nothing else differs between the arms.", "",
             "| family | errors open → closed | inspected | untouched | uncovered errors | "
             "false-inspected | declared share | actions changed |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]

    def cell(f, key):
        return f"{summary[f]['open'][key]} → {summary[f]['closed'][key]}"

    for f in FAMILIES:
        o, c = summary[f]["open"], summary[f]["closed"]
        share_o = "—" if o["declared_share"] is None else f"{o['declared_share']:.3f}"
        share_c = "—" if c["declared_share"] is None else f"{c['declared_share']:.3f}"
        lines.append(
            f"| {f} | {o['mean_errors']:.3f} → {c['mean_errors']:.3f} "
            f"| {o['inspected']} → {c['inspected']} "
            f"| {o['untouched']} → {c['untouched']} "
            f"| {o['declared_gap']} → {c['declared_gap']} "
            f"| {o['false_inspection']} → {c['false_inspection']} "
            f"| {share_o} → {share_c} "
            f"| {c['graphs'] - c['identical_actions']}/{c['graphs']} |"
        )

    lines += ["", "## Paired deltas", "",
              "| family | metric | closed − open | 95 % interval | wins / losses |",
              "|---|---|---:|---|---|"]
    for f in FAMILIES:
        for metric in ("errors", "untouched", "declared_gap", "false_inspection"):
            r = paired[(f, metric)]
            lines.append(f"| {f} | {metric} | {r['delta']:+.3f} "
                         f"| [{r['lo']:+.3f}, {r['hi']:+.3f}] | {r['wins']} / {r['losses']} |")

    def mark(ok):
        return "holds" if ok else "fails"

    lines += ["", "## Predictions", "",
              "| | prediction | outcome |", "|---|---|---|",
              f"| P1 | worse on ≥ 2 of sleep families (spike/real/ticket) | {mark(p1)} "
              f"({p1_n} of 3) |",
              f"| P2 | declared `inspected` at least halves everywhere | {mark(p2_all)} |",
              f"| P3 | `untouched` rises on all four | {mark(p3_all)} |",
              f"| P4 | uncovered errors rise on ≥ 3 of 4 | {mark(p4)} ({p4_n} of 4) |",
              f"| P5 | declared share ≥ open everywhere, strictly up on spike and modular | {mark(p5)} |"]
    if not p2_all:
        m_open = summary["modular"]["open"]["inspected"]
        m_closed = summary["modular"]["closed"]["inspected"]
        m_ratio = m_closed / max(1, m_open)
        lines += ["",
                  "P2 is the prediction that failed, and it failed in the direction worth naming: "
                  "declared `inspected` sinks more than halve on `spike`, `real` and `ticket` — to "
                  f"{summary['spike']['closed']['inspected']}, "
                  f"{summary['real']['closed']['inspected']} and "
                  f"{summary['ticket']['closed']['inspected']} — but only fall to "
                  f"{m_closed} of {m_open} on `modular` ({m_ratio:.2f}×, threshold 0.5×). With "
                  f"{m_open} inspected sinks before the loop, a 50 % cut is a different demand "
                  "than on a 7-sink family. The threshold is not moved; the mechanism still shows, "
                  "just less than predicted on the large graph."]

    lines += ["", "## What the loop actually does", ""]
    lines += [
        "It does not manufacture confidence. `false_inspected` *falls* on the families where it was "
        "non-zero, because almost nothing is declared `inspected` any more: on `real` and `ticket` the "
        "count goes to zero, on `spike` it drops from "
        f"{summary['spike']['open']['inspected']} to {summary['spike']['closed']['inspected']}, and on "
        f"`modular` from {summary['modular']['open']['inspected']} to "
        f"{summary['modular']['closed']['inspected']}.", "",
        "What rises is `untouched`, by "
        f"{paired[('spike', 'untouched')]['delta']:+.1f} on spike, "
        f"{paired[('modular', 'untouched')]['delta']:+.1f} on modular, "
        f"{paired[('real', 'untouched')]['delta']:+.1f} on real and "
        f"{paired[('ticket', 'untouched')]['delta']:+.1f} on ticket per graph. Writing off an unreviewed "
        "source keeps it unreviewed, so coverage is never reached — the frontier starves.", "",
        "The receipt therefore degenerates toward the `silent` arm from the inside: a delivery that "
        "answers \"we did not cover that\" about everything is not safer than one that overclaims. The "
        "deletion test in `outputs/supervisor-v1/` says the question \"how much did we miss\" has no "
        "answer without the receipt; closing the loop creates a second route to the same dead end, at "
        f"the cost of {paired[('ticket', 'errors')]['delta']:+.2f} (ticket), "
        f"{paired[('real', 'errors')]['delta']:+.2f} (real) and "
        f"{paired[('spike', 'errors')]['delta']:+.2f} (spike) additional surviving errors per graph. "
        "This is the argument for the prohibition being structural rather than stylistic.", "",
        "`modular` is the only family where the loop does not raise errors: it slightly lowers them "
        f"({paired[('modular', 'errors')]['delta']:+.3f}, interval "
        f"[{paired[('modular', 'errors')]['lo']:+.3f}, "
        f"{paired[('modular', 'errors')]['hi']:+.3f}], "
        f"{paired[('modular', 'errors')]['wins']} of {summary['modular']['closed']['graphs']} graphs "
        "worse). This is not the loop helping. With 3 sources the frontier empties early, so "
        "rescaling one belief column redirects an order that is nearly arbitrary to begin with: it "
        "changes on "
        f"{summary['modular']['closed']['graphs'] - summary['modular']['closed']['identical_actions']} "
        f"of {summary['modular']['closed']['graphs']} graphs and lands marginally better by chance. "
        "What does not depend on chance is the receipt: the same family loses "
        f"{100 * (1 - summary['modular']['closed']['inspected'] / max(1, summary['modular']['open']['inspected'])):.0f} % "
        "of its declared coverage "
        f"({summary['modular']['open']['inspected']} → "
        f"{summary['modular']['closed']['inspected']} inspected sinks) while its declared share "
        "climbs.", ""]

    replica_dir = OUT.parent / "drift-v1-blocka"
    if (replica_dir / "summary.json").exists():
        rp = json.loads((replica_dir / "summary.json").read_text())
        rv = json.loads((replica_dir / "verdict.json").read_text())
        rsum = {r["family"]: r for r in rp["summary"]}
        rpair = {(r["family"], r["metric"]): r for r in rp["paired"]}
        lines += ["## Replication on the numerically spent block", "",
                  f"The same frozen code first ran on graph seeds {rp['block'][0]}–{rp['block'][1]}. "
                  f"That range had already been spent by the ordered-benchmark experiments "
                  f"(as episode seeds, on different graphs), so it cannot carry the confirmatory "
                  f"claim — see `PREREGISTER_DRIFT.md` §2b. It is reported because it exists.", "",
                  f"Verdict there: `{rv['verdict']}`. Paired errors, closed − open:", "",
                  "| family | Δ errors | 95 % interval | inspected open → closed |",
                  "|---|---:|---|---:|"]
        for f in FAMILIES:
            r = rpair[(f, "errors")]
            o, c = rsum[f]["open"], rsum[f]["closed"]
            lines.append(f"| {f} | {r['delta']:+.3f} | [{r['lo']:+.3f}, {r['hi']:+.3f}] "
                         f"| {o['inspected']} → {c['inspected']} |")
        lines += ["",
                  "Directions agree on the three sleep families; magnitudes do not, which is exactly why "
                  "only paired deltas are compared and no mean is carried between blocks. `modular` is "
                  "again the family where the loop leaves the error count alone — there the interval "
                  f"[{rpair[('modular', 'errors')]['lo']:+.3f}, "
                  f"{rpair[('modular', 'errors')]['hi']:+.3f}] contains zero — while its receipt still "
                  "withdraws: declared `inspected` sinks fall from "
                  f"{rsum['modular']['open']['inspected']} to "
                  f"{rsum['modular']['closed']['inspected']} and its declared share climbs from "
                  f"{rsum['modular']['open']['declared_share']:.3f} to "
                  f"{rsum['modular']['closed']['declared_share']:.3f}. No block changes the "
                  "mechanism.", ""]

    lines += ["## Declared errors by depth (descriptive, not pre-registered)", "",
              "Depth is the longest path in edges from a source to the sink, so the bins are identical "
              "under both arms. No prediction was registered here, because the pilot showed the "
              "mechanism acts on coverage rather than on per-depth confidence.", "",
              "| family | depth | sinks | declared errors open → closed | inspected open → closed |",
              "|---|---:|---:|---:|---:|"]
    for f in FAMILIES:
        for label, lo, hi in BUCKETS:
            sel = [r for r in depth_rows if r["family"] == f and lo <= r["depth"] <= hi]
            if not sel:
                continue
            sinks = sel[0]["open_sinks"]
            de_o = sum(r["open_declared_errors"] for r in sel)
            de_c = sum(r["closed_declared_errors"] for r in sel)
            in_o = sum(r["open_inspected"] for r in sel)
            in_c = sum(r["closed_inspected"] for r in sel)
            lines.append(f"| {f} | {label} | {sinks} | {de_o} → {de_c} | {in_o} → {in_c} |")

    lines += ["", "## Bound on this claim", "",
              "* The loop is built by this repository; nothing here is evidence about an external "
              "pipeline.",
              "* 100 seeds per family on each of two blocks (confirmatory 5730–5829; 5600–5699 "
              "reported as a replication because the ledger had already spent it). Absolute means do "
              "not travel; only the paired deltas do.",
              "* The pilot block 5700–5729 is spent and disclosed; no threshold, statistic or family "
              "list was changed after it.",
              "* `false_inspected` falling is not a good outcome: it falls because the receipt stopped "
              "claiming coverage, which is the failure this file measures.",
              "* `p_catch` is fixed at 0.9. The multiplier `1 − p_catch` is the miss likelihood, not a "
              "tuned constant; a different hit rate would change the magnitude, not the mechanism."]

    (OUT / "drift_vs_open.md").write_text("\n".join(lines) + "\n")
    (OUT / "verdict.json").write_text(json.dumps({
        "verdict": v, "p1": p1, "p1_families": p1_n, "p2": p2_all, "p3": p3_all,
        "p4": p4, "p4_families": p4_n, "p5": p5, "inert": inert,
        "block": block, "policy": payload["policy"],
    }, indent=2) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
