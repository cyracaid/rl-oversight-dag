import unittest
from pathlib import Path

import numpy as np

import analyze_proposal_gaps as A


class AnalysisTests(unittest.TestCase):
    def test_constant_paired_difference(self):
        result = A.bootstrap(np.full((5, 200), -2.), 8, draws=1000)
        self.assertEqual(result['mean'], -2.)
        self.assertEqual(result['adjusted_ci'], [-2., -2.])

    def test_seed_uncertainty_is_not_flattened(self):
        delta = np.repeat(np.arange(5.)[:, None], 200, axis=1)
        result = A.bootstrap(delta, 8, draws=5000)
        self.assertLess(result['ci95'][0], 1.)
        self.assertGreater(result['ci95'][1], 3.)
        self.assertLessEqual(result['adjusted_ci'][0], result['ci95'][0])
        self.assertGreaterEqual(result['adjusted_ci'][1], result['ci95'][1])
        self.assertEqual(result, A.bootstrap(delta, 8, draws=5000))

    def test_incomplete_run_rejected_before_reading_checkpoints(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            A.validate({'status': 'in_progress'}, Path('/unused'))

    def test_invalid_difference_rejected(self):
        with self.assertRaises(ValueError):
            A.bootstrap([[float('nan')]], 8)


if __name__ == '__main__':
    unittest.main()
