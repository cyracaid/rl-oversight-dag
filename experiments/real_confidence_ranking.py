#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gap D, positive-only half: does the observable QC signal localise the error?

`signal_calibration_real.py` fits `mu_err / mu_good / sigma` and needs audited
*correct* rows to do it. We do not have any: every row in the correction file is
a confirmed error. So the full calibration is blocked.

What is not blocked: inside a record, the correct nodes are negatives. Each
replayed record therefore contains BOTH classes, and we can ask the one question
that matters for the paper --

    given a record we already know is wrong, does the pipeline's own observable
    signal rank the wrong node above the correct ones?

That is a localisation diagnostic, not a calibration. It needs no new human work
and it uses only the correction file we already have.

Two observables are compared:

1. `suspicion` -- the binary Step-5 flag rule already used by
   `replay_manual_corrections.py` (thresholds in that module's `T`). This is the
   signal every committed real-data result is built on, so it is the one that
   has to be measured.
2. `violation` -- exploratory, NOT pre-registered: the same rule as a continuous
   severity (hours past the threshold). It exists to separate "the rule has no
   information" from "the rule throws away its information by binarising".

Ranking is evaluated with tie-aware statistics, because the binary rule produces
massive ties (most records have one shared maximum). Optimistic and pessimistic
tie-breaks bracket the truth; a seeded random tie-break gives the expectation.

Never reads or writes participant-level rows to the repo. The CSV path defaults
to the local collaboration folder and must not be committed.

Usage:
    python3 experiments/real_confidence_ranking.py \
        [--csv ~/Documents/splsleep/manual_error_correction_updated.csv] \
        [--out runs/real-confidence-ranking/results.json]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import replay_manual_corrections as R  # noqa: E402

SINKS = sorted(R.SINKS) if hasattr(R, "SINKS") else []
SEED = 0
N_PERM = 2000


# --------------------------------------------------------------------------- #
# tie-aware statistics
# --------------------------------------------------------------------------- #
def auc_with_ties(scores, labels):
    """Mann-Whitney AUC; a tied positive/negative pair counts 0.5.

    Returns None when a record has only one class (undefined AUC).
    """
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    total = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                total += 1.0
            elif p == n:
                total += 0.5
    return total / (len(pos) * len(neg))


def rank_bounds(scores, idx):
    """(optimistic, pessimistic) rank of `scores[idx]`, 1-based."""
    s = scores[idx]
    better = sum(1 for j, x in enumerate(scores) if j != idx and x > s)
    equal = sum(1 for j, x in enumerate(scores) if j != idx and x == s)
    return better + 1, better + equal + 1


def hit_at_k_expected(scores, targets, k, rng, n_perm=N_PERM):
    """P(at least one target in the top-k) under a random tie-break."""
    if not targets:
        return None
    n = len(scores)
    hits = 0
    for _ in range(n_perm):
        order = sorted(range(n), key=lambda j: (-scores[j], rng.random()))
        if any(j in targets for j in order[:k]):
            hits += 1
    return hits / n_perm


def tie_census(scores):
    top = max(scores)
    return {
        "distinct_scores": len(set(scores)),
        "nodes_at_max": sum(1 for s in scores if s == top),
        "max_score": top,
    }


# --------------------------------------------------------------------------- #
# per-record evaluation
# --------------------------------------------------------------------------- #
TARGET_KINDS = ("source_leaf", "raw_leaf", "any_wrong")


def target_indices(kind, names, wrong, defective):
    if kind == "source_leaf":
        return defective if defective else wrong
    if kind == "raw_leaf":
        return {i for i, n in enumerate(names) if n in R.LEAVES and i in wrong}
    return wrong


def evaluate_record(row, score_fn, rng):
    """Per-record metrics for every target definition and the shared AUC.

    `auc` uses every wrong node as a positive and every correct node as a
    negative, so it does not depend on the target definition. The hit@k / rank
    metrics do, which is the point: a rule that ranks wrong-vs-correct well can
    still be useless for picking which node to look at.
    """
    names = list(R.NODES)
    scores = [float(score_fn(row, n)) for n in names]
    wrong = {i for i, n in enumerate(names) if n in row["wrong"]}
    defective = {i for i, n in enumerate(names) if n in row["defective"]}
    labels = [i in wrong for i in range(len(names))]

    per_target = {}
    for kind in TARGET_KINDS:
        targets = target_indices(kind, names, wrong, defective)
        if not targets:
            per_target[kind] = None
            continue
        ranks = [rank_bounds(scores, i) for i in targets]
        best_opt = min(r[0] for r in ranks)
        best_pess = min(r[1] for r in ranks)
        per_target[kind] = {
            "n_targets": len(targets),
            "rank_optimistic": best_opt,
            "rank_pessimistic": best_pess,
            "hit1_optimistic": 1.0 if best_opt <= 1 else 0.0,
            "hit1_pessimistic": 1.0 if best_pess <= 1 else 0.0,
            "hit3_optimistic": 1.0 if best_opt <= 3 else 0.0,
            "hit3_pessimistic": 1.0 if best_pess <= 3 else 0.0,
            "hit1_expected": hit_at_k_expected(scores, targets, 1, rng),
            "hit3_expected": hit_at_k_expected(scores, targets, 3, rng),
        }

    top = max(scores)
    top_nodes = sorted(n for n, s in zip(names, scores) if s == top)

    return {
        "row_id": row["row_id"],
        "pid": row["pid"],
        "error_type": row["error_type"],
        "n_nodes": len(names),
        "n_wrong": len(wrong),
        "n_defective": len(defective),
        "top_score": top,
        "top_nodes": top_nodes,
        "auc": auc_with_ties(scores, labels),
        "targets": per_target,
        "ties": tie_census(scores),
    }


# --------------------------------------------------------------------------- #
# observables
# --------------------------------------------------------------------------- #
def score_suspicion(row, name):
    return row["suspicion"][name]


def score_violation(row, name):
    """Exploratory continuous severity: hours past the same thresholds.

    Nodes that are not a raw pair or a derived hour get their own violation in
    the same units the boolean rule uses, so the ordering stays comparable to
    `suspicion`. Everything a boolean rule would score 1.0 gets > 0 here.
    """
    v = row["cur"]
    nan = float("nan")

    def over(x, limit):
        return 0.0 if (x != x) else max(0.0, x - limit)

    sol = v["SOL_calc"]
    sad = v["sleep_awake_diff"]
    agd = v["awake_getup_diff"]
    tib = v["TIB"]
    tst = v["TST"]
    se = v["SE"]
    raw = {
        "SOL_calc": over(abs(sol), R.T["unusual_sol_h"]),
        "sleep_awake_diff": max(
            over(sad, R.T["sleep_to_awake_max_h"]),
            over(R.T["short_sleep_h"] - sad if sad == sad else nan, 0.0),
        ),
        "awake_getup_diff": over(abs(agd), R.T["unusual_getup_h"]),
        "TIB": 24.0 if (tib <= 0 or tib > 24) else 0.0,
        "TST": 24.0 if (tib <= 0 or tst < 0) else 0.0,
        "SE": 100.0 if (se != se or se < R.T["se_min"] or se > R.T["se_max"]) else 0.0,
        "SOL_validity": 0.0 if v["SOL_validity"] else 1.0,
        "WASO_validity": 0.0 if v["WASO_validity"] else 1.0,
        "SE_conclusion": 0.0 if v["SE_conclusion"] else 1.0,
        "record_quality": 0.0 if v["record_quality"] else 1.0,
    }
    if name in raw:
        return raw[name]
    leaf = name
    desc = [n for n in R.NODES if leaf in R.ancestors(n)] + [leaf]
    return sum(raw[n] for n in desc if n in raw) / max(1, len(desc))


def node_group(name):
    """Coarse role of a node, used to show where any apparent signal comes from."""
    if name in R.LEAVES:
        return "raw_leaf"
    if name in VALIDITY_SINKS:
        return "validity_sink"
    return "derived"


VALIDITY_SINKS = {"SOL_validity", "WASO_validity", "SE_conclusion", "record_quality"}


def pooled_by_group(rows, score_fn):
    """Pool every (node, record) pair and compute AUC inside each node group.

    The pooled AUC is dominated by the validity sinks, whose value is wrong
    exactly when the check that feeds them fires. Splitting the groups separates
    "the rule re-reads its own consequences" from "the rule localises a cause".
    """
    buckets = {}
    for row in rows:
        for name in R.NODES:
            buckets.setdefault(node_group(name), []).append(
                (float(score_fn(row, name)), name in row["wrong"])
            )
    out = {}
    for g, pairs in sorted(buckets.items()):
        scores = [p[0] for p in pairs]
        labels = [p[1] for p in pairs]
        prev = sum(1 for l in labels if l) / len(labels)
        out[g] = {
            "n": len(pairs),
            "prevalence": round(prev, 3),
            "auc_pooled": (
                round(auc_with_ties(scores, labels), 4) if auc_with_ties(scores, labels) is not None else None
            ),
            "frac_scored_positive": round(sum(1 for x in scores if x > 0) / len(scores), 3),
            "mean_score": round(statistics.fmean(scores), 3),
        }
    return out


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def boot_ci(values, rng, n_boot=2000):
    if len(values) < 3:
        return [float("nan"), float("nan")]
    means = []
    n = len(values)
    for _ in range(n_boot):
        means.append(statistics.fmean(values[rng.randrange(n)] for _ in range(n)))
    means.sort()
    return [round(means[int(0.025 * n_boot)], 4), round(means[int(0.975 * n_boot) - 1], 4)]


def summarise(per_record, rng):
    aucs = [r["auc"] for r in per_record if r["auc"] is not None]
    n_nodes = per_record[0]["n_nodes"] if per_record else 0
    ties = {
        "records_one_distinct_score": sum(1 for r in per_record if r["ties"]["distinct_scores"] == 1),
        "records_with_tied_max": sum(1 for r in per_record if r["ties"]["nodes_at_max"] > 1),
        "mean_nodes_at_max": round(statistics.fmean(r["ties"]["nodes_at_max"] for r in per_record), 2),
        "mean_distinct_scores": round(statistics.fmean(r["ties"]["distinct_scores"] for r in per_record), 2),
    }
    by_target = {}
    for kind in TARGET_KINDS:
        sel = [r for r in per_record if r["targets"].get(kind)]
        if not sel:
            by_target[kind] = None
            continue
        t = [r["targets"][kind] for r in sel]
        by_target[kind] = {
            "records": len(sel),
            "n_targets_mean": round(statistics.fmean(x["n_targets"] for x in t), 2),
            "hit1_expected": round(statistics.fmean(x["hit1_expected"] for x in t), 4),
            "hit1_pessimistic": round(statistics.fmean(x["hit1_pessimistic"] for x in t), 4),
            "hit1_optimistic": round(statistics.fmean(x["hit1_optimistic"] for x in t), 4),
            "hit3_expected": round(statistics.fmean(x["hit3_expected"] for x in t), 4),
            "hit3_pessimistic": round(statistics.fmean(x["hit3_pessimistic"] for x in t), 4),
            "hit3_optimistic": round(statistics.fmean(x["hit3_optimistic"] for x in t), 4),
            "rank_optimistic_mean": round(statistics.fmean(x["rank_optimistic"] for x in t), 2),
            "rank_pessimistic_mean": round(statistics.fmean(x["rank_pessimistic"] for x in t), 2),
        }
    top_identity = Counter()
    for r in per_record:
        for n in r["top_nodes"]:
            top_identity[n] += 1
    return {
        "records": len(per_record),
        "n_nodes": n_nodes,
        "mean_n_wrong": round(statistics.fmean(r["n_wrong"] for r in per_record), 2),
        "mean_n_defective": round(statistics.fmean(r["n_defective"] for r in per_record), 2),
        "auc_mean": round(statistics.fmean(aucs), 4) if aucs else None,
        "auc_ci95": boot_ci(aucs, rng) if aucs else None,
        "auc_chance": 0.5,
        "by_target": by_target,
        "top1_identity": dict(top_identity.most_common()),
        "ties": ties,
    }


def per_type(per_record, rng):
    groups = {}
    for r in per_record:
        groups.setdefault(r["error_type"], []).append(r)
    out = {}
    for k, rows in sorted(groups.items()):
        aucs = [r["auc"] for r in rows if r["auc"] is not None]
        src = [r["targets"]["source_leaf"] for r in rows if r["targets"].get("source_leaf")]
        out[k] = {
            "n": len(rows),
            "auc_mean": round(statistics.fmean(aucs), 4) if aucs else None,
            "hit1_expected_source": (
                round(statistics.fmean(x["hit1_expected"] for x in src), 4) if src else None
            ),
            "note": "n < 5, descriptive only" if len(rows) < 5 else "",
        }
    return out


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=R.DEFAULT_CSV)
    ap.add_argument(
        "--out",
        default=os.path.join(HERE, os.pardir, "runs", "real-confidence-ranking", "results.json"),
    )
    ap.add_argument(
        "--include-per-record",
        action="store_true",
        help="also dump one block per record (no pids). Off by default: the "
        "committed artefact should stay aggregate-only.",
    )
    args = ap.parse_args()

    rows, dropped, gate_fail = R.load_rows(args.csv)
    if gate_fail:
        raise SystemExit(f"validation gate failed on {len(gate_fail)} cells: {gate_fail[:3]}")

    rng = random.Random(SEED)
    per_record = [evaluate_record(r, score_suspicion, rng) for r in rows]
    per_record_v = [evaluate_record(r, score_violation, rng) for r in rows]

    result = {
        "provenance": {
            "csv": args.csv,
            "seed": SEED,
            "permutations_per_record": N_PERM,
            "gate": {"cells_checked": len(rows) * 3, "mismatches": 0},
            "warning": "positives only: every record here is a confirmed error, so "
            "record-level detection/AUC is not measurable. Only within-record "
            "localisation is.",
        },
        "header": {
            "rows_replayed": len(rows),
            "rows_dropped": len(dropped),
            "participants": len({r["pid"] for r in rows}),
            "drop_reasons": dict(Counter(x["missing"][0] for x in dropped)),
        },
        "observables": {
            "suspicion_binary": {
                "aggregate": summarise(per_record, rng),
                "by_error_type": per_type(per_record, rng),
                "by_node_group": pooled_by_group(rows, score_suspicion),
            },
            "violation_continuous_exploratory": {
                "aggregate": summarise(per_record_v, rng),
                "by_error_type": per_type(per_record_v, rng),
                "by_node_group": pooled_by_group(rows, score_violation),
            },
        },
        "chance_reference": {
            "hit1": round(1 / per_record[0]["n_nodes"], 4),
            "hit3": round(3 / per_record[0]["n_nodes"], 4),
            "rank_mean": round((per_record[0]["n_nodes"] + 1) / 2, 2),
        },
    }
    if args.include_per_record:
        result["per_record"] = [{k: v for k, v in r.items() if k != "pid"} for r in per_record]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)

    print(json.dumps(result["header"], indent=2))
    for name, block in result["observables"].items():
        a = block["aggregate"]
        print(f"\n## {name}")
        print(f"  AUC {a['auc_mean']} {a['auc_ci95']}  (chance 0.50, n={a['records']})")
        print(f"  mean |wrong nodes| {a['mean_n_wrong']}, mean |source leaves| {a['mean_n_defective']}")
        print(
            f"  ties: tied max in {a['ties']['records_with_tied_max']}/{a['records']} records, "
            f"{a['ties']['mean_nodes_at_max']} nodes at max, "
            f"{a['ties']['mean_distinct_scores']} distinct scores/record"
        )
        for kind in TARGET_KINDS:
            t = a["by_target"].get(kind)
            if not t:
                continue
            print(
                f"  [{kind}] k={t['n_targets_mean']:.2f}  "
                f"hit@1 {t['hit1_expected']} [{t['hit1_pessimistic']},{t['hit1_optimistic']}]  "
                f"hit@3 {t['hit3_expected']} [{t['hit3_pessimistic']},{t['hit3_optimistic']}]  "
                f"rank {t['rank_optimistic_mean']}-{t['rank_pessimistic_mean']}"
            )
        print(f"  top-1 identity: {a['top1_identity']}")
        for g, b in block["by_node_group"].items():
            print(
                f"  [{g}] n={b['n']} prev={b['prevalence']} AUC={b['auc_pooled']} "
                f"frac>0={b['frac_scored_positive']} mean={b['mean_score']}"
            )
    c = result["chance_reference"]
    print(f"\nchance: hit@1 {c['hit1']}  hit@3 {c['hit3']}  rank {c['rank_mean']}")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
