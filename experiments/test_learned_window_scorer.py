#!/usr/bin/env python3
"""Tests for learned_window_scorer (features, logistic fit, ranking metric).

Run: python3 experiments/test_learned_window_scorer.py
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

import cross_record_replay as C
import learned_window_scorer as L


def night(bed_h, sol_min, sad_min, waso=0.0):
    base = C.BASE + timedelta(days=1, hours=bed_h)
    ts = {"bed": base,
          "sleep": base + timedelta(minutes=sol_min),
          "awake": base + timedelta(minutes=sol_min + sad_min),
          "getup": base + timedelta(minutes=sol_min + sad_min + 10)}
    return C.compute(ts, waso)


def test_shifted_block_has_higher_mid_deviation():
    clean = [night(23, 15, 430) for _ in range(4)]
    shifted = [night(23, 15, 430) for _ in range(2)] + [night(1, 15, 430) for _ in range(2)]
    f_clean = L.window_features(clean, L.record_context(clean), 0, 2)
    f_block = L.window_features(shifted, L.record_context(shifted), 2, 2)
    assert f_clean["mid_dev"] < 0.5, f_clean
    assert f_block["mid_dev"] > 1.0, f_block


def test_internal_spread_is_low_inside_a_shifted_run():
    """A shared cause makes the run *coherent*; that is what boundary contrast adds."""
    shifted = [night(23, 15, 430) for _ in range(2)] + [night(1, 15, 430) for _ in range(2)]
    ctx = L.record_context(shifted)
    inside = L.window_features(shifted, ctx, 2, 2)
    straddle = L.window_features(shifted, ctx, 1, 2)
    assert inside["internal_spread"] < 0.5
    assert straddle["internal_spread"] > inside["internal_spread"]


def test_boundary_contrast_positive_at_a_level_shift():
    """A window inside the shifted run that touches one clean neighbour shows a
    one-sided step; a window straddling the shift mixes levels and is penalised."""
    shifted = [night(23, 15, 430) for _ in range(3)] + [night(1, 15, 430) for _ in range(3)]
    ctx = L.record_context(shifted)
    edge = L.window_features(shifted, ctx, 1, 2)      # nights 1,2 inside run, 3 is clean
    assert edge["boundary_contrast"] > 0.5, edge
    straddle = L.window_features(shifted, ctx, 2, 2)  # night 2 shifted, night 3 clean
    assert straddle["internal_spread"] > edge["internal_spread"]
    assert straddle["boundary_contrast"] < 0.0


def test_zero_waso_share_is_detected():
    n = [night(23, 15, 430, waso=0.0), night(23, 15, 430, waso=25.0)]
    f = L.window_features(n, L.record_context(n), 0, 2)
    assert abs(f["waso_zero_frac"] - 0.5) < 1e-9


def test_auc_is_one_for_perfect_ranking_and_half_for_constant():
    y = np.array([0, 0, 1, 1])
    assert L.auc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert L.auc(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.5


def test_logistic_recovers_the_sign_of_a_separable_feature():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(400, 1))
    y = (x[:, 0] + 0.3 * rng.normal(size=400) > 0).astype(float)
    m = L.fit_logistic(x, y, epochs=2000)
    assert m["w"][0] > 0.5
    pred = (x[:, 0] * m["w"][0] > 0).astype(float)
    assert (pred == y).mean() > 0.85


def test_split_is_stable_across_processes():
    """Python salts hash() per process, so the split must not use it."""
    assert L.is_train("42", 0.6) is True
    assert L.is_train("7", 0.6) is True
    share = sum(L.is_train(str(i), 0.6) for i in range(1000)) / 1000
    assert 0.5 < share < 0.7, share


def test_split_is_deterministic_and_disjoint():
    pids = [str(i) for i in range(200)]
    train = {p for p in pids if L.is_train(p, 0.6)}
    test = set(pids) - train
    assert train and test
    assert not (train & test)
    assert train == {p for p in pids if L.is_train(p, 0.6)}


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"{len(fns)}/{len(fns)} passed")


if __name__ == "__main__":
    main()
