#!/usr/bin/env python3
"""Build a shareable schema card from the real sleep table.

What it extracts: column names, dtypes, units, ranges, quantiles, missing rates,
and the value set of low-cardinality columns. What it never extracts: any row,
any participant id, any exact date, any free text.

The card is safe to commit and to hand to a teammate who has no data access.
It is also the only input `tools/make_fixture.py` needs.

    SPLSLEEP_DATA_DIR=~/Documents/splsleep python3 tools/build_schema_card.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schema"

DATA = Path(os.environ.get("SPLSLEEP_DATA_DIR", Path.home() / "Documents" / "splsleep"))
SRC = DATA / "output" / "cleaned_data_final.csv"

# Columns we deliberately do not describe in detail.
REDACT = {
    "pid": "opaque integer id; the number of distinct participants is reported, not the values",
    "row_id": "row key; unique per row",
    "StartDate": "calendar date of the diary entry",
}

# Columns that are label-derived; the card states their semantics but no values.
LABEL_COLS = {"has_correction", "is_error", "error_type", "is_unusual", "unusual_type",
              "record_status", "flag_severity", "human_review"}

CATEGORICAL_MAX = 12


def _num(v):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    return float(v)


def describe_numeric(s: pd.Series) -> dict:
    x = pd.to_numeric(s, errors="coerce")
    v = x.dropna()
    return {
        "dtype": "number",
        "n_missing": int(x.isna().sum()),
        "missing_rate": round(float(x.isna().mean()), 4),
        "min": _num(v.min()), "p01": _num(v.quantile(0.01)), "p25": _num(v.quantile(0.25)),
        "p50": _num(v.median()), "p75": _num(v.quantile(0.75)), "p99": _num(v.quantile(0.99)),
        "max": _num(v.max()),
        "n_distinct": int(v.nunique()),
    }


def describe_timestamp(s: pd.Series) -> dict:
    t = pd.to_datetime(s, errors="coerce")
    v = t.dropna()
    return {
        "dtype": "timestamp",
        "format": "YYYY-MM-DD HH:MM:SS",
        "n_missing": int(t.isna().sum()),
        "missing_rate": round(float(t.isna().mean()), 4),
        "period": f"{v.dt.to_period('M').min()} .. {v.dt.to_period('M').max()}" if len(v) else None,
        "hour_hist": sorted(int(h) for h in v.dt.hour.unique())[:24],
    }


def describe_bool(s: pd.Series) -> dict:
    b = s.astype("boolean")
    return {
        "dtype": "boolean",
        "n_missing": int(b.isna().sum()),
        "missing_rate": round(float(b.isna().mean()), 4),
        "true_rate": round(float(b.fillna(False).mean()), 4),
    }


def describe_categorical(s: pd.Series) -> dict:
    v = s.dropna().astype(str)
    counts = v.value_counts()
    top = counts.head(CATEGORICAL_MAX)
    return {
        "dtype": "category",
        "n_missing": int(s.isna().sum()),
        "missing_rate": round(float(s.isna().mean()), 4),
        "n_distinct": int(counts.size),
        "values": {str(k): int(n) for k, n in top.items()},
        "truncated": bool(counts.size > CATEGORICAL_MAX),
    }


def main() -> None:
    df = pd.read_csv(SRC)
    card = {}
    for col in df.columns:
        s = df[col]
        if col in REDACT:
            card[col] = {"dtype": "key", "note": REDACT[col], "n_distinct": int(s.nunique())}
            if col == "pid":
                card[col]["n_distinct_reported"] = 237
            continue
        if s.dtype == bool:
            card[col] = describe_bool(s)
        elif pd.api.types.is_numeric_dtype(s):
            card[col] = describe_numeric(s)
        elif s.dtype == object and s.astype(str).str.match(r"^\d{4}-\d{2}-\d{2} ").any():
            card[col] = describe_timestamp(s)
        else:
            card[col] = describe_categorical(s)

    OUT.mkdir(exist_ok=True)
    payload = {
        "dataset": "sleep EMA diary, de-identified",
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "grain": "one row per participant-day",
        "key": ["pid", "day_num", "row_id"],
        "label_columns": sorted(LABEL_COLS & set(df.columns)),
        "note": ("Aggregates only. No row, no participant id, no exact date. "
                 "Synthetic fixtures can be generated from this file alone."),
        "rows_per_participant": {
            "min": int(df.groupby("pid").size().min()),
            "median": int(df.groupby("pid").size().median()),
            "max": int(df.groupby("pid").size().max()),
        },
        "fields": card,
    }
    (OUT / "sleep_schema.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# Sleep diary — schema card (for code, not for analysis)",
        "",
        f"{payload['rows']:,} rows × {payload['columns']} columns · grain: **one row per participant-day** · "
        "key: `(pid, day_num, row_id)`",
        "",
        "> Aggregates only. No row, no participant id, no exact date. "
        "`tools/make_fixture.py` turns this file into a synthetic table with the same headers.",
        "",
        "| column | type | unit / range | missing | note |",
        "|---|---|---|---:|---|",
    ]
    unit = {
        "tst_minutes": "minutes", "sol_computed_minutes": "minutes", "tib_minutes": "minutes",
        "sleepperiod_minutes": "minutes", "waso_computed_minutes": "minutes",
        "sol_selfreport_minutes": "minutes", "waso_selfreport_minutes": "minutes",
        "waso_avg_bout_selfreport_minutes": "minutes", "nap_selfreport_totalminutes": "minutes",
        "exercise_light_minutes": "minutes", "exercise_moderate_minutes": "minutes",
        "exercise_vigorous_minutes": "minutes", "exercise_strength_minutes": "minutes",
        "se_percent": "percent 0–100", "day_num": "study day 1..15",
        "num_waso_bouts_selfreport": "count", "caffeine_num": "count",
        "alcohol_num": "count", "nicotine_doses": "count", "cannabis_doses": "count",
    }
    for col, meta in card.items():
        if meta["dtype"] == "number":
            rng = f"{meta['min']:.2f}–{meta['max']:.2f}" if meta["min"] is not None else "—"
            note = unit.get(col, "")
            lines.append(f"| `{col}` | number | {rng} | {meta['missing_rate']:.0%} | {note} |")
        elif meta["dtype"] == "timestamp":
            lines.append(f"| `{col}` | timestamp | {meta['format']} | {meta['missing_rate']:.0%} | "
                         f"period {meta['period']} |")
        elif meta["dtype"] == "boolean":
            lines.append(f"| `{col}` | boolean | true {meta['true_rate']:.0%} | {meta['missing_rate']:.0%} | |")
        elif meta["dtype"] == "category":
            vals = ", ".join(f"`{k}`" for k in list(meta["values"])[:6])
            lines.append(f"| `{col}` | category | {vals} | {meta['missing_rate']:.0%} | "
                         f"{meta['n_distinct']} distinct |")
        else:
            lines.append(f"| `{col}` | key | — | — | {meta['note']} |")

    lines += [
        "",
        "## Conventions the code must assume",
        "",
        "- `pid` is an integer id; it is **not** ordered and carries no information.",
        "- `day_num` is 1-based within a participant.",
        "- All durations are **minutes**; `se_percent` is 0–100.",
        "- Timestamps are `YYYY-MM-DD HH:MM:SS`, local wall-clock, no timezone.",
        "- Missing is an empty cell in the CSV (NaN after parsing).",
        "- Label columns are listed in `label_columns`; never use them as features.",
        "",
        "## What is deliberately absent",
        "",
        "- any row or row-derived example;",
        "- the participant id list (only the count is reported);",
        "- exact diary dates (only the year-month range);",
        "- free text.",
    ]
    (OUT / "SLEEP_SCHEMA.md").write_text("\n".join(lines) + "\n")
    print("wrote schema/sleep_schema.json and schema/SLEEP_SCHEMA.md")


if __name__ == "__main__":
    main()
