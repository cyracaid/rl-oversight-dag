"""Append-only receipt store used by the review session.

The store is a thin wrapper around the hash-chained JSONL receipts.  It exists
so the rest of Phase 1 does not need to know whether receipts live in a local
file, an artifact version, or an evidence producer inbox; the contract is
``record`` / ``events`` / ``verify``.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from .receipts import ReviewEvent, append_event, read_events, verify


class ReceiptStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def record(self, event: ReviewEvent):
        return append_event(self.path, event)

    def events(self) -> list[ReviewEvent]:
        return read_events(self.path)

    def verify(self) -> tuple[bool, str]:
        return verify(self.path)

    def median_duration_s(self) -> float | None:
        durations = [e.duration_s for e in self.events()]
        return statistics.median(durations) if durations else None

    def count(self) -> int:
        return len(self.events())
