"""Locality tests for the v2 order mechanism.

These exist because the v2 gate reported the opposite of the truth: it said the defect
needed the chain's rank pattern, while a rule reading two adjacent comparisons per node
solves it exactly. See `outputs/ordered-gate-v2/CORRECTION.md`.

The first test is a *negative* result pinned in place. If a future mechanism replaces M2′,
its analogue must assert the reverse (accuracy well below 1), which is the only way this
failure cannot be repeated silently.
"""
import unittest

import numpy as np

from dag_role3 import generate_graph
from dag_role3.ordered import OrderedEnv, sample_ordered_episode

from run_ordered_gate import relational_features


def local_rule(clocks):
    """First-descent start, last-ascent end: each node's own two adjacent residuals."""
    c = np.asarray(clocks, float)
    desc = [i for i in range(len(c) - 1) if c[i] >= c[i + 1]]
    return tuple(sorted((desc[0], desc[-1] + 1))) if desc else None


class M2PrimeIsLocal(unittest.TestCase):
    def test_descent_ascent_rule_recovers_the_pair_exactly(self):
        for q, block in ((0.5, range(5600, 5640)), (1.0, range(5640, 5700))):
            hits = seen = 0
            for seed in block:
                graph = generate_graph("real", 5160 + (seed - block.start) % 12)
                episode = sample_ordered_episode(graph, seed, q=q)
                if episode.transposed is None:
                    continue
                seen += 1
                hits += local_rule(episode.clocks) == episode.misplaced
            self.assertGreater(seen, 10, f"no transposed episodes at q={q}")
            self.assertEqual(hits, seen,
                             f"M2' stopped being locally solvable at q={q}; that would be "
                             "news, and the correction file says otherwise")

    def test_rule_is_wrong_on_a_double_transposition(self):
        """Sanity check on the *limitation*: two disjoint swaps break the endpoints rule."""
        clocks = [100.0, 400.0, 430.0, 900.0, 950.0]
        # swap (0,2) and (3,4): recorded is not monotone, and endpoints rule sees (0,1)
        recorded = [clocks[2], clocks[1], clocks[0], clocks[4], clocks[3]]
        self.assertNotEqual(local_rule(recorded), (0, 2))


class RelationalFeaturesAreDegenerate(unittest.TestCase):
    def test_one_distinct_row_per_episode(self):
        """The v2 relational feature set is broadcast, so it cannot rank positions.

        This is what made G1b's pooled AUC 0.822 a measurement of clean-vs-transposed.
        """
        for seed in range(5600, 5610):
            graph = generate_graph("real", 5160 + (seed - 5600) % 12)
            episode = sample_ordered_episode(graph, seed, q=0.5)
            obs = OrderedEnv(graph, episode, budget=8).observation()
            rows = np.unique(np.round(relational_features(episode, obs), 9), axis=0)
            self.assertEqual(rows.shape[0], 1,
                             "feature set became position-specific; the v2 gate's numbers "
                             "must then be re-read, not the other way round")


if __name__ == "__main__":
    unittest.main()
