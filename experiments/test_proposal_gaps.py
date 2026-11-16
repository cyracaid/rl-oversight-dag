"""Scientific invariants for the proposal extension runner."""
import random
import unittest

import torch

import proposal_gaps as G


class ProposalGapTests(unittest.TestCase):
    def test_nstep_bootstrap_and_terminal(self):
        out = G.targets([0., 0., -2.], torch.tensor([9., 8., 7.]), 1)
        torch.testing.assert_close(out, torch.tensor([8., 7., -2.]))
        out = G.targets([0., 0., -2.], torch.tensor([9., 8., 7.]), 3)
        torch.testing.assert_close(out, torch.tensor([-2., -2., -2.]))

    def test_gain_and_adjacency(self):
        env = G.environment(91, 'normal', 1.)
        reviewed = [False] * G.M.N
        x = G.features(env, 'gain', reviewed, reviewed, G.M.R)
        self.assertEqual(x.shape, (G.M.N, G.M.K + 8))
        expected = torch.tensor([env['belief'].gain(i) / len(env['sinks'])
                                 for i in range(G.M.N)])
        torch.testing.assert_close(x[:, -1], expected)
        self.assertGreater(env['A'].count_nonzero().item(), 0)

    def test_drift_changes_truth_not_graph(self):
        a = G.environment(11, 'normal', 1.)
        b = G.environment(11, 'normal', 1e6)
        self.assertEqual(a['nodes'], b['nodes'])
        self.assertEqual(a['coins'], b['coins'])
        self.assertEqual(a['catch_uniforms'], b['catch_uniforms'])
        self.assertGreaterEqual(sum(b['base']), sum(a['base']))
        self.assertNotEqual(a['base'], b['base'])

    def test_replay_and_confidence(self):
        a = G.environment(51, 'normal', 1.)
        b = G.environment(51, 'noise', 1.)
        self.assertEqual(a['base'], b['base'])
        self.assertEqual(a['catch_uniforms'], b['catch_uniforms'])
        self.assertNotEqual(a['conf'], b['conf'])
        c = G.environment(51, 'oracle', 1.)
        self.assertEqual(c['conf'], [0. if v else 1. for v in c['base']])

    def test_all_optimizers_backward(self):
        for method in ['reinforce', 'ac', 'nstep3', 'nstep5']:
            torch.manual_seed(1)
            model = G.Agent('gain')
            loss, _, _ = G.rollout(model, 72, 'normal', 'gain', method, train=True)
            self.assertTrue(torch.isfinite(loss))
            loss.backward()
            self.assertTrue(any(p.grad is not None for p in model.policy.parameters()))
            if method != 'reinforce':
                self.assertTrue(any(p.grad is not None for p in model.critic.parameters()))


if __name__ == '__main__':
    unittest.main()
