#!/usr/bin/env python3
"""Check that the figures show the artifacts they claim, and that the paper uses them.

`figures/figure_data.json` records every plotted value; this test recomputes those
values from the artifacts independently of `make_figures.py`. A figure that drifts
from its JSON/CSV is then a test failure rather than a silent inconsistency between
a picture and the table beside it.

Run: python3 experiments/test_figures.py
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "figures", "figure_data.json")
SPEC = os.path.join(ROOT, "BENCHMARK_SPEC.md")
BASELINE_CSV = os.path.join(ROOT, "role3 improvement", "outputs", "v3-baselines", "benchmark_summary.csv")
LEARNED = os.path.join(ROOT, "role3 improvement", "outputs", "v3-learned", "learned_vs_marginal.json")
CEILING = os.path.join(ROOT, "triage_bench", "outputs", "ceiling.json")
RANKING = os.path.join(ROOT, "runs", "real-confidence-ranking", "results.json")
PAPERS = ("PAPER_DRAFT.md", "PAPER_DRAFT_KO.md", "PAPER_DRAFT_CN.md")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def load(path):
    return json.loads(read(path))


def plotted():
    return load(DATA)


def spec_sizes():
    body = read(SPEC).split("| family | n | budget", 1)[1]
    sizes = {}
    for line in body.splitlines():
        if not line.startswith("|"):
            if sizes:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[1].isdigit():
            sizes[cells[0].strip("`")] = int(cells[1])
    return sizes


def test_figure_one_matches_the_learned_table():
    sizes, levels, rows = spec_sizes(), {}, load(LEARNED)
    with open(BASELINE_CSV, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["policy"] == "marginal":
                levels[row["family"]] = float(row["mean_sink_errors"])
    expected = {(r["family"], r["learner"]): r for r in rows if r["learner"] in ("gnn", "dqn")}
    data = plotted()["fig1"]

    assert data["groups"] == sorted({v for v in sizes.values()}), data["groups"]
    got = {(p["family"], p["learner"]): p for p in data["points"]}
    assert set(got) == set(expected), (set(got) ^ set(expected))
    for key, row in expected.items():
        point = got[key]
        assert point["n"] == sizes[key[0]], (key, point["n"], sizes[key[0]])
        for field in ("delta", "lo", "hi"):
            assert abs(point[field] - row[field]) < 1e-9, (key, field, point[field], row[field])
        assert abs(point["marginal"] - levels[key[0]]) < 1e-9, key
        assert abs(point["relative_pct"] - 100.0 * row["delta"] / levels[key[0]]) < 1e-9, key


def test_figure_two_matches_the_queue_ceiling():
    ceiling, data = load(CEILING), plotted()["fig2"]
    expected_k = sorted(int(k) for k in ceiling["ceiling_recall"])
    assert data["k"] == expected_k, (data["k"], expected_k)
    assert data["recall"] == [ceiling["ceiling_recall"][str(k)] for k in expected_k]
    assert data["coverage_ceiling"] == ceiling["coverage"]["narrow_ceiling"]
    assert data["saturation"] == max(data["recall"])
    assert data["plateau_k"] == expected_k[data["recall"].index(data["saturation"])]
    assert abs(data["uncovered"] - (1.0 - data["saturation"])) < 1e-12
    tail = next(g for g in ceiling["type_table"] if g["g"] == data["tail_group"])
    assert (data["tail_size"], data["tail_base_rate"]) == (tail["size"], tail["mean"])
    assert data["narrow_in_queue"] == ceiling["coverage"]["narrow_in_queue"]
    assert data["narrow_total"] == ceiling["coverage"]["narrow_total"]


def test_figure_three_matches_the_localisation_ranking():
    agg = load(RANKING)["observables"]["suspicion_binary"]
    data = plotted()["fig3"]
    expect = [("all 14 nodes", agg["aggregate"]["auc_mean"], agg["aggregate"]["auc_ci95"]),
              ("4 validity sinks", agg["by_node_group"]["validity_sink"]["auc_pooled"], None),
              ("6 derived nodes", agg["by_node_group"]["derived"]["auc_pooled"], None),
              ("4 raw timestamps", agg["by_node_group"]["raw_leaf"]["auc_pooled"], None)]
    assert data["chance"] == 0.5
    assert len(data["bars"]) == len(expect)
    for got, (label, auc, ci) in zip(data["bars"], expect):
        assert got["label"] == label, (got["label"], label)
        assert abs(got["auc"] - auc) < 1e-9, (label, got["auc"], auc)
        assert (got["ci"] or None) == (list(ci) if ci else None), label
    assert data["hit1"] == agg["aggregate"]["by_target"]["source_leaf"]["hit1_expected"]
    assert data["ties_records"] == agg["aggregate"]["ties"]["records_with_tied_max"]


def test_every_figure_file_exists_and_is_not_empty():
    for key, entry in plotted().items():
        path = os.path.join(ROOT, "figures", entry["file"])
        assert os.path.exists(path), f"{key} missing: {path}"
        size = os.path.getsize(path)
        assert size > 20_000, f"{key} looks truncated ({size} bytes)"


def test_the_paper_shows_all_three_figures():
    """A figure nobody embeds is dead weight; keep the drafts and the files in step."""
    files = [entry["file"] for entry in plotted().values()]
    for name in PAPERS:
        body = read(os.path.join(ROOT, name))
        for f in files:
            assert f"figures/{f}" in body, f"{name} does not embed figures/{f}"


def main():
    failures = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        try:
            fn()
            print(f"ok   {name}")
        except AssertionError as error:
            failures += 1
            print(f"FAIL {name}\n{error}\n")
    print(f"{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
