#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-record (participant-level) replay: does a bad night survive aggregation?

The within-record replay (replay_manual_corrections.py) showed that a source
error corrupts ~42% of a record's nodes but is cleared by 1-2 root-cause reviews.
This script asks the next question for the sleep study: a conclusion is usually
computed over many nights per participant, so does one bad night change it?

Input: a de-identified daily export (pid, day_num, four times, sol_est, waso_est)
produced by R from the internal RDS. It is read from a temporary path and is not
committed; nothing per-row is printed or written to the repo.

Pipeline per night
  SOL  = sleep - bed
  SAD  = awake - sleep
  AGD  = getup - awake
  TIB  = getup - bed
  TST  = SAD - waso_est
  SE   = TST / TIB
  mid  = sleep + SAD/2

Conclusions per participant (the "sinks")
  C1 short_sleep   mean TST < 420 min
  C2 low_efficiency mean SE < 85 %
  C3 irregular      sd(sleep midpoint) > 60 min
  C4 data_quality   every night passes the package's order rules

Corruptions (both are real error types in the correction file)
  visible : +-12 h on one time field, chosen to break the order rules
            (order_error, 76 % of corrections)
  silent  : awake := sleep (WASO = 0), order stays valid
            (sleep_awake_equal_error)

For each participant and each night we corrupt that night and ask whether the
four conclusions flip, whether the pipeline QC flags it, and which review
policy finds it under a budget of 1-2 nights out of n.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

FIELDS = ("bed", "sleep", "awake", "getup")
BASE = datetime(2000, 1, 1)
T = dict(bed_to_sleep_max_h=7.0, awake_to_getup_max_h=7.0,
         sleep_to_awake_max_h=24.0, sol_excessive_min=120.0,
         waso_excessive_min=90.0, short_tst_min=420.0, low_se=85.0,
         irregular_sd_min=60.0)
MIN_NIGHTS = 10


def to_dt(sec, ap, day):
    if sec is None or ap is None:
        return None
    if isinstance(sec, str) and sec.strip() in ("", "NA"):
        return None
    if isinstance(ap, str) and ap.strip() in ("", "NA"):
        return None
    sec = float(sec)
    h, mi = int(sec // 3600), int((sec % 3600) // 60)
    ap = str(ap).strip().upper()
    if ap == "PM" and h < 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    try:
        d = int(float(day))
    except (TypeError, ValueError):
        d = 0
    return BASE + timedelta(days=d, hours=h, minutes=mi)


def minutes_of(x):
    try:
        m = str(x).strip().split(":")
        return int(m[0]) * 60 + int(m[1])
    except (ValueError, IndexError):
        return None


def load(path):
    recs = []
    drops = defaultdict(int)
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            ts = {
                "bed": to_dt(r.get("tb"), r.get("tb_ap"), r.get("day_num")),
                "sleep": to_dt(r.get("ts"), r.get("ts_ap"), r.get("day_num")),
                "awake": to_dt(r.get("ta"), r.get("ta_ap"), r.get("day_num")),
                "getup": to_dt(r.get("tg"), r.get("tg_ap"), r.get("day_num")),
            }
            if any(v is None for v in ts.values()):
                drops["missing_time"] += 1
                continue
            # The pipeline maps each record onto one night. Self-reported clock
            # times are ambiguous by up to a day, so anchor each field to the
            # previous one inside a +-12 h window (instead of only pushing it
            # forward, which can chain into a 25 h "night").
            for f in ("sleep", "awake", "getup"):
                prev = {"sleep": "bed", "awake": "sleep", "getup": "awake"}[f]
                while ts[f] - ts[prev] > timedelta(hours=12):
                    ts[f] = ts[f] - timedelta(days=1)
                while ts[f] < ts[prev]:
                    ts[f] = ts[f] + timedelta(days=1)
            night = compute(ts, minutes_of(r.get("waso_est")))
            if night is None:
                drops["implausible_duration"] += 1
                continue
            recs.append({"pid": r["pid"], "day": r.get("day_num"), "ts": ts, "night": night})
    load.drops = dict(drops)
    return recs


def compute(ts, waso_min):
    bed, sleep, awake, getup = (ts[f] for f in FIELDS)
    sol = (sleep - bed).total_seconds() / 60.0
    sad = (awake - sleep).total_seconds() / 60.0
    agd = (getup - awake).total_seconds() / 60.0
    tib = (getup - bed).total_seconds() / 60.0
    if tib <= 0 or tib > 24 * 60:
        return None
    waso = 0.0 if waso_min is None else float(waso_min)
    tst = sad - waso
    if tst <= 0 or tst > tib:
        return None
    se = 100.0 * tst / tib
    mid = sleep + (awake - sleep) / 2
    order_ok = (abs(sol) <= T["bed_to_sleep_max_h"] * 60
                and abs(agd) <= T["awake_to_getup_max_h"] * 60
                and abs(sad) <= T["sleep_to_awake_max_h"] * 60)
    sol_ok = 0 <= sol <= T["sol_excessive_min"]
    waso_ok = 0 <= waso <= T["waso_excessive_min"]
    return dict(sol=sol, sad=sad, agd=agd, tib=tib, tst=tst, se=se, mid=mid,
                order_ok=order_ok, sol_ok=sol_ok, waso_ok=waso_ok, _waso=waso)


def aggregate(nights):
    tst = [n["tst"] for n in nights]
    se = [n["se"] for n in nights]
    # sleep midpoint is a clock time, so its spread must be measured on the
    # circle (00:00 and 23:50 are 10 minutes apart, not 23h50m).
    ang = [2 * math.pi * (((n["mid"] - BASE).total_seconds() / 60.0) % 1440.0) / 1440.0 for n in nights]
    if len(ang) > 1:
        c = statistics.fmean(math.cos(a) for a in ang)
        sn = statistics.fmean(math.sin(a) for a in ang)
        r = math.hypot(c, sn)
        sd = math.sqrt(-2.0 * math.log(r)) * 1440.0 / (2 * math.pi) if 0 < r < 1 else 0.0
    else:
        sd = 0.0
    return dict(
        mean_tst=statistics.fmean(tst),
        mean_se=statistics.fmean(se),
        sd_mid=sd,
        n=len(nights),
        quality=all(n["order_ok"] for n in nights),
    )


def conclusions(agg):
    return {
        "C1_short_sleep": agg["mean_tst"] < T["short_tst_min"],
        "C2_low_efficiency": agg["mean_se"] < T["low_se"],
        "C3_irregular": agg["sd_mid"] > T["irregular_sd_min"],
        "C4_data_quality": agg["quality"],
    }


def corrupt(ts, waso, mode, rng, field=None):
    ts = dict(ts)
    if mode == "silent":
        # self-reported WASO lost to 0: order stays valid, nothing flags it
        return ts, 0.0
    # visible: 12 h shift that breaks the order rules
    field = field or rng.choice(FIELDS)
    for sign in (1, -1):
        cand = dict(ts)
        cand[field] = cand[field] + timedelta(hours=12 * sign)
        n = compute(cand, 0)
        if n is not None and not n["order_ok"]:
            return cand, waso
    cand = dict(ts)
    cand[field] = cand[field] + timedelta(hours=12)
    return cand, waso


def suspicion(night):
    s = 0.0
    if not night["order_ok"]:
        s += 2.0
    if not night["sol_ok"]:
        s += 1.0
    if not night["waso_ok"]:
        s += 1.0
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-csv", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir,
        "runs", "cross-record-replay", "results.json"))
    ap.add_argument("--seeds", type=int, default=20)
    args = ap.parse_args()

    recs = load(args.daily_csv)
    by_pid = defaultdict(list)
    for r in recs:
        by_pid[r["pid"]].append(r)
    pids = {p: sorted(v, key=lambda x: (x["ts"]["bed"], str(x["day"]))) for p, v in by_pid.items()}
    eligible = {p: v for p, v in pids.items() if len(v) >= MIN_NIGHTS}

    head = {
        "records_used": len(recs),
        "participants_total": len(pids),
        "participants_with_min_nights": len(eligible),
        "min_nights": MIN_NIGHTS,
        "nights_per_participant_median": statistics.median(len(v) for v in eligible.values()) if eligible else 0,
    }

    # ---- 1. does one bad night move the conclusions? -------------------------
    flips = defaultdict(lambda: defaultdict(int))
    deltas = defaultdict(lambda: defaultdict(list))
    detected = defaultdict(lambda: [0, 0])
    instances = defaultdict(int)

    for pid, nights in eligible.items():
        true_nights = [r["night"] for r in nights]
        true_agg = aggregate(true_nights)
        true_conc = conclusions(true_agg)
        n = len(nights)
        for mode in ("visible", "silent"):
            for i, r in enumerate(nights):
                inst, inst_waso = corrupt(r["ts"], r["night"]["_waso"], mode,
                                          random.Random(f"{pid}-{i}-{mode}"))
                bad = compute(inst, inst_waso)
                if bad is None:
                    continue
                changed = list(true_nights)
                changed[i] = bad
                agg = aggregate(changed)
                conc = conclusions(agg)
                instances[mode] += 1
                for k in true_conc:
                    if conc[k] != true_conc[k]:
                        flips[mode][k] += 1
                deltas[mode]["mean_tst"].append(abs(agg["mean_tst"] - true_agg["mean_tst"]))
                deltas[mode]["mean_se"].append(abs(agg["mean_se"] - true_agg["mean_se"]))
                deltas[mode]["sd_mid"].append(abs(agg["sd_mid"] - true_agg["sd_mid"]))
                detected[mode][1] += 1
                if suspicion(bad) > 0:
                    detected[mode][0] += 1

    def pct(x, n):
        return round(100.0 * x / n, 1) if n else float("nan")

    flip_table = {
        mode: {k: {"n": instances[mode], "p_flip_pct": pct(v, instances[mode])} for k, v in flips[mode].items()}
        for mode in instances
    }
    for mode in instances:
        for k in ("C1_short_sleep", "C2_low_efficiency", "C3_irregular", "C4_data_quality"):
            flip_table[mode].setdefault(k, {"n": instances[mode], "p_flip_pct": 0.0})
    delta_summary = {
        mode: {k: {"mean": round(statistics.fmean(v), 2),
                   "p90": round(sorted(v)[int(0.9 * (len(v) - 1))], 2)}
               for k, v in deltas[mode].items()}
        for mode in deltas
    }
    detect_table = {mode: {"pct_flagged": pct(detected[mode][0], detected[mode][1]),
                           "n": detected[mode][1]} for mode in detected}

    # ---- 1b. how close is each real conclusion to flipping? -------------------
    # For every participant, distance of the aggregate from its threshold, and
    # whether the p90 shift caused by one corrupted night would cross it.
    frag = {}
    for label, key, thr, direction in (
        ("C1_short_sleep", "mean_tst", T["short_tst_min"], "below"),
        ("C2_low_efficiency", "mean_se", T["low_se"], "below"),
        ("C3_irregular", "sd_mid", T["irregular_sd_min"], "above"),
    ):
        rows_f = []
        for pid, nights in eligible.items():
            agg = aggregate([r["night"] for r in nights])
            v = agg[key]
            margin = (thr - v) if direction == "below" else (v - thr)
            rows_f.append((pid, margin))
        p90 = delta_summary["visible"][key]["p90"]
        at_risk = sum(1 for _, m in rows_f if 0 < m <= p90)
        already = sum(1 for _, m in rows_f if m <= 0)
        frag[label] = {
            "n": len(rows_f),
            "median_margin": round(statistics.median(m for _, m in rows_f), 2),
            "p10_margin": round(sorted(m for _, m in rows_f)[max(0, int(0.1 * len(rows_f)))], 2),
            "p90_one_night_shift": p90,
            "pct_conclusion_true": pct(already, len(rows_f)),
            "pct_within_p90_shift": pct(at_risk, len(rows_f)),
        }

    # ---- 1c. flip rate by number of nights -----------------------------------
    by_n = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for pid, nights in eligible.items():
        n = len(nights)
        bucket = "10-13" if n <= 13 else ("14-20" if n <= 20 else "21+")
        true_conc = conclusions(aggregate([r["night"] for r in nights]))
        for mode in ("visible", "silent"):
            for i, r in enumerate(nights):
                inst, iw = corrupt(r["ts"], r["night"]["_waso"], mode, random.Random(f"{pid}-{i}-{mode}"))
                bad = compute(inst, iw)
                if bad is None:
                    continue
                ch = [x["night"] for x in nights]
                ch[i] = bad
                c2 = conclusions(aggregate(ch))
                by_n[bucket][mode][1] += 1
                if any(c2[k] != true_conc[k] for k in c2):
                    by_n[bucket][mode][0] += 1
    by_n_out = {
        b: {m: {"n": v[1], "pct_any_flip": pct(v[0], v[1])} for m, v in d.items()}
        for b, d in sorted(by_n.items())
    }

    # ---- 1d. what if the error is systematic, not a single night? ------------
    # A single night is diluted by the participant's other nights. If a defect is
    # systematic (a session, an import, a device), a fraction of the nights is
    # wrong at once. This measures how many conclusions that takes down.
    frac_flip = {}
    for frac in (0.1, 0.25, 0.5):
        cnt = defaultdict(lambda: [0, 0])
        for pid, nights in eligible.items():
            true_conc = conclusions(aggregate([r["night"] for r in nights]))
            k = max(1, int(round(frac * len(nights))))
            rng = random.Random(f"frac-{pid}-{frac}")
            for _ in range(5):
                idx = rng.sample(range(len(nights)), k)
                changed = [r["night"] for r in nights]
                for i in idx:
                    inst, iw = corrupt(nights[i]["ts"], nights[i]["night"]["_waso"], "visible", rng)
                    bad = compute(inst, iw)
                    if bad is not None:
                        changed[i] = bad
                c = conclusions(aggregate(changed))
                cnt["any"][1] += 1
                if any(c[x] != true_conc[x] for x in c):
                    cnt["any"][0] += 1
                for x in ("C1_short_sleep", "C2_low_efficiency", "C3_irregular"):
                    cnt[x][1] += 1
                    if c[x] != true_conc[x]:
                        cnt[x][0] += 1
        frac_flip[f"{int(frac*100)}pct"] = {
            x: {"n": v[1], "pct_flip": pct(v[0], v[1])} for x, v in cnt.items()
        }

    # ---- 2. review policies at the participant level -------------------------
    def run_policies(mode, budget, seeds):
        res = {}
        for policy in ("none", "random", "qc", "extreme", "oracle"):
            per_seed = []
            for seed in range(seeds):
                errs = []
                for pid, nights in eligible.items():
                    rng = random.Random(f"{seed}-{pid}-{policy}")
                    i_bad = rng.randrange(len(nights))
                    true_nights = [r["night"] for r in nights]
                    true_conc = conclusions(aggregate(true_nights))
                    bad_ts, bad_waso = corrupt(nights[i_bad]["ts"], nights[i_bad]["night"]["_waso"], mode, rng)
                    bad = compute(bad_ts, bad_waso)
                    if bad is None:
                        errs.append(0)
                        continue
                    cur = list(true_nights)
                    cur[i_bad] = bad
                    if policy == "none":
                        errs.append(sum(1 for k in true_conc
                                        if conclusions(aggregate(cur))[k] != true_conc[k]))
                        continue
                    reviewed = set()
                    for _ in range(budget):
                        if policy == "random":
                            cand = [j for j in range(len(cur)) if j not in reviewed]
                            j = rng.choice(cand)
                        elif policy == "qc":
                            cand = [j for j in range(len(cur)) if j not in reviewed]
                            j = max(cand, key=lambda x: (suspicion(cur[x]), rng.random()))
                        elif policy == "extreme":
                            med = statistics.median(n["tst"] for n in cur)
                            cand = [j for j in range(len(cur)) if j not in reviewed]
                            j = max(cand, key=lambda x: (abs(cur[x]["tst"] - med) + 10 * suspicion(cur[x]), rng.random()))
                        elif policy == "oracle":
                            # upper bound: knows which night is wrong
                            j = i_bad
                        reviewed.add(j)
                        if j == i_bad:
                            cur[i_bad] = true_nights[i_bad]
                    errs.append(sum(1 for k in true_conc if conclusions(aggregate(cur))[k] != true_conc[k]))
                per_seed.append(statistics.fmean(errs))
            res[policy] = {"mean": round(statistics.fmean(per_seed), 3),
                           "sd": round(statistics.pstdev(per_seed), 3) if len(per_seed) > 1 else 0.0}
        return res

    policy_table = {f"{mode}|b{b}": run_policies(mode, b, args.seeds)
                    for mode in ("visible", "silent") for b in (1, 2, 3)}

    head["records_dropped"] = getattr(load, "drops", {})
    out = {"header": head, "flip_table": flip_table, "delta": delta_summary,
           "detection": detect_table, "fragility": frag, "flip_by_nights": by_n_out,
           "flip_by_corrupted_fraction": frac_flip,
           "policies": policy_table, "thresholds": T, "min_nights": MIN_NIGHTS}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps(head, indent=2))
    print("\nconclusion flip rate when ONE night is corrupted:")
    for mode in ("visible", "silent"):
        print(f"  {mode}: " + ", ".join(f"{k} {v['p_flip_pct']}%" for k, v in flip_table[mode].items()))
    print("\nQC flag rate on the corrupted night:", detect_table)
    print("\naggregate shift (mean / p90):")
    for mode in ("visible", "silent"):
        print(f"  {mode}: " + ", ".join(f"{k} {v['mean']}/{v['p90']}" for k, v in delta_summary[mode].items()))
    print("\npolicy means (sink errors, 4 conclusions):")
    for key, tab in policy_table.items():
        print(f"  {key}: " + ", ".join(f"{p}={v['mean']}" for p, v in tab.items()))
    print("\nfragility of real conclusions:")
    for k, v in frag.items():
        print(f"  {k}: median margin {v['median_margin']}, p10 {v['p10_margin']}, "
              f"p90 shift {v['p90_one_night_shift']} -> {v['pct_within_p90_shift']}% at risk, "
              f"{v['pct_conclusion_true']}% already true")
    print("\nany-flip rate by nights per participant:")
    for b, v in by_n_out.items():
        print("  " + b + ": " + ", ".join(f"{m} {x['pct_any_flip']}% (n={x['n']})" for m, x in v.items()))
    print("\nflip rate when a FRACTION of nights is corrupted:")
    for f_, v in frac_flip.items():
        print(f"  {f_}: " + ", ".join(f"{x} {y['pct_flip']}%" for x, y in v.items() if x != "any")
              + f" | any {v['any']['pct_flip']}%")
    print("\ndropped records:", head["records_dropped"])
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
