#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capture-side pathologies: what has to be fixed before any scheduler can help.

§12d showed that a silent WASO→0 defect has nothing to schedule: every review
policy lands at 0.02-0.05 sink errors and even the oracle only reaches 0.01. A
scheduler cannot recover information that was never recorded. This script counts
those cases in the real export so the claim is measured, not asserted.

Everything here is a *per-record* aggregate. No per-row output is written.

Checks
------
  waso_all_zero        every night of the record reports WASO = 0. Efficiency is
                       then computed from the full sleep period, so C2 is not
                       interpretable. Suppress the conclusion; do not review it.
  waso_zero_share      share of nights reporting WASO = 0 across the cohort.
  records_ge50pct_waso_zero
                       records where half or more of the nights report WASO = 0:
                       the denominator of every SE aggregate is inflated.
  waso_run_ge3         >= 3 consecutive nights report WASO = 0 inside a record
                       that otherwise records awakenings. Compared against a
                       permutation null (the same number of zeros scattered at
                       random inside that record), because WASO = 0 is common
                       enough that a run can appear by chance alone.
  ampm_recoverable     the night breaks the order rules, but shifting exactly one
                       field by ±12 h makes it order-valid: an AM/PM convention
                       applied to one field. This is the `order_error` family
                       (57/75 corrections) and it is a *validation* rule, not a
                       review decision.
  coverage             nights present / span of the record's own day numbers.
                       Missing nights shrink the denominator of every aggregate
                       silently.

Not checked
-----------
`sleep_awake_equal`: `awake` in this export is the wake clock time, not a time
spent awake, so `awake == sleep` is the definition of a zero-length sleep period
and is never expected. The correction-log error type of that name cannot be
detected from these columns; it needs the diary's own WASO field.

Input: the de-identified daily export. Never committed.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from collections import Counter, defaultdict
from datetime import timedelta

import cross_record_replay as C

RUN_LEN = 3


def night_flags(ts, waso):
    """Per-night pathology flags, computed from raw times only."""
    night = C.compute(ts, waso)
    flags = {
        "waso_zero": waso == 0.0,
        "ampm_recover": False,
        "invalid": night is None,
    }
    if night is not None and not night["order_ok"]:
        for field in C.FIELDS:
            for sign in (12, -12):
                cand = dict(ts)
                cand[field] = cand[field] + timedelta(hours=sign)
                n2 = C.compute(cand, waso)
                if n2 is not None and n2["order_ok"]:
                    flags["ampm_recover"] = True
    return flags


def longest_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def expected_run_prob(flags, rng, draws=400, run_len=RUN_LEN):
    """P(longest run >= run_len) if the same number of zeros were scattered at random.

    Without this null, "45 % of records have a 3-night zero run" is not evidence
    of anything: WASO is zero on ~40 % of nights anyway.
    """
    flags = list(flags)
    if sum(flags) < run_len:
        return 0.0
    hits = 0
    for _ in range(draws):
        rng.shuffle(flags)
        hits += longest_run(flags) >= run_len
    return hits / draws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-csv", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir,
        "runs", "capture-checks", "results.json"))
    ap.add_argument("--min-nights", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261124)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    recs = C.load(args.daily_csv)
    by_pid = defaultdict(list)
    for r in recs:
        by_pid[r["pid"]].append(r)

    totals = Counter()
    expected_runs = 0.0
    coverages, zero_shares = [], []
    nights_total = 0
    n = 0

    for pid, rows in by_pid.items():
        rows = sorted(rows, key=lambda r: r["ts"]["bed"])
        if len(rows) < args.min_nights:
            continue
        n += 1
        nights_total += len(rows)

        flags = [night_flags(r["ts"], float(r["night"]["_waso"])) for r in rows]
        waso_zero = [f["waso_zero"] for f in flags]
        n_zero = sum(waso_zero)
        share = n_zero / len(rows)
        zero_shares.append(share)

        longest = longest_run(waso_zero)
        is_run = longest >= RUN_LEN and not all(waso_zero)

        totals["waso_all_zero"] += int(all(waso_zero))
        totals["nights_in_all_zero"] += n_zero if all(waso_zero) else 0
        totals["nights_waso_zero"] += n_zero
        totals["ge50pct_waso_zero"] += int(share >= 0.5)
        totals["waso_run"] += int(is_run)
        if is_run:
            expected_runs += expected_run_prob(waso_zero, rng)
        totals["any_ampm"] += int(any(f["ampm_recover"] for f in flags))
        totals["nights_ampm"] += sum(f["ampm_recover"] for f in flags)
        totals["invalid_nights"] += sum(f["invalid"] for f in flags)

        days = sorted({int(float(r["day"])) for r in rows
                       if r["day"] not in (None, "", "NA")})
        if len(days) >= 2:
            coverages.append(len(days) / (days[-1] - days[0] + 1))

    pct = lambda c: round(100.0 * c / n, 1) if n else 0.0
    out = {
        "header": {
            "participants": n,
            "nights": nights_total,
            "min_nights": args.min_nights,
            "run_len": RUN_LEN,
            "null_draws": 400,
            "seed": args.seed,
            "note": "aggregates only; no per-participant rows are written",
        },
        "prevalence": {
            "waso_all_zero": {
                "records": totals["waso_all_zero"], "pct": pct(totals["waso_all_zero"]),
                "nights": totals["nights_in_all_zero"]},
            "nights_reporting_waso_zero": {
                "nights": totals["nights_waso_zero"],
                "pct_of_nights": round(100.0 * totals["nights_waso_zero"] / nights_total, 1)
                if nights_total else 0.0},
            "records_ge50pct_waso_zero": {
                "records": totals["ge50pct_waso_zero"], "pct": pct(totals["ge50pct_waso_zero"]),
                "median_zero_share": round(statistics.median(zero_shares), 3) if zero_shares else 0.0},
            "waso_run_ge3": {
                "records": totals["waso_run"], "pct": pct(totals["waso_run"]),
                "expected_records_under_null": round(expected_runs, 1)},
            "ampm_recoverable": {
                "records": totals["any_ampm"], "pct": pct(totals["any_ampm"]),
                "nights": totals["nights_ampm"]},
            "coverage": {
                "median": round(statistics.median(coverages), 3) if coverages else 0.0,
                "records_below_0_8": sum(1 for c in coverages if c < 0.8),
                "pct_below_0_8": round(100.0 * sum(1 for c in coverages if c < 0.8)
                                       / len(coverages), 1) if coverages else 0.0,
                "records_below_0_5": sum(1 for c in coverages if c < 0.5)},
        },
        "action": {
            "waso_all_zero": "ask at intake whether awakenings were recorded; if not, "
                             "SE is not interpretable and C2 must be suppressed, not reviewed",
            "records_ge50pct_waso_zero": "report SE with the zero share attached; a mean over "
                                         "nights that mostly report no awakenings is not a mean",
            "waso_run_ge3": "compare against the null before calling it a dropped diary; "
                            "WASO = 0 is the modal value",
            "ampm_recoverable": "one 12 h shift repairs the night, so fix the convention at "
                                "the form and stop spending review budget on each occurrence",
            "coverage": "publish nights present / span next to every per-participant mean",
        },
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps(out["header"], indent=2))
    print(f"{'pathology':34s} {'records':>8s} {'pct':>6s} {'nights':>8s}")
    for k, v in out["prevalence"].items():
        if "records" in v:
            print(f"{k:34s} {v['records']:8d} {v.get('pct', 0):5.1f}% {v.get('nights', 0):8d}")
        elif "nights" in v:
            print(f"{k:34s} {'-':>8s} {v.get('pct_of_nights', 0):5.1f}% {v['nights']:8d}")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
