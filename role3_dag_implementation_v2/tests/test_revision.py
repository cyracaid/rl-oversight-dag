import unittest
import numpy as np
from dag_role3 import DAG, EpisodeSnapshot, OversightEnv, sample_episode, generate_graph
from dag_role3.belief import ParticleBelief
from dag_role3.policies import choose


class RevisionTests(unittest.TestCase):
    def test_review_uniforms_match_across_confidence_modes(self):
        g = generate_graph("spike", 4)
        snapshots = [sample_episode(g, 25, mode) for mode in ("normal", "noise", "oracle")]
        for snap in snapshots[1:]:
            self.assertEqual(snap.review_uniforms, snapshots[0].review_uniforms)
            self.assertEqual(snap.source_errors, snapshots[0].source_errors)
            self.assertEqual(snap.edge_coins, snapshots[0].edge_coins)

    def test_terminal_mask_and_zero_budget(self):
        g = generate_graph("real")
        for budget in (0, 1):
            env = OversightEnv.from_seed(g, 1, budget)
            if budget:
                env.step(0)
            self.assertFalse(env.observation()["mask"].any())
            with self.assertRaises(RuntimeError):
                env.step(1)

    def test_particle_observation_updates_ancestor(self):
        g = DAG(((), (0,)), (0, 1), (.5, 0.0))
        pf = ParticleBelief(g, np.array([.5, 0]), np.array([1]), 1024, 4)
        self.assertTrue(pf.update(1, True, 1))
        base, effective = pf.probabilities()
        np.testing.assert_allclose(base, [1, 0])
        np.testing.assert_allclose(effective, [1, 1])

    def test_particle_miss_matches_bayes(self):
        g = DAG(((),), (0,), (.5,))
        pf = ParticleBelief(g, np.array([.5]), np.array([]), 20000, 22)
        self.assertTrue(pf.update(0, False, .8))
        self.assertAlmostEqual(pf.probabilities()[0][0], 1/6, delta=.01)

    def test_impossible_particle_evidence(self):
        g = DAG(((),), (0,), (0.,))
        pf = ParticleBelief(g, np.array([0.]), np.array([]), 16, 9)
        self.assertFalse(pf.update(0, True, .9))

    def test_integration_without_truth_leakage(self):
        g = generate_graph("real")
        s = sample_episode(g, 12)
        other = EpisodeSnapshot(tuple(not v for v in s.source_errors),
                                {e:not v for e,v in s.edge_coins.items()}, s.edge_probs,
                                s.confidence, s.review_uniforms, s.seed)
        for particles in (0, 128):
            env = OversightEnv(g,s,particles=particles)
            env2 = OversightEnv(g,other,particles=particles)
            for key in env.observation():
                np.testing.assert_equal(env.observation()[key], env2.observation()[key])
            initial = env.observation()["features"]
            env.step(0)
            np.testing.assert_array_equal(initial, env.reset()["features"])

    def test_marginal_prioritizes_common_source(self):
        g = DAG(((), (0,), (0,)), (0, 1, 1), (.5, 0.), spike_probability=1.)
        env = OversightEnv.from_seed(g, 12, budget=2, confidence_mode="noise")
        self.assertEqual(choose(env.observation(),"marginal"), 0)

    def test_fractional_budget_rejected(self):
        with self.assertRaises(ValueError):
            OversightEnv.from_seed(generate_graph("real"), 1, budget=2.5)
