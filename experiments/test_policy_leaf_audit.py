import unittest
from policy_leaf_audit import WorldTable, evaluate


class LeafAuditTests(unittest.TestCase):
    def test_inherited_error_survives_child_review(self):
        table = WorldTable([[], [0]], [1., 0.], [1], 1.)
        tree = [dict(history=[], action=1),
                dict(history=[[1, 1]], mass=1., weighted_errors=1.)]
        result = evaluate(table, tree, 1., catch=1.)
        self.assertEqual(result['errors'], 1.)

    def test_probabilistic_repair_and_impossible_flag(self):
        table = WorldTable([[]], [.4], [0])
        tree = [dict(history=[], action=0),
                dict(history=[[0, 0]], mass=.64, weighted_errors=.04),
                dict(history=[[0, 1]], mass=.36, weighted_errors=0.)]
        self.assertAlmostEqual(evaluate(table, tree, .04)['errors'], .04)
        tree[1]['mass'] = .63
        with self.assertRaises(AssertionError):
            evaluate(table, tree, .04)


if __name__ == '__main__':
    unittest.main()
