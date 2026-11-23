"""Budget, calendar pairing, reviewer-feedback and end-to-end sleep replay checks."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import evaluate_sleep as sleep


def fixture(directory):
    daily = directory / "generated.csv"
    corrected = directory / "generated_corrected.csv"
    for path in (daily, corrected):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("pid", "day_num", "tb", "tb_ap", "ts", "ts_ap", "ta",
                             "ta_ap", "tg", "tg_ap", "waso_est"))
            for person in range(20):
                for day in range(12):
                    # Include gap and nonuniform days, repeat a few public QC alerts.
                    offset = day + (day >= 6)
                    awake = 6 * 3600 + 60 * (person % 6 + 10 * (day % 3))
                    waso = "00:05" if path == corrected and day in (2, 3) else "00:24"
                    writer.writerow((f"fixture-{person}", offset, 10 * 3600, "PM", 10 * 3600 + 35 * 60,
                                     "PM", awake, "AM", 6 * 3600 + 47 * 60, "AM", waso))
    return daily, corrected


def smoke(out):
    with tempfile.TemporaryDirectory() as tmp:
        daily, corrected = fixture(Path(tmp))
        subprocess.run([sys.executable, str(Path(sleep.__file__)), "--daily-csv", str(daily),
                        "--corrected-daily-csv", str(corrected), "--cohort", "synthetic_smoke",
                        "--legacy-seeds", "2", "--out", str(out)], check=True)
    return json.loads(out.read_text(encoding="utf-8"))


class TestSleep(unittest.TestCase):
    def test_finding_only_changes_second_day(self):
        days = [1, 2, 4, 5]
        scores = [3, 0, 2, 0]
        args = (scores, days, sleep.windows(days), [0, 1, 2, 3], [3, 1, 2, 0])
        found, _ = sleep.choose(*args, lambda i: i == 0)
        missed, _ = sleep.choose(*args, lambda i: False)
        self.assertEqual(found["feedback"], (0, 1))
        self.assertEqual(found["qc"], (0, 2))
        self.assertEqual(missed["feedback"], missed["qc"])
        self.assertEqual(sleep.windows(days), [(0, 1), (2, 3)])
        for name, chosen in found.items():
            if name != "before_review":
                self.assertEqual(len(set(chosen)), 2)

    def test_unrelated_nights_stay_corrupted(self):
        from datetime import timedelta
        clock = sleep.original.BASE
        raw = {field: clock + timedelta(hours=h)
               for field, h in zip(sleep.original.FIELDS, (22, 22.5, 30, 30.25))}
        good = sleep.original.compute(raw, 0)
        raw["bed"] -= timedelta(hours=12)
        bad = sleep.original.compute(raw, 0)
        target = sleep.original.conclusions(sleep.original.aggregate([good] * 4))
        scores, ties, _ = sleep.scenario_score([good] * 4, [bad, bad, good, good], {0, 1},
                                           [1, 2, 3, 4], [(0, 1), (1, 2), (2, 3)],
                                           [0, 1, 2, 3], [2, 3, 0, 1], target)
        self.assertGreater(scores["before_review"][0], 0)
        self.assertEqual(scores["random"], scores["before_review"])
        self.assertEqual(scores["contiguous"], [0] * 5)
        self.assertTrue(ties["qc_first_max_tied"])

    def test_participants_split_before_cases_are_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            result = smoke(path / "smoke_result.json")
            self.assertEqual(result["status"], "synthetic_implementation_check")
            splits = ["development", "evaluation"]
            self.assertEqual(sum(result["conditions"][s + "/clean"]["participants"] for s in splits), 20)
            for group in splits:
                clean = result["conditions"][group + "/clean"]
                self.assertEqual(clean["paired_differences"]["contiguous_minus_qc"]["mean"], 0)
                manual = result["conditions"][group + "/manual"]
                self.assertEqual(manual["participants"] * 2,
                                 result["scenario_ledger"][group + "/manual/nights_with_input_changes"])
                self.assertEqual(clean["participants"] * 4 * 10,
                                 result["conditions"][group + "/consecutive"]["scenarios"])
            daily, _ = fixture(path)
            legacy_path = path / "legacy.json"
            with open(os.devnull, "w") as sink:
                subprocess.run([sys.executable, str(Path(sleep.original.__file__)),
                                "--daily-csv", str(daily), "--out", str(legacy_path),
                                "--seeds", "2"], check=True, stdout=sink)
            legacy_data = json.loads(legacy_path.read_text(encoding="utf-8"))
            baseline = result["historical_baseline_check"]
            self.assertEqual(baseline["header"], legacy_data["header"])
            self.assertEqual(baseline["visible_b2_qc_four_conclusions"],
                             legacy_data["policies"]["visible|b2"]["qc"]["mean"])


if __name__ == "__main__":
    if "--smoke-out" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--smoke-out", type=Path, required=True)
        smoke(ap.parse_args().smoke_out)
    else:
        unittest.main()
