#!/usr/bin/env python3
"""Guard: the numbers published in the markdown must match the run artifacts.

This repo has already paid for stale numbers once (a superseded caveat in the
README contradicting the PPO row, fixed in af53a60) and twice in the block review
(a QC-scoring bug that invalidated a whole grid). The pattern is always the same:
the JSON is regenerated, the prose keeps the old table, and a reader cannot tell
which one is current.

So this test does not re-derive any science. It reads `runs/*/results.json` and
asserts that the rounded numbers a reader actually sees are the ones the artifact
contains. If you regenerate a run and the doc does not move, this fails.

Run: python3 experiments/test_published_numbers.py
No data file is needed; everything here is already committed.
"""
from __future__ import annotations

import collections
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCORER_JSON = os.path.join(ROOT, "runs", "learned-window-scorer", "results.json")
CAPTURE_JSON = os.path.join(ROOT, "runs", "capture-checks", "results.json")
SCORER_DOC = os.path.join(HERE, "LEARNED_WINDOW_SCORER_INTERPRETATION.md")
CAPTURE_DOC = os.path.join(HERE, "CAPTURE_CHECKS_INTERPRETATION.md")
RESULTS_DOC = os.path.join(HERE, "results.md")

STALE = 0.0005


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def policy_means():
    """mode -> budget -> policy -> mean sink errors, aggregated over eval seeds."""
    data = load(SCORER_JSON)
    acc = collections.defaultdict(list)
    for key, row in data["policies"].items():
        mode, budget, policy, _seed = key.split("|")
        acc[(mode, int(budget[1:]), policy)].append(row["mean"])
    out = collections.defaultdict(dict)
    for (mode, budget, policy), vals in acc.items():
        out[mode].setdefault(budget, {})[policy] = statistics.fmean(vals)
    return data, out


def test_scorer_header_matches_doc():
    data = load(SCORER_JSON)
    header = data["header"]
    assert header["participants"] == 196, header
    assert (header["train"], header["test"]) == (118, 78), header
    assert header["budgets"] == [2, 4], header
    doc = text(SCORER_DOC)
    assert "196 participants, 118 train / 78 held-out" in doc
    assert "budgets 2 and 4" in doc
    assert "8/8 tests" in doc, "the doc must state the suite size it was written against"


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def section(doc, start, end):
    i, j = doc.index(start), doc.index(end)
    return doc[i:j]


def test_scorer_table_matches_artifact():
    """Every published policy row must be reproducible from the JSON.

    Bold marks the best published policy in a row, so it is checked as well:
    0.071 (hand-crafted) on the shift at budget 2 is bold because it is the best
    number there, not because a learned policy was expected to win.
    """
    _data, means = policy_means()
    labels = {"visible ±12 h": "block_order", "silent WASO→0": "block_waso",
              "silent 90 min shift": "block_shift"}
    cols = ("night_qc", "block3_shift", "learned", "pooled")

    block = section(text(RESULTS_DOC), "### 12f.", "## 13.")
    seen, checked = None, 0
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) != 6:
            continue
        if row[0] in labels:
            seen = labels[row[0]]
        if seen is None or row[1] not in ("2", "4"):
            continue
        raw = row[2:6]
        got = [round(float(c.replace("*", "")), 3) for c in raw]
        budget = int(row[1])
        want = [round(means[seen][budget][c], 3) for c in cols]
        assert got == want, f"{seen} b{budget}: doc {got} != artifact {want}"
        bold = [float(c.replace("*", "")) for c in raw if c.startswith("**")]
        if bold:
            assert bold[0] == min(got), f"{seen} b{budget}: bold {bold[0]} is not the row min {min(got)}"
        checked += 1
    assert checked == 6, f"expected 6 published rows, matched {checked}"

    block = section(text(SCORER_DOC), "| corruption | budget |", "## Reading")
    seen, checked = None, 0
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) != 7:
            continue
        if row[0] in labels:
            seen = labels[row[0]]
        if seen is None or row[1] not in ("2", "4"):
            continue
        budget = int(row[1])
        got = [round(float(c.replace("*", "")), 3) for c in row[2:7]]
        want = [round(means[seen][budget][c], 3) for c in cols + ("oracle",)]
        assert got == want, f"{seen} b{budget} (interp): doc {got} != artifact {want}"
        checked += 1
    assert checked == 6, f"expected 6 rows in the interpretation doc, matched {checked}"


def test_scorer_aucs_match_artifact():
    data = load(SCORER_JSON)
    models = data["models"]
    per_family = {m: models[m]["test_auc_all"] for m in
                  ("block_order", "block_waso", "block_shift")}
    assert per_family == {"block_order": 0.991, "block_waso": 0.816,
                          "block_shift": 0.84}, per_family
    pooled = {m: v["test_auc_all"] for m, v in models["pooled"]["by_mode"].items()}
    assert pooled == {"block_order": 0.981, "block_waso": 0.749,
                      "block_shift": 0.72}, pooled

    interp = text(SCORER_DOC)
    assert "0.991" in interp and "0.816" in interp and "0.840" in interp
    assert "0.981 / 0.749 / 0.720" in interp
    assert "0.981 / 0.749 / 0.720" in text(RESULTS_DOC)


def test_learned_beats_night_qc_only_where_the_doc_says_so():
    """The doc calls visible 'the useful null' and the two silent families wins.

    Encode that as an assertion on the artifact, so a silent regression to
    'learning helps everywhere' (or nowhere) fails instead of reading well.
    """
    _data, means = policy_means()
    for budget in (2, 4):
        order = means["block_order"][budget]
        assert order["learned"] >= order["night_qc"] - STALE, (budget, order)
    for mode in ("block_waso", "block_shift"):
        for budget in (2, 4):
            row = means[mode][budget]
            assert row["learned"] <= row["night_qc"] + STALE, (mode, budget, row)


def test_capture_prevalence_matches_artifact():
    prev = load(CAPTURE_JSON)["prevalence"]
    doc = text(CAPTURE_DOC)
    results = text(RESULTS_DOC)

    all_zero = prev["waso_all_zero"]
    assert (all_zero["records"], all_zero["pct"], all_zero["nights"]) == (7, 3.6, 82)
    assert "| every night reports WASO = 0 | 7 | 3.6 % | 82 |" in doc
    assert "7 records, 3.6 % (82 nights)" in results

    zeros = prev["nights_reporting_waso_zero"]
    assert (zeros["nights"], zeros["pct_of_nights"]) == (933, 39.3)
    assert "| nights reporting WASO = 0 | — | 39.3 % of all nights | 933 |" in doc
    assert "933 nights, 39.3 %" in results

    half = prev["records_ge50pct_waso_zero"]
    assert (half["records"], half["pct"]) == (81, 41.3)
    assert "81 records, 41.3 %" in results

    run = prev["waso_run_ge3"]
    assert (run["records"], run["pct"], run["expected_records_under_null"]) == (88, 44.9, 69.3)
    assert "88 records, 44.9 % vs **69.3 expected under a permutation null**" in results

    ampm = prev["ampm_recoverable"]
    assert (ampm["records"], ampm["pct"], ampm["nights"]) == (20, 10.2, 21)
    assert "20 records, 10.2 % (21 nights)" in results

    cov = prev["coverage"]
    assert (cov["median"], cov["pct_below_0_8"], cov["records_below_0_5"]) == (0.917, 21.4, 0)
    assert "median 91.7 %, 21.4 % of records below 0.8" in results


def test_run_rate_is_never_cited_without_its_null():
    """44.9 % looks like a finding only if the 35.4 % base rate is dropped."""
    for path in (CAPTURE_DOC, RESULTS_DOC, os.path.join(ROOT, "PROJECT_POSITIONING.md")):
        doc = text(path)
        if "44.9" not in doc and "3-night" not in doc:
            continue
        assert "null" in doc.lower(), f"{path} cites the run rate without a null"


def test_docs_do_not_resurrect_the_retired_claim():
    """'RL saves review budget' may only appear inside the retired row."""
    retired = "RL reduces human review"
    positioning = text(os.path.join(ROOT, "PROJECT_POSITIONING.md"))
    for line in positioning.splitlines():
        if retired in line:
            assert "nowhere" in line, f"retired claim outside the 'nowhere' row: {line}"


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"{len(fns)}/{len(fns)} passed")


if __name__ == "__main__":
    main()
