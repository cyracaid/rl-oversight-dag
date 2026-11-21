"""Phase 1 tests: receipt binding, replay, metrics, and the session loop."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sciforge_review.graph import from_sleep_pipeline
from sciforge_review.loop import run_session
from sciforge_review.metrics import coverage, recall_at_minutes
from sciforge_review.policies import queue_order
from sciforge_review.receipts import ReviewEvent
from sciforge_review.simulate import sample_truth
from sciforge_review.store import ReceiptStore
from triage_bench.audit.receipts import Receipt


def _event(node: str, verdict: str = "accepted", offset_min: int = 0) -> ReviewEvent:
    base = datetime(2026, 11, 10, 9, 0, 0, tzinfo=timezone.utc)
    opened = base + timedelta(minutes=offset_min)
    return ReviewEvent(
        node_id=node,
        artifact_version="pipeline-n21-v1",
        verdict=verdict,
        actor_hash="reviewer:test",
        opened_at=opened.isoformat(timespec="seconds"),
        submitted_at=(opened + timedelta(minutes=1)).isoformat(timespec="seconds"),
        field_path=None,
        reason_code="order_error",
    )


class BindingTests(unittest.TestCase):
    def test_event_receipt_roundtrip(self) -> None:
        event = _event("time_bed", "corrected")
        receipt = event.to_receipt()
        self.assertEqual(receipt.row_key, "time_bed")
        self.assertEqual(receipt.artifact_version, "pipeline-n21-v1")
        self.assertEqual(receipt.actor, "reviewer:test")
        self.assertEqual(ReviewEvent.from_receipt(receipt), event)

    def test_receipt_without_node_is_rejected(self) -> None:
        receipt = Receipt(artifact_version="v1", verdict="accepted")
        with self.assertRaises(ValueError):
            ReviewEvent.from_receipt(receipt)


class StoreTests(unittest.TestCase):
    def test_chain_and_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp) / "r.jsonl")
            store.record(_event("a"))
            store.record(_event("b", "corrected"))
            ok, msg = store.verify()
            self.assertTrue(ok, msg)
            self.assertEqual(store.count(), 2)
            self.assertAlmostEqual(store.median_duration_s() or 0.0, 60.0)

            lines = store.path.read_text(encoding="utf-8").splitlines()
            lines[0] = lines[0].replace("accepted", "corrected")
            store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            ok, _ = store.verify()
            self.assertFalse(ok)

    def test_replay_returns_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp) / "r.jsonl")
            store.record(_event("a"))
            events = store.events()
            self.assertEqual([e.node_id for e in events], ["a"])


class MetricTests(unittest.TestCase):
    def test_recall_and_budget(self) -> None:
        truth = {"a": True, "b": True, "c": False}
        events = [_event("a", "corrected", 0), _event("b", "accepted", 1)]
        full = recall_at_minutes(events, truth)
        self.assertEqual(full.fixed, 1)
        self.assertEqual(full.total_true, 2)
        self.assertAlmostEqual(full.recall, 0.5)
        self.assertAlmostEqual(full.spent_min, 2.0)

        one = recall_at_minutes(events, truth, budget_min=1.0)
        self.assertEqual(one.reviews, 1)
        self.assertAlmostEqual(one.spent_min, 1.0)
        self.assertAlmostEqual(one.recall, 0.5)

    def test_coverage(self) -> None:
        known = {"a", "b", "c"}
        flagged = {"a", "b"}
        result = coverage([_event("a")], known, flagged)
        self.assertEqual(result.unreachable, 1)
        self.assertEqual(result.unreviewed, 1)
        self.assertEqual(result.reviewed, 1)


class SessionTests(unittest.TestCase):
    def test_session_writes_verified_receipts(self) -> None:
        graph = from_sleep_pipeline()
        truth = sample_truth(graph, seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp) / "r.jsonl")
            result = run_session(
                graph,
                queue_order(graph),
                truth,
                budget_minutes=8.0,
                mode="row",
                seed=3,
                store=store,
            )
            self.assertGreater(result.reviews, 0)
            self.assertLessEqual(result.spent_minutes, 8.0 + 1e-6)
            ok, msg = store.verify()
            self.assertTrue(ok, msg)
            self.assertEqual(store.count(), result.reviews)

    def test_session_is_deterministic(self) -> None:
        graph = from_sleep_pipeline()
        truth = sample_truth(graph, seed=5)
        with tempfile.TemporaryDirectory() as tmp:
            a = ReceiptStore(Path(tmp) / "a.jsonl")
            b = ReceiptStore(Path(tmp) / "b.jsonl")
            for store in (a, b):
                run_session(
                    graph,
                    queue_order(graph),
                    truth,
                    budget_minutes=8.0,
                    mode="witness",
                    seed=5,
                    store=store,
                )
            self.assertEqual(a.events(), b.events())


if __name__ == "__main__":
    unittest.main()
