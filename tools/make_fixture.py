#!/usr/bin/env python3
"""Generate a synthetic stand-in table from schema/sleep_schema.json.

No real data is read. The script samples each column independently from the
aggregates in the card (quantiles, category frequencies, missing rates), so the
result has the same headers, dtypes and rough ranges — and none of the real rows.

    python3 tools/make_fixture.py --rows 500 --out schema/fixture_sleep.csv

The output is a development fixture. It is never a substitute for the real data,
and it must never be used to produce a number that goes in the paper.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "sleep_schema.json"


def sample_numeric(meta: dict, rng: np.random.Generator) -> float:
    pts = [meta["p01"], meta["p25"], meta["p50"], meta["p75"], meta["p99"]]
    if any(v is None for v in pts):
        return float("nan")
    qs = [0.01, 0.25, 0.50, 0.75, 0.99]
    u = rng.uniform(qs[0], qs[-1])
    return float(np.interp(u, qs, pts))


def sample_timestamp(meta: dict, rng: np.random.Generator) -> str:
    hours = meta.get("hour_hist") or [0, 6, 7, 23]
    hour = int(rng.choice(hours))
    minute = int(rng.integers(0, 60))
    # period is "YYYY-MM .. YYYY-MM"; pick a month, then a day inside it
    try:
        a, b = meta["period"].split(" .. ")
        start = datetime.strptime(a, "%Y-%m")
        end = datetime.strptime(b, "%Y-%m")
        span = (end - start).days + 30
        day = start + timedelta(days=int(rng.integers(0, max(1, span))))
    except Exception:
        day = datetime(2021, 1, 1)
    return f"{day.year:04d}-{day.month:02d}-{day.day:02d} {hour:02d}:{minute:02d}:00"


def sample_category(meta: dict, rng: np.random.Generator) -> str:
    values = list(meta["values"])
    weights = np.array(list(meta["values"].values()), dtype=float)
    return str(rng.choice(values, p=weights / weights.sum()))


def coherent_night(rng: np.random.Generator, card: dict) -> dict:
    """One internally consistent diary night: bed -> sleep -> wake -> get-up."""
    f = card["fields"]
    sol = float(np.clip(rng.normal(24, 15), 0, 180))
    waso = float(np.clip(rng.gamma(1.6, 22), 0, 240))
    tst = float(np.clip(rng.normal(420, 55), 120, 720))
    bed_hour = float(rng.choice([21.5, 22, 22.5, 23, 23.5, 0.5], p=[.12, .22, .26, .22, .12, .06]))
    day = datetime(2021, 3, 1) + timedelta(days=int(rng.integers(0, 400)))
    bed = day.replace(hour=0, minute=0) + timedelta(hours=bed_hour)
    asleep = bed + timedelta(minutes=sol)
    awake = asleep + timedelta(minutes=tst + waso)
    getup = awake + timedelta(minutes=float(np.clip(rng.normal(18, 15), 0, 90)))
    tib = (getup - bed).total_seconds() / 60
    se = min(100.0, max(0.0, 100 * tst / tib)) if tib > 0 else float("nan")
    fmt = "%Y-%m-%d %H:%M:%S"
    return {
        "bedtime_selfreport_ts": bed.strftime(fmt),
        "sleeponset_selfreport_ts": asleep.strftime(fmt),
        "awakening_selfreport_ts": awake.strftime(fmt),
        "getup_selfreport_ts": getup.strftime(fmt),
        "tst_minutes": round(tst, 1),
        "sol_computed_minutes": round(sol, 1),
        "se_percent": round(se, 1),
        "tib_minutes": round(tib, 1),
        "sleepperiod_minutes": round((awake - asleep).total_seconds() / 60, 1),
        "waso_computed_minutes": round(waso, 1),
        "sol_selfreport_minutes": round(float(np.clip(sol + rng.normal(0, 12), 0, 240)), 1),
        "waso_selfreport_minutes": round(float(np.clip(waso + rng.normal(0, 20), 0, 300)), 1),
        "num_waso_bouts_selfreport": int(np.clip(rng.poisson(1.4), 0, 20)),
    }


REPORTED_RATE = 0.19     # matches the ~81% missingness of the timestamp block


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=500)
    ap.add_argument("--out", default="schema/fixture_sleep.csv")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    card = json.loads(SCHEMA.read_text())
    rng = np.random.default_rng(args.seed)
    fields = card["fields"]
    columns = list(fields)
    n_pid = fields["pid"]["n_distinct_reported"]

    rows = []
    for r in range(args.rows):
        row = {c: "" for c in columns}
        row["pid"] = int(rng.integers(1, n_pid + 1))
        row["row_id"] = r + 1
        row["day_num"] = int(rng.integers(1, 16))

        if rng.random() < REPORTED_RATE:
            row.update(coherent_night(rng, card))

        for col in columns:
            meta = fields[col]
            if col in row and row[col] != "":
                continue
            if meta["dtype"] == "number":
                if rng.random() < meta["missing_rate"]:
                    continue
                v = sample_numeric(meta, rng)
                row[col] = round(v, 2)
            elif meta["dtype"] == "boolean":
                row[col] = bool(rng.random() < meta["true_rate"])
            elif meta["dtype"] == "category":
                row[col] = sample_category(meta, rng)
        rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} — {args.rows} synthetic rows, {len(columns)} columns "
          f"(no real data read; ~{REPORTED_RATE:.0%} with a complete night)")


if __name__ == "__main__":
    main()
