"""Rank claims under a review budget and write a coverage receipt.

The receipt is the only artefact this module exists for. It answers two
questions the case tables cannot answer on their own: given B re-measurements,
which claims should get them, and what part of the weak mass is unreachable at
that budget.

Nothing here judges a claim. A claim is either stable across all five batches
or not; the receipt says how much unstable mass a given budget covers and names
what it does not cover.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter

BUDGETS = (8, 16, 32, 64, 128)


def queue(claims, rng):
    """What the case's own screen would let a reviewer see, in table order."""
    return [c for c in claims if c.presented]


def stability(claims, rng):
    """Weakest support first, then the widest disagreement across batches."""
    return sorted(queue(claims, rng), key=lambda c: (-c.disagreement, -c.spread))


def spread(claims, rng):
    """Largest measurement spread first, ignoring how the batches voted."""
    return sorted(queue(claims, rng), key=lambda c: -c.spread)


def cell_diverse(claims, rng):
    """Round robin across cells so one suspicious cell cannot fill the budget."""
    buckets = {}
    for claim in stability(claims, rng):
        buckets.setdefault(claim.cell, []).append(claim)
    order, keys = [], sorted(buckets)
    while any(buckets[k] for k in keys):
        for key in keys:
            if buckets[key]:
                order.append(buckets[key].pop(0))
    return order


def shuffled(claims, rng):
    order = queue(claims, rng)
    rng.shuffle(order)
    return order


RANKINGS = {"queue": queue, "stability": stability, "spread": spread,
            "cell_diverse": cell_diverse, "random": shuffled}


def digest(claim_ids):
    joined = "\n".join(sorted(claim_ids)).encode()
    return hashlib.sha256(joined).hexdigest()[:16]


def coverage(claims, order, budgets, ranking):
    weak = [c for c in claims if c.weak]
    weak_presented = [c for c in weak if c.presented]
    rows = []
    for budget in budgets:
        inspected = order[:budget]
        hit = sum(c.weak for c in inspected)
        rows.append({
            "budget": budget, "ranking": ranking,
            "inspected": len(inspected),
            "weak_inspected": hit,
            "weak_presented": len(weak_presented),
            "share_of_weak_presented": round(hit / len(weak_presented), 4)
                if weak_presented else 0.0,
            "wasted_reviews": len(inspected) - hit,
            "unreachable_ids": digest([c.id for c in weak_presented
                                       if c.id not in {i.id for i in inspected}]),
        })
    return rows


def receipt(claims, provenance, budgets=BUDGETS, seed=20261124):
    tiers = Counter(c.disagreement for c in claims)
    weak = [c for c in claims if c.weak]
    rows = []
    for name, ranking in RANKINGS.items():
        order = ranking(claims, random.Random(seed))
        rows += coverage(claims, order, budgets, name)
    by_cell = Counter(c.cell for c in weak if c.presented)
    return {
        "provenance": provenance,
        "inventory": {
            "claims": len(claims),
            "cells": len({c.cell for c in claims}),
            "contrasts": sorted({c.contrast for c in claims}),
            "metrics": sorted({c.metric for c in claims}),
            "presented": sum(c.presented for c in claims),
            "weak": len(weak),
            "weak_presented": sum(c.weak and c.presented for c in weak),
            "weak_off_queue": sum(c.weak and not c.presented for c in weak),
            "disagreement_histogram": {str(k): tiers[k] for k in sorted(tiers)},
            "screen": {
                "presented_stable": sum(c.presented and not c.weak for c in claims),
                "presented_weak": sum(c.presented and c.weak for c in claims),
                "rejected_stable": sum(not c.presented and not c.weak for c in claims),
                "rejected_weak": sum(not c.presented and c.weak for c in claims),
                "rejected_stable_spread_over_005": sum(
                    not c.presented and not c.weak and c.spread > 0.05
                    for c in claims),
            },
        },
        "weak_by_cell_top": by_cell.most_common(5),
        "budgets": list(budgets),
        "coverage": rows,
        "seed": seed,
    }


def render(data):
    inv = data["inventory"]
    prov = data["provenance"]
    lines = [
        "# Review coverage receipt — CUDA case",
        "",
        f"Case `{prov['case']}` at commit `{prov['pin']}`.",
        "Table digests: " + ", ".join(
            f"`{name}` {info['sha256'][:12]}" for name, info in prov["tables"].items()),
        f"{prov['recomputed_from_raw']} of {inv['claims']} claims had their per-batch",
        "ratios rebuilt bit-exactly from the raw batch table before use. The rest are",
        "within-method contrasts, whose ratios the raw table does not contain.",
        "",
        "## Inventory", "",
        f"- claims: **{inv['claims']}** across {inv['cells']} cells, "
        f"{len(inv['contrasts'])} contrast types, {len(inv['metrics'])} metrics",
        f"- presented as supported by the case's own screen: {inv['presented']}",
        f"- weak (at least one batch on the other side of unity): **{inv['weak']}**",
        f"- weak and presented: **{inv['weak_presented']}**",
        f"- weak but filtered out by the screen: {inv['weak_off_queue']}",
        "",
        "Batches on the minority side of unity: " + ", ".join(
            f"{k} → {v}" for k, v in inv["disagreement_histogram"].items()),
        "",
        "### Where the case's own screen puts each claim", "",
        "| | unanimous | weak |", "|---|---:|---:|",
        f"| presented | {inv['screen']['presented_stable']} | "
        f"{inv['screen']['presented_weak']} |",
        f"| filtered out | {inv['screen']['rejected_stable']} | "
        f"{inv['screen']['rejected_weak']} |",
        "",
        f"{inv['screen']['rejected_stable_spread_over_005']} of the "
        f"{inv['screen']['rejected_stable']} filtered-but-stable claims were dropped",
        "for measurement spread above 5 percent, not for direction. The two criteria",
        "are not separable from these tables alone, so the rejected column says what",
        "the screen did, not what it should have done.",
        "",
        "## Coverage by budget", "",
        "Share of weak *presented* claims inspected. A review spent on a stable",
        "claim is a wasted review under this budget model.", "",
    ]
    header = "| budget | " + " | ".join(
        sorted({r["ranking"] for r in data["coverage"]})) + " |"
    lines += [header, "|---:|" + "---:|" * len(
        sorted({r["ranking"] for r in data["coverage"]}))]
    rankings = sorted({r["ranking"] for r in data["coverage"]})
    for budget in data["budgets"]:
        cells = []
        for name in rankings:
            row = [r for r in data["coverage"]
                   if r["budget"] == budget and r["ranking"] == name][0]
            cells.append(f"{row['share_of_weak_presented']:.1%}")
        lines.append(f"| {budget} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## What this receipt does not say", "",
        "- It does not say a weak claim is wrong. Fewer than five batches agreeing",
        "  means the reported ratio hides a disagreement; it does not mean the",
        "  authors erred, and this file must not be quoted as an error count.",
        "- It does not cover `D/P` contrasts by independent recomputation. Those",
        "  ratios are within a method, so only the published per-batch values were",
        "  available; the recomputation check applies to the A/B contrasts.",
        "- It does not model what a re-measurement would cost in wall clock. The",
        "  budget is a count of claims, which is the unit a reviewer chooses.",
        "",
    ]
    return "\n".join(lines)
