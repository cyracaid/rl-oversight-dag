"""Tests for the calibration knob and the frozen verdict rules."""
import unittest

import numpy as np

from belief_decomposition import auc, calibrated, logit, sigmoid
from report_belief import verdict


def observation(belief):
    n = len(belief)
    features = np.zeros((n, 8), dtype=np.float32)
    features[:, 0] = 1.0          # one type, so k = 1 and k + 2 = 3
    features[:, 3] = belief
    return {"features": features, "mask": np.ones(n, dtype=bool)}


class MonotoneTests(unittest.TestCase):
    def test_gamma_one_returns_the_same_object(self):
        obs = observation([0.1, 0.4, 0.9])
        self.assertIs(calibrated(obs, 1.0), obs)

    def test_a_single_map_preserves_the_pairwise_order(self):
        belief = np.array([0.02, 0.3, 0.31, 0.7, 0.99])
        for gamma in (0.5, 0.75, 1.25, 2.0):
            curved = sigmoid(gamma * logit(belief))
            self.assertTrue(np.all(np.diff(curved) > 0), msg=f"gamma={gamma}")

    def test_auc_is_identical_under_the_knob(self):
        rng = np.random.default_rng(0)
        belief = rng.random(200)
        labels = rng.random(200) < belief
        base = auc(belief, labels)
        for gamma in (0.5, 0.75, 1.25, 2.0):
            self.assertEqual(auc(sigmoid(gamma * logit(belief)), labels), base)

    def test_gamma_below_one_flattens_and_above_sharpens(self):
        belief = np.array([0.2, 0.8])
        flat = sigmoid(0.5 * logit(belief))
        sharp = sigmoid(2.0 * logit(belief))
        self.assertLess(flat[1] - flat[0], belief[1] - belief[0])
        self.assertGreater(sharp[1] - sharp[0], belief[1] - belief[0])


class AucTests(unittest.TestCase):
    def test_perfect_separation_is_one(self):
        self.assertEqual(auc([0.1, 0.9], [False, True]), 1.0)

    def test_one_class_is_undefined_not_half(self):
        self.assertIsNone(auc([0.1, 0.9], [False, False]))

    def test_ties_get_average_ranks(self):
        self.assertEqual(auc([0.5, 0.5], [False, True]), 0.5)


class VerdictTests(unittest.TestCase):
    def test_lower_bound_above_forty_percent_is_calibration_bound(self):
        self.assertEqual(verdict([0.45, 0.8]), "calibration-bound")

    def test_lower_bound_above_zero_is_partial(self):
        self.assertEqual(verdict([0.02, 0.2]), "calibration-partial")

    def test_interval_containing_zero_is_policy_bound(self):
        self.assertEqual(verdict([-0.05, 0.07]), "policy-bound")

    def test_interval_entirely_negative_is_policy_bound_strong(self):
        self.assertEqual(verdict([-0.6, -0.4]), "policy-bound-strong")


if __name__ == "__main__":
    unittest.main()
