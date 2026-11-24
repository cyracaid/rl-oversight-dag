#!/usr/bin/env python3
"""The two layer-split tables stay two. No data needed."""

from __future__ import annotations

import unittest

import run_layered_report as R
from sync_sciforge_injection import payload_digest


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

    def test_the_measured_columns_are_measured_and_the_unmeasured_one_says_why(self):
        for row in self.sci:
            self.assertGreater(row["classes"], 0)
            self.assertLessEqual(row["caught"], row["classes"])
            for key in ("localization_at_1", "localization_at_1_isolated"):
                self.assertGreaterEqual(row[key], 0.0)
                self.assertLessEqual(row[key], 1.0)
            self.assertEqual(row["clean_twin_violations"], 0)
            self.assertIsNone(row["propagation_recall"])
            self.assertTrue(row["blocker"])

    def test_the_isolated_ranking_is_the_easier_condition(self):
        # If the mixed number ever overtook the isolated one the ordering would be
        # doing something the report does not describe, so pin the direction.
        for row in self.sci:
            self.assertLessEqual(row["localization_at_1"], row["localization_at_1_isolated"])

    def test_the_audit_covers_its_whole_vocabulary(self):
        self.assertEqual(sum(row["classes"] for row in self.sci), 15)
        self.assertEqual(sum(row["caught"] for row in self.sci), 15)

    def test_sciforge_numbers_carry_their_provenance(self):
        document = R._load(R.SCI_SOURCE)
        self.assertEqual(document["provenance"]["sha256"], payload_digest(document["payload"]))
        self.assertEqual(document["provenance"]["commit"] is None, False)

    def test_an_edited_number_cannot_pass_as_measured(self):
        # The digest only helps if the reader checks it, so the check is what the test
        # drives: a doctored payload must fail the same call the report makes.
        document = R._load(R.SCI_SOURCE)
        document["payload"]["summary"]["by_layer"]["argument"]["localization_at_1_mixed"] = 0.99
        self.assertNotEqual(document["provenance"]["sha256"], payload_digest(document["payload"]))

    def test_report_has_one_table_per_instance_and_no_pooled_row(self):
        self.assertEqual(self.text.count("\n| policy |"), 1)
        self.assertEqual(self.text.count("\n| layer | classes |"), 1)
        self.assertNotIn("pooled |", self.text)
        self.assertIn("There is no pooled row", self.text)


if __name__ == "__main__":
    unittest.main()
