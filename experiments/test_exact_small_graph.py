import itertools
import unittest

from exact_small_graph import ExactReview, suite


def brute(parents, prior, propagation, catch, budget):
    """Independent scalar enumeration including pre-drawn per-node catch coins."""
    n = len(parents)
    edges = [(p, i) for i, ps in enumerate(parents) for p in ps]
    probabilities = prior + [propagation]*len(edges) + [catch]*n
    worlds = []
    for bits in itertools.product([False, True], repeat=len(probabilities)):
        weight = 1.
        for bit, p in zip(bits, probabilities):
            weight *= p if bit else 1-p
        if weight:
            worlds.append((bits[:n], bits[n:n+len(edges)], bits[n+len(edges):], weight))
    sinks = [i for i in range(n) if not any(i in ps for ps in parents)]

    def errors(base, coins):
        result = list(base)
        for i in range(n):
            for e, (p, child) in enumerate(edges):
                if child == i:
                    result[i] = result[i] or (result[p] and coins[e])
        return result

    def visit(states, available, left):
        if not left:
            return sum(w*sum(errors(b, c)[i] for i in sinks) for b, c, u, w in states)
        values = []
        for a in available:
            branches = [[], []]
            for base, coins, catches, weight in states:
                flag = errors(base, coins)[a] and catches[a]
                new = list(base)
                if flag:
                    new[a] = False
                branches[int(flag)].append((new, coins, catches, weight))
            values.append(sum(visit(branch, [i for i in available if i != a], left-1)
                              for branch in branches if branch))
        return min(values)
    return visit(worlds, list(range(n)), budget)


class ExactPlanningTests(unittest.TestCase):
    def test_designated_outputs_exclude_isolated_nodes(self):
        env = ExactReview([[], [], [0]], [0., 1., 0.], sinks=[2])
        self.assertEqual(env.solve(0)['initial'], 0.)
        self.assertEqual(ExactReview([[], [], [0]], [0., 1., 0.]).solve(0)['initial'], 1.)

    def test_conditioned_generator_restores_original_configuration(self):
        from exact_conditioned_graph import case, S
        from belief import conf_posterior
        before = dict(S.CFG)
        c = case(32000)
        self.assertEqual(S.CFG, before)
        self.assertEqual(c, case(32000))
        self.assertEqual(c['sinks'], [4, 5])
        for conf, prior, conditioned in zip(c['confidence'], c['type_prior'], c['conditioned_prior']):
            self.assertAlmostEqual(conditioned, conf_posterior(conf, prior))

    def test_independent_exhaustive_oracle(self):
        for parents in [[[], [0]], [[], [], [0, 1]]]:
            prior = [.2, .7, .4][:len(parents)]
            env = ExactReview(parents, prior, .6, .9)
            for budget in range(1, len(parents)+1):
                self.assertAlmostEqual(env.solve(budget)['optimal'],
                                       brute(parents, prior, .6, .9, budget), places=11)

    def test_budget_one_and_optimality(self):
        for _, parents in suite()[:4]:
            env = ExactReview(parents, [.1, .2, .3, .4, .5, .6])
            self.assertAlmostEqual(env.solve(1)['gap'], 0.)
            result = env.solve(2)
            self.assertGreaterEqual(result['greedy']+1e-10, result['optimal'])
            self.assertGreaterEqual(result['fixed']+1e-10, result['optimal'])

    def test_inherited_flag_does_not_clear_upstream(self):
        env = ExactReview([[], [0]], [1., 0.], 1., 1.)
        self.assertAlmostEqual(env.fixed_value([1]), 1.)
        self.assertAlmostEqual(env.fixed_value([0]), 0.)

    def test_all_nodes_and_probability_limits(self):
        env = ExactReview([[], [0], [1]], [.2, .7, .4], .6, .9)
        self.assertAlmostEqual(env.solve(3)['optimal'], env.fixed_value([0, 1, 2]))
        self.assertAlmostEqual(env.fixed_value([0, 1, 2]), env.fixed_value([2, 1, 0]))
        self.assertAlmostEqual(ExactReview([[], [0]], [1., 1.], 1., 1.).solve(2)['optimal'], 0.)
        self.assertAlmostEqual(ExactReview([[], [0]], [.2, .7], 0., 0.).solve(2)['optimal'], .7)


if __name__ == '__main__':
    unittest.main()
