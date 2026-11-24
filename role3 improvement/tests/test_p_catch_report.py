"""Tests for the frozen verdict logic in report_p_catch.py.

These run on synthetic summary rows, so they check that the code implements the
decision table in PREREGISTER_P_CATCH.md and nothing about the sweep numbers.
"""
import unittest

from report_p_catch import verdict


def rows(gains, lows=None, highs=None):
    """Build the cells ``verdict`` reads: spike, marginal, four grid points."""
    grid = (0.60, 0.75, 0.90, 1.00)
    lows = lows or [g - 0.05 for g in gains]
    highs = highs or [g + 0.05 for g in gains]
    return [dict(family="spike", policy="marginal", p_catch=p,
                 gain_vs_confidence=g, paired_lo=lo, paired_hi=hi,
                 mean_sink_errors=1.0)
            for p, g, lo, hi in zip(grid, gains, lows, highs)]


class VerdictTests(unittest.TestCase):
    def test_monotone_and_separated_is_robust(self):
        result = verdict(rows([0.40, 0.30, 0.20, 0.10]))
        self.assertEqual(result["label"], "robust")

    def test_non_monotone_but_directional_is_direction_robust(self):
        result = verdict(rows([0.40, 0.20, 0.30, 0.10]))
        self.assertEqual(result["label"], "direction-robust")
        self.assertTrue(result["p1"])

    def test_reversed_cell_forces_conditional(self):
        result = verdict(rows([0.40, 0.30, 0.20, -0.10]))
        self.assertTrue(result["p4"])
        self.assertEqual(result["label"], "conditional")

    def test_fewer_than_three_separated_intervals_fails_p1(self):
        # Sign holds on every cell, but only two intervals exclude zero.
        gains = [0.40, 0.30, 0.20, 0.10]
        lows = [0.01, 0.02, -0.01, -0.02]
        result = verdict(rows(gains, lows=lows))
        self.assertTrue(result["p1_sign"])
        self.assertFalse(result["p1_separated"])
        self.assertEqual(result["label"], "conditional")

    def test_increasing_advantage_is_inverted(self):
        result = verdict(rows([0.10, 0.20, 0.30, 0.40]))
        self.assertTrue(result["p2_inverted"])
        self.assertEqual(result["label"], "inverted")


if __name__ == "__main__":
    unittest.main()
