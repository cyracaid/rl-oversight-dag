"""Review events bound to the append-only receipt chain.

Phase 1 keeps the Phase 0 receipt schema and adds the one field the review
control plane needs: the evidence node a receipt belongs to.  ``row_key`` is
reused for that id; the receipt still contains references and timestamps only.

The binding is deliberately thin.  A receipt that cannot name an immutable
artifact version is rejected by the upstream ``Receipt`` validation; a receipt
that cannot name a node is rejected here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from triage_bench.audit.receipts import (
    VERDICTS,
    Receipt,
    append_receipt,
    read_receipts,
    verify_chain,
)


@dataclass(frozen=True)
class ReviewEvent:
    node_id: str
    artifact_version: str
    verdict: str
    actor_hash: str
    opened_at: str
    submitted_at: str
    field_path: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not self.artifact_version.strip():
            raise ValueError("artifact_version must not be empty")
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if not self.actor_hash.strip():
            raise ValueError("actor_hash must not be empty")
        opened = datetime.fromisoformat(self.opened_at)
        submitted = datetime.fromisoformat(self.submitted_at)
        if submitted < opened:
            raise ValueError("submitted_at precedes opened_at")

    @property
    def duration_s(self) -> float:
        return (
            datetime.fromisoformat(self.submitted_at)
            - datetime.fromisoformat(self.opened_at)
        ).total_seconds()

    def to_receipt(self) -> Receipt:
        return Receipt(
            artifact_version=self.artifact_version,
            verdict=self.verdict,
            field_path=self.field_path,
            row_key=self.node_id,
            actor=self.actor_hash,
            opened_at=self.opened_at,
            submitted_at=self.submitted_at,
            reason_code=self.reason_code,
        )

    @classmethod
    def from_receipt(cls, receipt: Receipt) -> "ReviewEvent":
        if not receipt.row_key:
            raise ValueError("receipt has no node id (row_key)")
        if not receipt.actor:
            raise ValueError("receipt has no actor hash")
        if not (receipt.opened_at and receipt.submitted_at):
            raise ValueError("receipt has no review timestamps")
        return cls(
            node_id=receipt.row_key,
            artifact_version=receipt.artifact_version,
            verdict=receipt.verdict,
            actor_hash=receipt.actor,
            opened_at=receipt.opened_at,
            submitted_at=receipt.submitted_at,
            field_path=receipt.field_path,
            reason_code=receipt.reason_code,
        )


def append_event(path: Path, event: ReviewEvent) -> Receipt:
    return append_receipt(path, event.to_receipt())


def read_events(path: Path) -> list[ReviewEvent]:
    return [ReviewEvent.from_receipt(r) for r in read_receipts(path)]


def verify(path: Path) -> tuple[bool, str]:
    return verify_chain(path)
