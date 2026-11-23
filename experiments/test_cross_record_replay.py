#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the cross-record replay. Run: python3 experiments/test_cross_record_replay.py"""
import math
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cross_record_replay as C

BASE = C.BASE


def night(bed_h, sleep_h, awake_h, getup_h, waso=0):
    return C.compute(
        dict(bed=BASE + timedelta(hours=bed_h), sleep=BASE + timedelta(hours=sleep_h),
             awake=BASE + timedelta(hours=awake_h), getup=BASE + timedelta(hours=getup_h)),
        waso,
    )


def test_to_dt_handles_na_and_pm():
    assert C.to_dt("NA", "PM", "3") is None
    assert C.to_dt("36000", "NA", "3") is None
    got = C.to_dt("36000", "PM", "3")   # 10:00 PM
    assert (got.hour, got.minute) == (22, 0)
    got = C.to_dt("43200", "AM", "3")   # 12:00 AM
    assert got.hour == 0


def test_minutes_of():
    assert C.minutes_of("00:30") == 30
    assert C.minutes_of("1:05") == 65
    assert C.minutes_of("NA") is None


def test_compute_basic_metrics():
    n = night(23, 23.5, 30.5, 31, waso=30)   # 23:00 bed, 23:30 sleep, 06:30 awake, 07:00 up
    assert abs(n["sol"] - 30) < 1e-9
    assert abs(n["sad"] - 420) < 1e-9
    assert abs(n["tib"] - 480) < 1e-9
    assert abs(n["tst"] - 390) < 1e-9
    assert abs(n["se"] - 100 * 390 / 480) < 1e-9
    assert n["order_ok"] and n["sol_ok"] and n["waso_ok"]


def test_compute_rejects_impossible_nights():
    assert night(24, 25, 22, 30) is None      # getup 30 h after bed
    assert night(23, 23.5, 23.6, 30, waso=120) is None  # WASO longer than the sleep period


def test_aggregate_circular_sd_is_clock_based():
    # 23:50 and 00:10 midpoints are 20 minutes apart, not 23h40m
    n1 = night(23.0, 23.4, 24.0, 31.0)   # mid ~23:42
    n2 = night(23.4, 23.8, 24.4, 31.0)   # mid ~00:06
    agg = C.aggregate([n1, n2])
    assert 5 < agg["sd_mid"] < 60, agg["sd_mid"]


def test_conclusions_follow_thresholds():
    good = night(23, 23.5, 31.0, 31.5, waso=60)
    agg = C.aggregate([good] * 5)
    c = C.conclusions(agg)
    assert c["C1_short_sleep"] is True       # 6.5 h TST < 7 h
    assert c["C4_data_quality"] is True


def test_corrupt_visible_breaks_order_and_silent_does_not():
    ts = dict(bed=BASE + timedelta(hours=23), sleep=BASE + timedelta(hours=23.5),
              awake=BASE + timedelta(hours=31), getup=BASE + timedelta(hours=31.5))
    vis_ts, vis_waso = C.corrupt(ts, 15, "visible", __import__("random").Random(0))
    assert C.compute(vis_ts, vis_waso) is None or not C.compute(vis_ts, vis_waso)["order_ok"]
    sil_ts, sil_waso = C.corrupt(ts, 15, "silent", __import__("random").Random(0))
    sn = C.compute(sil_ts, sil_waso)
    assert sn is not None and sn["order_ok"] and sil_waso == 0.0


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
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
