"""Tests for the sampled counterfactual value and the frozen verdict rules."""
import unittest

import numpy as np

from dag_role3.counterfactual import CounterfactualValue
from dag_role3.graphs import DAG
from report_value import verdict


def observation(graph, belief, edge_prob, sinks):
    n = graph.n
    features = np.zeros((n, 8), dtype=np.float32)
    features[:, 0] = 1.0          # one type, k = 1, so k + 2 = 3 is the belief
    features[:, 3] = belief
    edge_index = graph.edge_index()
    return {
        "features": features,
        "mask": np.ones(n, dtype=bool),
        "edge_index": edge_index,
        "edge_probability": np.full(edge_index.shape[1], edge_prob),
        "topological_order": np.array(graph.topo),
        "sink_ids": np.asarray(sinks),
    }


class SharedAncestorTests(unittest.TestCase):
    """0 -> 1 -> 3, 0 -> 2 -> 3: one root error, two open paths to the sink."""

    def setUp(self):
        self.graph = DAG(parents=((), (0,), (0,), (1, 2)), types=(0, 0, 0, 0),
                         rates=(0.5,), family="custom")
        self.obs = observation(self.graph, belief=[0.5, 0, 0, 0],
                               edge_prob=1.0, sinks=[3])

    def test_reviewing_the_root_fixes_the_sink_every_time_it_is_wrong(self):
        view = CounterfactualValue(self.obs, particles=20_000, seed=1)
        value = view.value([0], p_catch=1.0)
        # The root is wrong with probability 0.5 and then carries the whole sink.
        self.assertAlmostEqual(value[0], 0.5, delta=0.02)

    def test_reviewing_a_middle_node_cannot_fix_an_inherited_error(self):
        view = CounterfactualValue(self.obs, particles=20_000, seed=1)
        value = view.value([1])
        self.assertAlmostEqual(value[1], 0.0, delta=0.002)

    def test_hit_rate_scales_the_value_linearly(self):
        full = CounterfactualValue(self.obs, particles=20_000, seed=1)
        half = CounterfactualValue(self.obs, particles=20_000, seed=1)
        self.assertAlmostEqual(full.value([0], p_catch=1.0)[0],
                               2 * half.value([0], p_catch=0.5)[0], delta=0.02)


class PropagationTests(unittest.TestCase):
    def test_shared_ancestor_is_counted_once_per_particle(self):
        graph = DAG(parents=((), (0,), (1,)), types=(0, 0, 0), rates=(0.5,),
                    family="custom")
        obs = observation(graph, belief=[1.0, 0, 0], edge_prob=1.0, sinks=[2])
        view = CounterfactualValue(obs, particles=100, seed=0)
        # Source error is certain and both edges are open, so the sink is certain.
        self.assertTrue(view.effective()[:, 2].all())


class VerdictTests(unittest.TestCase):
    def test_lower_bound_above_forty_percent_is_strong(self):
        self.assertEqual(verdict([0.45, 0.8]), "strong")

    def test_lower_bound_above_zero_is_partial(self):
        self.assertEqual(verdict([0.05, 0.3]), "partial")

    def test_interval_containing_zero_is_null(self):
        self.assertEqual(verdict([-0.02, 0.1]), "null")

    def test_interval_entirely_negative_is_worse(self):
        self.assertEqual(verdict([-0.09, -0.01]), "worse")


if __name__ == "__main__":
    unittest.main()
