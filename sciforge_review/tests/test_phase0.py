"""Phase 0 tests: receipts, claims, adapter, deterministic simulation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sciforge_review.adapters import SimulatedAdapter
from sciforge_review.claims import Claim, ClaimKind, ClaimVerdict, Span, sufficiency_check
from sciforge_review.graph import from_sleep_pipeline
from sciforge_review.policies import belief_greedy, queue_order, type_prior
from sciforge_review.simulate import run_episode
from triage_bench.audit.receipts import Receipt, append_receipt, verify_chain


class ReceiptTests(unittest.TestCase):
    def test_chain_and_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.jsonl"
            for i in range(3):
                append_receipt(
                    path,
                    Receipt(
                        artifact_version=f"v{i}",
                        verdict="accepted",
                        field_path="TIME_AWAKE",
                        opened_at="2026-11-10T09:00:00+00:00",
                        submitted_at="2026-11-10T09:01:02+00:00",
                    ),
                )
            ok, msg = verify_chain(path)
            self.assertTrue(ok, msg)
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1].replace("accepted", "corrected")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            ok, _ = verify_chain(path)
            self.assertFalse(ok)

    def test_duration_and_order(self) -> None:
        r = Receipt(
            artifact_version="v1",
            verdict="accepted",
            opened_at="2026-11-10T09:00:00+00:00",
            submitted_at="2026-11-10T09:01:02+00:00",
        )
        self.assertAlmostEqual(r.duration_s or 0.0, 62.0)
        with self.assertRaises(ValueError):
            Receipt(
                artifact_version="v1",
                verdict="accepted",
                opened_at="2026-11-10T09:02:00+00:00",
                submitted_at="2026-11-10T09:01:00+00:00",
            )


class ClaimTests(unittest.TestCase):
    def test_insufficient_when_checks_fail(self) -> None:
        claim = Claim(
            claim_id="c1",
            text="The intervention reduced errors (d = 5.28).",
            span=Span("results", 0, 6, "The in"),
            kind=ClaimKind.RESULT,
        )
        gate = sufficiency_check(
            claim, has_control=False, n=None, effect_size=5.28, stats_complete=False
        )
        self.assertEqual(gate.verdict, ClaimVerdict.INSUFFICIENT)
        self.assertEqual(len(gate.reasons), 4)

    def test_supported_when_checks_pass(self) -> None:
        claim = Claim(
            claim_id="c2",
            text="A small effect was observed.",
            span=Span("results", 0, 5, "A sma"),
            kind=ClaimKind.RESULT,
        )
        gate = sufficiency_check(
            claim, has_control=True, n=120, effect_size=0.4, stats_complete=True
        )
        self.assertEqual(gate.verdict, ClaimVerdict.SUPPORTED)


class AdapterTests(unittest.TestCase):
    def test_simulated_success_and_failure(self) -> None:
        adapter = SimulatedAdapter()
        ok = adapter.run("plate.read_absorbance", {"plate_id": "p1", "wavelength_nm": 600})
        bad = adapter.run("plate.read_absorbance", {"simulate": "bubble"})
        self.assertEqual(ok.status, "succeeded")
        self.assertEqual(bad.status, "failed")
        self.assertEqual(bad.failure_code, "bubble")


class SimulationTests(unittest.TestCase):
    def test_deterministic_and_cost_aware(self) -> None:
        graph = from_sleep_pipeline()
        a = run_episode(graph, queue_order(graph), 8.0, "row", seed=7)
        b = run_episode(graph, queue_order(graph), 8.0, "row", seed=7)
        self.assertEqual(a, b)
        row = run_episode(graph, queue_order(graph), 8.0, "row", seed=7)
        witness = run_episode(graph, queue_order(graph), 8.0, "witness", seed=7)
        self.assertGreaterEqual(witness.reviews, row.reviews)

    def test_all_policies_are_permutations(self) -> None:
        graph = from_sleep_pipeline()
        for policy in (queue_order, type_prior, belief_greedy):
            order = policy(graph)
            self.assertEqual(sorted(order), list(range(graph.n)))


if __name__ == "__main__":
    unittest.main()
