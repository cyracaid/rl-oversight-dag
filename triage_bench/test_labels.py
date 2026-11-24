#!/usr/bin/env python3
"""The sleep labels in the shared `{layer, code}` shape. No data needed."""

from __future__ import annotations

import unittest

from bench.labels import LAYER, MISSING, as_error_type, as_key


class AsErrorTypeTest(unittest.TestCase):
    def test_a_code_carries_the_instance_layer(self):
        self.assertEqual(
            as_error_type("order_error"), {"layer": "value", "code": "order_error"}
        )

    def test_a_new_code_is_still_value_layer(self):
        # The layer belongs to the instance, not to a per-code lookup table, so an
        # unseen code is labelled rather than silently dropped.
        self.assertEqual(as_error_type("a_code_nobody_has_seen")["layer"], LAYER)

    def test_whitespace_around_a_code_is_not_part_of_it(self):
        self.assertEqual(as_error_type("  bed_sleep_diff_error ")["code"], "bed_sleep_diff_error")

    def test_nothing_to_label_returns_none(self):
        for blank in (None, float("nan"), "", "   ", MISSING):
            self.assertIsNone(as_error_type(blank), msg=repr(blank))

    def test_key_is_the_pair_flattened(self):
        self.assertEqual(as_key("order_error"), "value:order_error")
        self.assertEqual(as_key(None), MISSING)


if __name__ == "__main__":
    unittest.main()
