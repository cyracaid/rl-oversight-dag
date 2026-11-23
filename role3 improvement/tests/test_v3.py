import unittest
from dataclasses import replace
import numpy as np

from dag_role3 import DAG, OversightEnv, sample_episode, generate_graph
from dag_role3.belief import ParticleBelief
from dag_role3.policies import marginal_scores
from dag_role3.training import potential, replay_observation


class V3Tests(unittest.TestCase):
    def test_recovery_replays_past_fixes(self):
        graph = DAG(((), (0,)), (0, 0), (.5,))
        pf = ParticleBelief(graph, np.array([.5, .5]), np.array([1.]), 1024, 8)
        self.assertTrue(pf.update(0, True, 1.))
        # Simulate finite-population loss of an unreviewed local error hypothesis.
        pf.base[:] = False
        pf.propagate()
        self.assertTrue(pf.update(1, True, 1.))
        self.assertEqual(pf.recoveries, 1)
        np.testing.assert_allclose(pf.probabilities()[0], [0., 0.])
        self.assertEqual(len(pf.history), 2)

    def test_analytic_chain_posterior(self):
        # B has no local error and always inherits A. A miss at B gives P(A)=1/6.
        graph = DAG(((), (0,)), (0, 1), (.5, 0.))
        pf = ParticleBelief(graph, np.array([.5, 0.]), np.array([1.]), 100000, 4)
        self.assertTrue(pf.update(1, False, .8))
        self.assertAlmostEqual(pf.probabilities()[0][0], 1/6, delta=.005)

    def test_marginal_matches_numerical_derivative(self):
        graph = DAG(((), (0,), (0,), (1, 2)), (0,)*4, (.3,))
        obs = OversightEnv.from_seed(graph, 42, budget=2).observation()
        def objective(base):
            effective = np.zeros(graph.n)
            for v in graph.topo:
                product = 1.
                for e, (u, child) in enumerate(obs['edge_index'].T):
                    if child == v:
                        product *= 1 - obs['edge_probability'][e] * effective[u]
                effective[v] = 1 - (1-base[v]) * product
            return effective[list(graph.sinks)].sum()
        base = obs['features'][:,3].astype(float)
        numeric = []
        for i in range(graph.n):
            plus, minus = base.copy(), base.copy()
            plus[i] += 1e-6
            minus[i] -= 1e-6
            numeric.append(base[i] * (objective(plus)-objective(minus))/2e-6)
        np.testing.assert_allclose(marginal_scores(obs), numeric, atol=1e-8)
        # Correlated posterior marginals cannot be substituted into that derivative.
        obs['features'][:,4] = .99
        np.testing.assert_allclose(marginal_scores(obs), numeric, atol=1e-8)

    def test_shaped_return_preserves_objective(self):
        env = OversightEnv.from_seed(generate_graph('real'), 32)
        obs = env.observation()
        first_potential = potential(obs)
        raw_return = shaped_return = 0.
        while not env.done:
            action = int(np.flatnonzero(obs['mask'])[0])
            next_obs, reward, _, _ = env.step(action)
            raw_return += reward
            shaped_return += reward + potential(next_obs) - potential(obs)
            obs = next_obs
        self.assertAlmostEqual(shaped_return, raw_return-first_potential)

    def test_snapshot_cannot_be_mutated(self):
        graph = generate_graph('spike')
        snapshot = sample_episode(graph, 1)
        edge = next(iter(snapshot.edge_coins))
        with self.assertRaises(TypeError):
            snapshot.edge_coins[edge] = False
        with self.assertRaises(TypeError):
            snapshot.edge_probs[edge] = .1

    def test_invalid_snapshot_rejected(self):
        graph = generate_graph('real')
        snapshot = sample_episode(graph, 1)
        for invalid in (replace(snapshot, confidence=(.5,)),
                        replace(snapshot, edge_probs={}),
                        replace(snapshot, review_uniforms=(float('nan'),)*graph.n),
                        replace(snapshot, confidence=(2.,)*graph.n)):
            with self.assertRaises(ValueError):
                OversightEnv(graph, invalid)

    def test_audit_return_is_detached(self):
        env = OversightEnv.from_seed(generate_graph('real'), 8, budget=1)
        env.step(0)
        audit = env.final_audit()
        audit['trace'][0]['node'] = -99
        self.assertEqual(env.final_audit()['trace'][0]['node'], 0)

    def test_replay_retains_exact_model_inputs(self):
        obs = OversightEnv.from_seed(generate_graph('real'), 3).observation()
        compact = replay_observation(obs)
        self.assertEqual(set(compact), {'features', 'edge_index', 'mask'})
        for key in compact:
            np.testing.assert_array_equal(compact[key], obs[key])

    def test_graph_copies_mutable_inputs(self):
        parents = [[], [0]]
        graph = DAG(parents, [0, 0], [.3])
        parents[1].clear()
        self.assertEqual(graph.parents, ((), (0,)))
        with self.assertRaises(ValueError):
            DAG(((),), (0.5,), (.3,))
