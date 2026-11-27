import unittest
from policy_leaf_audit import WorldTable
from solver_action_audit import solve, saved_detail_equal


class SolverAuditTests(unittest.TestCase):
    def test_json_candidate_keys_normalized_but_values_still_checked(self):
        self.assertTrue(saved_detail_equal({'candidate_values': {3: .125}},
                                           {'candidate_values': {'3': .125}}))
        self.assertFalse(saved_detail_equal({'candidate_values': {3: .125}},
                                            {'candidate_values': {'3': .25}}))

    def test_single_node_catch_and_budget(self):
        table = WorldTable([[]], [.4], [0])
        self.assertAlmostEqual(solve(table, 0)['optimal'], .4)
        self.assertAlmostEqual(solve(table, 1)['optimal'], .04)

    def test_inherited_error_and_two_reviews(self):
        table = WorldTable([[], [0]], [1., 0.], [1], 1.)
        result = solve(table, 1, catch=1.)
        self.assertEqual(result['optimal'], 0.)
        self.assertEqual(result['optimal_first'], 0)
        self.assertEqual(result['greedy'], 0.)


if __name__ == '__main__':
    unittest.main()
