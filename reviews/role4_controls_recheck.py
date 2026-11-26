"""Recheck role 4's structural controls (`role4_controls/`).

Two questions, neither of which `role4_controls/reproduce.py` answers by itself:

A. Anchor. `reproduce.py` prints, for the fresh block 7100-7199, "no frozen benchmark or v1 rows exist
   for it; the row-by-row acceptance check applies to the 90000 block only". So the fresh block's
   `intact` rows were never checked against anything. This script recomputes them from the environment
   alone and diffs errors *and* action sequences.

B. Clean-room agreement. `reviews/role4_independent/` is an implementation of the same written protocol
   by an agent that never saw `run_controls.py`. Compare the two, row by row and cell by cell.

Run from the repository root:

    python reviews/role4_controls_recheck.py                 # anchor + summary comparison (~2 min)
    python reviews/role4_controls_recheck.py --quick         # 10 graphs per family
    python reviews/role4_controls_recheck.py --clean-room    # also rerun the clean room (~4 min) and
                                                             # compare the 4,500 row-level records

Writes `reviews/role4_controls_recheck.md`. Nothing under `role4_controls/` is written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE4 = ROOT / "role4_controls" / "results"
INDEP = ROOT / "reviews" / "role4_independent"
OUT_MD = ROOT / "reviews" / "role4_controls_recheck.md"

FRESH_START = 7100
FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "structural", "marginal")
BUDGET = {"spike": 16, "real": 8}

# role4 column -> clean-room column, for the summary tables
SUMMARY_FIELDS = (
    ("mean_sink_errors", "mean_sink_errors"),
    ("gain_vs_confidence", "mean_gain"),
    ("paired_lo", "gain_lo"),
    ("paired_hi", "gain_hi"),
    ("gain_removed_vs_intact", "gain_removed_vs_intact"),
    ("removed_lo", "removed_lo"),
    ("removed_hi", "removed_hi"),
)


def rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def num(row: dict, key: str) -> float | None:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else None


def anchor(quick: bool) -> dict:
    sys.path.insert(0, str(ROOT / "role3 improvement"))
    from dag_role3 import generate_graph, sample_episode              # noqa: E402
    from dag_role3.policies import run_public_policy                 # noqa: E402

    n_graphs = 10 if quick else 100
    committed = {}
    for row in rows(ROLE4 / "v2_confirm" / "controls_v2.csv"):
        if row["condition"] != "intact":
            continue
        committed[(row["family"], int(row["graph_seed"]), row["policy"])] = (
            int(row["sink_errors"]), " ".join(row["actions"].split()))

    error_mismatch, action_mismatch, missing = [], [], 0
    for family in FAMILIES:
        for i in range(n_graphs):
            seed = FRESH_START + i
            graph = generate_graph(family, seed)
            snapshot = sample_episode(graph, 20000 + seed)
            budget = BUDGET.get(family, 50)
            for policy in POLICIES:
                key = (family, seed, policy)
                if key not in committed:
                    missing += 1
                    continue
                errors, actions = run_public_policy(graph, snapshot, policy, budget)
                mine = (errors, " ".join(map(str, actions)))
                if mine[0] != committed[key][0]:
                    error_mismatch.append((key, committed[key][0], mine[0]))
                if mine[1] != committed[key][1]:
                    action_mismatch.append((key, committed[key][1], mine[1]))
    return dict(compare=n_graphs * len(FAMILIES) * len(POLICIES),
                error_mismatch=error_mismatch, action_mismatch=action_mismatch, missing=missing)


def compare_summary() -> dict:
    theirs = {(r["family"], r["condition"], r["policy"]): r
              for r in rows(ROLE4 / "controls_summary.csv")}
    mine = {(r["family"], r["condition"], r["policy"]): r
            for r in rows(INDEP / "out" / "controls_summary.csv")}
    shared = sorted(set(theirs) & set(mine))
    field_bad = {}
    for col_theirs, col_mine in SUMMARY_FIELDS:
        bad = []
        for key in shared:
            a, b = num(theirs[key], col_theirs), num(mine[key], col_mine)
            if a is None or b is None:
                continue
            if abs(a - b) > 1e-9:
                bad.append((key, a, b))
        field_bad[col_theirs] = bad
    labelled = [k for k in shared if theirs[k].get("verdict")]
    label_bad = [(k, theirs[k]["verdict"], mine[k]["verdict"]) for k in labelled
                 if theirs[k]["verdict"] != mine[k]["verdict"]]
    return dict(keys=len(shared), missing=len(set(theirs) ^ set(mine)),
                field_bad=field_bad, labelled=len(labelled), label_bad=label_bad)


def compare_worst() -> dict:
    theirs = {(r["family"], r["policy"]): r for r in rows(ROLE4 / "benchmark_worst_of_n.csv")}
    mine = {(r["family"], r["policy"]): r for r in rows(INDEP / "out" / "benchmark_worst_of_n.csv")}
    shared = sorted(set(theirs) & set(mine))
    bad = []
    for key in shared:
        a, b = theirs[key], mine[key]
        for x, y in (("worst_of_n", "worst_of_n"), ("max_sink_errors", "max_sink_errors"),
                     ("p95_sink_errors", "p95_sink_errors")):
            if abs(float(a[x]) - float(b[y])) > 1e-9:
                bad.append((key, x, a[x], b[y]))
    return dict(keys=len(shared), missing=len(set(theirs) ^ set(mine)), bad=bad)


def compare_diagnostics() -> dict:
    theirs = {}
    for r in rows(ROLE4 / "diagnostics.csv"):
        condition = "rewire" if r["condition"] == "rewire_v1" else r["condition"]
        theirs[(r["diagnostic"], r["family"], condition, r["policy"])] = float(r["value"])
    mine = {}
    for r in rows(INDEP / "out" / "diagnostics.csv"):
        if r["graph_seed"] not in ("median", "pooled"):
            continue
        mine[(r["diagnostic"], r["family"], r["condition"], r["policy"])] = float(r["value"])
    shared = sorted(set(theirs) & set(mine))
    bad = [(k, theirs[k], mine[k]) for k in shared if abs(theirs[k] - mine[k]) > 1e-3]
    return dict(keys=len(shared), missing=len(set(theirs) ^ set(mine)), bad=bad)


def compare_rows() -> dict:
    theirs = {(r["family"], r["graph_seed"], r["condition"], r["policy"]): r
              for r in rows(ROLE4 / "controls.csv")}
    mine = {(r["family"], r["graph_seed"], r["condition"], r["policy"]): r
            for r in rows(INDEP / "out" / "controls.csv")}
    shared = sorted(set(theirs) & set(mine))
    error_bad = [k for k in shared
                 if int(theirs[k]["sink_errors"]) != int(mine[k]["sink_errors"])]
    action_bad = [k for k in shared
                  if theirs[k]["actions"].split() != mine[k]["actions"].split()]
    return dict(keys=len(shared), missing=len(set(theirs) ^ set(mine)),
                error_bad=error_bad, action_bad=action_bad)


def mark(ok: bool) -> str:
    return "PASS" if ok else "**FAIL**"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="10 graphs per family instead of 100")
    ap.add_argument("--clean-room", action="store_true",
                    help="rerun reviews/role4_independent/reimplement.py first (writes its out/)")
    ap.add_argument("--skip-anchor", action="store_true")
    args = ap.parse_args()

    if args.clean_room:
        print("running the clean-room implementation ...", flush=True)
        subprocess.run([sys.executable, str(INDEP / "reimplement.py")], cwd=INDEP, check=True)

    a = None if args.skip_anchor else anchor(args.quick)
    s = compare_summary()
    w = compare_worst()
    d = compare_diagnostics()
    r = compare_rows() if (INDEP / "out" / "controls.csv").exists() else None

    lines = [
        "# role 4 structural controls — independent recheck",
        "",
        f"- run: {dt.datetime.now():%Y-%m-%d %H:%M}, commit `{subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()}`",
        f"- machine: {platform.system()} {platform.release()}, Python {platform.python_version()}",
        "- clean room: `reviews/role4_independent/` — protocol in `PROTOCOL.md`, ambiguities in `NOTES.md`",
        "",
        "## A. Anchor for the fresh block 7100–7199",
        "",
        "`role4_controls/reproduce.py` states that this block has no frozen rows to check against, so its",
        "`intact` rows were unanchored. Recomputed here from the environment only.",
        "",
    ]
    if a is None:
        lines += ["_skipped_", ""]
    else:
        ok = not a["error_mismatch"] and not a["action_mismatch"] and not a["missing"]
        lines += [
            f"- compared rows: **{a['compare']}** ({'10' if args.quick else '100'} graphs × "
            f"{len(FAMILIES)} families × {len(POLICIES)} policies)",
            f"- sink-error mismatches: **{len(a['error_mismatch'])}**",
            f"- action-sequence mismatches: **{len(a['action_mismatch'])}**",
            f"- rows missing on either side: **{a['missing']}**",
            "",
            f"**{mark(ok)}**",
            "",
        ]

    lines += [
        "## B. Clean-room agreement (block 90000–90099)",
        "",
        "| comparison | compared | mismatches |",
        "|---|---:|---:|",
        f"| summary cells (6 float fields) | {s['keys']} | "
        f"{sum(len(v) for v in s['field_bad'].values())} |",
        f"| verdict labels the author assigned | {s['labelled']} | {len(s['label_bad'])} |",
        f"| worst-of-n rows (3 fields) | {w['keys']} | {len(w['bad'])} |",
        f"| diagnostics (aggregate) | {d['keys']} | {len(d['bad'])} |",
    ]
    if r is not None:
        lines.append(f"| row-level records (errors + actions) | {r['keys']} | "
                     f"{len(r['error_bad']) + len(r['action_bad'])} |")
    else:
        lines.append("| row-level records | — | not compared (rerun with `--clean-room`) |")
    lines += ["", f"key sets differ by {s['missing']} summary / {w['missing']} worst-of-n / "
                  f"{d['missing']} diagnostics keys.", ""]
    for col, bad in s["field_bad"].items():
        if bad:
            lines.append(f"- `{col}`: {bad[:5]}")
    if s["label_bad"]:
        lines += ["", "label differences (author, clean room):", ""] + [f"- {b}" for b in s["label_bad"]]
    if w["bad"]:
        lines += ["", f"worst-of-n differences: {w['bad'][:5]}"]
    if d["bad"]:
        lines += ["", f"diagnostics differences: {d['bad'][:5]}"]
    if r is not None and (r["error_bad"] or r["action_bad"]):
        lines += ["", f"row differences: {(r['error_bad'] + r['action_bad'])[:5]}"]

    clean = (not any(s["field_bad"].values()) and not s["label_bad"] and not w["bad"] and not d["bad"]
             and (r is None or (not r["error_bad"] and not r["action_bad"])))
    lines += [
        "",
        f"**{'PASS' if clean else 'FAIL'}** — the v1 control tables follow from the written protocol.",
        "",
        "## What this does not cover",
        "",
        "1. **Environment.** Both implementations import `dag_role3`; a bug shared by every user of it is",
        "   invisible here.",
        "2. **Intervals are not independent.** The clean room was not allowed to read",
        "   `run_benchmark.interval`; it recovered the procedure from the frozen summary and matched every",
        "   frozen bound to <1e-9 (`NOTES.md`, ambiguity 1). Point estimates are independent, intervals are",
        "   calibrated, and the verdicts read interval signs.",
        "3. **v2 is not reimplemented.** `rewire_order`, the ten draws, the three-level verdict and the",
        "   20 % margin are role 4's code only. The `inconclusive` label rests on it.",
        "4. **`flatten` and `rewire` have no ground truth.** Only `intact` can be anchored; the controls can",
        "   be shown to be *implemented as specified*, not to be *the right experiment*.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {OUT_MD.relative_to(ROOT)}")
    return 0 if clean and (a is None or (not a["error_mismatch"] and not a["action_mismatch"])) else 1


if __name__ == "__main__":
    sys.exit(main())
