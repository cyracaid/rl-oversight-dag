import copy
import itertools
import unittest
import numpy as np
from belief import ParticleBelief
from sampled_planning import world_errors
import outcome_averaged_rollout as oa


class OutcomeAveragedTests(unittest.TestCase):
    def belief(self, catch=.7):
        return ParticleBelief([[], [0], [0]], range(3), [1, 2],
                              {(0, 1): .6, (0, 2): .6}, [.4, .3, .2], catch, 64, 9)

    def scalar(self, b, available, remaining, samples, seed, averaged):
        # Independent per-node catch enumeration; no recursive branch helper.
        worlds = np.random.default_rng(seed).integers(b.M, size=samples)
        catches = np.random.default_rng(seed+20000000).random((samples, b.N)) < b.p_catch
        result = {}
        for first in [i for i, ok in enumerate(available) if ok]:
            total = 0.
            for trial, world in enumerate(worlds):
                outcomes = itertools.product([False, True], repeat=b.N) if averaged else [catches[trial]]
                for coins in outcomes:
                    weight = np.prod([b.p_catch if x else 1-b.p_catch for x in coins]) if averaged else 1.
                    if not weight:
                        continue
                    p = copy.deepcopy(b); p.rng = np.random.default_rng(seed+trial+100000)
                    base = b.B[:, world].copy(); edges = b.C[:, world].copy()
                    mask = list(available); action = first
                    for step in range(remaining):
                        flag = bool(world_errors(base, edges, b)[action] and coins[action])
                        if flag:
                            base[action] = False
                        p.observe(action, flag); mask[action] = False
                        if step+1 < remaining:
                            action = p.best_action(mask)
                    total += weight*sum(world_errors(base, edges, b)[b.is_sink])
            result[first] = float(total/samples)
        return result

    def test_independent_adaptive_catch_enumeration_and_control(self):
        b = self.belief()
        for averaged in [True, False]:
            expected = self.scalar(b, [True]*3, 3, 5, 17, averaged)
            action, d = oa.choose(b, [True]*3, 3, 5, 17, averaged)
            for a, value in expected.items():
                self.assertAlmostEqual(d['candidate_values'][a], value, places=12)
            order = [b.best_action([True]*3)]+[a for a in expected if a != b.best_action([True]*3)]
            self.assertEqual(action, min(order, key=expected.get))
            self.assertLessEqual(d['simulated_reviews'], 3*5*7)
            self.assertAlmostEqual(d['max_mass_error'], 0., places=12)

    def test_deterministic_catches_and_inherited_error(self):
        for catch in [0., 1.]:
            b = ParticleBelief([[], [0]], range(2), [1], {(0, 1): 1.},
                               [1., 0.], catch, 64, 2)
            a, d = oa.choose(b, [True, True], 1, 3, 8)
            self.assertEqual(d['candidate_values'][1], 1.)
            self.assertEqual(d['candidate_values'][0], 1.-catch)
            self.assertEqual(d['simulated_reviews'], 6)
            _, mask_d = oa.choose(b, [False, True], 1, 3, 8)
            self.assertEqual(list(mask_d['candidate_values']), [1])

    def test_reproducibility_shared_worlds_and_nonmutation(self):
        b = self.belief(); before = copy.deepcopy(b)
        a, d = oa.choose(b, [True]*3, 2, 7, 23)
        self.assertEqual((a, d), oa.choose(b, [True]*3, 2, 7, 23))
        _, control = oa.choose(b, [True]*3, 2, 7, 23, False)
        self.assertEqual(d['world_indices_sha256'], control['world_indices_sha256'])
        self.assertEqual(d['posterior_seed_base'], control['posterior_seed_base'])
        np.testing.assert_array_equal(b.B, before.B)
        np.testing.assert_array_equal(b.C, before.C)
        self.assertEqual(b.rng.bit_generator.state, before.rng.bit_generator.state)
        self.assertEqual(b.n_degenerate, before.n_degenerate)

    def test_invalid_budgets(self):
        b = self.belief()
        for mask, remaining, samples in [([True]*3, 0, 4), ([True]*3, 4, 4),
                                         ([True]*3, 2, 0), ([True], 1, 4)]:
            with self.assertRaises(ValueError):
                oa.choose(b, mask, remaining, samples)

    def test_selector_integrates_actual_feedback_policy(self):
        from exact_small_graph import ExactReview
        from integrate_particle_policy import integrate
        b = self.belief()
        env = ExactReview([[], [0], [0]], [.4, .3, .2], sinks=[1, 2], catch=.7)
        for method in ['averaged', 'sampled-control']:
            result = integrate(env, b, 2, 0, method, oa.selector)
            self.assertAlmostEqual(result['leaf_mass'], 1.)
            self.assertGreaterEqual(result['errors'], 0.)
            for node in result['tree']:
                if 'action' in node:
                    self.assertEqual(node['detail']['search']['averaged'], method == 'averaged')
                    self.assertNotIn(node['action'], [a for a, flag in node['history']])


if __name__ == '__main__':
    unittest.main()
