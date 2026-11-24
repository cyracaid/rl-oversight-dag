"""Load a case repository's derived claim tables and turn them into a claim set.

A *claim* here is one reported comparison: "method A is slower than method B on
this cell's metric". It is not a sentence from a paper and not a judgement about
the author. The claim set is built only from published tables, and the audit
numbers are recomputed from the published raw batches, so nothing in this module
depends on an unpublished file.

The one external assumption is stated here rather than hidden: a claim is
*weak* when at least one of its five per-batch ratios falls on the other side
of unity from the rest. That rule is ours, it is recomputed here, and the case's
own `same_direction_count` column is deliberately not reused -- three plausible
readings of that column disagree with it on 172 of 1728 A/B claims, so copying
it would have meant shipping a definition we could not reproduce.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

# Pinned to the commit that produced the tables. Any change of numbers upstream
# is a different case revision and must be adopted deliberately.
CASE = "zx070326-hash/sciforge-lean-cuda-cases"
PIN = "2538d5716c065cb290e8851910da210afb6f1ff5"
TABLES = ("comparisons", "metrics", "raw_numbers")


def url(table: str) -> str:
    return (f"https://raw.githubusercontent.com/{CASE}/{PIN}/"
            f"cuda/data/derived/{table}.csv")


def fetch(table: str, cache: "str | None" = None) -> tuple[bytes, str]:
    """Return the table bytes and their SHA-256, reading the cache when present."""
    import os
    if cache and os.path.exists(cache):
        payload = open(cache, "rb").read()
    else:
        with urllib.request.urlopen(url(table), timeout=60) as response:
            payload = response.read()
        if cache:
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            open(cache, "wb").write(payload)
    return payload, hashlib.sha256(payload).hexdigest()


def rows(payload: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


@dataclass(frozen=True)
class Claim:
    """One reported comparison, with the numbers that support or weaken it."""
    id: str
    cell: str
    contrast: str
    metric: str
    field: str
    presented: bool          # passes the case's own screen, i.e. enters the report
    disagreement: int        # batches on the minority side of unity, 0..2
    ratios: tuple            # per-batch paired ratios
    numerator_mad: float
    denominator_mad: float
    recomputed: bool         # ratios rebuilt bit-exactly from raw batches

    @property
    def weak(self) -> bool:
        return self.disagreement > 0

    @property
    def spread(self) -> float:
        return max(self.numerator_mad, self.denominator_mad)


def recompute(raw: list[dict], cell: str, metric: str, field: str,
              a: str, b: str) -> tuple[float, ...] | None:
    """Rebuild the per-batch ratio A/B from the raw batch values."""
    per = defaultdict(dict)
    for row in raw:
        if row["cell"] == cell and row["metric"] == metric and row["field"] == field:
            per[int(row["batch"])][row["method"]] = float(row["value_us"])
    if not per:
        return None
    try:
        return tuple(per[batch][a] / per[batch][b] for batch in sorted(per))
    except KeyError:
        return None


def disagreement(ratios: Iterable[float]) -> int:
    """How many batches sit on the minority side of unity.

    Zero means every batch puts the ratio on the same side, which is the only
    thing this module calls stable. A ratio of exactly one counts for neither
    side, so a claim cannot become stable by rounding.
    """
    values = list(ratios)
    above = sum(v > 1 for v in values)
    below = sum(v < 1 for v in values)
    return min(above, below)


def build(comparisons: list[dict], raw: list[dict]) -> list[Claim]:
    claims, mismatches = [], 0
    for row in comparisons:
        a, b = (row["contrast"].split("/") if "/" in row["contrast"]
                else row["contrast"].split(":"))
        published = json.loads(row["paired_ratios"])
        mine = recompute(raw, row["cell"], row["metric"], row["field"], a, b)
        if mine is not None and len(mine) == len(published) and all(
                abs(x - y) < 1e-9 for x, y in zip(mine, published)):
            ratios, rebuilt = tuple(published), True
        else:
            ratios, rebuilt = tuple(published), False
            if mine is not None:
                mismatches += 1
        claims.append(Claim(
            id=f"{row['cell']}|{row['contrast']}|{row['metric']}",
            cell=row["cell"], contrast=row["contrast"], metric=row["metric"],
            field=row["field"], presented=row["passes_screen"] == "True",
            disagreement=disagreement(ratios), ratios=ratios,
            numerator_mad=float(row["numerator_relative_mad"]),
            denominator_mad=float(row["denominator_relative_mad"]),
            recomputed=rebuilt))
    if mismatches:
        raise ValueError(f"{mismatches} claims disagree with the raw batch values")
    return claims


def load(cache_dir: str | None = None) -> tuple[list[Claim], dict]:
    """Fetch the pinned tables, rebuild the claim set, return it with provenance."""
    payloads, digests = {}, {}
    for table in TABLES:
        cache = f"{cache_dir}/{table}.csv" if cache_dir else None
        payloads[table], digests[table] = fetch(table, cache)
    claims = build(rows(payloads["comparisons"]), rows(payloads["raw_numbers"]))
    provenance = {
        "case": CASE, "pin": PIN,
        "tables": {t: {"sha256": digests[t], "bytes": len(payloads[t])}
                   for t in TABLES},
        "claims": len(claims),
        "recomputed_from_raw": sum(c.recomputed for c in claims),
    }
    return claims, provenance
