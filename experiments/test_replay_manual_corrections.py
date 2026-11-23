#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the manual-correction replay. Run: python3 experiments/test_replay_manual_corrections.py"""
import math
import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_manual_corrections as R


def _t(s):
    return datetime.strptime(s, "%m/%d/%y %H:%M")


def test_parse_time_formats():
    assert R.parse_time("3/14/27 23:30") == _t("3/14/27 23:30")
    assert R.parse_time("3/14/27 23:30:00") == _t("3/14/27 23:30")
    assert R.parse_time("3/14/27") is None
    assert R.parse_time("") is None


def test_apply_correction_same_day_pm():
    v = _t("3/15/27 00:05")
    got = R.apply_correction(v, "Same day 06:35:00 AM")
    assert (got.hour, got.minute, got.day) == (6, 35, 15)
    got = R.apply_correction(v, "Same day 1:15:00 PM")
    assert (got.hour, got.minute) == (13, 15)


def test_apply_correction_minus_hours():
    v = _t("3/15/27 13:15")
    assert R.apply_correction(v, "Minus 12 hours").hour == 1
    assert R.apply_correction(v, "Plus 2 hours").hour == 15
    assert R.apply_correction(v, "nonsense") is None


def test_compute_matches_csv_diffs_on_one_row():
    ts = dict(bed=_t("3/14/27 23:00"), sleep=_t("3/14/27 23:30"),
              awake=_t("3/15/27 01:00"), getup=_t("3/15/27 08:40"))
    v = R.compute(ts, 5)
    assert abs(v["SOL_calc"] - 0.5) < 1e-9
    assert abs(v["sleep_awake_diff"] - 1.5) < 1e-9
    assert abs(v["awake_getup_diff"] - 7.666666667) < 1e-6
    assert abs(v["TIB"] - 9.666666667) < 1e-6


def test_sink_flags_follow_config_thresholds():
    good = dict(bed=_t("3/14/27 23:00"), sleep=_t("3/14/27 23:30"),
                awake=_t("3/15/27 07:30"), getup=_t("3/15/27 08:00"))
    v = R.compute(good, 30)
    assert v["SOL_validity"] and v["WASO_validity"] and v["SE_conclusion"] and v["record_quality"]
    bad = dict(good)
    bad["sleep"] = _t("3/14/27 13:30")  # AM/PM flip
    v = R.compute(bad, 30)
    assert not v["record_quality"]


def test_real_csv_gate_and_replay_shape():
    if not os.path.exists(R.DEFAULT_CSV):
        print("skip: real CSV not found")
        return
    rows, dropped, gate_fail = R.load_rows(R.DEFAULT_CSV)
    assert not gate_fail, gate_fail[:3]
    assert len(rows) + len(dropped) == 75
    assert len(rows) == 53
    for r in rows:
        assert 0 <= r["sink_errors"] <= 4
        assert r["defective"] <= set(R.LEAVES)
        assert all(0.0 <= r["suspicion"][n] <= 1.0 for n in R.NODES)


def test_root_cause_review_clears_record():
    if not os.path.exists(R.DEFAULT_CSV):
        print("skip: real CSV not found")
        return
    rows, _, _ = R.load_rows(R.DEFAULT_CSV)
    row = max(rows, key=lambda r: len(r["defective"]))
    ep = R.Episode(row, 1.0, "root_cause")
    pre = ep.sink_errors()
    assert pre > 0
    assert ep.review("SE_conclusion", random.Random(0))
    assert ep.sink_errors() == 0


def test_local_review_needs_depth():
    if not os.path.exists(R.DEFAULT_CSV):
        print("skip: real CSV not found")
        return
    rows, _, _ = R.load_rows(R.DEFAULT_CSV)
    row = next(r for r in rows if "time_bed" in r["defective"] and len(r["defective"]) == 1)
    ep = R.Episode(row, 1.0, "local")
    before = ep.sink_errors()
    ep.review("SE_conclusion", random.Random(0))  # depth 3: cannot reach time_bed
    assert ep.sink_errors() == before
    ep.review("time_bed", random.Random(0))
    assert "time_bed" in ep.fixed


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
