"""Information access and paired-evaluation checks for development controls."""
import unittest
import numpy as np
import torch
import proposal_gaps as P
import compare_type_priors as C


class TypePriorTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_type_prior_ignores_confidence_and_hidden_truth(self):
        a = P.environment(1000, 'normal', 1.)
        b = P.environment(1000, 'noise', 2.)
        x, y = C.type_belief(a, 1000), C.type_belief(b, 1000)
        np.testing.assert_array_equal(x.B, y.B)
        np.testing.assert_array_equal(x.C, y.C)
        self.assertEqual(x.M, a['belief'].M)
        self.assertEqual(x.p_catch, a['belief'].p_catch)
        self.assertEqual(x.desc, a['belief'].desc)

    def test_ranking_uses_type_rate_and_index_ties(self):
        nodes = [{'type': 1}, {'type': 4}, {'type': 4}, {'type': 0}]
        self.assertEqual(C.type_action(nodes, [False]*4), 1)
        self.assertEqual(C.type_action(nodes, [False, True, False, False]), 2)

    def test_controls_keep_truth_stream_and_budget(self):
        for policy in C.CONTROLS:
            a, ta = C.control_rollout(1000, 'normal', 1., policy)
            b, tb = C.control_rollout(1000, 'noise', 1., policy)
            self.assertEqual(a, b)
            self.assertEqual([r['action'] for r in ta], [r['action'] for r in tb])
            self.assertEqual(len(ta), P.M.R)
            self.assertEqual(len({r['action'] for r in ta}), P.M.R)
            self.assertEqual(a['initial_errors']-a['errors'],
                             sum(r['realized_sink_reduction'] for r in ta))
            if policy == 'type ranking':
                self.assertIsNone(a['degeneracies'])
                self.assertTrue(all(r['degenerate'] is None for r in ta))

    def test_descriptive_pairing_preserves_seeds(self):
        rows = [dict(condition='noise/matched', graph=g, policy=p, seed=s,
                     errors=e, degeneracies=None, flags=2, reduction=1,
                     type_counts=[0, 0, 0, 0, 16])
                for g in (1000, 1001)
                for p, s, e in [('belief greedy', None, 4),
                                 ('type belief greedy', None, 2),
                                 ('type ranking', None, 3),
                                 ('observed/nstep3', 1, 1),
                                 ('observed/nstep3', 2, 3)]]
        summary = C.summarize(rows)
        one = next(r for r in summary if r['policy']=='observed/nstep3' and r['seed']==1)
        self.assertEqual(one['delta_vs_type_belief'], -1)
        self.assertEqual(one['episodes'], 2)
        all_seeds = next(r for r in summary if r['policy']=='observed/nstep3' and r['seed']=='all')
        self.assertEqual(all_seeds['errors'], 2)
        self.assertEqual(all_seeds['delta_vs_type_belief'], 0)


if __name__ == '__main__':
    unittest.main()
