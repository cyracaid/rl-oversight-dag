"""Tests for the depth-two planner and the frozen verdict rules."""
import unittest

import numpy as np

from dag_role3.graphs import DAG
from dag_role3.planning import Planner, Topology, belief_column
from dag_role3.policies import marginal_scores


def observation(graph, belief, edge_prob, sinks, mask=None):
    n = graph.n
    features = np.zeros((n, 8), dtype=np.float32)
    features[:, 0] = 1.0          # one type, so k = 1 and k + 2 = 3
    features[:, 3] = belief
    features[:, 4] = 0.0
    edge_index = graph.edge_index()
    return {
        "features": features,
        "mask": np.ones(n, dtype=bool) if mask is None else np.asarray(mask, bool),
        "edge_index": edge_index,
        "edge_probability": np.full(edge_index.shape[1], edge_prob),
        "topological_order": np.array(graph.topo),
        "sink_ids": np.asarray(sinks),
    }


def chain_observation(length=4, belief=None, edge_prob=0.8):
    parents = tuple(() if i == 0 else (i - 1,) for i in range(length))
    graph = DAG(parents=parents, types=(0,) * length, rates=(0.5,), family="custom")
    belief = [0.5] * length if belief is None else belief
    return graph, observation(graph, belief, edge_prob, [length - 1])


class DerivativeTests(unittest.TestCase):
    def test_matches_the_forward_derivative_used_by_the_rule(self):
        # 0 -> 1 -> 3, 0 -> 2 -> 3, so the two paths share a root.
        graph = DAG(parents=((), (0,), (0,), (1, 2)), types=(0,) * 4,
                    rates=(0.5,), family="custom")
        obs = observation(graph, [0.4, 0.6, 0.2, 0.3], 0.7, [3])
        topology = Topology(obs)
        ours = topology.derivatives(belief_column(obs)) * belief_column(obs)
        np.testing.assert_allclose(ours, marginal_scores(obs), atol=1e-12)

    def test_a_sure_input_edge_gives_unit_derivative_at_the_source(self):
        graph, obs = chain_observation(3, belief=[1.0, 0.0, 0.0], edge_prob=1.0)
        derivatives = Topology(obs).derivatives(belief_column(obs))
        self.assertAlmostEqual(derivatives[0], 1.0)

    def test_a_broken_edge_gives_zero_derivative(self):
        graph, obs = chain_observation(3, belief=[1.0, 0.0, 0.0], edge_prob=0.0)
        derivatives = Topology(obs).derivatives(belief_column(obs))
        self.assertAlmostEqual(derivatives[0], 0.0)

    def test_reviewing_a_sink_moves_the_sink_itself(self):
        graph, obs = chain_observation(2, belief=[0.0, 1.0], edge_prob=0.5)
        derivatives = Topology(obs).derivatives(belief_column(obs))
        self.assertAlmostEqual(derivatives[1], 1.0)

    def test_two_shared_paths_make_the_derivative_quadratic(self):
        # Root 0 feeds 1 and 2, both feeding sink 3, every edge certain. Then
        # e3 = 1 - (1 - b0)^2, so the forward derivative is 2(1 - b0): it
        # vanishes at b0 = 1 even though the review still removes the error.
        graph = DAG(parents=((), (0,), (0,), (1, 2)), types=(0,) * 4,
                    rates=(0.5,), family="custom")
        half = observation(graph, [0.5, 0.0, 0.0, 0.0], 1.0, [3])
        self.assertAlmostEqual(
            Topology(half).derivatives(belief_column(half))[0], 1.0)
        certain = observation(graph, [1.0, 0.0, 0.0, 0.0], 1.0, [3])
        self.assertAlmostEqual(
            Topology(certain).derivatives(belief_column(certain))[0], 0.0)


class PlannerTests(unittest.TestCase):
    def test_acts_on_a_legal_unreviewed_node(self):
        graph, obs = chain_observation(4)
        obs["mask"][0] = False
        action = Planner(branches=("catch",)).act(obs)
        self.assertTrue(obs["mask"][action])

    def test_is_deterministic(self):
        graph, obs = chain_observation(4)
        planner = Planner(branches=("catch", "miss"))
        self.assertEqual(planner.act(obs), planner.act(obs))

    def test_a_single_hub_makes_one_step_and_two_steps_agree(self):
        # Independent leaves feeding one sink: no shared ancestor, so the second
        # step cannot interact with the first and the planner keeps the rule's
        # first choice.
        parents = ((), (), (), (0, 1, 2))
        graph = DAG(parents=parents, types=(0,) * 4, rates=(0.2,), family="custom")
        obs = observation(graph, [0.9, 0.5, 0.1, 0.0], 0.9, [3])
        scores = marginal_scores(obs)
        available = np.flatnonzero(obs["mask"])
        expected = int(available[np.argmax(scores[available])])
        self.assertEqual(Planner(branches=("catch",)).act(obs), expected)

    def test_the_full_variant_prefers_a_node_that_is_likely_to_miss(self):
        # Documented defect, not a bug: the environment lowers the belief after
        # a missed review, so a planner that weights both outcomes reads "this
        # node will probably be missed, and then its belief drops" as an
        # improvement. It prefers the low-risk leaf for that reason alone.
        parents = ((), (), (), (0, 1, 2))
        graph = DAG(parents=parents, types=(0,) * 4, rates=(0.2,), family="custom")
        obs = observation(graph, [0.9, 0.3, 0.05, 0.0], 0.9, [3])
        scores = marginal_scores(obs)
        available = np.flatnonzero(obs["mask"])
        expected = int(available[np.argmax(scores[available])])
        self.assertEqual(expected, 0)
        self.assertEqual(Planner(branches=("catch",)).act(obs), expected)
        self.assertNotEqual(Planner(branches=("catch", "miss")).act(obs), expected)


if __name__ == "__main__":
    unittest.main()
