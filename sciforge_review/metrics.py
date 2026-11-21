"""Metrics recomputed from receipts, not from the simulator's memory."""

from __future__ import annotations

from dataclasses import dataclass

from .receipts import ReviewEvent


@dataclass(frozen=True)
class RecallAtMinutes:
    budget_min: float | None
    spent_min: float
    reviews: int
    fixed: int
    total_true: int
    recall: float
    errors_per_hour: float


def recall_at_minutes(
    events: list[ReviewEvent],
    truth: dict[str, bool],
    budget_min: float | None = None,
) -> RecallAtMinutes:
    """Join receipts with the offline truth table.

    ``budget_min`` re-applies the budget from the receipt durations; use it to
    check that the session stopped where it claimed to.
    """
    selected: list[ReviewEvent] = []
    spent = 0.0
    for event in events:
        minutes = event.duration_s / 60.0
        if budget_min is not None and spent + minutes > budget_min + 1e-9:
            break
        selected.append(event)
        spent += minutes

    corrected = {e.node_id for e in selected if e.verdict == "corrected"}
    fixed = sum(1 for node_id in corrected if truth.get(node_id, False))
    total_true = sum(1 for value in truth.values() if value)
    recall = fixed / total_true if total_true else 0.0
    return RecallAtMinutes(
        budget_min=budget_min,
        spent_min=spent,
        reviews=len(selected),
        fixed=fixed,
        total_true=total_true,
        recall=recall,
        errors_per_hour=fixed / (spent / 60.0) if spent else 0.0,
    )


@dataclass(frozen=True)
class Coverage:
    known: int
    flagged: int
    reviewed: int
    unreachable: int
    unreviewed: int


def coverage(events: list[ReviewEvent], known: set[str], flagged: set[str]) -> Coverage:
    reviewed = {e.node_id for e in events}
    return Coverage(
        known=len(known),
        flagged=len(flagged),
        reviewed=len(reviewed),
        unreachable=len(known - flagged),
        unreviewed=len(flagged - reviewed),
    )
