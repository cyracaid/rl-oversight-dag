#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the block-review MDP. Run: python3 experiments/test_block_review_mdp.py"""
import os
import random
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cross_record_replay as C
import block_review_mdp as B

BASE = C.BASE


def make_participant(n=12, waso=20):
    ts_list, waso_list, nights = [], [], []
    for i in range(n):
        ts = dict(bed=BASE + timedelta(days=i, hours=23),
                  sleep=BASE + timedelta(days=i, hours=23.5),
                  awake=BASE + timedelta(days=i, hours=30.5),
                  getup=BASE + timedelta(days=i, hours=31))
        ts_list.append(ts)
        waso_list.append(float(waso))
        nights.append(C.compute(ts, float(waso)))
    return ts_list, waso_list, nights


def episode(mode, seed, run_len=4, n=12):
    ts_list, waso_list, nights = make_participant(n)
    new_ts, new_waso, bad = B.corrupt_block(ts_list, waso_list, mode, run_len, random.Random(seed))
    assert new_ts is not None, mode
    start = [C.compute(new_ts[i], new_waso[i]) for i in range(len(new_ts))]
    ep = B.Episode(nights, start, bad, B.medoid_mid(start), 20.0)
    return ts_list, waso_list, nights, new_ts, new_waso, bad, ep


def test_circular_helpers():
    assert B.circ_diff(23.9 * 60, 0.1 * 60) < 20
    _, _, nights = make_participant()
    assert 0 <= B.mid_minutes(nights[0]) < 1440
    assert B.circ_diff(B.medoid_mid(nights), B.mid_minutes(nights[0])) < 1


def test_block_order_breaks_every_night_in_the_run():
    ts_list, waso_list, _, new_ts, new_waso, bad, _ = episode("block_order", 1)
    assert len(bad) == 4
    for i in bad:
        assert not C.compute(new_ts[i], new_waso[i])["order_ok"]
    for i in range(len(new_ts)):
        if i not in bad:
            assert new_ts[i] == ts_list[i]


def test_block_waso_is_silent_and_order_valid():
    ts_list, _, _, _, new_waso, bad, _ = episode("block_waso", 2)
    assert len(bad) == 4 and all(new_waso[i] == 0.0 for i in bad)
    for i in bad:
        night = C.compute(ts_list[i], new_waso[i])
        assert night["order_ok"] and night["sol_ok"] and night["waso_ok"]


def test_block_shift_is_order_valid_and_moves_midpoint():
    ts_list, waso_list, nights, new_ts, new_waso, bad, _ = episode("block_shift", 3)
    for i in bad:
        night = C.compute(new_ts[i], new_waso[i])
        assert night["order_ok"] and night["waso_ok"]
        assert abs(night["tst"] - nights[i]["tst"]) < 1e-9      # TST untouched
        assert abs(B.circ_diff(B.mid_minutes(night), B.mid_minutes(nights[i])) - B.SHIFT_MIN) < 1e-6


def test_one_night_is_not_enough_evidence_but_two_are():
    _, _, _, _, _, bad, ep = episode("block_waso", 4)
    i = sorted(bad)[0]
    ep.opened = {i}
    assert ep.suspicious(i)                 # WASO = 0 in a record that records it
    assert ep.unrepaired() == set(bad)      # but nothing gets repaired from one night
    ep.evidence |= {i, sorted(bad)[1]}
    assert len(ep.evidence) >= 2            # the run can now be named
    ep.repair_all()
    assert ep.unrepaired() == set()


def test_quiet_record_gives_no_waso_evidence():
    """If the participant never records WASO, WASO = 0 is not suspicious."""
    ts_list, waso_list, nights = make_participant(waso=0)
    ep = B.Episode(nights, nights, {0}, B.medoid_mid(nights), 0.0)
    assert not ep.suspicious(0)


def test_qc_flag_outweighs_midpoint_deviation():
    """The QC policy must keep using the flags: one flag > any midpoint term."""
    ts_list, waso_list, nights = make_participant()
    # night 3: order broken by a 12 h shift on bed only (midpoint unchanged)
    broken = dict(ts_list[3])
    broken["bed"] = broken["bed"] - timedelta(hours=12)
    # night 7: order-valid, but 300 min off the record's own midpoint
    drifted = dict(ts_list[7])
    for f in ("sleep", "awake", "getup"):
        drifted[f] = drifted[f] + timedelta(minutes=300)
    cur = list(nights)
    cur[3] = C.compute(broken, 20.0)
    cur[7] = C.compute(drifted, 20.0)
    assert not cur[3]["order_ok"] and cur[7]["order_ok"]
    ep = B.Episode(nights, cur, {3}, B.medoid_mid(cur), 20.0)
    assert B.window_score("night_qc", ep, 3, 1) > B.window_score("night_qc", ep, 7, 1)
    assert B.choose("night_qc", ep, 1, random.Random(0), "nights")[0] == 3
    # ... and the midpoint policies pick the other one, by construction
    assert B.window_score("night_mid", ep, 7, 1) > B.window_score("night_mid", ep, 3, 1)


def test_choose_respects_night_budget():
    _, _, _, _, _, bad, ep = episode("block_shift", 5)
    ep.opened = {0, 1, 2}
    s, length = B.choose("block3_shift", ep, remaining=3, rng=random.Random(0), cost="nights")
    assert length == 3 and not (set(range(s, s + length)) & ep.opened)
    s, length = B.choose("block3_shift", ep, remaining=2, rng=random.Random(0), cost="nights")
    assert length == 2


def test_attempt_cost_lets_a_block_read_three_nights_for_one_attempt():
    _, _, _, _, _, bad, ep = episode("block_shift", 6)
    s, length = B.choose("block3_shift", ep, remaining=1, rng=random.Random(0), cost="attempts")
    assert length == 3


def test_oracle_targets_the_corrupted_run():
    _, _, _, _, _, bad, ep = episode("block_shift", 7)
    s, length = B.choose("oracle", ep, remaining=3, rng=random.Random(0), cost="nights")
    assert len(set(range(s, s + length)) & bad) == length


def test_instances_are_paired_across_policies():
    """Same seed/mode must produce the same corrupted record whatever the policy."""
    ts_list, waso_list, nights = make_participant()
    a = B.corrupt_block(ts_list, waso_list, "block_shift", 4, random.Random("3-1-block_shift-4"))
    b = B.corrupt_block(ts_list, waso_list, "block_shift", 4, random.Random("3-1-block_shift-4"))
    assert a[2] == b[2] and a[0] == b[0]


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
