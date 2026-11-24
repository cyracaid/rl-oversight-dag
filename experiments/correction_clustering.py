#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Do the 75 human corrections come in runs, or one night at a time?

The block-review MDP assumes the review unit can be a contiguous run of nights
because a shared cause corrupts a run.  That assumption is only worth an
experiment if the real corrections look like runs.  This script measures it
directly: for every record with two or more corrected nights, count how many of
its corrected day pairs are adjacent (day_num differing by 1), and compare with
the same count under a null that places the same number of corrected nights
uniformly at random inside that record's own observation set.

Input: manual_error_correction_updated.csv (gitignored) and the de-identified
daily export.  Nothing per-row is written to the repo; only aggregates.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
from collections import defaultdict

import cross_record_replay as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corrections", required=True)
    ap.add_argument("--daily-csv", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir,
        "runs", "correction-clustering", "results.json"))
    ap.add_argument("--draws", type=int, default=4000)
    args = ap.parse_args()

    days_by_pid = defaultdict(set)
    for r in C.load(args.daily_csv):
        try:
            days_by_pid[str(r["pid"]).strip()].add(int(float(r["day"])))
        except (TypeError, ValueError):
            pass

    corr = defaultdict(list)
    with open(args.corrections, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                corr[str(r["pid"]).strip()].append(int(float(r["day_num"])))
            except (TypeError, ValueError):
                continue

    rng = random.Random(20261124)
    rows, obs_total, exp_total = [], 0.0, 0.0
    for pid, days in corr.items():
        days = sorted(set(days))
        if len(days) < 2:
            continue
        observed_days = sorted(days_by_pid.get(pid, ()))
        if not observed_days:
            rows.append({"matched": False, "n_corrected": len(days)})
            continue
        inside = [d for d in days if d in days_by_pid[pid]]
        obs = sum(1 for a, b in zip(inside, inside[1:]) if b - a == 1)
        k = min(len(inside), len(observed_days))
        if k >= 2:
            tot = 0
            for _ in range(args.draws):
                s = sorted(rng.sample(observed_days, k))
                tot += sum(1 for a, b in zip(s, s[1:]) if b - a == 1)
            exp = tot / args.draws
        else:
            exp = 0.0
        rows.append({
            "matched": True,
            "n_corrected": len(days),
            "n_corrected_inside_export": len(inside),
            "n_observed": len(observed_days),
            "adjacent_pairs": obs,
            "expected_adjacent_pairs": round(exp, 2),
        })
        obs_total += obs
        exp_total += exp

    matched = [r for r in rows if r["matched"]]
    out = {
        "header": {
            "corrected_rows": sum(len(set(v)) for v in corr.values()),
            "records_total": len(corr),
            "records_with_2plus_corrected_nights": len(corr) - sum(
                1 for v in corr.values() if len(set(v)) == 1),
            "records_matched_to_export": len(matched),
            "draws": args.draws,
        },
        "adjacent_pairs_observed": int(obs_total),
        "adjacent_pairs_expected_if_scattered": round(exp_total, 2),
        "ratio": round(obs_total / exp_total, 2) if exp_total else None,
        "per_record": rows,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(json.dumps(out["header"], indent=2))
    print(f"adjacent corrected-night pairs: {out['adjacent_pairs_observed']} "
          f"vs {out['adjacent_pairs_expected_if_scattered']} expected if scattered "
          f"(ratio {out['ratio']})")
    for r in sorted(matched, key=lambda x: -x["n_corrected"]):
        print(f"  n_corr={r['n_corrected']:2d} inside={r['n_corrected_inside_export']:2d} "
              f"observed={r['n_observed']:2d} adjacent={r['adjacent_pairs']} "
              f"exp={r['expected_adjacent_pairs']}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
