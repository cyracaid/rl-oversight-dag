"""The information ceiling of the real queue.

Three bounds, computed from labels but reported as bounds (not policies):

    coverage  a policy can only see flagged rows, so the 7 (narrow) / 17 (broad)
              corrections that were never flagged are unreachable.
    type      within the queue, a policy that only sees the flag type can do no
              better than ordering the type groups by their positive rate,
              because within a group the items are exchangeable.
    power     with 68 positives over 203 participants, differences below ~10pp
              are not distinguishable -- this bounds what any paper can claim.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bench import config
from bench.load import KEYS, load_queue, load_rows
from bench.metrics import bootstrap_paired_diff, recall_at_k
from bench.policies import _type_group, type_partition_scores


def main() -> None:
    data = config.require_data()
    queue = load_queue(data)
    rows = load_rows(data)

    # coverage: corrections that never entered the queue
    narrow = pd.read_csv(data / config.FILES["labels"])
    for k in KEYS:
        narrow[k] = pd.to_numeric(narrow[k], errors="coerce").fillna(-1).astype(int)
    narrow_keys = set(map(tuple, narrow[KEYS].drop_duplicates().itertuples(index=False, name=None)))
    queue_keys = set(map(tuple, queue[KEYS].itertuples(index=False, name=None)))
    # broad corrections come from the label column, which load_rows drops
    raw = pd.read_csv(data / config.FILES["rows"])
    for k in KEYS:
        raw[k] = pd.to_numeric(raw[k], errors="coerce").fillna(-1).astype(int)
    broad_keys = set(map(tuple, raw.loc[raw["human_review"] == "corrected", KEYS]
                         .drop_duplicates().itertuples(index=False, name=None)))

    coverage = {
        "narrow_total": len(narrow_keys),
        "narrow_in_queue": len(narrow_keys & queue_keys),
        "narrow_unflagged": len(narrow_keys - queue_keys),
        "broad_total": len(broad_keys),
        "broad_in_queue": len(broad_keys & queue_keys),
        "broad_unflagged": len(broad_keys - queue_keys),
    }
    coverage["narrow_ceiling"] = coverage["narrow_in_queue"] / coverage["narrow_total"]
    coverage["broad_ceiling"] = coverage["broad_in_queue"] / coverage["broad_total"]

    # type table + ceiling curve
    group = _type_group(queue)
    y = queue["y_broad"].to_numpy(int)
    tab = (pd.DataFrame({"g": group, "y": y}).groupby("g")["y"]
           .agg(["size", "sum", "mean"]).sort_values("mean", ascending=False))
    scores = type_partition_scores(queue)
    ks = [50, 100, 140, 200, 400]
    ceiling = {k: round(recall_at_k(scores, y, k), 4) for k in ks}

    # deployable comparison, and its power
    from bench.policies import score_all
    m1 = score_all(queue)["m1_first"]
    diffs = {}
    for k in (50, 100, 140):
        d, lo, hi = bootstrap_paired_diff(queue, scores, m1, k)
        diffs[f"k{k}"] = {"diff": round(d, 4), "lo95": round(lo, 4), "hi95": round(hi, 4)}

    out = {"coverage": coverage, "type_table": tab.reset_index().to_dict("records"),
           "ceiling_recall": ceiling, "partition_minus_m1_first": diffs}
    (config.OUT_DIR / "ceiling.json").write_text(json.dumps(out, indent=2) + "\n")

    lines = [
        "# The information ceiling of the real queue",
        "",
        "## 1. Coverage (what no policy can reach)",
        "",
        "| label set | corrections | in queue | never flagged | ceiling |",
        "|---|---:|---:|---:|---:|",
        f"| narrow (manual file) | {coverage['narrow_total']} | {coverage['narrow_in_queue']} "
        f"| {coverage['narrow_unflagged']} | **{coverage['narrow_ceiling']:.1%}** |",
        f"| broad (human_review) | {coverage['broad_total']} | {coverage['broad_in_queue']} "
        f"| {coverage['broad_unflagged']} | **{coverage['broad_ceiling']:.1%}** |",
        "",
        "An infinite review budget still cannot exceed these numbers, because the",
        "unflagged rows never enter the queue.",
        "",
        "## 2. Type ceiling (what a type-only policy can reach)",
        "",
        "| flag type | items | positives | rate |",
        "|---|---:|---:|---:|",
    ]
    for _, r in tab.iterrows():
        lines.append(f"| {r.name} | {int(r['size'])} | {int(r['sum'])} | {r['mean']:.1%} |")
    lines += [
        "",
        "Within a type group the items are exchangeable, so the best a type-only",
        "policy can do is take the groups in rate order. That ceiling is:",
        "",
        "| k | 50 | 100 | 140 | 200 | 400 |",
        "|---|---:|---:|---:|---:|---:|",
        "| ceiling recall | " + " | ".join(f"{ceiling[k]:.1%}" for k in ks) + " |",
        "",
        "It saturates at the k that exhausts the M1-bearing block (103 + 37 = 140).",
        "",
        "## 3. Power (what this sample can even detect)",
        "",
        "`type_partition` (M1-only > M1+M4 > M4 > other) minus `m1_first`:",
        "",
        "| k | difference | 95% CI |",
        "|---|---:|---|",
    ]
    for k, d in diffs.items():
        lines.append(f"| {k[1:]} | {d['diff']:+.1%} | [{d['lo95']:+.1%}, {d['hi95']:+.1%}] |")
    lines += [
        "",
        "Every CI crosses zero. With 68 positives across 203 participants, a ~7pp",
        "difference is inside the noise: **this sample cannot support claims below",
        "roughly 10pp.** Say that in the paper instead of picking the winning row.",
    ]
    (config.OUT_DIR / "ceiling.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(out["coverage"], indent=2))
    print("ceiling:", ceiling)


if __name__ == "__main__":
    main()
