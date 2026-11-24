#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Can the cross-night consistency score be *learned* instead of hand-written?

§12d found that the action unit (one night vs a run) is secondary and the score
is primary: on a silent 90 min block shift, a window policy scored by distance
from the record's medoid midpoint reaches the oracle at a 2-night budget, while a
per-night QC policy needs roughly twice the budget. That score was hand-crafted.

This script asks the follow-up question a reviewer will ask: is the score a
property of *that* hand-crafted formula, or is it learnable from observable
per-window features? If a plain logistic model trained on some participants
ranks windows as well on held-out participants, then "you need a cross-night
consistency signal" is an actionable statement and not a restatement of one
formula's luck.

Method
------
Observable features per candidate window (no access to the corrupted index set):

  qc_sum, qc_max        package order/SOL/WASO flags inside the window
  mid_dev, mid_dev_max  |mid - record medoid| in hours
  internal_spread       mean pairwise circular distance inside the window
  boundary_contrast     mean step at the two window edges minus internal spread
                        (a level shift is coherent inside and different outside)
  waso_zero_frac        share of nights reporting WASO = 0
  tst_dev               |mean TST in window - record median TST| in hours
  record_circ_sd        context: how irregular the record already is
  pos, length           normalised position and window length

Label: does the window intersect the corrupted run? (training only)

Split: participants are split by a hash, so every policy, budget and seed is
evaluated on the same held-out participants. The scorer never sees a held-out
participant's labels.

`--pooled` additionally trains ONE scorer on all three corruption modes and
evaluates it per mode. That is the interesting variant: it asks whether a single
score can find defects without being told which family it is looking at.

Reported: ranking quality on held-out windows (AUC) and the same paired
sink-error evaluation as block_review_mdp.py.

Input: the de-identified daily export. Nothing per-row is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
from collections import defaultdict

import numpy as np

import block_review_mdp as B
import cross_record_replay as C

LENGTHS = (2, 3)
FEATURES = ("qc_sum", "qc_max", "mid_dev", "mid_dev_max", "internal_spread",
            "boundary_contrast", "waso_zero_frac", "tst_dev", "record_circ_sd",
            "pos", "length")


# --------------------------------------------------------------------------- #
# record-level context and window features
# --------------------------------------------------------------------------- #
def record_context(nights):
    mids = [B.mid_minutes(n) for n in nights]
    med = B.medoid_mid(nights)
    devs = [B.circ_diff(m, med) for m in mids]
    sd = statistics.fmean(devs) if devs else 0.0      # mean absolute deviation
    tst = statistics.median(n["tst"] for n in nights) if nights else 0.0
    return dict(medoid=med, mad=sd, median_tst=tst)


def window_features(nights, ctx, start, length):
    n = len(nights)
    idx = list(range(start, start + length))
    mids = [B.mid_minutes(nights[i]) for i in idx]
    devs = [B.circ_diff(m, ctx["medoid"]) for m in mids]
    pairs = [B.circ_diff(a, b) for i, a in enumerate(mids) for b in mids[i + 1:]]
    internal = statistics.fmean(pairs) if pairs else 0.0

    steps = []
    if start > 0:
        steps.append(B.circ_diff(mids[0], B.mid_minutes(nights[start - 1])))
    if start + length < n:
        steps.append(B.circ_diff(mids[-1], B.mid_minutes(nights[start + length])))
    boundary = statistics.fmean(steps) if steps else 0.0

    qc = [B.qc_score(nights[i]) for i in idx]
    tst = statistics.fmean(nights[i]["tst"] for i in idx)

    return {
        "qc_sum": float(sum(qc)),
        "qc_max": float(max(qc)),
        "mid_dev": statistics.fmean(devs) / 60.0,
        "mid_dev_max": max(devs) / 60.0,
        "internal_spread": internal / 60.0,
        "boundary_contrast": (boundary - internal) / 60.0,
        "waso_zero_frac": sum(1 for i in idx if nights[i]["_waso"] == 0.0) / length,
        "tst_dev": abs(tst - ctx["median_tst"]) / 60.0,
        "record_circ_sd": ctx["mad"] / 60.0,
        "pos": start / max(1, n - length),
        "length": float(length),
    }


def vector(feat):
    return np.array([feat[k] for k in FEATURES], dtype=float)


# --------------------------------------------------------------------------- #
# logistic regression (plain numpy; no sklearn dependency in this repo)
# --------------------------------------------------------------------------- #
def fit_logistic(X, y, epochs=4000, lr=0.15, l2=1e-3, seed=0):
    rng = np.random.default_rng(seed)
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Z = (X - mu) / sd
    w = rng.normal(scale=0.01, size=Z.shape[1])
    b = 0.0
    pos = max(1, int(y.sum()))
    neg = max(1, len(y) - pos)
    weight = np.where(y > 0.5, len(y) / (2 * pos), len(y) / (2 * neg))

    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-np.clip(Z @ w + b, -60, 60)))
        g = (p - y) * weight
        gw = Z.T @ g / len(y) + l2 * w
        gb = g.mean()
        w -= lr * gw
        b -= lr * gb
    return dict(mu=mu, sd=sd, w=w, b=b)


def score(model, feats):
    Z = (np.array([vector(f) for f in feats]) - model["mu"]) / model["sd"]
    return Z @ model["w"] + model["b"]


def auc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    pos, neg = s[y > 0.5], s[y < 0.5]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float((pos[:, None] > neg[None, :]).mean()
                 + 0.5 * (pos[:, None] == neg[None, :]).mean())


# --------------------------------------------------------------------------- #
# data collection
# --------------------------------------------------------------------------- #
def cohort_of(recs, min_nights):
    by_pid = defaultdict(list)
    for r in recs:
        by_pid[r["pid"]].append(r)
    cohort = {}
    for pid, rows in by_pid.items():
        rows = sorted(rows, key=lambda r: r["ts"]["bed"])
        if len(rows) < min_nights:
            continue
        cohort[pid] = ([r["ts"] for r in rows],
                       [float(r["night"]["_waso"]) for r in rows],
                       [r["night"] for r in rows])
    return cohort


def collect(cohort, pids, mode, seeds, run_len):
    """Observable features for every candidate window, plus the training label."""
    X, y, rows = [], [], []
    for pid in pids:
        ts_list, waso_list, _ = cohort[pid]
        for seed in seeds:
            crng = random.Random(f"{seed}-{pid}-{mode}-{run_len}")
            new_ts, new_waso, bad = B.corrupt_block(ts_list, waso_list, mode, run_len, crng)
            if new_ts is None:
                continue
            start_nights = [C.compute(new_ts[i], new_waso[i]) for i in range(len(new_ts))]
            ctx = record_context(start_nights)
            for length in LENGTHS:
                for s in range(0, len(start_nights) - length + 1):
                    X.append(vector(window_features(start_nights, ctx, s, length)))
                    y.append(float(bool(set(range(s, s + length)) & bad)))
                    rows.append((pid, mode, seed, s, length))
    return np.array(X), np.array(y), rows


# --------------------------------------------------------------------------- #
# episode loop (mirrors block_review_mdp, with a pluggable scorer)
# --------------------------------------------------------------------------- #
def _episode_repair(ep, idx, prng):
    ep.opened |= set(idx)
    for i in idx:
        if i in ep.bad and ep.suspicious(i):
            ep.evidence.add(i)
    for i in idx:
        if i in ep.bad and ep.cur[i] is not ep.truth[i] and not ep.cur[i]["order_ok"]:
            if prng.random() < B.CATCH:
                ep.cur[i] = ep.truth[i]
    if len(ep.evidence) >= 2 and prng.random() < B.CATCH:
        ep.repair_all()


def run_one(model, cohort, pids, mode, budget, seed, run_len, tag="learned"):
    errs, clean, trials = [], [], 0
    for pid in pids:
        ts_list, waso_list, nights = cohort[pid]
        crng = random.Random(f"{seed}-{pid}-{mode}-{run_len}")
        new_ts, new_waso, bad = B.corrupt_block(ts_list, waso_list, mode, run_len, crng)
        if new_ts is None:
            continue
        trials += 1
        prng = random.Random(f"{seed}-{pid}-{mode}-{tag}-{budget}")
        start = [C.compute(new_ts[i], new_waso[i]) for i in range(len(new_ts))]
        ep = B.Episode(nights, start, bad, B.medoid_mid(start),
                       statistics.median(waso_list) if waso_list else 0.0)

        rem = budget
        while rem > 0:
            avail = [i for i in range(len(ep.cur)) if i not in ep.opened]
            if not avail:
                break
            n = len(ep.cur)
            ctx = record_context(ep.cur)
            cands, feats = [], []
            for cap in LENGTHS:
                length = min(cap, rem)
                if length < 1:
                    continue
                for s in range(0, n - length + 1):
                    if any(i in ep.opened for i in range(s, s + length)):
                        continue
                    cands.append((s, length))
                    feats.append(window_features(ep.cur, ctx, s, length))
            if not cands:
                break
            k = int(np.argmax(score(model, feats)))
            s, length = cands[k]
            _episode_repair(ep, list(range(s, s + length)), prng)
            rem -= length

        errs.append(ep.sink_errors())
        clean.append(not ep.unrepaired())
    return errs, clean, trials


def run_fixed(name, cohort, pids, mode, budget, seed, run_len):
    """Hand-crafted baselines, identical episode mechanics."""
    errs, clean, trials = [], [], 0
    for pid in pids:
        ts_list, waso_list, nights = cohort[pid]
        crng = random.Random(f"{seed}-{pid}-{mode}-{run_len}")
        new_ts, new_waso, bad = B.corrupt_block(ts_list, waso_list, mode, run_len, crng)
        if new_ts is None:
            continue
        trials += 1
        prng = random.Random(f"{seed}-{pid}-{name}-{budget}")
        start = [C.compute(new_ts[i], new_waso[i]) for i in range(len(new_ts))]
        ep = B.Episode(nights, start, bad, B.medoid_mid(start),
                       statistics.median(waso_list) if waso_list else 0.0)
        rem = budget
        while rem > 0:
            pick = B.choose(name, ep, rem, prng, "nights")
            if pick is None:
                break
            s, length = pick
            _episode_repair(ep, list(range(s, s + length)), prng)
            rem -= length
        errs.append(ep.sink_errors())
        clean.append(not ep.unrepaired())
    return errs, clean, trials


def is_train(pid, frac=0.6):
    """Stable across processes: Python's hash() of a str is salted per run."""
    h = int.from_bytes(hashlib.blake2b(str(pid).encode(), digest_size=8).digest(), "big")
    return (h % 10_000) / 10_000.0 < frac


def summarise(errs, clean, trials):
    return {
        "mean": round(statistics.fmean(errs), 4) if errs else 0.0,
        "pct_record_clean": round(100.0 * sum(clean) / len(clean), 1) if clean else 0.0,
        "trials": trials,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-csv", required=True)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--eval-seeds", type=int, default=20)
    ap.add_argument("--budgets", default="2,4")
    ap.add_argument("--run-len", type=int, default=4)
    ap.add_argument("--min-nights", type=int, default=10)
    ap.add_argument("--train-frac", type=float, default=0.6)
    ap.add_argument("--pooled", action="store_true",
                    help="also train one scorer on all corruption modes pooled")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir,
        "runs", "learned-window-scorer", "results.json"))
    args = ap.parse_args()

    recs = C.load(args.daily_csv)
    cohort = cohort_of(recs, args.min_nights)
    pids = sorted(cohort)
    train = [p for p in pids if is_train(p, args.train_frac)]
    test = [p for p in pids if not is_train(p, args.train_frac)]
    budgets = [int(b) for b in args.budgets.split(",")]
    train_seeds, eval_seeds = range(args.seeds), range(args.eval_seeds)

    out = {"header": {
        "participants": len(pids), "train": len(train), "test": len(test),
        "train_frac": args.train_frac, "run_len": args.run_len,
        "budgets": budgets, "train_seeds": args.seeds, "eval_seeds": args.eval_seeds,
        "lengths": list(LENGTHS), "features": list(FEATURES),
        "note": "aggregates only; split by hashed pid so all policies share held-out participants",
    }, "models": {}, "policies": {}}

    def record_policy(policy, mode, budget, seed, errs, clean, trials):
        out["policies"][f"{mode}|b{budget}|{policy}|s{seed}"] = summarise(errs, clean, trials)

    for mode in B.MODES:
        X, y, _ = collect(cohort, train, mode, train_seeds, args.run_len)
        if len(y) == 0 or y.sum() == 0:
            out["models"][mode] = {"error": "no positive windows"}
            continue
        model = fit_logistic(X, y)

        Xt, yt, rows_t = collect(cohort, test, mode, train_seeds, args.run_len)
        st = score(model, [dict(zip(FEATURES, r)) for r in Xt])
        per_len = {}
        for L in LENGTHS:
            sel = np.array([r[4] == L for r in rows_t])
            if sel.sum():
                per_len[str(L)] = {"windows": int(sel.sum()),
                                   "auc": round(auc(yt[sel], st[sel]), 3)}
        out["models"][mode] = {
            "train_windows": int(len(y)), "train_positive_rate": round(float(y.mean()), 3),
            "test_windows": int(len(yt)), "test_positive_rate": round(float(yt.mean()), 3),
            "test_auc_all": round(auc(yt, st), 3),
            "weights": {k: round(float(w), 3) for k, w in zip(FEATURES, model["w"])},
            "per_length": per_len,
        }

        for seed in eval_seeds:
            for budget in budgets:
                record_policy("learned", mode, budget, seed,
                              *run_one(model, cohort, test, mode, budget, seed, args.run_len))
        for name in ("night_qc", "block3_shift", "oracle"):
            for seed in eval_seeds:
                for budget in budgets:
                    record_policy(name, mode, budget, seed,
                                  *run_fixed(name, cohort, test, mode, budget, seed, args.run_len))

    if args.pooled:
        Xp, yp = [], []
        for mode in B.MODES:
            Xm, ym, _ = collect(cohort, train, mode, train_seeds, args.run_len)
            if len(ym):
                Xp.append(Xm)
                yp.append(ym)
        Xp, yp = np.vstack(Xp), np.concatenate(yp)
        pooled = fit_logistic(Xp, yp)
        out["models"]["pooled"] = {
            "train_windows": int(len(yp)),
            "train_positive_rate": round(float(yp.mean()), 3),
            "weights": {k: round(float(w), 3) for k, w in zip(FEATURES, pooled["w"])},
            "by_mode": {},
        }
        for mode in B.MODES:
            Xt, yt, _ = collect(cohort, test, mode, train_seeds, args.run_len)
            st = score(pooled, [dict(zip(FEATURES, r)) for r in Xt])
            out["models"]["pooled"]["by_mode"][mode] = {
                "test_windows": int(len(yt)), "test_auc_all": round(auc(yt, st), 3)}
            for seed in eval_seeds:
                for budget in budgets:
                    record_policy("pooled", mode, budget, seed,
                                  *run_one(pooled, cohort, test, mode, budget, seed,
                                           args.run_len, tag="pooled"))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps(out["header"], indent=2))
    for mode, m in out["models"].items():
        if "error" in m:
            print(mode, m["error"])
            continue
        if mode == "pooled":
            print("\npooled scorer:")
            for mm, v in m["by_mode"].items():
                print(f"  {mm}: AUC {v['test_auc_all']} over {v['test_windows']} windows")
        else:
            print(f"\n{mode}: test AUC {m['test_auc_all']}  "
                  f"(pos rate {m['test_positive_rate']})")
            for L, v in m["per_length"].items():
                print(f"  length {L}: AUC {v['auc']} over {v['windows']} windows")
        top = sorted(m["weights"].items(), key=lambda kv: -abs(kv[1]))[:5]
        print("  largest weights:", ", ".join(f"{k}={v}" for k, v in top))
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
