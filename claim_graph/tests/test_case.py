"""Tests for the claim graph layer.

These run on synthetic rows shaped like the case tables so the suite does not
need network access. The recomputation check is tested against a hand-built
batch table, because that check is the one that decides whether an audit number
is independent of the table it audits.
"""
import random
import unittest

from claim_graph import case, plan


STABLE = "[2.0, 2.1, 2.05, 1.95, 2.0]"
STRADDLING = "[2.0, 2.1, 0.5, 1.95, 2.0]"


def comparison(cell="c1", contrast="a/b", metric="m1", field="f1",
               presented=True, ratios=STABLE, num=0.01, den=0.02):
    return {"cell": cell, "contrast": contrast, "metric": metric, "field": field,
            "status": "full_five_batches",
            "ratio_of_medians": "2.0",
            "passes_screen": "True" if presented else "False",
            "paired_ratios": ratios,
            "same_direction_count": "5",
            "twice_larger_relative_mad": "0.5",
            "numerator_relative_mad": str(num),
            "denominator_relative_mad": str(den)}


def raw(cell="c1", metric="m1", field="f1", a=(10, 20, 5), b=(5, 10, 2)):
    rows = []
    for batch, (x, y) in enumerate(zip(a, b)):
        rows.append({"cell": cell, "method": "a", "metric": metric, "field": field,
                     "batch": str(batch), "value_us": str(x)})
        rows.append({"cell": cell, "method": "b", "metric": metric, "field": field,
                     "batch": str(batch), "value_us": str(y)})
    return rows


class DisagreementTests(unittest.TestCase):
    def test_five_ratios_on_one_side_are_unanimous(self):
        self.assertEqual(case.disagreement([2.0, 2.1, 1.9, 2.05, 2.2]), 0)

    def test_a_straddling_ratio_is_counted_once(self):
        self.assertEqual(case.disagreement([2.0, 2.1, 0.5, 2.05, 2.2]), 1)

    def test_a_ratio_of_exactly_one_counts_for_neither_side(self):
        self.assertEqual(case.disagreement([1.0, 1.0, 2.0, 2.0, 2.0]), 0)


class BuildTests(unittest.TestCase):
    def test_ratios_matching_raw_are_marked_recomputed(self):
        claims = case.build([comparison(ratios="[2.0, 2.0, 2.5]")], raw())
        self.assertTrue(claims[0].recomputed)
        self.assertFalse(claims[0].weak)

    def test_disagreement_with_raw_raises(self):
        with self.assertRaises(ValueError):
            case.build([comparison(ratios="[9.0, 9.0, 9.0]")], raw())

    def test_within_method_contrast_is_not_recomputed_and_not_flagged(self):
        claims = case.build([comparison(contrast="a:f1", ratios="[3.0, 3.2, 3.1]")],
                            raw())
        self.assertFalse(claims[0].recomputed)


class PlanTests(unittest.TestCase):
    def setUp(self):
        rows = [comparison(cell=f"c{i % 3}",
                           ratios=STRADDLING if i % 2 else STABLE)
                for i in range(12)]
        self.claims = case.build(rows, [])
        self.provenance = {"case": "x", "pin": "y", "tables": {},
                           "recomputed_from_raw": 0}

    def test_stability_puts_every_weak_claim_before_any_stable_one(self):
        order = plan.stability(self.claims, random.Random(0))
        flags = [c.weak for c in order]
        self.assertEqual(flags, sorted(flags, reverse=True))

    def test_coverage_is_monotone_in_budget(self):
        order = plan.stability(self.claims, random.Random(0))
        rows = plan.coverage(self.claims, order, (2, 4, 8), "stability")
        hits = [r["weak_inspected"] for r in rows]
        self.assertEqual(hits, sorted(hits))

    def test_queue_never_contains_a_filtered_out_claim(self):
        self.assertTrue(all(c.presented for c in plan.queue(self.claims,
                                                            random.Random(0))))

    def test_receipt_is_json_serialisable_and_keeps_the_seed(self):
        import json
        data = plan.receipt(self.claims, self.provenance, budgets=(2, 4))
        json.dumps(data)
        self.assertEqual(data["seed"], 20261124)


if __name__ == "__main__":
    unittest.main()
