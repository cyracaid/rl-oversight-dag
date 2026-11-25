"""Tests for the prohibited loop: depth, frontier, compounding, and the copy."""
import unittest

import numpy as np

from dag_role3.drift import downweight, frontier_sources, optimistic_features, sink_depth
from dag_role3.graphs import DAG
from dag_role3.supervisor import coverage_truth


def diamond():
    return DAG(parents=((), (0,), (0,), (1, 2)), types=(0, 0, 0, 0), rates=(0.2,),
               family="custom", sink_override=(3,))


def two_source():
    # 0 and 1 both reach 2; 2 is the sink. One reviewed source leaves 2 partial.
    return DAG(parents=((), (), (0, 1)), types=(0, 0, 0), rates=(0.2, 0.2),
               family="custom", sink_override=(2,))


def observation(n, k, base=None):
    f = np.zeros((n, k + 7), dtype=np.float32)
    f[:, k + 2] = 0.5 if base is None else base
    return {"features": f}


class DepthTests(unittest.TestCase):
    def test_depth_counts_edges_from_a_source(self):
        graph = diamond()
        self.assertEqual(sink_depth(graph), {3: 2})

    def test_depth_is_longest_path_not_shortest(self):
        # 0 -> 3 directly, and 0 -> 1 -> 2 -> 3, so the sink sits at depth 3.
        graph = DAG(parents=((), (0,), (1,), (0, 2)), types=(0, 0, 0, 0), rates=(0.2,),
                    family="custom", sink_override=(3,))
        self.assertEqual(sink_depth(graph), {3: 3})

    def test_depth_is_per_sink(self):
        graph = DAG(parents=((), (0,), (1,)), types=(0, 0, 0), rates=(0.2,),
                    family="custom", sink_override=(1, 2))
        self.assertEqual(sink_depth(graph), {1: 1, 2: 2})


class FrontierTests(unittest.TestCase):
    def test_a_partial_sink_puts_its_unreviewed_sources_on_the_frontier(self):
        graph = two_source()
        self.assertEqual(frontier_sources(graph, reviewed=[0]), {1})

    def test_a_fully_reviewed_sink_contributes_nothing(self):
        graph = two_source()
        self.assertEqual(coverage_truth(graph, [0, 1])[2], "inspected")
        self.assertEqual(frontier_sources(graph, reviewed=[0, 1]), set())

    def test_an_untouched_sink_contributes_nothing(self):
        graph = two_source()
        self.assertEqual(coverage_truth(graph, [])[2], "untouched")
        self.assertEqual(frontier_sources(graph, reviewed=[]), set())

    def test_reviewed_sources_are_never_on_the_frontier(self):
        graph = two_source()
        self.assertFalse(frontier_sources(graph, reviewed=[0]) & {0})

    def test_a_precomputed_coverage_map_is_honoured(self):
        graph = two_source()
        truth = {2: "partial"}
        self.assertEqual(frontier_sources(graph, reviewed=[0], truth=truth), {1})
        overridden = {2: "untouched"}
        self.assertEqual(frontier_sources(graph, reviewed=[0], truth=overridden), set())


class WeightTests(unittest.TestCase):
    def test_the_multiplier_is_the_miss_likelihood(self):
        state = downweight({}, {1, 2}, 0.9)
        self.assertAlmostEqual(state[1], 0.1)
        self.assertAlmostEqual(state[2], 0.1)

    def test_weights_compound_over_decisions(self):
        state = {}
        for _ in range(3):
            downweight(state, {1}, 0.9)
        self.assertAlmostEqual(state[1], 1e-3)

    def test_a_node_keeps_its_weight_after_leaving_the_frontier(self):
        state = downweight({}, {1}, 0.9)
        downweight(state, {2}, 0.9)
        self.assertAlmostEqual(state[1], 0.1)
        self.assertAlmostEqual(state[2], 0.1)

    def test_a_p_catch_of_one_changes_nothing(self):
        self.assertAlmostEqual(downweight({}, {1}, 1.0)[1], 0.0)


class FeatureTests(unittest.TestCase):
    def test_only_the_belief_column_moves(self):
        obs = observation(3, 2)
        before = obs["features"].copy()
        scaled = optimistic_features(obs, {1: 0.1})
        diff = np.abs(scaled - before).sum(axis=0)
        k = obs["features"].shape[1] - 7
        moved = np.flatnonzero(diff)
        self.assertEqual(moved.tolist(), [k + 2])
        self.assertAlmostEqual(float(scaled[1, k + 2]), 0.05, places=6)
        self.assertAlmostEqual(float(scaled[0, k + 2]), 0.5, places=6)

    def test_the_observation_is_not_mutated(self):
        obs = observation(3, 2)
        before = obs["features"].copy()
        optimistic_features(obs, {1: 0.1})
        np.testing.assert_array_equal(obs["features"], before)

    def test_no_weights_is_a_copy(self):
        obs = observation(3, 2)
        out = optimistic_features(obs, {})
        np.testing.assert_array_equal(out, obs["features"])
        self.assertIsNot(out, obs["features"])


if __name__ == "__main__":
    unittest.main()
