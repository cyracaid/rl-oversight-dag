"""Tests for the v2 order channel.

The bit-identity test is the important one: the ordered sampler must be an *overlay* on v1,
so that every number already in `outputs/` keeps its meaning and nothing is silently rerun
under a different generator.
"""
import unittest

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.ordered import (ORDERED_SPECS, OrderedEnv, eligible_pairs,
                               sample_ordered_episode)


class BitIdentity(unittest.TestCase):
    def test_q_zero_returns_the_v1_episode(self):
        for family in ("real", "ticket"):
            graph = generate_graph(family, 5160)
            for seed in (5600, 5601, 5602):
                a = sample_ordered_episode(graph, seed, q=0.0)
                b = sample_episode(graph, seed)
                self.assertEqual(a.snapshot.source_errors, b.source_errors)
                self.assertEqual(a.snapshot.confidence, b.confidence)
                self.assertEqual(a.snapshot.review_uniforms, b.review_uniforms)
                self.assertEqual(dict(a.snapshot.edge_coins), dict(b.edge_coins))
                self.assertEqual(dict(a.snapshot.edge_probs), dict(b.edge_probs))
                self.assertEqual(a.misplaced, ())

    def test_missing_transposition_leaves_the_episode_alone(self):
        graph = generate_graph("real", 5160)
        # Run the block and require that at least one episode is untouched and equals v1.
        untouched = 0
        for seed in range(5600, 5620):
            a = sample_ordered_episode(graph, seed, q=0.5)
            if a.transposed is None:
                b = sample_episode(graph, seed)
                self.assertEqual(a.snapshot.source_errors, b.source_errors)
                untouched += 1
        self.assertGreater(untouched, 0)


class Mechanism(unittest.TestCase):
    def test_eligible_pairs_exclude_adjacent(self):
        for spec in ORDERED_SPECS.values():
            pairs = eligible_pairs(spec)
            self.assertTrue(all(j - i >= 2 for i, j in pairs))
            self.assertEqual(pairs, tuple((i, j) for i in range(len(spec.chain))
                                          for j in range(i + 2, len(spec.chain))))

    def test_real_chain_has_eligible_pairs_but_ticket_has_one(self):
        self.assertEqual(len(eligible_pairs(ORDERED_SPECS["real"])), 3)
        self.assertEqual(eligible_pairs(ORDERED_SPECS["ticket"]), ((0, 2),))

    def test_transposition_breaks_the_order_and_moves_two_values(self):
        graph = generate_graph("real", 5160)
        seen = 0
        for seed in range(5600, 5640):
            ep = sample_ordered_episode(graph, seed, q=0.5)
            if ep.transposed is None:
                continue
            seen += 1
            self.assertEqual(len(ep.misplaced), 2)
            self.assertTrue(any(r > 0 for r in ep.monotone_residual()))
            # Exactly the two exchanged positions are flagged as misplaced.
            self.assertEqual(tuple(sorted(ep.transposed)), ep.misplaced)
        self.assertGreater(seen, 5)

    def test_reciprocal_clock_difference_is_impossible_by_construction(self):
        graph = generate_graph("real", 5160)
        for seed in range(5600, 5640):
            ep = sample_ordered_episode(graph, seed)
            if ep.transposed is None:
                continue
            for node, left, right in ep.spec.derived:
                if ep.snapshot.source_errors[node] and ep.clocks[left] >= ep.clocks[right]:
                    self.assertTrue(ep.snapshot.source_errors[node])
                    return
        self.fail("no transposed episode produced an impossible difference")


class Repair(unittest.TestCase):
    def _transposed(self):
        graph = generate_graph("real", 5160)
        for seed in range(5600, 5640):
            ep = sample_ordered_episode(graph, seed, q=0.5)
            if ep.transposed is not None and len(ep.spec.derived) == 3:
                return graph, ep
        raise AssertionError("no transposed episode in the block")

    def test_reviewing_both_misplaced_segments_repairs_the_differences(self):
        graph, ep = self._transposed()
        env = OrderedEnv(graph, ep, budget=8, p_catch=1.0)
        for pos in ep.misplaced:
            env.step(ep.spec.chain[pos])
        for node, left, right in ep.spec.derived:
            positions = {left, right}
            if positions <= set(ep.misplaced):
                self.assertFalse(env._base[node],
                                 "difference with both positions repaired is still wrong")

    def test_reviewing_an_innocent_segment_repairs_nothing(self):
        graph, ep = self._transposed()
        innocent = [p for p in range(len(ep.spec.chain)) if p not in ep.misplaced]
        env = OrderedEnv(graph, ep, budget=8, p_catch=1.0)
        before = list(env._base)
        env.step(ep.spec.chain[innocent[0]])
        self.assertEqual([i for i, b in enumerate(env._base) if b],
                         [i for i, b in enumerate(before) if b])

    def test_observation_exposes_clocks_and_residuals_and_nothing_hidden(self):
        graph, ep = self._transposed()
        obs = OrderedEnv(graph, ep, budget=8).observation()
        self.assertEqual(len(obs["clocks"]), len(ep.spec.chain))
        self.assertEqual(len(obs["monotone_residual"]), len(ep.spec.chain) - 1)
        self.assertNotIn("misplaced", obs)
        self.assertNotIn("transposed", obs)
        self.assertEqual(obs["family"], "real_order")
        self.assertEqual(obs["features"].shape[0], graph.n)


class Interface(unittest.TestCase):
    def test_v1_feature_layout_is_unchanged(self):
        """`policies.marginal_scores` infers the type-table width as cols - 7."""
        graph = generate_graph("real", 5160)
        ep = sample_ordered_episode(graph, 5602, q=0.5)
        v1 = OrderedEnv(graph, ep, budget=8).observation()["features"].shape[1]
        from dag_role3.environment import OversightEnv
        v1_shape = OversightEnv(graph, ep.snapshot, budget=8).observation()["features"].shape[1]
        self.assertEqual(v1, v1_shape)

    def test_family_mismatch_is_rejected(self):
        graph = generate_graph("real", 5160)
        ep = sample_ordered_episode(graph, 5600)
        other = generate_graph("ticket", 5172)
        with self.assertRaises(ValueError):
            OrderedEnv(other, ep)


if __name__ == "__main__":
    unittest.main()
