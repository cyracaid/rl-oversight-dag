#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replay the 75 real manual corrections on a reduced sleep-pipeline DAG.

Goal: replace "synthetic graph with type rates copied from the correction file"
with an actual per-record replay: the graph values come from the record's own
timestamps, and the ground truth comes from the human correction stored in
manual_error_correction_updated.csv.

What is real here
-----------------
* Every node value is computed from that record's timestamps (not sampled).
* The truth state is the record after applying the human's correction
  (`column_to_correct` + `correct_value`).
* Node error = current value disagrees with the truth value.
* Sink errors = the four conclusion flags disagree with the truth flags.

What is not real
----------------
* The DAG is a 14-node reduction of the 21-node pipeline in
  real_pipeline_graph.py; it is recomputed here in Python, not taken from the
  R package output. The three diff columns shipped with the CSV (bed_sleep_diff_h,
  sleep_awake_diff_h, awake_getup_diff_h) are used as a validation gate: if our
  computation disagrees with them, the script refuses to report.
* The reviewer is simulated (catch probability), not the actual annotator.
* 53 of 75 rows have four complete timestamps; 22 rows miss a time and are
  excluded from the replay (listed, not silently dropped).

Reviewer models
---------------
root_cause : inspecting any wrong node identifies the record's defective source
             field(s) and fixes them (matches the `problem_humanidentified`
             column, where a human names the root cause from a downstream anomaly).
local      : inspecting a node only fixes a defect at that node or at its direct
             parents. Fixing a depth-3 sink therefore needs a walk up the graph.

The point of running both is to show how much of the "scheduling" problem is an
artefact of the reviewer model rather than of the data.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import statistics
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(
    os.path.expanduser("~"), "Documents", "splsleep", "manual_error_correction_updated.csv"
)

FIELDS = ("bed", "sleep", "awake", "getup")

# ---- reduced DAG -------------------------------------------------------------
# name -> parents
NODES = {
    "time_bed": [],
    "time_sleep": [],
    "time_awake": [],
    "time_getup": [],
    "SOL_calc": ["time_bed", "time_sleep"],
    "sleep_awake_diff": ["time_sleep", "time_awake"],
    "awake_getup_diff": ["time_awake", "time_getup"],
    "TIB": ["time_bed", "time_getup"],
    "TST": ["time_sleep", "time_awake"],
    "SE": ["TST", "TIB"],
    "SOL_validity": ["SOL_calc"],
    "WASO_validity": ["time_sleep", "time_awake"],
    "SE_conclusion": ["SE", "SOL_calc"],
    "record_quality": ["time_bed", "time_sleep", "time_awake", "time_getup"],
}
LEAVES = [n for n, p in NODES.items() if not p]
SINKS = ["SOL_validity", "WASO_validity", "SE_conclusion", "record_quality"]

# thresholds from splsleep inst/config_default.yaml
T = dict(
    bed_to_sleep_max_h=7.0,
    awake_to_getup_max_h=7.0,
    sleep_to_awake_max_h=24.0,
    sol_excessive_min=120.0,
    waso_excessive_min=90.0,
    se_min=0.0,
    se_max=100.0,
    ratio_min=0.5,
    ratio_max=1.0,
    # "unusual" band, used only for the observable suspicion signal
    unusual_sol_h=3.0,
    unusual_getup_h=3.0,
    short_sleep_h=3.0,
)

TIME_TOL = timedelta(minutes=1)
HOUR_TOL = 0.02


def parse_time(s):
    s = (s or "").strip()
    for fmt in ("%m/%d/%y %H:%M", "%m/%d/%y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def apply_correction(value, correct):
    """Apply the human's `correct_value` to one field. Returns None if unparseable."""
    c = (correct or "").strip()
    m = re.match(r"same day (\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?", c, re.I)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ap = (m.group(4) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return value.replace(hour=h, minute=mi, second=0, microsecond=0)
    m = re.search(r"(minus|plus)\s+(\d+)\s*hours?", c, re.I)
    if m:
        d = timedelta(hours=int(m.group(2)))
        return value - d if m.group(1).lower() == "minus" else value + d
    return None


def minutes_of(hhmm):
    if not hhmm:
        return None
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", hhmm)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def compute(ts, waso_min):
    """Node values for one record. `ts` is a dict of datetimes."""
    bed, sleep, awake, getup = (ts[f] for f in FIELDS)
    sol_h = (sleep - bed).total_seconds() / 3600.0
    sad_h = (awake - sleep).total_seconds() / 3600.0
    agd_h = (getup - awake).total_seconds() / 3600.0
    tib_h = (getup - bed).total_seconds() / 3600.0
    waso = 0.0 if waso_min is None else float(waso_min)
    tst_h = sad_h - waso / 60.0
    if tib_h > 0:
        se = 100.0 * tst_h / tib_h
        ratio = tst_h / tib_h
    else:
        se, ratio = float("nan"), float("nan")

    sol_ok = 0.0 <= sol_h * 60.0 <= T["sol_excessive_min"]
    waso_ok = 0.0 <= waso <= T["waso_excessive_min"]
    se_ok = (
        not math.isnan(se)
        and T["se_min"] <= se <= T["se_max"]
        and T["ratio_min"] <= ratio <= T["ratio_max"]
    )
    rec_ok = (
        abs(sol_h) <= T["bed_to_sleep_max_h"]
        and abs(agd_h) <= T["awake_to_getup_max_h"]
        and abs(sad_h) <= T["sleep_to_awake_max_h"]
    )
    return {
        "time_bed": bed,
        "time_sleep": sleep,
        "time_awake": awake,
        "time_getup": getup,
        "SOL_calc": sol_h,
        "sleep_awake_diff": sad_h,
        "awake_getup_diff": agd_h,
        "TIB": tib_h,
        "TST": tst_h,
        "SE": se,
        "SOL_validity": sol_ok,
        "WASO_validity": waso_ok,
        "SE_conclusion": se_ok,
        "record_quality": rec_ok,
    }


def node_differs(name, a, b):
    x, y = a[name], b[name]
    if isinstance(x, bool):
        return x != y
    if isinstance(x, datetime):
        return abs(x - y) > TIME_TOL
    if isinstance(x, float) and math.isnan(x) and math.isnan(y):
        return False
    return abs(x - y) > HOUR_TOL


def ancestors(name):
    out, stack = set(), list(NODES[name])
    while stack:
        p = stack.pop()
        if p in out:
            continue
        out.add(p)
        stack.extend(NODES[p])
    return out


def load_rows(path):
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    kept, dropped, gate_fail = [], [], []
    for r in rows:
        ts = {f: parse_time(r.get(f"time_{f}_corrected")) for f in FIELDS}
        if any(v is None for v in ts.values()):
            missing = [f for f, v in ts.items() if v is None]
            dropped.append({"row_id": r.get("row_id"), "pid": r.get("pid"), "missing": missing})
            continue

        # validation gate: our derived hours must match the CSV's own columns
        sol_h = (ts["sleep"] - ts["bed"]).total_seconds() / 3600.0
        sad_h = (ts["awake"] - ts["sleep"]).total_seconds() / 3600.0
        agd_h = (ts["getup"] - ts["awake"]).total_seconds() / 3600.0
        for got, col in ((sol_h, "bed_sleep_diff_h"), (sad_h, "sleep_awake_diff_h"), (agd_h, "awake_getup_diff_h")):
            try:
                want = float(r.get(col, ""))
            except ValueError:
                continue
            if abs(got - want) > 0.02:
                gate_fail.append({"row_id": r.get("row_id"), "col": col, "ours": round(got, 3), "csv": want})

        cols = [
            c.strip().replace("_corrected", "").replace("time_", "")
            for c in (r.get("column_to_correct") or "").split(",")
            if c.strip()
        ]
        truth = dict(ts)
        ok = True
        for c in cols:
            if c not in truth:
                ok = False
                break
            nv = apply_correction(truth[c], r.get("correct_value"))
            if nv is None:
                ok = False
                break
            truth[c] = nv
        if not ok:
            dropped.append({"row_id": r.get("row_id"), "pid": r.get("pid"), "missing": ["unparsed_correction"]})
            continue

        waso = minutes_of(r.get("duration_totalmin_waso_estimate_am"))
        cur_vals = compute(ts, waso)
        tru_vals = compute(truth, waso)
        wrong = {n for n in NODES if node_differs(n, cur_vals, tru_vals)}
        defective_leaves = {n for n in LEAVES if n in wrong}
        kept.append(
            dict(
                row_id=r.get("row_id"),
                pid=r.get("pid"),
                error_type=(r.get("error_type") or "").strip() or "unlabeled",
                agreement=r.get("agreement_cd_mtb"),
                cols=cols,
                waso_min=waso,
                cur=cur_vals,
                truth=tru_vals,
                wrong=wrong,
                defective=defective_leaves,
                sink_errors=sum(1 for s in SINKS if s in wrong),
                suspicion=suspicion(cur_vals),
            )
        )
    return kept, dropped, gate_fail


def suspicion(v):
    """Observable QC signal. Uses only the current (pre-review) values."""
    s = {n: 0.0 for n in NODES}
    sol_h, sad_h, agd_h = v["SOL_calc"], v["sleep_awake_diff"], v["awake_getup_diff"]
    tib_h, tst_h, se = v["TIB"], v["TST"], v["SE"]
    # raw-pair checks (the same rules the package's Step-5 classification uses)
    s["SOL_calc"] = 1.0 if abs(sol_h) > T["unusual_sol_h"] else 0.0
    s["sleep_awake_diff"] = 1.0 if (sad_h > T["sleep_to_awake_max_h"] or sad_h < T["short_sleep_h"]) else 0.0
    s["awake_getup_diff"] = 1.0 if abs(agd_h) > T["unusual_getup_h"] else 0.0
    s["TIB"] = 1.0 if tib_h <= 0 or tib_h > 24 else 0.0
    s["TST"] = 1.0 if tib_h <= 0 or tst_h < 0 else 0.0
    s["SE"] = 1.0 if (math.isnan(se) or se < T["se_min"] or se > T["se_max"]) else 0.0
    s["SOL_validity"] = 1.0 if not v["SOL_validity"] else 0.0
    s["WASO_validity"] = 1.0 if not v["WASO_validity"] else 0.0
    s["SE_conclusion"] = 1.0 if not v["SE_conclusion"] else 0.0
    s["record_quality"] = 1.0 if not v["record_quality"] else 0.0
    for leaf in LEAVES:
        desc = [n for n in NODES if leaf in ancestors(n)] + [leaf]
        s[leaf] = sum(s[n] for n in desc) / max(1, len(desc))
    return s


class Episode:
    """One record. State = which leaves have been fixed."""

    def __init__(self, row, p_catch, reviewer):
        self.row = row
        self.p_catch = p_catch
        self.reviewer = reviewer
        self.fixed = set()

    def values(self):
        ts = {f: self.row["cur"][f"time_{f}"] for f in FIELDS}
        for leaf in self.fixed:
            if leaf in self.defective():
                ts[leaf.replace("time_", "")] = self.row["truth"][leaf]
        return compute(ts, self.row["waso_min"])

    def defective(self):
        return self.row["defective"]

    def wrong_nodes(self):
        v = self.values()
        return {n for n in NODES if node_differs(n, v, self.row["truth"])}

    def review(self, node, rng):
        """Attempt a review at `node`. Returns True if it fixed something."""
        pre = self.wrong_nodes()
        if node not in pre:
            return False
        if rng.random() >= self.p_catch:
            return False
        defects = self.defective() - self.fixed
        if not defects:
            return False
        if self.reviewer == "root_cause":
            target = set(defects)
        else:  # local: this node or its direct parents
            reach = {node} | set(NODES[node])
            target = {d for d in defects if d in reach}
        if not target:
            return False
        self.fixed |= target
        return True

    def sink_errors(self):
        v = self.values()
        return sum(1 for s in SINKS if node_differs(s, v, self.row["truth"]))


def policy_choice(policy, ep, rng, reviewed):
    avail = [n for n in NODES if n not in reviewed]
    if not avail:
        return None
    susp = ep.row["suspicion"]
    if policy == "random":
        return rng.choice(avail)
    if policy == "threshold":
        return max(avail, key=lambda n: (susp[n], rng.random()))
    if policy == "structural":
        influence = {n: 1 + sum(1 for s in SINKS if n == s or n in ancestors(s)) for n in NODES}
        return max(avail, key=lambda n: (susp[n] * influence[n], rng.random()))
    if policy == "leaf_first":
        leaves_avail = [n for n in avail if n in LEAVES]
        pool = leaves_avail or avail
        return max(pool, key=lambda n: (susp[n], rng.random()))
    if policy == "oracle":
        # truth-guided greedy: fix as many defects, then as many wrong nodes, as possible
        best, best_key = None, None
        for n in avail:
            probe = Episode(ep.row, 1.0, ep.reviewer)
            probe.fixed = set(ep.fixed)
            pre_sink = probe.sink_errors()
            pre_wrong = len(probe.wrong_nodes())
            probe.review(n, random.Random(0))
            key = (
                len(probe.fixed) - len(ep.fixed),        # defects fixed
                pre_sink - probe.sink_errors(),          # sink errors removed now
                pre_wrong - len(probe.wrong_nodes()),    # wrong nodes removed
            )
            if best_key is None or key > best_key:
                best, best_key = n, key
        return best
    raise ValueError(policy)


def run_policy(rows, policy, budget, p_catch, reviewer, seeds):
    out = []
    for seed in range(seeds):
        errs = []
        first_clear = []
        for row in rows:
            rng = random.Random(seed * 7919 + zlib.crc32(str(row["row_id"]).encode()) % 100003)
            ep = Episode(row, p_catch, reviewer)
            reviewed = set()
            cleared_at = None
            if ep.sink_errors() == 0:
                cleared_at = 0
            for step in range(budget):
                n = policy_choice(policy, ep, rng, reviewed)
                if n is None:
                    break
                reviewed.add(n)
                ep.review(n, rng)
                if cleared_at is None and ep.sink_errors() == 0:
                    cleared_at = step + 1
            errs.append(ep.sink_errors())
            first_clear.append(cleared_at)
        out.append({"seed": seed, "mean": statistics.fmean(errs), "errors": errs, "cleared_at": first_clear})
    means = [o["mean"] for o in out]
    return {
        "mean": statistics.fmean(means),
        "sd_across_seeds": statistics.pstdev(means) if len(means) > 1 else 0.0,
        "per_seed": means,
        "errors_seed0": out[0]["errors"],
        "cleared_at_seed0": out[0]["cleared_at"],
    }


def boot_ci(values, n_boot=2000, seed=0):
    rng = random.Random(seed)
    n = len(values)
    if n < 2:
        return (float("nan"), float("nan"))
    bs = []
    for _ in range(n_boot):
        bs.append(statistics.fmean(rng.choice(values) for _ in range(n)))
    bs.sort()
    return (bs[int(0.025 * n_boot)], bs[int(0.975 * n_boot)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--out", default=os.path.join(HERE, os.pardir, "runs", "replay-manual-corrections", "results.json"))
    ap.add_argument("--seeds", type=int, default=30)
    args = ap.parse_args()

    rows, dropped, gate_fail = load_rows(args.csv)
    if gate_fail:
        raise SystemExit(f"validation gate failed on {len(gate_fail)} cells: {gate_fail[:3]}")

    head = {
        "csv": args.csv,
        "rows_in_file": len(rows) + len(dropped),
        "rows_replayed": len(rows),
        "rows_dropped": len(dropped),
        "participants": len({r["pid"] for r in rows}),
        "drop_reasons": dict(Counter(x["missing"][0] for x in dropped)),
        "validation_gate": {"cells_checked": len(rows) * 3, "mismatches": 0},
    }

    # descriptive: what the errors actually look like
    def desc(rows):
        d = {}
        d["error_type"] = dict(Counter(r["error_type"] for r in rows))
        d["defective_leaf_count"] = dict(Counter(len(r["defective"]) for r in rows))
        d["sink_errors_before"] = {
            "mean": statistics.fmean(r["sink_errors"] for r in rows),
            "hist": dict(sorted(Counter(r["sink_errors"] for r in rows).items())),
        }
        d["wrong_node_count"] = {
            "mean": statistics.fmean(len(r["wrong"]) for r in rows),
            "hist": dict(sorted(Counter(len(r["wrong"]) for r in rows).items())),
        }
        # how many sink errors one perfect review of the defective leaf can remove
        d["sink_errors_after_one_root_review"] = statistics.fmean(
            0.0 if r["defective"] else r["sink_errors"] for r in rows
        )
        # propagation evidence: how many sink errors follow from one source defect
        one = [r["sink_errors"] for r in rows if len(r["defective"]) == 1]
        d["one_defect_sink_errors"] = {
            "n": len(one),
            "mean": statistics.fmean(one) if one else float("nan"),
            "hist": dict(sorted(Counter(one).items())),
        }
        per_type = defaultdict(list)
        for r in rows:
            per_type[r["error_type"]].append(r["sink_errors"])
        d["sink_errors_by_type"] = {
            k: {"n": len(v), "mean": round(statistics.fmean(v), 2)} for k, v in sorted(per_type.items())
        }
        # does the observable suspicion point at a defective leaf? (top-1 hit rate)
        hits = []
        for r in rows:
            if not r["defective"]:
                hits.append(None)
                continue
            best = max(NODES, key=lambda n: (r["suspicion"][n], n))
            hits.append(1.0 if best in r["wrong"] else 0.0)
        hits = [h for h in hits if h is not None]
        d["suspicion_top1_is_wrong"] = statistics.fmean(hits) if hits else float("nan")
        d["suspicion_top1_n"] = len(hits)
        return d

    result = {"header": head, "descriptive": desc(rows), "policies": {}}

    for reviewer in ("root_cause", "local"):
        for budget in (1, 2, 4, 8):
            key = f"{reviewer}|b{budget}"
            result["policies"][key] = {}
            for policy in ("none", "random", "threshold", "structural", "leaf_first", "oracle"):
                if policy == "none":
                    v = statistics.fmean(r["sink_errors"] for r in rows)
                    result["policies"][key][policy] = {"mean": v, "sd_across_seeds": 0.0}
                    continue
                res = run_policy(rows, policy, budget, 0.9, reviewer, args.seeds)
                lo, hi = boot_ci(res["errors_seed0"])
                res["ci95_row_bootstrap"] = [lo, hi]
                res.pop("errors_seed0")
                result["policies"][key][policy] = res

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(result["descriptive"], indent=2, default=str))
    print("\nrows replayed:", head["rows_replayed"], "dropped:", head["rows_dropped"])
    print("\n| reviewer | budget | none | random | threshold | structural | leaf_first | oracle |")
    print("|---|---|---|---|---|---|---|---|")
    for reviewer in ("root_cause", "local"):
        for budget in (1, 2, 4, 8):
            p = result["policies"][f"{reviewer}|b{budget}"]
            cells = []
            for pol in ("none", "random", "threshold", "structural", "leaf_first", "oracle"):
                m = p[pol]["mean"]
                cells.append(f"{m:.2f}" if pol == "none" else f"{m:.2f} ({p[pol]['sd_across_seeds']:.2f})")
            print(f"| {reviewer} | {budget} | " + " | ".join(cells) + " |")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
