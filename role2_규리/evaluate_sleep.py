"""Two-night review of participant sleep conclusions. Outputs contain aggregates."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path

import numpy as np

from _env import ROOT, ensure_experiments

ensure_experiments()
import cross_record_replay as original

LABELS = ("C1_short_sleep", "C2_low_efficiency", "C3_irregular", "C4_data_quality")
POLICIES = ("before_review", "random", "qc", "contiguous", "feedback")
SHIFTS = (("bed", -720), ("getup", 720), ("sleep", 60), ("awake", -60))
REQUIRED = {"pid", "day_num", "tb", "tb_ap", "ts", "ts_ap", "ta", "ta_ap",
            "tg", "tg_ap", "waso_est"}
ARCHIVE = ROOT / "runs" / "cross-record-replay" / "results.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_for(pid):
    key = hashlib.sha256(f"role2-sleep-v1-split/{pid}".encode()).digest()
    return "development" if int.from_bytes(key[:8], "big") % 5 == 0 else "evaluation"


def read_panel(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing panel columns: {', '.join(sorted(missing))}")
        for row in reader:
            if not row["pid"].strip() or row["pid"].strip().upper() == "NA":
                raise ValueError("Missing participant code; prepare an unambiguous keyed export.")
            try:
                day = float(row["day_num"])
            except (TypeError, ValueError):
                day = math.nan
            if not math.isfinite(day) or not day.is_integer():
                raise ValueError("The day_num column must use integer calendar-day offsets.")
    records = original.load(path)
    groups = defaultdict(list)
    for row in records:
        groups[row["pid"]].append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: (row["ts"]["bed"], str(row["day"])))
    return dict(groups), dict(original.load.drops)


def baseline(groups, drops, seeds):
    """Replay the exact historical visible|b2 QC cell with its original RNG."""
    eligible = {pid: rows for pid, rows in groups.items() if len(rows) >= original.MIN_NIGHTS}
    if not eligible:
        raise ValueError("No participant has enough usable nights.")
    header = {
        "records_used": sum(map(len, groups.values())),
        "participants_total": len(groups),
        "participants_with_min_nights": len(eligible),
        "min_nights": original.MIN_NIGHTS,
        "nights_per_participant_median": statistics.median(map(len, eligible.values())),
        "records_dropped": drops,
    }
    means = []
    for seed in range(seeds):
        errors = []
        for pid, rows in eligible.items():
            rng = random.Random(f"{seed}-{pid}-qc")
            index = rng.randrange(len(rows))
            current = [r["night"] for r in rows]
            target = original.conclusions(original.aggregate(current))
            raw, waso = original.corrupt(rows[index]["ts"], current[index]["_waso"], "visible", rng)
            changed = original.compute(raw, waso)
            if changed is None:
                errors.append(0)
                continue
            current[index] = changed
            reviewed = set()
            for _ in range(2):
                rest = [i for i in range(len(rows)) if i not in reviewed]
                selected = max(rest, key=lambda i: (original.suspicion(current[i]), rng.random()))
                reviewed.add(selected)
                current[selected] = rows[selected]["night"]
            after = original.conclusions(original.aggregate(current))
            errors.append(sum(target[key] != after[key] for key in target))
        means.append(statistics.fmean(errors))
    result = {"header": header, "legacy_seeds": seeds,
              "visible_b2_qc_four_conclusions": round(statistics.fmean(means), 3)}
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    expected = dict(archive["header"], visible_b2_qc_four_conclusions=archive["policies"]["visible|b2"]["qc"]["mean"])
    actual = dict(header, visible_b2_qc_four_conclusions=result["visible_b2_qc_four_conclusions"])
    result["differences_from_archive"] = {k: {"current": v, "archive": expected[k]}
                                          for k, v in actual.items() if v != expected[k]}
    return result


def windows(days):
    return [(i, i + 1) for i in range(len(days) - 1) if days[i + 1] - days[i] == 1]


def eligible_groups(groups):
    counts = Counter()
    eligible = {}
    for pid, rows in groups.items():
        rows = sorted(rows, key=lambda row: int(float(row["day"])))
        days = [int(float(row["day"])) for row in rows]
        if len(rows) < original.MIN_NIGHTS:
            counts["fewer_than_ten_nights"] += 1
        elif len(set(days)) != len(days):
            counts["duplicate_days"] += 1
        elif not windows(days):
            counts["no_consecutive_days"] += 1
        else:
            eligible[pid] = rows
    return eligible, dict(counts)


def priorities(pid, n, name):
    values = list(range(n))
    random.Random(f"role2-sleep-v1/{name}/{pid}").shuffle(values)
    return values


def choose(scores, days, pairs, ties, random_order, review):
    """Read observed scores, dates and the finding on the first reviewed night."""
    rank = sorted(range(len(days)), key=lambda i: (scores[i], ties[i]), reverse=True)
    ordered_pairs = sorted(pairs, key=lambda pair: (
        sum(scores[i] for i in pair), *sorted((ties[i] for i in pair), reverse=True)),
        reverse=True)
    first, second = rank[:2]
    adjacent = [i for i in rank[1:] if abs(days[i] - days[first]) == 1]
    feedback_second = adjacent[0] if review(first) and adjacent else second
    best_pair_score = sum(scores[i] for i in ordered_pairs[0])
    selection = {"before_review": (), "random": tuple(random_order[:2]),
                 "qc": (first, second), "contiguous": ordered_pairs[0],
                 "feedback": (first, feedback_second)}
    ties_found = {"qc_first_max_tied": scores.count(scores[first]) > 1,
                  "contiguous_max_tied": sum(sum(scores[i] for i in p) == best_pair_score for p in pairs) > 1}
    return selection, ties_found


def scenario_score(truth, current, changed, days, pairs, ties, lottery, target):
    choices, ties_found = choose([original.suspicion(n) for n in current], days, pairs,
                                 ties, lottery, changed.__contains__)
    metrics = {}
    for policy, selected in choices.items():
        restored = list(current)
        for i in selected:
            restored[i] = truth[i]
        actual = original.conclusions(original.aggregate(restored))
        errors = [int(actual[key] != target[key]) for key in LABELS]
        metrics[policy] = [sum(errors[:3]), *errors]
    return metrics, ties_found, choices


def evaluate(groups, corrected=None, case_writer=None):
    # Only participant-level averages leave the scenario loop. They keep the
    # statistical unit the same even when some people supply more windows.
    per_person = []
    ledger = Counter()
    for pid, rows in sorted(groups.items()):
        days = [int(float(r["day"])) for r in rows]
        pairs = windows(days)
        truth = [r["night"] for r in rows]
        target = original.conclusions(original.aggregate(truth))
        ties = priorities(pid, len(days), "tie")
        lottery = priorities(pid, len(days), "random")
        split = split_for(pid)
        local = {}

        def record(condition, reference, current, changed, ref_target, variant):
            metrics, tie_flags, choices = scenario_score(reference, current, changed, days, pairs,
                                                        ties, lottery, ref_target)
            if case_writer is not None:
                altered_days = " ".join(str(days[i]) for i in sorted(changed))
                for policy, selected in choices.items():
                    opened_days = " ".join(str(days[i]) for i in selected)
                    case_writer.writerow((pid, split, condition, variant, altered_days,
                                          policy, opened_days, *metrics[policy]))
            if condition not in local:
                local[condition] = {"sums": np.zeros((len(POLICIES), 5), dtype=int),
                                    "cases": 0, "ties": Counter()}
            entry = local[condition]
            entry["sums"] += np.array([metrics[p] for p in POLICIES])
            entry["cases"] += 1
            entry["ties"].update(tie_flags)

        record("clean", truth, truth, set(), target, "none")
        for field, minutes in SHIFTS:
            altered = []
            for r in rows:
                times = dict(r["ts"])
                times[field] += timedelta(minutes=minutes)
                altered.append(original.compute(times, r["night"]["_waso"]))
            for condition, locations in (("single", [(i,) for i in range(len(rows))]),
                                         ("consecutive", pairs)):
                for indices in locations:
                    tag = f"{split}/{condition}/{field}{minutes:+d}"
                    if any(altered[i] is None for i in indices):
                        ledger[tag + "/noncomputable"] += 1
                        continue
                    ledger[tag + "/included"] += 1
                    current = list(truth)
                    for i in indices:
                        current[i] = altered[i]
                    record(condition, truth, current, set(indices), target, f"{field}{minutes:+d}")

        if corrected is not None:
            other = corrected.get(pid, [])
            if days != [int(float(r["day"])) for r in other]:
                ledger[f"{split}/manual/unmatched_participant_days"] += 1
            else:
                reference = [r["night"] for r in other]
                changed = {i for i, (a, b) in enumerate(zip(rows, other))
                           if a["ts"] != b["ts"] or a["night"]["_waso"] != b["night"]["_waso"]}
                ledger[f"{split}/manual/aligned_participants"] += 1
                ledger[f"{split}/manual/nights_with_input_changes"] += len(changed)
                record("manual", reference, truth, changed,
                       original.conclusions(original.aggregate(reference)), "documented")

        for condition, entry in local.items():
            per_person.append((pid, split, condition, entry["cases"],
                               entry["sums"] / entry["cases"], entry["ties"]))
    return per_person, dict(sorted(ledger.items()))


def summarize(per_person):
    result = {}
    for split, condition in sorted({(r[1], r[2]) for r in per_person}):
        entries = [r for r in per_person if r[1:3] == (split, condition)]
        values = np.array([r[4] for r in entries])
        labels = ("wrong_conclusions_C1_C3", *LABELS)
        means = dict(zip(POLICIES, [dict(zip(labels, v.tolist())) for v in values.mean(axis=0)]))
        paired = values[:, [POLICIES.index("contiguous"), POLICIES.index("feedback")], 0]
        differences = paired - values[:, POLICIES.index("qc"), 0, None]
        contrasts = {}
        samples = []
        if len(entries) > 1:
            rng = np.random.default_rng(20261123)
            for _ in range(100):
                indices = rng.integers(0, len(entries), size=(100, len(entries)))
                samples.append(differences[indices].mean(axis=1))
            lo, hi = np.quantile(np.concatenate(samples), [.025, .975], axis=0)
        for j, policy in enumerate(("contiguous", "feedback")):
            interval = [float(lo[j]), float(hi[j])] if samples else None
            contrasts[policy + "_minus_qc"] = {
                "mean": float(differences[:, j].mean()), "ci95_participant_bootstrap": interval,
                "upper_below_zero": interval[1] < 0 if interval else None}
        ties = sum((r[5] for r in entries), Counter())
        result[f"{split}/{condition}"] = {"participants": len(entries), "scenarios": sum(r[3] for r in entries),
                                          "scenarios_with_ties": dict(ties),
                                          "means": means, "paired_differences": contrasts}
    return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-csv", type=Path, required=True)
    ap.add_argument("--corrected-daily-csv", type=Path, help="Optional aligned human-corrected export")
    ap.add_argument("--out", type=Path, required=True, help="Aggregate JSON output")
    ap.add_argument("--cohort", choices=("historical", "different", "synthetic_smoke"), default="historical")
    ap.add_argument("--private-pairs", type=Path, help="Optional participant means outside the repository")
    ap.add_argument("--private-cases", type=Path, help="Optional paired scenario outcomes outside the repository")
    ap.add_argument("--legacy-seeds", type=int, default=20)
    args = ap.parse_args()
    if args.legacy_seeds < 1:
        ap.error("--legacy-seeds must be positive")
    private = [p.resolve() for p in (args.private_pairs, args.private_cases) if p]
    if any(p.is_relative_to(ROOT) for p in private):
        ap.error("Store optional participant/scenario outputs outside the repository")
    inputs = {args.daily_csv.resolve()}
    if args.corrected_daily_csv:
        inputs.add(args.corrected_daily_csv.resolve())
    outputs = [args.out.resolve(), *private]
    if len(set(outputs)) != len(outputs) or inputs.intersection(outputs):
        ap.error("Inputs and outputs must have distinct paths")
    groups, drops = read_panel(args.daily_csv)
    legacy = baseline(groups, drops, args.legacy_seeds)
    result = {"cohort": args.cohort, "historical_baseline_check": legacy, "budget_nights": 2,
              "bootstrap_draws": 10000, "bootstrap_seed": 20261123,
              "split": "sha256(role2-sleep-v1-split/{pid}) first uint64 mod 5",
              "input_sha256": digest(args.daily_csv), "code_sha256": digest(Path(__file__)),
              "legacy_code_sha256": digest(Path(original.__file__)),
              "protocol_sha256": digest(Path(__file__).parent / "results/sleep-v1/protocol.md")}
    if args.cohort == "historical" and legacy["differences_from_archive"]:
        result["status"] = "baseline_discrepancy"
        write_json(args.out, result)
        raise SystemExit("The historical baseline differs; see the aggregate check in --out.")
    eligible, result["new_exclusions_after_legacy_load"] = eligible_groups(groups)
    if not eligible:
        raise SystemExit("No participants with ten nights including an adjacent-day pair.")
    corrected = None
    if args.corrected_daily_csv:
        corrected_raw, corrected_drops = read_panel(args.corrected_daily_csv)
        corrected, corrected_exclusions = eligible_groups(corrected_raw)
        result["confirmed_corrections_input"] = {
            "sha256": digest(args.corrected_daily_csv), "loader_drops": corrected_drops,
            "exclusions": corrected_exclusions,
            "corrected_only_eligible_participants": len(corrected.keys() - eligible.keys())}
    with ExitStack() as stack:
        case_writer = None
        if args.private_cases:
            args.private_cases.parent.mkdir(parents=True, exist_ok=True)
            stream = stack.enter_context(args.private_cases.open("w", encoding="utf-8", newline=""))
            case_writer = csv.writer(stream)
            case_writer.writerow(("pid", "split", "condition", "variant", "changed_days", "policy",
                                  "opened_days", "errors_C1_C3", *LABELS))
        people, result["scenario_ledger"] = evaluate(eligible, corrected, case_writer)
    result["conditions"] = summarize(people)
    result["status"] = ("synthetic_implementation_check" if args.cohort == "synthetic_smoke" else
                        "completed" if "evaluation/consecutive" in result["conditions"] else
                        "insufficient_evaluation_cases")
    if args.private_cases:
        result["private_cases_sha256"] = digest(args.private_cases)
    if args.private_pairs:
        args.private_pairs.parent.mkdir(parents=True, exist_ok=True)
        with args.private_pairs.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("pid", "split", "condition", "cases", "policy", "errors_C1_C3", *LABELS))
            for pid, split, condition, cases, means, _ in people:
                for policy, row in zip(POLICIES, means):
                    writer.writerow((pid, split, condition, cases, policy, *row))
        result["private_pairs_sha256"] = digest(args.private_pairs)
    write_json(args.out, result)
    print(f"{result['status']}; {len(eligible)} eligible participants")


if __name__ == "__main__":
    main()
