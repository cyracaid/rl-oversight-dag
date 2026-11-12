# Sharing the sleep data without sharing the sleep data

The rule is simple: **the real table never leaves your machine.** What teammates
need in order to write code is the *shape* of the table, not any row of it.

This directory holds that shape.

**Teammates start here: [TEAM_HANDOFF.md](TEAM_HANDOFF.md)** — ordered header,
parsing recommendations, schema caveats, label boundaries, and owner/deliverable map.

---

## What is here

| File | What it is | Safe to share? |
|---|---|---|
| `sleep_schema.json` | machine-readable column card: type, missing rate, quantiles, category values | **yes** — aggregates only |
| `SLEEP_SCHEMA.md` | the same card as a table you can read | **yes** |
| `fixture_sleep.csv` | *generated* synthetic rows, same headers | **no need to share** — teammates generate it |

`fixture_sleep.csv` is git-ignored on purpose. It is synthetic, but keeping it out
of the repo removes any chance of it being mistaken for real data.

## How a teammate uses this

```bash
python3 tools/make_fixture.py --rows 500        # writes schema/fixture_sleep.csv
```

Then their code reads that file exactly as it will read the real one later:

```python
import pandas as pd
df = pd.read_csv(path)          # path = fixture now, real file later
```

The fixture has the same 39 column names and approximates some marginal ranges
and missingness. Its complete night block is internally consistent; independently
filled fields elsewhere may not be. CSV type inference, labels and joint missingness
are not preserved. Use it for loader plumbing, not scientific or clinical validation.

## What the card deliberately omits

- any row, or a row-derived example;
- the participant id list (only the count, and rows-per-participant min/median/max);
- exact diary dates (only the year-month range);
- free text;
- any participant-level statistic that could single someone out.

## What else to hand over besides the card

| Item | Why they need it | Where it lives |
|---|---|---|
| grain and key: one row per participant-day, `(pid, day_num, row_id)` | joins, dedup, grouping | `SLEEP_SCHEMA.md` top line |
| units: durations in minutes, `se_percent` in 0–100 | a factor-of-60 bug is the classic one | card, unit column |
| missing = empty cell | don't invent sentinels like `-1` | card, conventions |
| label columns (never features) | leakage | `label_columns` in the JSON |
| derived-field definitions (TST, TIB, SE, SOL, WASO) | they must recompute the same thing | `splsleep/SCHEMA.md` — a definitions file, not data |
| invariants: `bed ≤ sleep ≤ wake ≤ get-up`, `0 ≤ SE ≤ 100` | their checks need a ground truth for "legal" | this file, below |
| rows per participant: min 3, median 61, max 75 | sizing loops and splits | `rows_per_participant` in the JSON |

## Intended invariants for valid complete nights

```
bedtime ≤ sleeponset ≤ awakening ≤ getup
tib  = getup − bedtime
tst  ≈ sleeponset → awakening, minus WASO
se   = tst / tib × 100        0 ≤ se ≤ 100
sol  = sleeponset − bedtime
```

These are validation targets, not guarantees for every synthetic or real record.
Raw/erroneous records can violate them; confirm derived-field definitions locally.

## If someone needs more detail

Extend the card, never the data: add an aggregate (a quantile, a rate, a
cross-tab of two categorical columns with counts ≥ 5) to
`tools/build_schema_card.py`, regenerate, and share the JSON. Do not paste rows
into chat, into a notebook, or into an agent prompt.

## Regenerating the card

On the machine that holds the data:

```bash
SPLSLEEP_DATA_DIR=~/Documents/splsleep python3 tools/build_schema_card.py
```

The script refuses nothing — it simply never writes a row. Check the diff before
committing: it should contain only numbers and column names.
