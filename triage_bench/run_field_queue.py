#!/usr/bin/env python3
"""Field-level review: the third escape, and why it moves cost rather than recall.

A row-level rule fires on a whole row, but the rule's *witness* names the two
fields that conflict (`M1_viol_pairs`: bed_sleep / sleep_awake / awake_getup).
If a curator checks only those two fields instead of all four timestamps, the
reading cost halves. This script measures what that costs in coverage.

Caveat, stated up front: the correction log records the field(s) a human fixed,
not every field they read, so "covered" means "at least one corrected field is
inside the witness pair". Multi-field corrections can extend outside it.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bench import config
from bench.load import KEYS, load_queue

PAIR_FIELDS = {"bed_sleep": {"bed", "sleep"}, "sleep_awake": {"sleep", "awake"},
               "awake_getup": {"awake", "getup"}}


def _fields(cell) -> set[str]:
    if not isinstance(cell, str):
        return set()
    out = set()
    for part in cell.split(","):
        name = part.replace("_corrected", "").replace("time_", "").strip()
        if name and name != "nan":
            out.add(name)
    return out


def _witness(cell) -> set[str]:
    if not isinstance(cell, str) or not cell.strip():
        return set()
    out: set[str] = set()
    for part in cell.split("+"):
        out |= PAIR_FIELDS.get(part.strip(), set())
    return out


def main() -> None:
    data = config.require_data()
    queue = load_queue(data)
    labels = pd.read_csv(data / config.FILES["labels"])
    for k in KEYS:
        labels[k] = pd.to_numeric(labels[k], errors="coerce").fillna(-1).astype(int)
    label_map = {tuple(r[KEYS].values): r["column_to_correct"]
                 for _, r in labels.drop_duplicates(KEYS).iterrows()}

    m1 = queue.loc[queue["m1"]].sort_values("queue_pos").copy()
    m1["witness"] = m1["M1_viol_pairs"].fillna("").map(_witness)
    m1["corrected"] = [label_map.get(tuple(r), None) for r in m1[KEYS].values]
    m1["cf"] = m1["corrected"].map(_fields)
    known = m1.loc[m1["cf"].map(len) > 0].copy()
    known["covered"] = [bool(cf & w) for cf, w in zip(known["cf"], known["witness"])]
    known["strict"] = [cf.issubset(w) for cf, w in zip(known["cf"], known["witness"])]

    by_pair = (known.assign(pair=known["M1_viol_pairs"].fillna(""))
               .groupby("pair")
               .agg(n=("covered", "size"), covered=("covered", "sum"), strict=("strict", "sum")))
    by_pair["coverage"] = by_pair["covered"] / by_pair["n"]

    # cost: row review reads 4 timestamps, pair-scoped reads |witness|
    size = known["witness"].map(len).replace(0, 4).to_numpy()
    y = known["covered"].to_numpy(int)
    row_cost = 4 * np.arange(1, len(known) + 1)
    pair_cost = np.cumsum(size)
    cum = np.cumsum(y)
    total = int(y.sum())

    curve = {}
    for frac in (0.5, 0.75, 0.9, 1.0):
        need = int(np.ceil(frac * total))
        i = int(np.argmax(cum >= need))
        curve[f"{int(frac*100)}pct"] = {"row_reads": int(row_cost[i]),
                                       "pair_reads": int(pair_cost[i]),
                                       "rows_reviewed": i + 1}

    out = {
        "m1_rows": int(len(m1)),
        "m1_rows_with_known_field": int(len(known)),
        "covered": int(known["covered"].sum()),
        "coverage": round(float(known["covered"].mean()), 4),
        "strict_multi_field": int(known["strict"].sum()),
        "by_pair": by_pair.reset_index().to_dict("records"),
        "reads_to_reach": curve,
        "row_reads_all": int(row_cost[-1]),
        "pair_reads_all": int(pair_cost[-1]),
    }
    (config.OUT_DIR / "field_queue.json").write_text(json.dumps(out, indent=2) + "\n")

    lines = [
        "# Field-level review: half the reading, most of the recall",
        "",
        f"M1-bearing rows: **{len(m1)}**, of which **{len(known)}** have a recorded",
        "corrected field. The rule's witness names the conflicting pair.",
        "",
        f"- at least one corrected field inside the witness pair: **{out['covered']}/{len(known)} "
        f"= {out['coverage']:.1%}**",
        f"- *all* corrected fields inside the pair (strict): {out['strict_multi_field']}/{len(known)}",
        "",
        "| witness pair | rows | covered | strict | coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in by_pair.reset_index().iterrows():
        lines.append(f"| {r['pair']} | {int(r['n'])} | {int(r['covered'])} | "
                     f"{int(r['strict'])} | {r['coverage']:.1%} |")
    lines += [
        "",
        "## Cost model",
        "",
        "Row review reads 4 timestamps. Pair-scoped review reads the witness pair",
        "(2 fields in 139 of 140 rows). Reads needed to reach a fraction of the",
        "covered positives, in queue order:",
        "",
        "| recall of covered positives | rows reviewed | row reads | pair reads |",
        "|---|---:|---:|---:|",
    ]
    for frac, d in curve.items():
        lines.append(f"| {frac} | {d['rows_reviewed']} | {d['row_reads']} | {d['pair_reads']} |")
    lines += [
        "",
        f"To cover every positive it can reach, row review spends "
        f"**{out['row_reads_all']}** field-reads and pair-scoped spends "
        f"**{out['pair_reads_all']}** — a {1 - out['pair_reads_all']/out['row_reads_all']:.0%} reduction.",
        "",
        "This moves **cost**, not recall: the type ceiling is unchanged, and the",
        "strict column shows multi-field corrections that spill outside the pair.",
        "It is still the only escape that survives: under a time budget, halving",
        "the reads per review doubles what the queue can buy.",
    ]
    (config.OUT_DIR / "field_queue.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: out[k] for k in ("coverage", "covered", "m1_rows_with_known_field",
                                        "row_reads_all", "pair_reads_all")}, indent=2))
    print(by_pair.reset_index().to_string(index=False))


if __name__ == "__main__":
    main()
