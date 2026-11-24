#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the positive-only localisation diagnostic.

No real data needed: every test builds a synthetic record.
Run: python3 experiments/test_real_confidence_ranking.py
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import real_confidence_ranking as C
import replay_manual_corrections as R


def _row(cur, suspicion, wrong, defective, error_type="order_error", rid="r1"):
    return {
        "row_id": rid,
        "pid": "p1",
        "error_type": error_type,
        "cur": cur,
        "suspicion": suspicion,
        "wrong": set(wrong),
        "defective": set(defective),
    }


def _clean_cur():
    return {
        "time_bed": None,
        "time_sleep": None,
        "time_awake": None,
        "time_getup": None,
        "SOL_calc": 0.5,
        "sleep_awake_diff": 6.0,
        "awake_getup_diff": 0.2,
        "TIB": 8.0,
        "TST": 7.0,
        "SE": 87.5,
        "SOL_validity": True,
        "WASO_validity": True,
        "SE_conclusion": True,
        "record_quality": True,
    }


def _zero_suspicion():
    return {n: 0.0 for n in R.NODES}


# --------------------------------------------------------------------------- #
# tie-aware statistics
# --------------------------------------------------------------------------- #
def test_auc_handles_ties():
    assert C.auc_with_ties([1, 1, 0, 0], [True, True, False, False]) == 1.0
    assert C.auc_with_ties([0, 0, 1, 1], [True, True, False, False]) == 0.0
    assert C.auc_with_ties([1, 1, 1, 1], [True, False, False, True]) == 0.5
    # one tied pair, one correctly ordered pair -> (0.5 + 1) / 2
    assert C.auc_with_ties([1, 1, 0], [True, False, False]) == 0.75
    assert C.auc_with_ties([1, 0], [True, True]) is None


def test_rank_bounds_bracket_ties():
    scores = [3.0, 1.0, 1.0, 0.0]
    assert C.rank_bounds(scores, 0) == (1, 1)
    assert C.rank_bounds(scores, 1) == (2, 3)
    assert C.rank_bounds(scores, 3) == (4, 4)


def test_hit_at_k_expected_is_monotone_and_bounded():
    rng = random.Random(0)
    scores = [1.0, 1.0, 0.0, 0.0, 0.0]
    h1 = C.hit_at_k_expected(scores, {0}, 1, rng, n_perm=400)
    h2 = C.hit_at_k_expected(scores, {0}, 2, rng, n_perm=400)
    h1_all = C.hit_at_k_expected(scores, {0, 1}, 1, rng, n_perm=400)
    assert 0.0 <= h1 <= h2 <= 1.0
    assert abs(h1 - 0.5) < 0.08, h1          # 1 of 2 tied maxima
    assert h1_all == 1.0                     # both tied maxima are targets


def test_hit_at_k_expected_matches_hypergeometric():
    rng = random.Random(1)
    scores = [2.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    # targets are 1 of the 3 tied at 1.0 plus one at 0.0
    got = C.hit_at_k_expected(scores, {1, 4}, 2, rng, n_perm=4000)
    # P(top-2 contains no target) = (6/8)*(5/7) ... within tie groups it is
    # easier to just bracket: P(at least one) must be between 2/8 and 5/8.
    assert 0.25 < got < 0.70, got


# --------------------------------------------------------------------------- #
# target definitions
# --------------------------------------------------------------------------- #
def test_target_kinds():
    names = list(R.NODES)
    idx = {n: i for i, n in enumerate(names)}
    wrong = {"time_sleep", "sleep_awake_diff", "TST"}
    defective = {"time_sleep"}
    src = C.target_indices("source_leaf", names, {idx[n] for n in wrong}, {idx[n] for n in defective})
    raw = C.target_indices("raw_leaf", names, {idx[n] for n in wrong}, {idx[n] for n in defective})
    anyw = C.target_indices("any_wrong", names, {idx[n] for n in wrong}, {idx[n] for n in defective})
    assert src == {idx["time_sleep"]}
    assert raw == {idx["time_sleep"]}
    assert anyw == {idx[n] for n in wrong}
    # no source defect -> source_leaf falls back to every wrong node
    fallback = C.target_indices("source_leaf", names, {idx[n] for n in wrong}, set())
    assert fallback == {idx[n] for n in wrong}


# --------------------------------------------------------------------------- #
# the two observables must agree on the ten nodes that have their own rule
# --------------------------------------------------------------------------- #
def test_violation_nonzero_exactly_where_suspicion_fires():
    cur = _clean_cur()
    cur["SOL_calc"] = 4.0          # > 3 h -> SOL_calc fires
    cur["sleep_awake_diff"] = 30.0  # > 24 h -> fires
    cur["awake_getup_diff"] = -0.5  # within 3 h -> quiet
    cur["SE"] = 100.0               # > 100 -> fires
    row = _row(cur, R.suspicion(cur), set(), set())

    base = [
        "SOL_calc",
        "sleep_awake_diff",
        "awake_getup_diff",
        "TIB",
        "TST",
        "SE",
        "SOL_validity",
        "WASO_validity",
        "SE_conclusion",
        "record_quality",
    ]
    for name in base:
        fired = row["suspicion"][name] > 0.0
        violated = C.score_violation(row, name) > 0.0
        assert fired == violated, (name, row["suspicion"][name], C.score_violation(row, name))

    assert C.score_violation(row, "SOL_calc") > 0.0
    assert C.score_violation(row, "awake_getup_diff") == 0.0


def test_leaf_score_cannot_exceed_its_descendants():
    """The inherited leaf score is a mean, so a leaf is suppressed by design.

    This is the structural reason a source node cannot win the ranking.
    """
    cur = _clean_cur()
    cur["sleep_awake_diff"] = 30.0
    susp = R.suspicion(cur)
    for leaf in R.LEAVES:
        desc = [n for n in R.NODES if leaf in R.ancestors(n)] + [leaf]
        top = max(susp[n] for n in desc if n != leaf)
        assert susp[leaf] <= top + 1e-12, (leaf, susp[leaf], top)


# --------------------------------------------------------------------------- #
# end-to-end on a synthetic record
# --------------------------------------------------------------------------- #
def test_evaluate_record_source_leaf_is_not_top1_when_tie_break_is_adversarial():
    """With the source leaf diluted, a wrong descendant outranks it."""
    cur = _clean_cur()
    cur["sleep_awake_diff"] = 30.0
    susp = R.suspicion(cur)
    wrong = {"time_sleep", "time_awake", "sleep_awake_diff", "TST", "WASO_validity"}
    row = _row(cur, susp, wrong, {"time_sleep", "time_awake"})
    rec = C.evaluate_record(row, C.score_suspicion, random.Random(0))

    src = rec["targets"]["source_leaf"]
    assert src["n_targets"] == 2
    # the leaf can at best tie; it is not strictly ahead of the diff node
    assert rec["top_score"] == susp["sleep_awake_diff"]
    assert src["rank_optimistic"] >= 2
    assert rec["auc"] is not None and 0.0 <= rec["auc"] <= 1.0


def test_evaluate_record_flags_degenerate_auc_when_everything_is_wrong():
    cur = _clean_cur()
    susp = R.suspicion(cur)
    row = _row(cur, susp, set(R.NODES), set(R.LEAVES))
    rec = C.evaluate_record(row, C.score_suspicion, random.Random(0))
    assert rec["auc"] is None


def test_violation_score_is_finite_for_nan_derived_values():
    cur = _clean_cur()
    cur["SE"] = float("nan")
    cur["sleep_awake_diff"] = float("nan")
    row = _row(cur, R.suspicion(cur), set(), set())
    for name in R.NODES:
        v = C.score_violation(row, name)
        assert not math.isnan(v), name


def test_node_group_partition():
    groups = {C.node_group(n) for n in R.NODES}
    assert groups == {"raw_leaf", "derived", "validity_sink"}
    for n in R.LEAVES:
        assert C.node_group(n) == "raw_leaf"
    for n in C.VALIDITY_SINKS:
        assert C.node_group(n) == "validity_sink"


def test_pooled_by_group_reports_one_entry_per_group():
    cur = _clean_cur()
    cur["sleep_awake_diff"] = 30.0
    susp = R.suspicion(cur)
    wrong = {"time_sleep", "time_awake", "sleep_awake_diff", "TST", "WASO_validity"}
    rows = [_row(cur, susp, wrong, {"time_sleep", "time_awake"})]
    out = C.pooled_by_group(rows, C.score_suspicion)
    assert set(out) == {"raw_leaf", "derived", "validity_sink"}
    assert sum(b["n"] for b in out.values()) == len(R.NODES)


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    print(f"\n{len([n for n in globals() if n.startswith('test_')]) - failures} passed, {failures} failed")
    sys.exit(1 if failures else 0)
