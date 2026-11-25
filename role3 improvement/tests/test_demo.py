"""Tests for the receipt demo: it may quote numbers, never invent them.

The page exists to make one claim visible -- remove the receipt and the question
"what did we miss?" stops having an answer. That claim is only honest if every
number on the page traces back to ``outputs/supervisor-v1/summary.json``. These
tests pin that, so a later hand edit cannot turn the demo into a second source.
"""
import json
import re
import unittest

from make_demo import FAMILIES, build


def payload_of(html):
    match = re.search(
        r'<script id="payload" type="application/json">(.*?)</script>', html, re.S
    )
    if match is None:
        raise AssertionError("rendered page has no payload block")
    return json.loads(match.group(1))


def summary_rows():
    from make_demo import SUMMARY

    payload = json.loads(SUMMARY.read_text())
    return {r["family"]: r for r in payload["rows"] if r["policy"] == "marginal"}


class DemoNumbersTest(unittest.TestCase):
    def setUp(self):
        self.html, self.data = build()
        self.rows = summary_rows()

    def test_every_value_is_traced_to_the_summary(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                cell = self.data["cells"][family]
                row = self.rows[family]
                self.assertEqual(cell["wrong"], row["wrong_sinks"])
                self.assertEqual(cell["honest"]["uncovered"], row["declared_gap"])
                self.assertEqual(cell["honest"]["false_inspected"], row["false_inspection"])
                self.assertAlmostEqual(cell["honest"]["share"], row["declared_share"], places=12)
                self.assertEqual(cell["graphs"], row["graphs"])

    def test_rendered_payload_matches_build(self):
        self.assertEqual(payload_of(self.html), self.data)

    def test_no_placeholder_survives(self):
        self.assertNotIn("__PAYLOAD__", self.html)

    def test_story_invariant_holds_per_family(self):
        # The honest column splits the surviving errors into "outside coverage"
        # and "inside full coverage but wrong". If that ever fails to add up, the
        # three-column story is wrong and the page must not render.
        for family in FAMILIES:
            with self.subTest(family=family):
                cell = self.data["cells"][family]
                self.assertEqual(
                    cell["wrong"],
                    cell["honest"]["uncovered"] + cell["honest"]["false_inspected"],
                )

    def test_overclaim_denies_every_surviving_error(self):
        # overclaim's whole point: no error is admitted as uncovered.
        for family in FAMILIES:
            with self.subTest(family=family):
                cell = self.data["cells"][family]
                self.assertEqual(cell["overclaim"]["uncovered"], 0)
                self.assertEqual(cell["overclaim"]["false_inspected"], cell["wrong"])

    def test_footer_names_the_register_and_the_block(self):
        for needle in ("v1:p_catch>=0.90", "5400", "make_demo.py", "summary.json"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.data["footer"])


if __name__ == "__main__":
    unittest.main()
