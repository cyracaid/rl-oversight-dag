import unittest

from compare_bounded_planning import evaluate
from exact_small_graph import ExactReview


class BoundedPlanningTests(unittest.TestCase):
    def test_full_depth_matches_bellman(self):
        for parents in [[[], [0]], [[], [], [0, 1]], [[], [0], [0]]]:
            env = ExactReview(parents, [.2, .7, .4][:len(parents)])
            for budget in range(1, len(parents)+1):
                result = evaluate(env, budget, budget)
                self.assertAlmostEqual(result['errors'], env.solve(budget)['optimal'])

    def test_budget_one_matches_greedy(self):
        env = ExactReview([[], [0], [0]], [.3, .1, .8])
        self.assertAlmostEqual(evaluate(env, 1, 1)['errors'], env.solve(1)['greedy'])

    def test_inherited_error_and_no_detection(self):
        env = ExactReview([[], [0]], [1., 0.], 1., 1.)
        self.assertEqual(evaluate(env, 1, 1)['errors'], 0.)
        env = ExactReview([[], [0]], [1., 0.], 1., 0.)
        self.assertEqual(evaluate(env, 2, 2)['errors'], 1.)


if __name__ == '__main__':
    unittest.main()
