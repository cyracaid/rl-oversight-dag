#!/usr/bin/env python3
"""The results, split by layer — two tables, never one.

The paper reports two instances, and they do not share a single error code: the sleep
corrections are all value-layer defects, the SciForge audit findings are evidence- and
argument-layer. A pooled precision would average "did it spot a bad timestamp" with
"did it spot a claim overreaching its evidence", which is not one question.

So this script emits one table per instance, each keyed by `layer`, and refuses to
produce a combined row. Cells with no measurement stay empty with the reason, because
the reason is a result too.

Reads only committed aggregates under `outputs/`, so it runs without the IRB data. The
SciForge half comes from `outputs/sciforge_injection.json`, copied from the SciForge
repository by `sync_sciforge_injection.py`; the digest in its provenance is re-checked
here, so an edited number cannot pass as a measured one.

    python3 triage_bench/run_layered_report.py
"""

from __future__ import annotations

import json

from bench import config
from sync_sciforge_injection import OUT_NAME as SCI_SOURCE, payload_digest

OUT = config.OUT_DIR

# Policies worth a row. Everything else is in recall_at_k.json for the figures.
POLICIES = [
    ("queue_order", "pipeline queue order"),
    ("random", "random"),
    ("rule_count", "rule count (AI severity)"),
    ("m1_first", "M1-bearing first"),
    ("m1_then_sol_gap", "M1 first, then SOL gap"),
    ("oracle", "oracle"),
]

KS = [100, 200, 400]

# The one cell Table 2 still cannot fill, stated once so the row and the note agree.
PROPAGATION_BLOCKER = (
    "no recipe asserts a stale cascade; the corpus scores localization only"
)


def _load(name: str) -> dict:
    return json.loads((OUT / name).read_text())


def _reviews_to(curve: dict[str, float], target: float) -> int | str:
    for k in sorted(curve, key=int):
        if curve[k] >= target:
            return int(k)
    return "—"


def sleep_rows() -> list[dict]:
    """The sleep queue: one layer, real reviews, real labels."""
    recall = _load("recall_at_k.json")
    summary = _load("queue_summary.json")
    rows = []
    for key, label in POLICIES:
        curve = recall["curves"][key]
        rows.append({
            "instance": "sleep (splsleep)",
            "layer": "value",
            "policy": label,
            "recall": {str(k): curve[str(k)] for k in KS},
            "reviews_to_half": _reviews_to(curve, 0.5),
            "queue": summary["candidates"],
            "base_rate": summary["precision"],
        })
    return rows


def _sciforge_payload() -> dict:
    """The copied audit result, refused unless its digest matches the numbers."""
    document = _load(SCI_SOURCE)
    recorded = document["provenance"]["sha256"]
    actual = payload_digest(document["payload"])
    if recorded != actual:
        raise ValueError(
            f"{SCI_SOURCE}: numbers do not match their provenance digest "
            f"({actual} != {recorded}); run sync_sciforge_injection.py"
        )
    return document["payload"]


def sciForge_rows() -> list[dict]:
    """The evidence-dag audit: two layers, one injection pair per finding class.

    `localization_at_1` is reported twice because the two conditions answer different
    questions. Isolated, a three-node graph makes rank 0 nearly free, so it is a wiring
    check. Mixed, the injected finding competes with three unrelated single-source
    claims and the audit's tiebreak is a content hash, so the number is a floor rather
    than a curve.

    Propagation recall stays `None`: no recipe asserts a stale cascade, so there is
    nothing to score. The corpus measures localization only, and saying so is cheaper
    than inventing a propagation number.
    """
    summary = _sciforge_payload()["summary"]
    rows = []
    for layer in ("evidence", "argument"):
        block = summary["by_layer"][layer]
        rows.append({
            "instance": "SciForge (evidence-dag)",
            "layer": layer,
            "classes": block["classes"],
            "caught": block["caught"],
            "localization_at_1_isolated": block["localization_at_1"],
            "localization_at_1": block["localization_at_1_mixed"],
            "localization_at_3": block["localization_at_3_mixed"],
            "clean_twin_violations": block["clean_twin_violations"],
            "propagation_recall": None,
            "blocker": PROPAGATION_BLOCKER,
        })
    return rows


def check_layers(rows: list[dict]) -> None:
    """Refuse any row that would pool layers or fail to name one.

    This is the whole point of the split, so it is enforced rather than documented:
    an `all`/`mixed`/missing layer is a bug in the report, not a reporting choice.
    """
    for row in rows:
        layer = row.get("layer")
        if layer not in {"value", "evidence", "argument"}:
            raise ValueError(f"row does not name a comparable layer: {row!r}")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def render(sleep: list[dict], sci: list[dict]) -> str:
    lines = [
        "# Results by layer — two tables, never one",
        "",
        "Generated by `run_layered_report.py` from the committed aggregates. The two",
        "instances share the `layer` axis and nothing else: not one error code is",
        "common to both, and no cell below is comparable across the two tables.",
        "",
        "## Table 1 — sleep queue (`layer = value`)",
        "",
        "Every correction in `manual_error_correction_updated.csv` is a value-level",
        "defect: the datum exists, it is cited in the pipeline, and it is wrong. So",
        "this table has one layer and reports recall on the real review queue.",
        "",
        f"Queue: {sleep[0]['queue']} candidates, base rate {sleep[0]['base_rate']:.1%}.",
        "",
        "| policy | R@100 | R@200 | R@400 | reviews to reach 50% |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sleep:
        cells = " | ".join(_pct(row["recall"][str(k)]) for k in KS)
        lines.append(f"| {row['policy']} | {cells} | {row['reviews_to_half']} |")
    lines += [
        "",
        "| bound | value |",
        "|---|---:|",
        f"| coverage ceiling (narrow) | {_load('ceiling.json')['coverage']['narrow_ceiling']:.1%} |",
        f"| type-only ceiling @k=200 | {_load('ceiling.json')['ceiling_recall']['200']:.1%} |",
        "",
        "`layer` is constant here, so this table cannot separate value-layer from any",
        "other failure — that is a property of the instance, not a missing column.",
        "",
        "## Table 2 — evidence-dag audit (`layer = evidence | argument`)",
        "",
        "One injected corruption per finding class, each with a clean twin the audit",
        "must ignore. Ground truth is the mutation, so nothing here is hand-labelled.",
        "",
        "| layer | classes | caught | localization@1 (isolated) | localization@1 (mixed) | clean-twin violations | propagation recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sci:
        lines.append(
            f"| {row['layer']} | {row['classes']} | {row['caught']} | "
            f"{_pct(row['localization_at_1_isolated'])} | {_pct(row['localization_at_1'])} | "
            f"{row['clean_twin_violations']} | {_pct(row['propagation_recall'])} |"
        )
    lines += [
        "",
        "Coverage is the firm claim: every one of the 15 finding types is reachable from a",
        "single structural difference, and no clean twin fires. The mixed column is the",
        "honest localization number — at equal severity the audit orders by node id, which",
        "is a content hash, so a 3–5 node graph makes rank a coin toss and the value is a",
        "floor, not a measurement of reviewer-facing ordering.",
        "",
        "Propagation recall is empty because it is unmeasured, not because it is zero:",
        f"{PROPAGATION_BLOCKER}. Filling it needs a recipe whose corrupted node has",
        "descendants that must go `stale`, and none of the 15 has one yet.",
        "",
        "The copy path is `sync_sciforge_injection.py` -> `outputs/sciforge_injection.json`,",
        "which records the SciForge commit and a digest over the numbers; `_sciforge_payload`",
        "re-checks that digest before the table is built.",
        "",
        "Gap codes are a third axis and do not appear above: they report whether a",
        "chain resolved, not whether a node is wrong, and they carry their own digests.",
        "",
        "## The rule this report exists to enforce",
        "",
        "There is no pooled row. A model built for `register_unwarranted` scores 0 on",
        "`order_error` while never having been asked the question, so the only honest",
        "cross-instance sentence is the one both tables support separately: each",
        "instance surfaces defects at its dominant layer. `check_layers` raises rather",
        "than warning, so a future edit cannot quietly add a combined line.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    sleep = sleep_rows()
    sci = sciForge_rows()
    check_layers(sleep + sci)
    text = render(sleep, sci)
    (OUT / "layered_report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
