"""A minimal review session that writes receipts as it goes.

The session is deliberately dumb: it follows a ranking, decides whether the
reviewer catches the node's source error, and appends one receipt per
submission.  It does not know about sinks or propagation; those belong to the
evaluation, not to the receipt.

The point is the replay: after the session, every number is recomputed from
the receipts on disk, not from the simulator's memory.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .graph import EvidenceGraph
from .policies import PER_FIELD_MINUTES, field_count
from .receipts import ReviewEvent
from .simulate import P_CATCH
from .store import ReceiptStore

DEFAULT_START = "2026-11-10T09:00:00+00:00"


@dataclass(frozen=True)
class SessionResult:
    reviews: int
    spent_minutes: float
    fixed: int
    path: Path


def run_session(
    graph: EvidenceGraph,
    order: list[int],
    truth: dict[str, bool],
    budget_minutes: float,
    mode: str,
    seed: int,
    store: ReceiptStore,
    actor_hash: str = "reviewer:sim",
    start: str = DEFAULT_START,
) -> SessionResult:
    rng = random.Random(seed)
    per_review = field_count(mode) * PER_FIELD_MINUTES
    clock = datetime.fromisoformat(start)
    spent = 0.0
    reviews = 0
    fixed = 0

    for idx in order:
        if spent + per_review > budget_minutes + 1e-9:
            break
        node = graph.nodes[idx]
        opened = clock + timedelta(minutes=spent)
        submitted = opened + timedelta(minutes=per_review)
        is_true = truth.get(node.name, False)
        caught = is_true and rng.random() < P_CATCH
        event = ReviewEvent(
            node_id=node.name,
            artifact_version=f"pipeline-n{graph.n}-v1",
            verdict="corrected" if caught else "accepted",
            actor_hash=actor_hash,
            opened_at=opened.isoformat(timespec="seconds"),
            submitted_at=submitted.isoformat(timespec="seconds"),
            field_path=None if mode == "row" else "witness_pair",
            reason_code=node.error_type,
        )
        store.record(event)
        spent += per_review
        reviews += 1
        fixed += int(caught)

    return SessionResult(reviews=reviews, spent_minutes=spent, fixed=fixed, path=store.path)
