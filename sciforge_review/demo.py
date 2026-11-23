"""Phase 0 demo: receipts + read-only policies + cost-aware review.

Run from the project root:

    python3 -m sciforge_review.demo

Writes ``sciforge_review/outputs/review_card.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

from .adapters import SimulatedAdapter
from .claims import Claim, ClaimKind, Span, sufficiency_check
from .graph import from_sleep_pipeline
from .policies import belief_greedy, queue_order, type_prior
from .simulate import evaluate, no_review

OUT = Path(__file__).parent / "outputs"
BUDGETS = (4.0, 8.0, 16.0)
SEEDS = 30


def _fmt(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}"


def build_card(rows) -> str:
    lines = [
        "# Review Card — Phase 0",
        "",
        "> Synthetic demo harness over the N=21 sleep-pipeline DAG. **Not** the",
        "> paper's simulator, and **not** a claim about the real queue; the real",
        "> queue anchors are quoted separately below from `triage_bench`.",
        "",
        "## What this measures",
        "",
        "- **Cost-aware review**: a row review reads 4 fields; a witness-pair review",
        "  reads 2. At 62 s per row review, the same minutes buy twice the coverage.",
        "- **Paired episodes**: every policy sees the same seed, base errors, and",
        "  edge coins. Metrics are averaged over 30 seeds.",
        "- **Read-only**: policies rank nodes; nothing is written or sealed.",
        "",
        "## Synthetic N=21 result",
        "",
        "| policy | mode | budget (min) | reviews | sink errors | recall | errors/hour |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        if " @ " in r.policy:
            mode = "witness" if "(witness)" in r.policy else "row"
            policy = r.policy.split(" @ ")[0]
            budget = r.policy.split(" @ ")[1].split(" ")[0]
        else:
            mode, policy, budget = "—", r.policy, "—"
        lines.append(
            f"| {policy} | {mode} | {budget} | {_fmt(r.reviews, 1)} | "
            f"{_fmt(r.sink_errors)} | {_fmt(r.recall, 3)} | {_fmt(r.errors_per_hour, 1)} |"
        )

    lines += [
        "",
        "## Real-queue anchors (not recomputed here)",
        "",
        "From `triage_bench/README.md`, `CEILING.md`, and",
        "`AUDIT_CHAIN_DESIGN.md` (generated 2026-11-09, not yet rerun by a teammate):",
        "",
        "| fact | value |",
        "|---|---|",
        "| review queue | 1,048 flags, 68 human-confirmed errors (6.5% precision) |",
        "| best type rule | M1-bearing first reaches **83.8%** of errors in **140 reviews (13%)** |",
        "| pipeline's own order | worse than random at k=400 (23.5% vs 39.7%) |",
        "| information ceiling | 17 broad corrections were never flagged (7 narrow); no ranking can reach them |",
        "| cost | median **62 s** per row review; witness-pair review halves reading cost |",
        "| cost model | 60/120/240 min: whole row 8.8/25.0/63.2% vs witness pair **25.0/63.2/83.8%** |",
        "",
        "## What this implies for SciForge",
        "",
        "1. **Measure first.** The receipt schema is the unit of account: who reviewed",
        "   which version/field, when they opened and submitted, and what they decided.",
        "2. **Direct, do not decide.** `belief_greedy` is a read-only ranking; the",
        "   human still seals. Learned policies are offline comparisons, not the product.",
        "3. **Expose the gap.** Coverage (unflagged rows) and `insufficient` evidence",
        "   are first-class outputs; ranking cannot fix what was never flagged.",
        "",
        "## Shape A / B / C in one core",
        "",
        "| shape | shared primitive | Phase 0 status |",
        "|---|---|---|",
        "| A review control plane | `EvidenceGraph` + `ReviewReceipt` + policy | graph + policies + receipt reuse |",
        "| B claim audit | `Claim` + `Span` + `sufficiency_check` | interface + checklist |",
        "| C instrument adapter | `InstrumentCapability` + `InstrumentRun` | simulated adapter |",
        "",
        "## Next",
        "",
        "- Wire the receipt writer into the demo (the `triage_bench/audit/receipts.py`",
        "  hash chain is already tested).",
        "- Port the receipt contract and the read-only policy interface into a",
        "  SciForge worktree; keep the local prototype as the reference implementation.",
        "- Replace the synthetic DAG with a SciForge evidence-graph export when the",
        "  P0/P1 fields from `triage_bench/SCIFORGE_ASK.md` are available.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    graph = from_sleep_pipeline()
    policies = {
        "queue order": queue_order(graph),
        "type prior": type_prior(graph),
        "belief greedy": belief_greedy(graph),
    }

    rows = [no_review(graph, seeds=SEEDS)]
    for mode in ("row", "witness"):
        rows.extend(evaluate(graph, policies, budgets=BUDGETS, mode=mode, seeds=SEEDS))

    # Smoke the B and C interfaces so Phase 0 is not only A.
    claim = Claim(
        claim_id="c1",
        text="The intervention reduced errors (d = 5.28).",
        span=Span("results", 0, 6, "The in"),
        kind=ClaimKind.RESULT,
    )
    gate = sufficiency_check(
        claim, has_control=False, n=None, effect_size=5.28, stats_complete=False
    )
    adapter = SimulatedAdapter()
    ok = adapter.run("plate.read_absorbance", {"plate_id": "p1", "wavelength_nm": 600})
    bad = adapter.run("plate.read_absorbance", {"simulate": "bubble"})

    OUT.mkdir(parents=True, exist_ok=True)
    card = build_card(rows)
    (OUT / "review_card.md").write_text(card, encoding="utf-8")
    (OUT / "review_card.json").write_text(
        json.dumps([r.__dict__ for r in rows], indent=2), encoding="utf-8"
    )

    print(card)
    print(f"\nclaim gate: {gate.verdict.value} reasons={gate.reasons}")
    print(f"adapter: {ok.status} / {bad.status} ({bad.failure_code})")


if __name__ == "__main__":
    main()
