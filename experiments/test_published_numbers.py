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
import csv
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


RETIRED_PHRASES = ("reduces human review", "saves review", "review budget by",
                    "cuts review", "reduction in human review")


def test_docs_do_not_resurrect_the_retired_claim():
    """'RL saves review budget' may only appear inside a disclaimer."""
    positioning = text(os.path.join(ROOT, "PROJECT_POSITIONING.md"))
    for line in positioning.splitlines():
        if "reduces human review" in line:
            assert "nowhere" in line, f"retired claim outside the 'nowhere' row: {line}"

    # The paper is allowed to *disclaim* the claim, never to assert it.
    flat = " ".join(paper_text().split())
    for phrase in RETIRED_PHRASES:
        start = flat.find(phrase)
        while start != -1:
            window = flat[max(0, start - 160):start + 160].lower()
            assert any(k in window for k in ("does not claim", "retired", "nowhere")), (
                f"paper asserts a retired claim near {phrase!r}: {window[-120:]}")
            start = flat.find(phrase, start + 1)


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"{len(fns)}/{len(fns)} passed")


# --------------------------------------------------------------------------- #
# The paper draft: same guard, one more document
# --------------------------------------------------------------------------- #
PAPER = os.path.join(ROOT, "PAPER_DRAFT.md")
BASELINE_CSV = os.path.join(ROOT, "role3 improvement", "outputs", "v3-baselines", "benchmark_summary.csv")
LEARNED_JSON = os.path.join(ROOT, "role3 improvement", "outputs", "v3-learned", "learned_vs_marginal.json")
CEILING_JSON = os.path.join(ROOT, "triage_bench", "outputs", "ceiling.json")
RANK_JSON = os.path.join(ROOT, "runs", "real-confidence-ranking", "results.json")
DP_REPORT = os.path.join(ROOT, "role3 improvement", "outputs", "dp-ceiling", "report.md")
DP_AMEND = os.path.join(ROOT, "role3 improvement", "outputs", "dp-ceiling", "AMENDMENT.md")


def paper_text():
    return text(PAPER).replace("\u2212", "-")


def clean(cell):
    return cell.replace("**", "").replace("`", "").strip()


def paper_table(start, end):
    block = paper_text()
    i, j = block.index(start), block.index(end)
    return [cells(line) for line in block[i:j].splitlines() if line.startswith("|")]


def test_paper_standing_table_matches_benchmark_csv():
    """The paper's headline table must be the CSV, not a hand-copy of it."""
    rows = {}
    with open(BASELINE_CSV, encoding="utf-8-sig") as fh:
        for rec in csv.DictReader(fh):
            rows.setdefault(rec["family"], {})[rec["policy"]] = float(rec["mean_sink_errors"])

    families = ("spike", "modular", "ba", "er", "real", "ticket")
    seen = 0
    for row in paper_table("### 3.5 Standing table", "Against `confidence` on `spike`"):
        if len(row) != 6 or clean(row[0]) not in families:
            continue
        fam = clean(row[0])
        got = [round(float(clean(c)), 2) for c in row[1:5]]
        want = [round(rows[fam][p], 2) for p in ("marginal", "confidence", "type_prior", "oracle")]
        assert got == want, f"{fam}: paper {got} != csv {want}"
        headroom = round(rows[fam]["marginal"] - rows[fam]["oracle"], 2)
        assert round(float(clean(row[5])), 2) == headroom, f"{fam}: headroom {row[5]} != {headroom}"
        seen += 1
    assert seen == 6, f"expected 6 published families, matched {seen}"


def test_paper_learned_table_matches_artifact():
    """Every Δ [CI] string in the paper must be built from the learned JSON."""
    data = {(d["family"], d["learner"]): d for d in load(LEARNED_JSON) if d.get("seeds")}
    block = paper_text()
    i, j = block.index("### 4.1 Three architectures"), block.index("All 36 (family, learner, seed) cells")
    seen = 0
    for line in block[i:j].splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) != 4 or clean(row[0]) not in ("spike", "real", "ticket", "modular", "er", "ba"):
            continue
        fam = clean(row[0])
        for col, learner in ((2, "gnn"), (3, "dqn")):
            d = data[(fam, learner)]
            want = f"{d['delta']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]"
            assert clean(row[col]) == want, f"{fam} {learner}: paper {clean(row[col])} != {want}"
            seen += 1
    assert seen == 12, f"expected 12 published cells, matched {seen}"


SUPERVISOR_DOC = os.path.join(
    ROOT, "role3 improvement", "outputs", "supervisor-v1", "receipt_vs_silent.md")


def test_paper_receipt_table_matches_supervisor_artifact():
    """The coverage-receipt table is copied from the run, not retyped."""
    src = {}
    for line in text(SUPERVISOR_DOC).splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) != 8 or row[0] not in ("spike", "modular", "real", "ticket"):
            continue
        src[(row[0], row[1].strip("`"))] = row

    seen = 0
    for line in paper_text().splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) != 7 or clean(row[0]) not in ("spike", "modular", "real", "ticket"):
            continue
        key = (clean(row[0]), clean(row[1]))
        assert key in src, f"receipt row {key} is not in the artifact"
        want = src[key]
        got = [float(clean(c)) for c in row[2:7]]
        exp = [round(float(want[2]), 3), int(want[3]), int(want[4]),
               int(want[5]), round(float(want[6]), 3)]
        assert got[:3] == [exp[0], exp[1], exp[2]], f"{key}: {got[:3]} != {exp[:3]}"
        assert got[3] == exp[3], f"{key}: false-inspected {got[3]} != {exp[3]}"
        assert abs(got[4] - exp[4]) < 5e-4, f"{key}: share {got[4]} != {exp[4]}"
        seen += 1
    assert seen == 8, f"expected 8 receipt cells, matched {seen}"


def test_paper_receipt_shortfall_matches_artifact():
    """The 0.002 miss and the 10.2/14.9 split must be the artifact's numbers."""
    src = {}
    for line in text(SUPERVISOR_DOC).splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) == 8 and row[0] == "modular" and row[1].strip("`") in ("marginal", "oracle"):
            src[row[1].strip("`")] = row

    rule, oracle = src["marginal"], src["oracle"]
    shortfall = 0.90 - float(rule[6])
    assert f"{shortfall:.3f}" in paper_text(), f"shortfall {shortfall:.3f} missing"
    assert f"{int(rule[4])} of {int(rule[3])}" in paper_text(), "1587 of 1767 missing"
    for row in (rule, oracle):
        pct = 100 * int(row[5]) / int(row[3])
        assert f"{pct:.1f}" in paper_text(), f"{pct:.1f} % missing for {row[1]}"


TENX_DOC = os.path.join(ROOT, "role2_규리", "results", "confirm-10x", "comparison.md")


def test_paper_ten_x_matches_its_artifact():
    """The 10x budget row is quoted from the comparison table, not remembered."""
    block, doc = text(TENX_DOC), paper_text()
    line = next(l for l in block.splitlines()
                if l.startswith("| 정상 신뢰도 | gnn |") and "+0.262" in l)
    row = cells(line)
    multiple = row[3].replace("−", "-")
    assert multiple in doc, f"10x delta {multiple} missing from the paper"
    seeds = row[2]
    for value in seeds.split(", "):
        assert value.split()[-1] in doc, f"seed value {value} missing"


def test_paper_tie_counts_match_the_learned_artifact():
    """'the two exceptions are ties' must name the ties the JSON actually has."""
    data = [r for r in load(LEARNED_JSON) if not r.get("seeds")]
    loose = sorted(r["ties"] for r in data if r["lo"] <= 0 <= r["hi"])
    assert len(loose) == 2, loose
    doc = paper_text()
    flat = " ".join(doc.split())
    assert f"{loose[0]}\u2013{loose[1]} of 100" in flat, (loose, "tie range not in the paper")


def test_paper_queue_ceiling_matches_artifact():
    ceil = load(CEILING_JSON)
    doc = paper_text()
    assert f"{ceil['coverage']['narrow_ceiling'] * 100:.1f}" in doc
    assert f"{ceil['coverage']['broad_ceiling'] * 100:.1f}" in doc
    for k in ("50", "100", "140"):
        pct = f"{ceil['ceiling_recall'][k] * 100:.1f}"
        assert pct in doc, f"ceiling at k={k} ({pct} %) missing from the paper"
    assert f"{ceil['partition_minus_m1_first']['k100']['diff'] * 100:+.1f}" in doc


def test_paper_localisation_table_matches_artifact():
    agg = load(RANK_JSON)["observables"]["suspicion_binary"]
    a, groups = agg["aggregate"], agg["by_node_group"]
    src, ties = a["by_target"]["source_leaf"], a["ties"]
    chance = load(RANK_JSON)["chance_reference"]
    doc = paper_text()

    lo, hi = a["auc_ci95"]
    assert f"{a['auc_mean']:.3f} [{lo:.3f}, {hi:.3f}]" in doc, (a["auc_mean"], lo, hi)
    for g in ("validity_sink", "derived", "raw_leaf"):
        assert f"{groups[g]['auc_pooled']:.3f}" in doc, g
    assert f"{src['hit1_expected']:.3f} / {src['hit3_expected']:.3f}" in doc
    assert f"{chance['hit1']:.3f} / {chance['hit3']:.3f}" in doc
    assert f"{src['rank_optimistic_mean']:.1f}\u2013{src['rank_pessimistic_mean']:.1f}" in doc
    assert ties["records_with_tied_max"] == 51, ties


def test_paper_dp_numbers_match_the_ceiling_artifacts():
    """The report rounds to 3 dp; the amendment keeps the measured 4-dp value."""
    report, amend, doc = text(DP_REPORT), text(DP_AMEND), paper_text()
    real, ticket = 0.0219, 0.0059
    assert f"-{real:.3f}" in report and f"-{ticket:.3f}" in report
    assert f"-{real:.4f}" in amend, "the amendment must keep the unrounded real value"
    assert f"-{real:.4f}" in doc and f"-{ticket:.4f}" in doc
    assert "1.73" in report and "1.73" in doc


def test_paper_never_cites_the_run_rate_without_its_null():
    doc = paper_text()
    if "44.9" in doc or "3-night" in doc:
        assert "null" in doc.lower()


if __name__ == "__main__":
    main()
