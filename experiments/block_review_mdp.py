#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Block review MDP: is the review unit one night, or a run of nights?

Why this experiment exists
-------------------------
The two real-data replays showed that per-night review scheduling is not much of
a problem on its own: one corrupt night is diluted by the participant's other
nights, and the package QC rules already find it.  What did move conclusions was
a *systematic* defect on 25 % of a participant's nights.

A systematic defect is not a property of one night.  It is a property of a run of
nights that share a cause: one session, one import, one device, one respondent
convention applied to a whole page of the diary.  So the decision problem is not
"which node" but "which block", and two things change:

  * a single night of a *silent* defect looks perfectly plausible, so opening one
    night yields no evidence that anything is wrong;
  * once the shared cause is named, the whole run is repaired at once, so the
    repair cost is O(runs) rather than O(nights).

That is the only place a block action can pay for itself, and this script
measures how much, against the obvious baselines.

Corruptions (all three appear in manual_error_correction_updated.csv, except the
last, which is a plausible session-wide clock offset)
----------------------------------------------------
  block_order : a run gets the same +/-12 h shift on one field (AM/PM convention
                applied to a session).  Order rules break -> every night in the
                run is individually visible.  (57/75 real corrections.)
  block_waso  : a run reports WASO = 0 (recording of awakenings stopped).
                Order stays valid and each night looks normal.  (2/75.)
  block_shift : a run is offset by 90 min on all four fields (session imported
                against the wrong clock).  Everything order-valid and plausible;
                only the run's position against the rest of the record shows it.
                Yields a 23.8 % any-conclusion flip at 4/12 nights, measured on
                this cohort, so the reward actually moves.

Cost model
----------
`--cost nights`   : budget is the number of nights a human reads.  A window of
                    length L costs L.  This is the fair comparison of unit size.
`--cost attempts` : budget is the number of times a human opens the record; one
                    opening reveals up to `--window` adjacent nights.  This is
                    how the 75 corrections were actually made, and under it a
                    block policy wins by construction -- reported as a
                    sensitivity analysis, not as evidence.

Policies
--------
  none, night_random, night_qc (package flags), night_extreme (|TST - median|),
  night_mid (|mid - record medoid|), block2/block3 of each score, oracle (knows
  the run; ceiling, not a policy).

Instances are paired: the corruption depends on (seed, pid, mode) only, so every
policy faces the identical corrupted record and differences can be bootstrapped.

Input is the de-identified daily export (`${TMPDIR}/spl_daily_export.csv`).
Nothing per-row is written.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
from collections import defaultdict
from datetime import timedelta

import cross_record_replay as C

SINKS = ("C1_short_sleep", "C2_low_efficiency", "C3_irregular", "C4_data_quality")
FIELDS = ("bed", "sleep", "awake", "getup")
CATCH = 0.9          # P(a reviewer actually fixes what they see)
SHIFT_MIN = 90.0     # block_shift magnitude, calibrated on this cohort
MID_SUSPECT = 45.0   # a night this far off the record medoid counts as evidence
MID_TIEBREAK = 0.05  # weight of the midpoint term inside the QC score (< 1 flag)


# --------------------------------------------------------------------------- #
# circular clock helpers
# --------------------------------------------------------------------------- #
def mid_minutes(night):
    return ((night["mid"] - C.BASE).total_seconds() / 60.0) % 1440.0


def circ_diff(a, b):
    d = abs(a - b) % 1440.0
    return min(d, 1440.0 - d)


def medoid_mid(nights):
    """Medoid, not circular mean: a minority of shifted nights must not drag it."""
    mids = [mid_minutes(n) for n in nights]
    best, best_cost = mids[0], float("inf")
    for m in mids:
        cost = sum(circ_diff(m, o) for o in mids)
        if cost < best_cost:
            best, best_cost = m, cost
    return best


# --------------------------------------------------------------------------- #
# corruption
# --------------------------------------------------------------------------- #
def corrupt_block(ts_list, waso_list, mode, run_len, rng):
    """Return (ts_out, waso_out, corrupted index set), or (None, None, set())."""
    n = len(ts_list)
    if n < run_len:
        return None, None, set()
    start = rng.randrange(0, n - run_len + 1)
    block = set(range(start, start + run_len))

    if mode == "block_order":
        cands = [(f, timedelta(hours=sign)) for f in FIELDS for sign in (12, -12)]
        rng.shuffle(cands)
        for field, delta in cands:
            out = []
            for i, ts in enumerate(ts_list):
                if i not in block:
                    out.append(ts)
                    continue
                nt = dict(ts)
                nt[field] = nt[field] + delta
                out.append(nt)
            ok = True
            for i in block:
                night = C.compute(out[i], waso_list[i])
                if night is None or night["order_ok"]:
                    ok = False
                    break
            if ok:
                return out, list(waso_list), block
        return None, None, set()

    if mode == "block_waso":
        waso_out = [0.0 if i in block else waso_list[i] for i in range(n)]
        for i in block:
            night = C.compute(ts_list[i], 0.0)
            if night is None or not night["order_ok"]:
                return None, None, set()
        return list(ts_list), waso_out, block

    if mode == "block_shift":
        out = []
        for i, ts in enumerate(ts_list):
            if i not in block:
                out.append(ts)
                continue
            nt = {f: ts[f] + timedelta(minutes=SHIFT_MIN) for f in FIELDS}
            night = C.compute(nt, waso_list[i])
            if night is None or not night["order_ok"]:
                return None, None, set()
            out.append(nt)
        return out, list(waso_list), block

    raise ValueError(mode)


# --------------------------------------------------------------------------- #
# episode
# --------------------------------------------------------------------------- #
def qc_score(night):
    s = 0.0
    if not night["order_ok"]:
        s += 2.0
    if not night["sol_ok"]:
        s += 1.0
    if not night["waso_ok"]:
        s += 1.0
    return s


def conclusions(nights):
    return C.conclusions(C.aggregate(nights))


class Episode:
    def __init__(self, truth_nights, start_nights, bad, median, waso_typical):
        self.truth = truth_nights
        self.cur = list(start_nights)
        self.bad = set(bad)
        self.median = median
        self.waso_typical = waso_typical
        self.opened = set()
        self.evidence = set()      # opened nights that look wrong; never decays
        self.truth_concl = conclusions(truth_nights)

    # -- reward ------------------------------------------------------------ #
    def sink_errors(self):
        cur = conclusions(self.cur)
        return sum(1 for k in SINKS if cur[k] != self.truth_concl[k])

    def unrepaired(self):
        return {i for i in self.bad if self.cur[i] is not self.truth[i]}

    def repair_all(self):
        for i in self.bad:
            self.cur[i] = self.truth[i]

    # -- observation -------------------------------------------------------- #
    def suspicious(self, i):
        night = self.cur[i]
        if not night["order_ok"] or not night["sol_ok"]:
            return True
        # WASO = 0 in a record that normally records awakenings: silent, but a
        # reviewer who has opened the record can see it against the other nights
        if night["_waso"] == 0.0 and self.waso_typical >= 10.0:
            return True
        return circ_diff(mid_minutes(night), self.median) > MID_SUSPECT


def mid_term(ep, i):
    """Midpoint deviation in [0, 1]; deliberately smaller than one QC flag."""
    return min(circ_diff(mid_minutes(ep.cur[i]), ep.median) / MID_SUSPECT, 1.0)


def window_score(policy, ep, start, length):
    idx = list(range(start, start + length))
    if "shift" in policy or "mid" in policy:
        return statistics.fmean(circ_diff(mid_minutes(ep.cur[i]), ep.median) for i in idx)
    if "qc" in policy:
        return sum(qc_score(ep.cur[i]) for i in idx) + MID_TIEBREAK * sum(mid_term(ep, i) for i in idx)
    if "extreme" in policy:
        med = statistics.median(ep.cur[i]["tst"] for i in range(len(ep.cur)))
        return abs(statistics.fmean(ep.cur[i]["tst"] for i in idx) - med)
    raise ValueError(policy)


def choose(policy, ep, remaining, rng, cost):
    n = len(ep.cur)
    avail = [i for i in range(n) if i not in ep.opened]
    if not avail:
        return None

    if policy == "oracle":
        cap = 3
        best, best_hit = None, -1
        for length in range(1, cap + 1):
            price = 1 if cost == "attempts" else length
            if price > remaining:
                continue
            for s in range(0, n - length + 1):
                if any(i in ep.opened for i in range(s, s + length)):
                    continue
                hit = len(set(range(s, s + length)) & ep.bad)
                if hit > best_hit:
                    best, best_hit = (s, length), hit
        if best is None:                        # budget < any window
            return (rng.choice(avail), 1)
        return best

    if policy == "night_random":
        return (rng.choice(avail), 1)

    if policy.startswith("night_"):
        return (max(avail, key=lambda x: (window_score(policy, ep, x, 1), rng.random())), 1)

    if policy.startswith("block"):
        cap = int(policy[5])
        length = cap if cost == "attempts" else min(cap, remaining)
        cands = [s for s in range(0, n - length + 1)
                 if not any(i in ep.opened for i in range(s, s + length))]
        if not cands:
            return (rng.choice(avail), 1)
        return (max(cands, key=lambda x: (window_score(policy, ep, x, length), rng.random())),
                length)

    raise ValueError(policy)


# --------------------------------------------------------------------------- #
# one cohort pass
# --------------------------------------------------------------------------- #
def run_one(policy, cohort, mode, budget, seed, run_len, cost):
    errs, clean, trials = [], [], 0
    for pid, (ts_list, waso_list, nights) in cohort.items():
        crng = random.Random(f"{seed}-{pid}-{mode}-{run_len}")   # paired instances
        new_ts, new_waso, bad = corrupt_block(ts_list, waso_list, mode, run_len, crng)
        if new_ts is None:
            continue
        trials += 1
        prng = random.Random(f"{seed}-{pid}-{policy}-{mode}-{cost}-{budget}")
        start = [C.compute(new_ts[i], new_waso[i]) for i in range(len(new_ts))]
        waso_typical = statistics.median(waso_list) if waso_list else 0.0
        ep = Episode(nights, start, bad, medoid_mid(start), waso_typical)

        if policy != "none":
            remaining = budget
            while remaining > 0:
                pick = choose(policy, ep, remaining, prng, cost)
                if pick is None:
                    break
                s, length = pick
                idx = list(range(s, s + length))
                ep.opened |= set(idx)
                remaining -= (1 if cost == "attempts" else length)
                for i in idx:
                    if i in ep.bad and ep.suspicious(i):
                        ep.evidence.add(i)
                # per-night defects can be fixed from the single night that shows them
                for i in idx:
                    if i in ep.bad and ep.cur[i] is not ep.truth[i] and not ep.cur[i]["order_ok"]:
                        if prng.random() < CATCH:
                            ep.cur[i] = ep.truth[i]
                # two inspected nights of the same run name the shared cause
                if len(ep.evidence) >= 2 and prng.random() < CATCH:
                    ep.repair_all()
        errs.append(ep.sink_errors())
        clean.append(not ep.unrepaired())
    return errs, clean, trials


POLICIES = ("none", "night_random", "night_qc", "night_extreme", "night_mid",
            "block2_qc", "block3_qc", "block2_shift", "block3_shift", "block3_mid",
            "oracle")
MODES = ("block_order", "block_waso", "block_shift")


def boot_ci(deltas, rng, n_boot=2000):
    if len(deltas) < 3:
        return (0.0, 0.0)
    means = []
    for _ in range(n_boot):
        means.append(statistics.fmean(rng.choice(deltas) for _ in deltas))
    means.sort()
    return (means[int(0.025 * len(means))], means[int(0.975 * len(means))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-csv", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir,
        "runs", "block-review-mdp", "results.json"))
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--run-len", type=int, default=4)
    ap.add_argument("--cost", choices=("nights", "attempts"), default="nights")
    ap.add_argument("--budgets", default="2,4,6")
    ap.add_argument("--calibrate", action="store_true",
                    help="sweep block_shift magnitude/length and report the any-conclusion "
                         "flip rate, then exit (justifies SHIFT_MIN); no grid is run")
    args = ap.parse_args()
    budgets = [int(b) for b in args.budgets.split(",")]

    recs = C.load(args.daily_csv)
    by_pid = defaultdict(list)
    for r in recs:
        by_pid[r["pid"]].append(r)
    cohort = {}
    for pid, v in by_pid.items():
        if len(v) < C.MIN_NIGHTS:
            continue
        v = sorted(v, key=lambda x: x["ts"]["bed"])
        cohort[pid] = ([r["ts"] for r in v],
                       [float(r["night"]["_waso"]) for r in v],
                       [r["night"] for r in v])

    if args.calibrate:
        sweep = {}
        for run_len in (3, 4, 5):
            for mag in (30, 45, 60, 90, 120):
                rates = []
                for pid, (ts_list, waso_list, nights) in cohort.items():
                    truth = conclusions(nights)
                    n = len(ts_list)
                    hits = []
                    for start in range(0, n - run_len + 1):
                        out = []
                        for i, ts in enumerate(ts_list):
                            if start <= i < start + run_len:
                                out.append({f: ts[f] + timedelta(minutes=mag) for f in FIELDS})
                            else:
                                out.append(ts)
                        cur_nights = [C.compute(out[i], waso_list[i]) for i in range(n)]
                        if any(x is None for x in cur_nights):
                            continue
                        cur = conclusions(cur_nights)
                        hits.append(any(cur[k] != truth[k] for k in SINKS))
                    if hits:
                        rates.append(statistics.fmean(hits))
                sweep[f"len{run_len}_m{mag}"] = round(100 * statistics.fmean(rates), 1)
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out.replace(".json", "_calibration.json"), "w", encoding="utf-8") as fh:
            json.dump({"participants": len(cohort),
                       "pct_records_any_conclusion_flip": sweep}, fh, indent=2)
        print(json.dumps({"participants": len(cohort), "sweep_pct_any_flip": sweep}, indent=2))
        return

    out = {
        "header": {
            "participants": len(cohort),
            "nights": sum(len(v[2]) for v in cohort.values()),
            "run_len": args.run_len,
            "seeds": args.seeds,
            "cost": args.cost,
            "budgets": budgets,
            "catch": CATCH,
            "shift_min": SHIFT_MIN,
            "mid_suspect_min": MID_SUSPECT,
        },
        "policies": {},
        "paired": {},
    }

    seed_cache = {}
    for mode in MODES:
        for budget in budgets:
            key = f"{mode}|{args.cost}|b{budget}"
            out["policies"][key] = {}
            for policy in POLICIES:
                per_seed, clean, trials = [], [], 0
                for seed in range(args.seeds):
                    cache_key = (policy, mode, budget, seed)
                    if cache_key not in seed_cache:
                        seed_cache[cache_key] = run_one(policy, cohort, mode, budget,
                                                        seed, args.run_len, args.cost)
                    errs, cl, tr = seed_cache[cache_key]
                    if not errs:
                        continue
                    trials = tr
                    per_seed.append((errs, cl))
                flat = [e for errs, _ in per_seed for e in errs]
                flat_clean = [c for _, cl in per_seed for c in cl]
                out["policies"][key][policy] = {
                    "mean": round(statistics.fmean(flat), 3),
                    "se": round(statistics.pstdev(flat) / math.sqrt(len(flat)), 4) if len(flat) > 1 else 0.0,
                    "pct_record_clean": round(100 * statistics.fmean(flat_clean), 1),
                    "trials": trials,
                }

    # paired deltas vs the best night-only policy and vs night_qc
    rng = random.Random(7)
    for mode in MODES:
        for budget in budgets:
            key = f"{mode}|{args.cost}|b{budget}"
            base = "night_qc"
            for policy in ("block3_qc", "block3_shift", "block3_mid", "night_mid"):
                d = []
                for seed in range(args.seeds):
                    a = seed_cache.get((policy, mode, budget, seed))
                    b = seed_cache.get((base, mode, budget, seed))
                    if not a or not b or not a[0] or len(a[0]) != len(b[0]):
                        continue
                    d.append(statistics.fmean(x - y for x, y in zip(a[0], b[0])))
                if d:
                    lo, hi = boot_ci(d, rng)
                    out["paired"][f"{key}|{policy}-{base}"] = {
                        "delta": round(statistics.fmean(d), 3),
                        "ci95": [round(lo, 3), round(hi, 3)],
                    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps(out["header"], indent=2))
    short = {"block2_qc": "b2qc", "block3_qc": "b3qc", "block2_shift": "b2sh",
             "block3_shift": "b3sh", "block3_mid": "b3mid", "night_random": "nrand",
             "night_extreme": "next", "night_mid": "nmid", "night_qc": "nqc",
             "none": "none", "oracle": "orac"}
    for mode in MODES:
        print(f"\n{mode}")
        print("| budget | " + " | ".join(short[p] for p in POLICIES) + " |")
        for budget in budgets:
            row = out["policies"][f"{mode}|{args.cost}|b{budget}"]
            print(f"| {budget} | " + " | ".join(f"{row[p]['mean']:.2f}" for p in POLICIES) + " |")
    print("\npaired deltas vs night_qc (negative = better)")
    for k, v in out["paired"].items():
        print(f"  {k}: {v['delta']:+.3f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}]")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
