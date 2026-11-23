"""The standard-library belief is checked against exact enumeration and against the numpy original (no full runs)."""
import itertools
import random
import unittest

import belief as numpy_belief
import belief_stdlib as B

PARENTS = [[], [], [0, 1], [2]]
TOPO = [0, 1, 2, 3]
SINKS = {3}
EDGE_PROB = {(0, 2): 0.6, (1, 2): 0.5, (2, 3): 0.7}
BASE_PROB = [0.3, 0.2, 0.1, 0.15]
CATCH = 0.9
EDGES = [(0, 2), (1, 2), (2, 3)]


def propagate(base, coins):
    err = [False] * 4
    for i in TOPO:
        err[i] = base[i]
        for p in PARENTS[i]:
            if err[p] and coins[EDGES.index((p, i))]:
                err[i] = True
    return err


def states(weights_fn=None):
    """All (base, coins, weight) configurations with prior weights, optionally re-weighted."""
    for base in itertools.product([False, True], repeat=4):
        for coins in itertools.product([False, True], repeat=3):
            weight = 1.0
            for i, b in enumerate(base):
                weight *= BASE_PROB[i] if b else 1 - BASE_PROB[i]
            for k, c in enumerate(coins):
                weight *= EDGE_PROB[EDGES[k]] if c else 1 - EDGE_PROB[EDGES[k]]
            yield list(base), list(coins), weight


def exact_p_err(observations=()):
    """Exact posterior expectation of err after a sequence of (node, flagged) observations."""
    rows = [(base, coins, weight) for base, coins, weight in states()]
    for node, flagged in observations:
        new_rows = []
        for base, coins, weight in rows:
            err = propagate(base, coins)
            weight *= (CATCH * err[node]) if flagged else (1 - CATCH * err[node])
            if flagged:
                base = [False if i == node else b for i, b in enumerate(base)]
            new_rows.append((base, coins, weight))
        rows = new_rows
    total = sum(weight for _, _, weight in rows)
    out = [0.0] * 4
    for base, coins, weight in rows:
        for i, e in enumerate(propagate(base, coins)):
            out[i] += weight * e / total
    return out


def exact_gain(i):
    total = 0.0
    for base, coins, weight in states():
        before = propagate(base, coins)[3]
        cleared = [False if k == i else b for k, b in enumerate(base)]
        total += weight * (before - propagate(cleared, coins)[3])
    return CATCH * total


def make(cls=B.ParticleBelief, m=8192, seed=1, base_prob=BASE_PROB, catch=CATCH):
    return cls(PARENTS, TOPO, SINKS, EDGE_PROB, base_prob, catch, n_particles=m, seed=seed)


class SamplingTests(unittest.TestCase):
    def test_bernoulli_bits_have_the_right_frequency_and_edge_cases(self):
        belief = make(m=8192)
        for p in (0.01, 0.3, 0.5, 0.99):
            ones = belief._bernoulli_bits(p).bit_count() / belief.M
            self.assertAlmostEqual(ones, p, delta=0.03, msg=str(p))
        self.assertEqual(belief._bernoulli_bits(0.0), 0)
        self.assertEqual(belief._bernoulli_bits(1.0), (1 << belief.M) - 1)

    def test_permute_maps_bit_k_to_bit_index_k(self):
        belief = make(m=8)
        row = 0b10110010           # bits 7..0
        self.assertEqual(belief._permute(row, list(range(8))), row)
        self.assertEqual(belief._permute(row, [1, 1, 1, 1, 0, 0, 0, 0]), 0b00001111)  # bit 1 is set, bit 0 is not
        index = [7, 6, 5, 4, 3, 2, 1, 0]
        reversed_row = belief._permute(row, index)
        self.assertEqual([(reversed_row >> k) & 1 for k in range(8)], [(row >> j) & 1 for j in index])

    def test_same_seed_same_particles_different_seed_different_particles(self):
        a, b, c = make(seed=3), make(seed=3), make(seed=4)
        self.assertEqual((a.base_bits, a.coin_bits), (b.base_bits, b.coin_bits))
        self.assertNotEqual(a.base_bits, c.base_bits)

    def test_constructor_validation(self):
        with self.assertRaises(ValueError):
            make(m=100)
        with self.assertRaises(ValueError):
            make(catch=1.5)


class ExactEnumerationTests(unittest.TestCase):
    def assert_close(self, got, want, delta=0.03):
        for i, (g, w) in enumerate(zip(got, want)):
            self.assertAlmostEqual(g, w, delta=delta, msg=f"node {i}: {g} vs {w}")

    def test_prior_error_and_base_probabilities_and_gain(self):
        belief = make()
        self.assert_close(belief.p_base(), BASE_PROB)
        self.assert_close(belief.p_err(), exact_p_err())
        self.assert_close([belief.gain(i) for i in range(4)], [exact_gain(i) for i in range(4)])

    def test_posterior_after_a_flag(self):
        belief = make()
        belief.observe(2, True)
        self.assertEqual(belief.base_bits[2], 0)
        want = exact_p_err([(2, True)])
        self.assert_close(belief.p_err(), want, delta=0.04)

    def test_posterior_after_a_clean_review_and_after_a_sequence(self):
        belief = make()
        belief.observe(3, False)
        self.assert_close(belief.p_err(), exact_p_err([(3, False)]), delta=0.04)
        belief = make(seed=2)
        belief.observe(2, True)
        belief.observe(3, False)
        self.assert_close(belief.p_err(), exact_p_err([(2, True), (3, False)]), delta=0.05)

    def test_best_action_is_the_exact_argmax_and_ranking_is_sorted(self):
        belief = make()
        exact = [exact_gain(i) for i in range(4)]
        available = [True] * 4
        self.assertEqual(belief.best_action(available), max(range(4), key=lambda i: exact[i]))
        ranked = belief.ranking(available)
        self.assertEqual(ranked[0][0], belief.best_action(available))
        self.assertEqual([g for _, g in ranked], sorted((g for _, g in ranked), reverse=True))
        self.assertEqual({i for i, _ in belief.ranking([False, True, False, True])}, {1, 3})

    def test_agrees_with_the_numpy_original_on_the_same_model(self):
        a, b = make(B.ParticleBelief, seed=5), make(numpy_belief.ParticleBelief, seed=5)
        for x, y in zip(a.p_err(), list(b.p_err())):
            self.assertAlmostEqual(x, y, delta=0.03)
        for i in range(4):
            self.assertAlmostEqual(a.gain(i), b.gain(i), delta=0.03)
        for belief in (a, b):
            belief.observe(2, True)
            belief.observe(3, False)
        for x, y in zip(a.p_err(), list(b.p_err())):
            self.assertAlmostEqual(x, y, delta=0.05)


class DegenerateTests(unittest.TestCase):
    def test_a_flag_that_no_particle_explains_is_counted_and_changes_nothing_else(self):
        belief = make(m=64, base_prob=[0.0, 0.0, 0.0, 0.0])
        before = list(belief.err)
        belief.observe(3, True)
        self.assertEqual((belief.n_degenerate, belief.err), (1, before))

    def test_an_observation_the_model_excludes_is_counted_not_a_division_by_zero(self):
        belief = make(m=64, base_prob=[1.0, 0.0, 0.0, 0.0], catch=1.0)
        belief.base_bits[3] = 0
        belief.coin_bits = [(1 << 64) - 1] * 3        # every error propagates to the sink
        belief._refresh()
        belief.observe(3, False)                       # catch rate 1 and every particle erroneous
        self.assertEqual(belief.n_degenerate, 1)


class LargerGraphTests(unittest.TestCase):
    def random_graph(self, n=80, layers=4, seed=0):
        rng = random.Random(seed)
        per = n // layers
        layer = [i // per for i in range(n)]
        parents = [[] if layer[i] == 0 else rng.sample(
            [j for j in range(n) if layer[j] == layer[i] - 1], rng.choice([1, 2])) for i in range(n)]
        return parents, sorted(range(n), key=lambda i: layer[i]), {i for i in range(n) if layer[i] == layers - 1}

    def test_a_full_review_sequence_runs_and_stays_consistent(self):
        parents, topo, sinks = self.random_graph()
        edge_prob = {(p, i): 0.6 for i, ps in enumerate(parents) for p in ps}
        belief = B.ParticleBelief(parents, topo, sinks, edge_prob, [0.1] * 80, 0.9, n_particles=256, seed=1)
        available = [True] * 80
        rng = random.Random(2)
        for _ in range(8):
            action = belief.best_action(available)
            self.assertTrue(available[action])
            available[action] = False
            belief.observe(action, rng.random() < 0.3)
            self.assertTrue(all(0.0 <= p <= 1.0 for p in belief.p_err()))
            self.assertEqual(len(belief.base_bits), 80)
        self.assertTrue(all(row < (1 << 256) for row in belief.base_bits + belief.coin_bits))


if __name__ == "__main__":
    unittest.main()


class CompareHarnessTests(unittest.TestCase):
    def test_gate_logic(self):
        import compare_belief_stdlib as C
        good = dict(equivalence=dict(paired_difference_stdlib_minus_numpy=dict(mean=0.01, low=-0.05, high=0.07)),
                    latency={"80": dict(stdlib=dict(rank_all_s=0.2), numpy=dict(rank_all_s=0.2)),
                             "500": dict(stdlib=dict(rank_all_s=4.0), numpy=dict(rank_all_s=3.0))})
        self.assertTrue(C.evaluate_gate(good)["passed"])
        wide = dict(good, equivalence=dict(paired_difference_stdlib_minus_numpy=dict(mean=0.0, low=-0.2, high=0.2)))
        self.assertFalse(C.evaluate_gate(wide)["passed"])
        slow = dict(good, latency={"80": dict(stdlib=dict(rank_all_s=0.2), numpy=dict(rank_all_s=0.2)),
                                   "500": dict(stdlib=dict(rank_all_s=6.0), numpy=dict(rank_all_s=3.0))})
        self.assertFalse(C.evaluate_gate(slow)["passed"])
        self.assertFalse(C.evaluate_gate(dict(good, latency={}))["passed"])

    def test_bootstrap_is_deterministic_and_brackets_the_mean(self):
        import compare_belief_stdlib as C
        diffs = [0, 1, -1, 0, 2, -2, 1, 0]
        a, b = C.bootstrap_ci(diffs, 500), C.bootstrap_ci(diffs, 500)
        self.assertEqual(a, b)
        self.assertLessEqual(a["low"], a["mean"])
        self.assertLessEqual(a["mean"], a["high"])

    def test_smoke_run_writes_reports_and_refuses_overwrite(self):
        import json
        import tempfile
        from pathlib import Path
        import compare_belief_stdlib as C
        with tempfile.TemporaryDirectory() as tmp:
            C.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
            report = json.loads(Path(tmp, "a", "results.json").read_text())
            self.assertIn("gate", report)
            self.assertEqual(set(report["equivalence"]["mean_errors"]), {"numpy", "stdlib"})
            self.assertTrue(Path(tmp, "a", "results.md").exists())
            with self.assertRaises(SystemExit):
                C.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])

    def test_bad_arguments(self):
        import compare_belief_stdlib as C
        for extra in (["--graphs", "0"], ["--particles", "100"], ["--sizes", "4"], ["--repeats", "0"]):
            with self.assertRaises(SystemExit):
                C.parse(["--out-dir", "x", *extra])
