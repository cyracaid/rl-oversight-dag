import tempfile
import unittest
from pathlib import Path

from triage_bench.audit.coverage import (UNAVAILABLE, coverage, summarize_export,
                                         to_export_receipts)
from triage_bench.audit.receipts import (Receipt, append_receipt, read_receipts,
                                         verify_chain)


def R(row_key, submitted="2026-11-20T01:00:00+00:00", opened="2026-11-20T00:58:00+00:00",
      verdict="corrected", **kw):
    return Receipt(artifact_version="sha256:v1", verdict=verdict, row_key=row_key,
                   opened_at=opened, submitted_at=submitted, **kw)


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "receipts.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_chain_links_and_verifies(self):
        append_receipt(self.path, R("h1"))
        append_receipt(self.path, R("h2"))
        self.assertTrue(verify_chain(self.path)[0])

    def test_deleted_line_breaks_chain(self):
        append_receipt(self.path, R("h1"))
        append_receipt(self.path, R("h2"))
        append_receipt(self.path, R("h3"))
        lines = self.path.read_text().splitlines()
        self.path.write_text("\n".join(lines[:1] + lines[2:]) + "\n")
        self.assertFalse(verify_chain(self.path)[0])

    def test_rejected_verdict_is_refused(self):
        with self.assertRaises(ValueError):
            R("h1", verdict="looks-fine")


class DurationTests(unittest.TestCase):
    def test_duration_is_derived_not_stored(self):
        rec = R("h1")
        self.assertAlmostEqual(rec.duration_s, 120.0)

    def test_no_timestamps_gives_none_not_zero(self):
        rec = R("h1", opened=None, submitted=None)
        self.assertIsNone(rec.duration_s)


class ExportBridgeTests(unittest.TestCase):
    def test_maps_row_keys_to_nodes(self):
        receipts = [R("h1"), R("h2")]
        out, counters = to_export_receipts(receipts, {"h1": "n1", "h2": "n2"})
        self.assertEqual([r["node_id"] for r in out], ["n1", "n2"])
        self.assertEqual(out[0]["duration_min"], 2.0)
        self.assertEqual(counters["receipts_unmapped"], 0)

    def test_unmapped_receipt_is_counted_not_dropped(self):
        out, counters = to_export_receipts([R("h1"), R("zzz")], {"h1": "n1"})
        self.assertEqual(len(out), 1)
        self.assertEqual(counters["receipts_unmapped"], 1)

    def test_rereview_supersedes_but_is_counted(self):
        out, counters = to_export_receipts(
            [R("h1"), R("h1", submitted="2026-11-21T01:00:00+00:00")],
            {"h1": "n1"})
        self.assertEqual(len(out), 1)
        self.assertEqual(counters["receipts_superseded"], 1)

    def test_receipt_without_submitted_at_is_flagged(self):
        out, counters = to_export_receipts([R("h1", opened=None, submitted=None)], {"h1": "n1"})
        self.assertEqual(out, [])
        self.assertEqual(counters["receipts_without_submitted_at"], 1)


class CoverageTests(unittest.TestCase):
    def test_unreviewed_errors_are_unknown_not_correct(self):
        block = coverage([{"node_id": "n1", "reviewed_at": "t", "verdict": "accepted",
                           "duration_min": 2.0}], ["n1", "n2", "n3"])
        self.assertEqual(block["errors_without_receipt"], 2)
        self.assertAlmostEqual(block["coverage_fraction"], 1 / 3)
        self.assertEqual(block["missing_error_ids"], ["n2", "n3"])

    def test_recall_at_minutes_unavailable_when_any_duration_missing(self):
        block = coverage([
            {"node_id": "n1", "reviewed_at": "t", "verdict": "accepted", "duration_min": 2.0},
            {"node_id": "n2", "reviewed_at": "t", "verdict": "accepted"},
        ], ["n1", "n2"])
        self.assertEqual(block["capabilities"]["recall_at_minutes"]["status"], UNAVAILABLE)
        self.assertIn("1/2", block["capabilities"]["recall_at_minutes"]["reason"])

    def test_recall_at_minutes_available_when_all_durations_present(self):
        block = coverage([
            {"node_id": "n1", "reviewed_at": "t", "verdict": "accepted", "duration_min": 2.0},
            {"node_id": "n2", "reviewed_at": "t", "verdict": "accepted", "duration_min": 3.5},
        ], ["n1"])
        cap = block["capabilities"]["recall_at_minutes"]
        self.assertEqual(cap["status"], "available")
        self.assertAlmostEqual(cap["minutes_total"], 5.5)

    def test_human_order_partial_without_timestamps(self):
        block = coverage([
            {"node_id": "n1", "reviewed_at": "t", "verdict": "accepted"},
            {"node_id": "n2", "verdict": "accepted"},
        ], [])
        self.assertEqual(block["capabilities"]["human_baseline_order"]["status"], "partial")

    def test_empty_error_set_is_unavailable_not_zero(self):
        block = coverage([], [])
        self.assertEqual(block["coverage_fraction"], UNAVAILABLE)

    def test_end_to_end_from_chain_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.jsonl"
            append_receipt(path, R("h1"))
            block = summarize_export(path, {"h1": "n1"}, ["n1", "n2"])
            self.assertEqual(block["coverage"]["errors_with_receipt"], 1)
            self.assertEqual(block["coverage"]["errors_without_receipt"], 1)
            self.assertEqual(block["receipts"][0]["node_id"], "n1")


if __name__ == "__main__":
    unittest.main()
