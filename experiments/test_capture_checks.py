#!/usr/bin/env python3
"""Tests for capture_checks (run-rate null, AM/PM recovery, coverage helper).

Run: python3 experiments/test_capture_checks.py
"""
from __future__ import annotations

import random
from datetime import timedelta

import capture_checks as K
import cross_record_replay as C


def test_longest_run_counts_consecutive_zeros():
    assert K.longest_run([False, True, True, True, False, True]) == 3
    assert K.longest_run([True, True]) == 2
    assert K.longest_run([]) == 0


def test_run_null_is_near_one_when_zeros_are_abundant():
    """With 9 of 12 nights zero, a 3-night run is almost certain by chance."""
    rng = random.Random(0)
    p = K.expected_run_prob([True] * 9 + [False] * 3, rng, draws=200)
    assert p > 0.9, p


def test_run_null_is_near_zero_when_zeros_are_rare():
    rng = random.Random(0)
    p = K.expected_run_prob([True] * 3 + [False] * 9, rng, draws=200)
    assert p < 0.15, p


def test_run_null_short_circuits_below_run_len():
    rng = random.Random(0)
    assert K.expected_run_prob([True, False, False, True], rng) == 0.0


def test_ampm_recover_flags_a_single_field_shift():
    """Sleep entered as 10:30 AM instead of 22:30: bed -> sleep is 12 h, which the
    package rejects; shifting sleep by -12 h repairs the night."""
    base = C.BASE + timedelta(days=1)
    ts = {"bed": base + timedelta(hours=22, minutes=30),
          "sleep": base + timedelta(hours=34, minutes=30),
          "awake": base + timedelta(hours=40),
          "getup": base + timedelta(hours=41)}
    flags = K.night_flags(ts, 30.0)
    assert flags["ampm_recover"], "expected one 12 h shift to repair the night"


def test_clean_night_is_not_flagged():
    base = C.BASE + timedelta(days=1)
    ts = {"bed": base + timedelta(hours=23),
          "sleep": base + timedelta(hours=23, minutes=20),
          "awake": base + timedelta(hours=29),
          "getup": base + timedelta(hours=30)}
    flags = K.night_flags(ts, 15.0)
    assert not flags["ampm_recover"]
    assert not flags["invalid"]
    assert flags["waso_zero"] is False


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"{len(fns)}/{len(fns)} passed")


if __name__ == "__main__":
    main()
