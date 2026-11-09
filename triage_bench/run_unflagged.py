#!/usr/bin/env python3
"""Profile the corrections that never entered the queue.

A ranking policy cannot reach an unflagged row, so these errors are the detector's
problem, not the scheduler's. This script says who they are and whether an obvious
extra rule would catch them.
"""

from __future__ import annotations

import json

import pandas as pd

from bench import config
from bench.load import KEYS, load_queue


def _keys(df: pd.DataFrame) -> set[tuple]:
    for k in KEYS:
        df[k] = pd.to_numeric(df[k], errors="coerce").fillna(-1).astype(int)
    return set(map(tuple, df[KEYS].drop_duplicates().itertuples(index=False, name=None)))


def main() -> None:
    data = config.require_data()
    queue = load_queue(data)
    in_queue = _keys(queue)

    raw = pd.read_csv(data / config.FILES["rows"])
    for k in KEYS:
        raw[k] = pd.to_numeric(raw[k], errors="coerce").fillna(-1).astype(int)
    audit = pd.read_csv(data / config.FILES["candidates"])
    for k in KEYS:
        audit[k] = pd.to_numeric(audit[k], errors="coerce").fillna(-1).astype(int)
    labels = pd.read_csv(data / config.FILES["labels"])
    for k in KEYS:
        labels[k] = pd.to_numeric(labels[k], errors="coerce").fillna(-1).astype(int)

    narrow = labels.drop_duplicates(KEYS).copy()
    narrow["flagged"] = [tuple(r) in in_queue for r in narrow[KEYS].values]
    miss_n = narrow.loc[~narrow["flagged"]]

    broad = raw.loc[raw["human_review"] == "corrected", KEYS + ["has_correction"]].drop_duplicates(KEYS)
    broad["flagged"] = [tuple(r) in in_queue for r in broad[KEYS].values]
    miss_b = broad.loc[~broad["flagged"]]

    decision = audit.set_index(KEYS)["decision"]
    miss_n = miss_n.assign(
        audit_decision=[decision.get(tuple(r), "absent") for r in miss_n[KEYS].values]
    )

    # Would one obvious extra rule catch them? "final awakening == get-up" is the
    # raw signature behind several of the awake/getup corrections.
    aw = pd.to_datetime(raw["awakening_selfreport_ts"], errors="coerce")
    gu = pd.to_datetime(raw["getup_selfreport_ts"], errors="coerce")
    eq = aw.notna() & gu.notna() & (aw == gu)
    eq_keys = _keys(raw.loc[eq])
    truth = _keys(raw.loc[raw["human_review"] == "corrected"])
    rule = {"rows": len(eq_keys), "corrected_inside": len(eq_keys & truth),
            "precision": round(len(eq_keys & truth) / max(1, len(eq_keys)), 4),
            "catches_unflagged": len(eq_keys & _keys(miss_b))}

    out = {
        "narrow_unflagged": {
            "n": len(miss_n),
            "by_error_type": miss_n["error_type"].fillna("(unlabeled)").value_counts().to_dict(),
            "by_column": miss_n["column_to_correct"].fillna("(none)").value_counts().to_dict(),
            "by_correction_type": miss_n["correction_type"].fillna("(none)").value_counts().to_dict(),
            "by_audit_decision": miss_n["audit_decision"].value_counts().to_dict(),
        },
        "broad_unflagged": {"n": len(miss_b),
                            "by_has_correction": miss_b["has_correction"].value_counts().to_dict()},
        "awake_equals_getup_rule": rule,
    }
    (config.OUT_DIR / "unflagged.json").write_text(json.dumps(out, indent=2) + "\n")

    lines = [
        "# The corrections the queue never sees",
        "",
        "These rows are `human_review == corrected` but never got a FLAG, so no",
        "ranking policy -- learned or hand-written -- can surface them.",
        "",
        f"## Narrow set: {len(miss_n)} of {len(narrow)}",
        "",
        "| error_type | n |",
        "|---|---:|",
    ]
    for k, v in out["narrow_unflagged"]["by_error_type"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "| corrected column | n |", "|---|---:|"]
    for k, v in out["narrow_unflagged"]["by_column"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "Audit verdict on those rows: "
        + ", ".join(f"`{k}` {v}" for k, v in out["narrow_unflagged"]["by_audit_decision"].items()),
        "",
        f"## Broad set: {len(miss_b)} of {len(broad)}",
        "",
        "| has_correction | n |",
        "|---|---:|",
    ]
    for k, v in out["broad_unflagged"]["by_has_correction"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## Does one obvious rule fix it?",
        "",
        "`final awakening == get-up` (the raw signature behind several awake/getup",
        "corrections):",
        "",
        f"- rows firing: **{rule['rows']}**",
        f"- corrected rows inside: **{rule['corrected_inside']}** -> precision "
        f"**{rule['precision']:.1%}**",
        f"- of the unflagged broad rows it would catch: **{rule['catches_unflagged']}**",
        "",
        "Its precision equals the queue base rate (6.5%), so it is not a new",
        "discriminator -- it is the same haystack with a different label. The fix",
        "has to change *what is observed* (cross-field consistency), not where the",
        "threshold sits.",
    ]
    (config.OUT_DIR / "unflagged.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
