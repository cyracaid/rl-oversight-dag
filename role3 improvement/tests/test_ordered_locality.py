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


class NoPermutationMechanismIsRelational(unittest.TestCase):
    """The closure of the order line, pinned as a test.

    `analyse_order_localisability.py` and `outputs/ordered-v3-design/DESIGN.md` claim that in a
    monotone chain the culprit set is `{p : rank(clock_p) != p}` for *any* permutation mechanism.
    If that ever stops being true the design study is wrong and v3 becomes possible again, so it
    is worth an assertion rather than a paragraph.
    """

    def _rank_rule(self, clocks):
        order = np.argsort(np.argsort(np.asarray(clocks, float)))
        return {p for p in range(len(clocks)) if abs(order[p] - p) > 0.5}

    def test_rank_rule_solves_single_and_double_transpositions(self):
        """Accuracy over draws, not per draw: measurement noise can invert two close clocks.

        The design study measures 0.998-1.000 at the sampler's own settings, so a per-draw
        assertion would be false for the wrong reason.
        """
        rng = np.random.default_rng(20261125)
        for mechanism in ("single", "double", "double_adjacent"):
            hits = 0
            for _ in range(400):
                true = np.cumsum(rng.uniform(20, 480, 4)) + rng.uniform(1200, 1560)
                recorded = list(true)
                culprits = set()
                if mechanism == "single":
                    i, j = sorted(rng.choice(4, 2, replace=False))
                    recorded[i], recorded[j] = recorded[j], recorded[i]
                    culprits = {int(i), int(j)}
                else:
                    if mechanism == "double_adjacent":
                        pairs = [(0, 1), (2, 3)]
                    else:
                        perm = rng.permutation(4)
                        pairs = [(perm[0], perm[1]), (perm[2], perm[3])]
                    for a, b in pairs:
                        recorded[a], recorded[b] = recorded[b], recorded[a]
                        culprits |= {int(a), int(b)}
                recorded = np.asarray(recorded) + rng.normal(0, 8, 4)
                hits += self._rank_rule(recorded) == culprits
            self.assertGreaterEqual(hits / 400, 0.98, mechanism)

    def test_descent_rule_fails_where_rank_rule_does_not(self):
        """The planned v3 mechanism: adjacent comparisons lose, rank does not."""
        # true chain 1300 < 1500 < 1900 < 2400, with positions (0,1) and (2,3) swapped
        recorded = np.array([1500.0, 1300.0, 2400.0, 1900.0])
        self.assertNotEqual(local_rule(recorded), {0, 1, 2, 3})
        self.assertEqual(self._rank_rule(recorded), {0, 1, 2, 3})


if __name__ == "__main__":
    unittest.main()
