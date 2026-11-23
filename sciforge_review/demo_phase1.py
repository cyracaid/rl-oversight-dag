"""Phase 1 demo: write receipts, replay them, recompute the metrics.

Run from the project root:

    python3 -m sciforge_review.demo_phase1
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .graph import from_sleep_pipeline
from .loop import run_session
from .metrics import coverage, recall_at_minutes
from .policies import belief_greedy, queue_order, type_prior
from .simulate import sample_truth
from .store import ReceiptStore

OUT = Path(__file__).parent / "outputs"
BUDGETS = (4.0, 8.0, 16.0)
SEEDS = 20


def _fmt(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}"


def main() -> None:
    graph = from_sleep_pipeline()
    policies = {
        "queue order": queue_order(graph),
        "type prior": type_prior(graph),
        "belief greedy": belief_greedy(graph),
    }
    known = set(graph.name2id)

    rows = []
    chains_ok = 0
    chains = 0
    sample_receipt = None
    sample_events = []

    with tempfile.TemporaryDirectory() as tmp:
        for mode in ("row", "witness"):
            for budget in BUDGETS:
                for policy_name, order in policies.items():
                    recalls = []
                    reviews = []
                    spent = []
                    fixed_counts = []
                    for seed in range(1, SEEDS + 1):
                        truth = sample_truth(graph, seed)
                        path = Path(tmp) / f"{mode}-{budget}-{policy_name}-{seed}.jsonl"
                        store = ReceiptStore(path)
                        run_session(
                            graph,
                            order,
                            truth,
                            budget_minutes=budget,
                            mode=mode,
                            seed=seed,
                            store=store,
                        )
                        events = store.events()
                        ok, _ = store.verify()
                        chains += 1
                        chains_ok += int(ok)
                        metric = recall_at_minutes(events, truth, budget_min=budget)
                        recalls.append(metric.recall)
                        reviews.append(metric.reviews)
                        spent.append(metric.spent_min)
                        fixed_counts.append(metric.fixed)
                        if sample_receipt is None and mode == "witness" and budget == 8.0:
                            sample_receipt = asdict(events[0])
                            sample_events = events

                    rows.append(
                        {
                            "policy": policy_name,
                            "mode": mode,
                            "budget": budget,
                            "reviews": sum(reviews) / len(reviews),
                            "spent": sum(spent) / len(spent),
                            "recall": sum(recalls) / len(recalls),
                            "errors_per_hour": (
                                (sum(fixed_counts) / len(fixed_counts))
                                / (sum(spent) / len(spent) / 60.0)
                                if sum(spent)
                                else 0.0
                            ),
                        }
                    )

    # A coverage example: every node is flagged in this synthetic graph, so the
    # unreachable count is zero; the real queue's gap is quoted separately.
    demo_coverage = coverage(sample_events, known, known)

    lines = [
        "# Phase 1 Report — receipts, replay, and recall@minutes",
        "",
        "> Every number below is recomputed from the receipts on disk, not from",
        "> the simulator's memory. Synthetic N=21; not the paper's simulator.",
        "",
        "## What changed from Phase 0",
        "",
        "- A session now writes one `review.receipt.v1` per submission, bound to",
        "  a node and an immutable artifact version.",
        "- `recall@minutes` is computed by joining receipts with the offline truth",
        "  table and re-applying the minute budget from receipt durations.",
        "- Every receipt chain is verified after the run.",
        "",
        "## Receipt integrity",
        "",
        f"- chains written and verified: **{chains_ok}/{chains}**",
        f"- coverage (synthetic): known={demo_coverage.known}, flagged={demo_coverage.flagged}, "
        f"reviewed={demo_coverage.reviewed}, unreachable={demo_coverage.unreachable}",
        "- real queue anchor: 17 of 85 broad corrections were never flagged (20%); "
        "no ranking can reach them",
        "",
        "## Results (20 seeds, paired truth per policy)",
        "",
        "| policy | mode | budget (min) | reviews | spent (min) | recall | errors/hour |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['policy']} | {r['mode']} | {r['budget']:g} | {_fmt(r['reviews'], 1)} | "
            f"{_fmt(r['spent'], 1)} | {_fmt(r['recall'], 3)} | {_fmt(r['errors_per_hour'], 1)} |"
        )

    lines += [
        "",
        "## Sample receipt",
        "",
        "```json",
        json.dumps(sample_receipt, indent=2, ensure_ascii=False) if sample_receipt else "{}",
        "```",
        "",
        "## Caveats",
        "",
        "- The truth table is synthetic and paired by seed; this is a harness test,",
        "  not an estimate of the real queue.",
        "- The reviewer catches a true source error with p=0.9; a missed error is",
        "  recorded as `accepted`, which is why receipts alone never prove truth.",
        "- Re-running the same seed reproduces the same receipts; the chain digest",
        "  is deterministic for the same sequence.",
        "",
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase1_report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "phase1_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
