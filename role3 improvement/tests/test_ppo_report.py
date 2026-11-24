"""Tests for the frozen PPO verdict rules."""
import unittest

from report_ppo import p2_check, verdict


def row(delta, low, high):
    return {"delta_vs_marginal": delta, "ci_low": low, "ci_high": high}


class VerdictTests(unittest.TestCase):
    def test_all_positive_and_separated_is_a_third_loss(self):
        self.assertEqual(verdict([row(0.3, 0.1, 0.5), row(0.4, 0.2, 0.6)]),
                         "third-loss")

    def test_all_intervals_touching_zero_is_a_tie(self):
        self.assertEqual(verdict([row(0.1, -0.1, 0.3), row(0.2, -0.2, 0.6)]),
                         "tie")

    def test_all_negative_and_separated_flips_the_headline(self):
        self.assertEqual(verdict([row(-0.3, -0.5, -0.1)]), "learned-wins")

    def test_sign_flip_is_unstable_not_an_average(self):
        self.assertEqual(verdict([row(0.3, 0.1, 0.5), row(-0.1, -0.3, 0.1)]),
                         "unstable")

    def test_mixed_separation_with_one_sign_is_not_promoted(self):
        self.assertEqual(verdict([row(0.3, 0.1, 0.5), row(0.1, -0.05, 0.25)]),
                         "mixed")


class P2Tests(unittest.TestCase):
    def test_seed_inside_the_reinforce_bound(self):
        reference = [{"delta": 0.3}, {"delta": 0.51}, {"delta": 0.4}]
        result = p2_check([row(0.1, 0.0, 0.2)], reference)
        self.assertTrue(result["all_seeds_inside"])
        self.assertAlmostEqual(result["bound"], 0.4033333333333333, places=9)

    def test_seed_above_the_bound_fails_p2(self):
        reference = [{"delta": 0.3}, {"delta": 0.51}, {"delta": 0.4}]
        result = p2_check([row(0.5, 0.3, 0.7)], reference)
        self.assertFalse(result["all_seeds_inside"])
        self.assertFalse(result["mean_inside"])


if __name__ == "__main__":
    unittest.main()
