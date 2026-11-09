"""Review receipts: the append-only record our evaluation needs.

One receipt per human review submission. Nothing else. The schema is deliberately
small because every extra field is a field a human has to produce.

Design rules (see AUDIT_CHAIN_DESIGN.md):

    append-only      a receipt is never edited; corrections are new receipts
    one per action   one submission, not per keystroke or per dwell poll
    ids, not content no artifact text, no participant data, no free-text notes
    hash chained     `prev` is the sha256 of the previous line, so deletion and
                     reordering are detectable without a server
    field-level      `field_path` is the finest subject; omit it and the receipt
                     degrades to row level (and loses the cost signal)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "review.receipt.v1"
VERDICTS = ("accepted", "corrected", "rejected", "needs_revision", "unresolved", "skipped")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _digest(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


@dataclass(frozen=True)
class Receipt:
    artifact_version: str          # immutable version id (or a hash of it)
    verdict: str                   # one of VERDICTS
    field_path: str | None = None  # e.g. "TIME_AWAKE"; None = row-level review
    row_key: str | None = None     # hashed internal key, never a raw pid
    actor: str | None = None       # hashed reviewer id
    opened_at: str | None = None
    submitted_at: str | None = None
    reason_code: str | None = None
    second_reviewer: str | None = None   # hashed id of the second reader, if any
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prev: str | None = None
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}, got {self.verdict!r}")
        if self.opened_at and self.submitted_at:
            if datetime.fromisoformat(self.submitted_at) < datetime.fromisoformat(self.opened_at):
                raise ValueError("submitted_at precedes opened_at")

    @property
    def duration_s(self) -> float | None:
        if not (self.opened_at and self.submitted_at):
            return None
        a = datetime.fromisoformat(self.opened_at)
        b = datetime.fromisoformat(self.submitted_at)
        return (b - a).total_seconds()

    def payload(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "prev"}

    def digest(self) -> str:
        return _digest(self.payload())


def append_receipt(path: Path, receipt: Receipt) -> Receipt:
    """Append one receipt, linking it to the previous line's digest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = last_digest(path)
    linked = Receipt(**{**asdict(receipt), "prev": prev})
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**asdict(linked), "digest": linked.digest()}, sort_keys=True) + "\n")
    return linked


def read_receipts(path: Path) -> list[Receipt]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row.pop("digest", None)
        out.append(Receipt(**row))
    return out


def last_digest(path: Path) -> str | None:
    if not Path(path).exists():
        return None
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(lines[-1])["digest"] if lines else None


def verify_chain(path: Path) -> tuple[bool, str]:
    """Recompute every digest and check the prev links."""
    prev = None
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        digest = row.pop("digest", None)
        rec = Receipt(**{**row, "prev": prev})
        if rec.digest() != digest:
            return False, f"line {i}: digest mismatch"
        if row.get("prev") != prev:
            return False, f"line {i}: broken prev link"
        prev = digest
    return True, "ok"
