#!/usr/bin/env python3
"""The two layer-split tables stay two. No data needed."""

from __future__ import annotations

import unittest

import run_layered_report as R


class LayerGuardTest(unittest.TestCase):
    def test_named_layers_pass(self):
        R.check_layers([{"layer": layer} for layer in ("value", "evidence", "argument")])

    def test_pooling_is_refused(self):
        for bad in ("all", "mixed", "pooled", "", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                R.check_layers([{"layer": bad}])

    def test_a_missing_layer_is_refused(self):
        with self.assertRaises(ValueError):
            R.check_layers([{"policy": "m1_first"}])


class RenderedReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sleep = R.sleep_rows()
        cls.sci = R.sciForge_rows()
        cls.text = R.render(cls.sleep, cls.sci)

    def test_every_row_names_its_instance_and_layer(self):
        for row in self.sleep + self.sci:
            self.assertIn(row["layer"], {"value", "evidence", "argument"})
            self.assertTrue(row["instance"])

    def test_sleep_recall_is_measured(self):
        for row in self.sleep:
            for k in R.KS:
                self.assertGreaterEqual(row["recall"][str(k)], 0.0)
                self.assertLessEqual(row["recall"][str(k)], 1.0)

    def test_unmeasured_cells_say_why(self):
        for row in self.sci:
            self.assertIsNone(row["localization_at_1"])
            self.assertTrue(row["blocker"])

    def test_report_has_one_table_per_instance_and_no_pooled_row(self):
        self.assertEqual(self.text.count("\n| policy |"), 1)
        self.assertEqual(self.text.count("\n| instance | layer |"), 1)
        self.assertNotIn("pooled |", self.text)
        self.assertIn("There is no pooled row", self.text)


if __name__ == "__main__":
    unittest.main()
