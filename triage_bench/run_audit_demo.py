#!/usr/bin/env python3
"""End-to-end demo of the audit chain: receipts -> cost model -> recall per minute.

No real review timings exist yet, so the per-field time is sampled from a stated
distribution. Everything else is real: the queue, the ordering, and the labels.
The point is the *ratio* between row-level and field-scoped review, which does not
depend on the assumed seconds.

Outputs a hash-chained receipt log (subject ids hashed, no raw keys) so the
format can be inspected before anyone writes a real one.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import numpy as np

from audit.receipts import Receipt, append_receipt, read_receipts, verify_chain
from bench import config
from bench.load import load_queue
from bench.policies import score_all, type_partition_scores

SECONDS_PER_FIELD = 30.0      # assumption, stated in the output
COST_ROW = 4                  # timestamps read when reviewing a whole row
COST_PAIR = 2                 # timestamps read when the witness pair is known


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:16]


def recall_at_cost(y: np.ndarray, cost: np.ndarray, budget: float) -> float:
    """Recall reachable by spending `budget` minutes in the given order."""
    spent = np.cumsum(cost)
    keep = spent <= budget
    return float(y[keep].sum() / y.sum()) if y.sum() else float("nan")


def main() -> None:
    data = config.require_data()
    queue = load_queue(data)
    y = queue["y_broad"].to_numpy(int)

    scores = score_all(queue)
    scores["type_partition"] = type_partition_scores(queue)
    order = np.argsort(-scores["m1_first"], kind="stable")

    rng = np.random.default_rng(config.SEED)
    per_field = np.clip(rng.lognormal(np.log(SECONDS_PER_FIELD / 60), 0.35, len(order)), 0.15, 3.0)
    cost_row = per_field * COST_ROW
    cost_pair = per_field * COST_PAIR

    oy, oc_row, oc_pair = y[order], cost_row[order], cost_pair[order]

    budgets = [30, 60, 120, 240]
    table = {b: {"row": recall_at_cost(oy, oc_row, b),
                 "pair": recall_at_cost(oy, oc_pair, b)} for b in budgets}

    # write the first 200 reviews as a demo receipt log
    path = config.OUT_DIR / "demo_receipts.jsonl"
    if path.exists():
        path.unlink()
    start = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
    clock = start
    for rank, i in enumerate(order[:200]):
        dur = timedelta(seconds=float(per_field[i]) * 60 * COST_PAIR)
        rec = Receipt(
            artifact_version=_hash(f"row-{int(queue.iloc[i]['row_id'])}"),
            row_key=_hash(str(int(queue.iloc[i]["pid"]))),
            field_path=None,
            actor=_hash("curator-a"),
            opened_at=clock.isoformat(timespec="seconds"),
            submitted_at=(clock + dur).isoformat(timespec="seconds"),
            verdict="corrected" if y[i] else "accepted",
            reason_code="order_error" if queue.iloc[i]["m1"] else "window_illegal",
        )
        clock = clock + dur + timedelta(seconds=15)
        append_receipt(path, rec)

    ok, msg = verify_chain(path)
    receipts = read_receipts(path)
    durations = [r.duration_s for r in receipts if r.duration_s]

    out = {
        "seconds_per_field_assumed": SECONDS_PER_FIELD,
        "receipts": len(receipts),
        "chain_ok": ok,
        "chain_message": msg,
        "median_review_seconds": float(np.median(durations)),
        "recall_by_minutes": {str(b): {k: round(v, 4) for k, v in d.items()} for b, d in table.items()},
        "minutes_to_target": {
            f"{int(t*100)}pct": {
                name: float(np.cumsum(cost)[np.argmax(np.cumsum(oy) >= t * oy.sum())])
                for name, cost in (("row", oc_row), ("pair", oc_pair))
            } for t in (0.25, 0.50, 0.75)
        },
    }
    (config.OUT_DIR / "audit_demo.json").write_text(json.dumps(out, indent=2) + "\n")

    lines = [
        "# Audit chain demo: receipts to recall per minute",
        "",
        f"Chain verified: **{ok}** ({msg}); {len(receipts)} receipts, median review "
        f"{np.median(durations):.0f}s at an assumed {SECONDS_PER_FIELD:.0f}s per field.",
        "",
        "| review budget | row-level (4 fields) | witness pair (2 fields) |",
        "|---|---:|---:|",
    ]
    for b in budgets:
        lines.append(f"| {b} min | {table[b]['row']:.1%} | {table[b]['pair']:.1%} |")
    lines += [
        "",
        "| target recall | row-level | witness pair |",
        "|---|---:|---:|",
    ]
    for target, d in out["minutes_to_target"].items():
        lines.append(f"| {target} | {d['row']:.0f} min | {d['pair']:.0f} min |")
    lines += [
        "",
        "",
        "The per-field seconds are an assumption; the ratio is not. Replace the",
        "assumption with the median from real receipts and the table rescales.",
        "",
        "Receipt log: `outputs/demo_receipts.jsonl` (subject ids hashed, no raw keys).",
    ]
    (config.OUT_DIR / "audit_demo.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
