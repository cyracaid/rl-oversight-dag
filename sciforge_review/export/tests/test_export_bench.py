import unittest

import numpy as np

from sciforge_review.export.bench import (POLICIES, State, episode, precision_at,
                                          recall_at, reviews_to_half)
from sciforge_review.export.load_export import ExportError, from_payload, load_export

TINY = {
    "project": "tiny",
    "snapshot_at": "2026-11-20T00:00:00Z",
    "synthetic": True,
    "nodes": [
        {"id": "a", "type": "dataset"},
        {"id": "b", "type": "run"},
        {"id": "c", "type": "figure"},
        {"id": "d", "type": "claim", "is_sink": True},
    ],
    "edges": [
        {"src": "a", "dst": "b", "rel": "derived_from"},
        {"src": "b", "dst": "c", "rel": "derived_from"},
        {"src": "c", "dst": "d", "rel": "derived_from"},
        {"src": "a", "dst": "d", "rel": "supports"},
    ],
    "corrections": [{"node_id": "b", "error_type": "stale"}],
    "receipts": [{"node_id": "a", "reviewed_at": "2026-11-20T01:00:00Z",
                  "verdict": "accepted", "duration_min": 5}],
}


class LoaderTests(unittest.TestCase):
    def test_tiny_parses(self):
        g = from_payload(TINY)
        self.assertEqual(g.n, 4)
        self.assertEqual(g.parents[1], (0,))
        self.assertEqual(g.reach[0], 3)
        self.assertEqual(g.report["non_propagation_edges_ignored"], 1)
        self.assertEqual(g.report["corrections"], 1)
        self.assertTrue(g.synthetic)

    def test_rejects_cycle(self):
        bad = {**TINY, "edges": [
            {"src": "a", "dst": "b", "rel": "derived_from"},
            {"src": "b", "dst": "a", "rel": "derived_from"},
        ]}
        with self.assertRaises(ExportError):
            from_payload(bad)

    def test_rejects_unknown_endpoint(self):
        bad = {**TINY, "edges": [{"src": "a", "dst": "zz", "rel": "derived_from"}]}
        with self.assertRaises(ExportError):
            from_payload(bad)

    def test_rejects_duplicate_id(self):
        bad = {**TINY, "nodes": TINY["nodes"] + [{"id": "a", "type": "run"}]}
        with self.assertRaises(ExportError):
            from_payload(bad)

    def test_rejects_bad_verdict(self):
        bad = {**TINY, "receipts": [{"node_id": "a", "verdict": "looks-fine"}]}
        with self.assertRaises(ExportError):
            from_payload(bad)

    def test_rejects_missing_field(self):
        bad = {k: v for k, v in TINY.items() if k != "edges"}
        with self.assertRaises(ExportError):
            from_payload(bad)

    def test_duplicate_correction_counted_not_silently_dropped(self):
        dup = {**TINY, "corrections": TINY["corrections"] + TINY["corrections"]}
        g = from_payload(dup)
        self.assertEqual(g.report["duplicate_corrections_dropped"], 1)

    def test_unknown_type_is_reported(self):
        odd = {**TINY, "nodes": [{"id": "a", "type": "notes"}] + TINY["nodes"][1:]}
        g = from_payload(odd)
        self.assertEqual(g.report["unknown_node_types"], ["notes"])

    def test_mock_file_loads(self):
        path = __import__("pathlib").Path(__file__).resolve().parents[1] / "sciforge_mock_v1.json"
        g = load_export(path)
        self.assertEqual(g.n, 21)
        self.assertTrue(g.synthetic)
        self.assertGreaterEqual(len(g.corrections), 1)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.graph = from_payload(TINY)
        self.truth = {1: True}

    def test_state_refuses_unreviewed_verdict(self):
        state = State(graph=self.graph, reviewed=frozenset(), revealed={})
        with self.assertRaises(PermissionError):
            state.verdict(1)

    def test_state_exposes_only_reviewed_verdicts(self):
        state = State(graph=self.graph, reviewed=frozenset({0}), revealed={0: False})
        self.assertEqual(set(state.revealed), {0})
        with self.assertRaises(PermissionError):
            state.verdict(1)

    def test_every_policy_is_labelfree_and_deterministic(self):
        state = State(graph=self.graph, reviewed=frozenset({0}), revealed={0: False})
        for name, fn in POLICIES.items():
            first = fn(state)
            self.assertEqual(first, fn(state), name)
            self.assertNotIn(0, first, name)
            self.assertEqual(sorted(first), sorted(first), name)
            self.assertNotIn("truth", state.__dict__, name)

    def test_episode_reviews_distinct_nodes(self):
        for name, fn in POLICIES.items():
            chosen = episode(self.graph, self.truth, 3)[name]
            self.assertEqual(len(chosen), 3, name)
            self.assertEqual(len(set(chosen)), 3, name)

    def test_adaptive_reranks_after_a_verdict(self):
        # Flat prior: only downstream risk can separate the two orders.
        revealed = {1: True}
        state_plain = State(graph=self.graph, reviewed=frozenset(), revealed={})
        state_seen = State(graph=self.graph, reviewed=frozenset({1}), revealed=revealed)
        self.assertNotEqual(POLICIES["marginal_adaptive"](state_plain),
                            POLICIES["marginal_adaptive"](state_seen))


class MetricTests(unittest.TestCase):
    def test_recall_and_precision(self):
        truth = {0: True, 3: True, 5: True}
        chosen = [0, 1, 2, 3]
        self.assertAlmostEqual(recall_at(chosen, truth, 4), 2 / 3)
        self.assertAlmostEqual(precision_at(chosen, truth, 4), 0.5)

    def test_reviews_to_half_is_nan_when_unreachable(self):
        self.assertTrue(np.isnan(reviews_to_half([1, 2], {0: True, 3: True})))

    def test_reviews_to_half_counts_reviews(self):
        self.assertEqual(reviews_to_half([0, 1], {0: True, 1: True}), 1.0)


if __name__ == "__main__":
    unittest.main()
