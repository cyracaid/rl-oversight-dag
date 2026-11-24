"""From review receipts to an export the frozen protocol can score.

`receipts.py` writes the append-only chain. This module answers the two questions
the evaluation protocol actually asks, and refuses to answer them when the data
does not support an answer:

  1. **Which errors has a human actually looked at?** Errors with no receipt are
     *unknown*, not *correct*. Writing them as correct silently inflates every
     coverage claim, so they are reported as `errors_without_receipt`.
  2. **What did the review cost?** Only computable when both timestamps exist.
     `recall@minutes` is therefore reported as `unavailable`, never as 0.

Everything is counted with an explicit denominator. Nothing is dropped silently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from .receipts import Receipt, read_receipts

UNAVAILABLE = "unavailable"


def to_export_receipts(
    receipts: Iterable[Receipt],
    key_map: Mapping[str, str],
) -> tuple[list[dict], dict]:
    """Map chain receipts onto export `receipts` entries.

    ``key_map`` maps ``row_key`` (hashed internal key) to a node id in the export.
    Unmapped receipts are returned in the counter block instead of being dropped:
    a receipt we cannot place is a measurement gap, not noise.
    """
    out: list[dict] = []
    unmapped: list[str] = []
    duplicate_ids: list[str] = []
    missing_time: list[str] = []
    seen: set[str] = set()

    for rec in receipts:
        node_id = key_map.get(rec.row_key or "")
        if node_id is None:
            unmapped.append(rec.row_key or rec.event_id)
            continue
        if node_id in seen:
            # Two receipts for the same node are legitimate (re-review). The
            # export format keys receipts by node, so keep the last submission
            # and count the replacement instead of hiding it.
            duplicate_ids.append(node_id)
            out = [r for r in out if r["node_id"] != node_id]
        seen.add(node_id)
        if not rec.submitted_at:
            missing_time.append(node_id)
            continue
        entry = {
            "node_id": node_id,
            "reviewed_at": rec.submitted_at,
            "verdict": rec.verdict,
        }
        if rec.duration_s is not None:
            entry["duration_min"] = round(rec.duration_s / 60.0, 3)
        out.append(entry)

    counters = {
        "receipts_in": len(seen) + len(unmapped),
        "receipts_exported": len(out),
        "receipts_unmapped": len(unmapped),
        "receipts_superseded": len(duplicate_ids),
        "receipts_without_submitted_at": len(missing_time),
        "unmapped_keys": unmapped[:20],
    }
    return out, counters


def coverage(
    export_receipts: list[dict],
    error_ids: Iterable[str],
    *,
    counters: Mapping[str, object] | None = None,
) -> dict:
    """Receipt coverage over the error set, with explicit denominators."""
    errors = list(dict.fromkeys(error_ids))
    reviewed = {r["node_id"] for r in export_receipts}
    covered = [e for e in errors if e in reviewed]
    missing = [e for e in errors if e not in reviewed]

    with_duration = [r for r in export_receipts if "duration_min" in r]
    without_duration = [r for r in export_receipts if "duration_min" not in r]
    timed = [r for r in export_receipts if r.get("reviewed_at")]

    n_err = len(errors)
    n_rec = len(export_receipts)
    block = {
        "errors_total": n_err,
        "errors_with_receipt": len(covered),
        "errors_without_receipt": len(missing),
        "coverage_fraction": (len(covered) / n_err) if n_err else UNAVAILABLE,
        "receipts_total": n_rec,
        "receipts_with_duration": len(with_duration),
        "receipts_missing_duration": len(without_duration),
        "duration_coverage_fraction": (len(with_duration) / n_rec) if n_rec else UNAVAILABLE,
        "receipts_with_timestamp": len(timed),
        "missing_error_ids": missing[:20],
    }
    if counters:
        block["load"] = dict(counters)

    block["capabilities"] = {
        "human_baseline_order": (
            {"status": "available"}
            if n_rec and len(timed) == n_rec
            else {"status": "partial" if timed else UNAVAILABLE,
                  "reason": f"{len(timed)}/{n_rec} receipts carry submitted_at"}
        ),
        "recall_at_minutes": (
            {"status": "available",
             "minutes_total": round(sum(r["duration_min"] for r in with_duration), 3)}
            if n_rec and len(with_duration) == n_rec
            else {"status": UNAVAILABLE,
                  "reason": f"{len(without_duration)}/{n_rec} receipts have no "
                            "opened_at/submitted_at pair; duration is not zero"}
        ),
    }
    return block


def summarize_export(
    receipt_path: Path,
    key_map: Mapping[str, str],
    error_ids: Iterable[str],
) -> dict:
    """End-to-end: chain file -> export receipts -> coverage block."""
    export_receipts, counters = to_export_receipts(read_receipts(receipt_path), key_map)
    return {
        "receipts": export_receipts,
        "coverage": coverage(export_receipts, error_ids, counters=counters),
    }
