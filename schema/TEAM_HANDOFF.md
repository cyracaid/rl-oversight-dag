# Sleep data handoff / 睡眠数据交接

This package lets teammates write loaders and checks without receiving real rows.
The real sleep table stays with its authorized data holder. No participant IDs,
exact diary dates, free text, real rows, or correction records are included here.

## What to read

| File | Purpose |
|---|---|
| [sleep_headers.csv](sleep_headers.csv) | Exact ordered header, 39 columns, zero data rows |
| [SLEEP_SCHEMA.md](SLEEP_SCHEMA.md) | Human-readable column types, units and aggregate missingness |
| [sleep_schema.json](sleep_schema.json) | Machine-readable aggregate schema; authoritative header order is `fields` order |
| [../tools/make_fixture.py](../tools/make_fixture.py) | Generate synthetic development inputs locally, never research results |
| [../TEAM_CLAIMS.md](../TEAM_CLAIMS.md) | Detailed five-person job allocation, English |
| [../TEAM_CLAIMS_KO.md](../TEAM_CLAIMS_KO.md) | Korean job allocation |
| [../TEAM_CLAIMS_CN.md](../TEAM_CLAIMS_CN.md) | Chinese job allocation |

## Parsing contract and known limits

The card describes an exported CSV, not a strict source-system type contract.
CSV has no native dtypes. Suggested in-memory types below are recommendations;
they do not assert an unverified source dtype.

| Field group | Suggested representation | Rule |
|---|---|---|
| `pid`, `row_id` | opaque strings | Identifier equality only; no numeric/ordinal features |
| `day_num` | nullable integer | Study day; do not assume `(pid, day_num)` uniquely identifies a row |
| four `*_selfreport_ts` columns | nullable datetime | Local wall-clock `YYYY-MM-DD HH:MM:SS`, timezone unspecified |
| `StartDate` | nullable date/string | Card redacts details as `key`; verify actual format locally before enforcing a parser |
| durations | nullable float | Minutes, not hours or seconds |
| `se_percent` | nullable float | 0–100, not 0–1 |
| `num_waso_bouts_selfreport`, substance counts | nullable numeric | Validate integrality locally before enforcing integer dtype |
| boolean fields | nullable boolean | Parse CSV `True`/`False` explicitly; never use `bool("False")` |
| categorical fields, `*_raw` | nullable string | Listed values can be truncated; not an exhaustive enum |
| `error_type` | nullable string pending local verification | Current snapshot is entirely missing; inferred `number` is not a semantic type |

Missing means empty CSV cell. Rounded `true 0%` / `missing 100%` in Markdown may
hide small nonzero rates: use exact JSON counts/rates, not rounded prose. Category
values and counts in this card are observed aggregates, not schema guarantees.
The current card is a snapshot of `output/cleaned_data_final.csv`; it has no source
checksum/version receipt, so it is not proof that another export has identical types.

`row_id` is reported unique in this snapshot. `(pid, day_num, row_id)` is the
documented join key, not evidence that one participant has only one record/day.
Rows per participant range up to 75 while day_num ranges 1–15; check duplicates
locally rather than silently deduplicating.

## Label / feature boundary

For the initial prediction interface, exclude all eight fields listed in
`sleep_schema.json:label_columns` from features: `error_type`, `flag_severity`,
`has_correction`, `human_review`, `is_error`, `is_unusual`, `record_status`,
`unusual_type`. Also exclude participant/row identifiers and exact dates as model
features. Raw ambiguity indicators need a decision-time availability check.
Any later use of pre-review flags needs a documented timestamp/availability audit;
do not infer availability from a final cleaned export.

This card does NOT provide the human-confirmed correction labels or the 27/48
annotator agreement split. Those cannot be reconstructed from missing `error_type`
or a synthetic fixture. Label-dependent analyses run at the authorized source;
only approved aggregate results return to the team. Split by participant when
evaluating prediction, so one participant cannot leak across train/test.

## Member handoff and acceptance

| Owner | Gets | Returns |
|---|---|---|
| Person 1: PM / review | This package + method reports | One index of claim → script → JSON → figure; block unverified numbers |
| Person 2: learning experiments | Synthetic DAG generator + boundary protocol; schema for interface work | Complete seed results/checkpoints and measured contrasts, no assumed BC conclusion |
| Person 3: environment | Schema + fixture generator + N=21 pipeline code | Loader/validator, unit and missingness checks, DAG definitions, reproduction log |
| Person 4: baselines / controls | Same synthetic inputs and graph evaluation protocol | Baselines/controls on identical graphs and randomness; label analyses only if labels are provided |
| Person 5: data interface / narrative | Schema package; authorized local access if applicable | Confirm source types/definitions locally, maintain field contract, return approved aggregate evidence |

The detailed job-allocation pages contain older experiment status. In particular,
BC 1.14 vs teacher 1.15 is NOT verified because its table and JSON conflict.
Credit assignment is a hypothesis, not established by BC alone. Boundary experiment
code and preregistration are under local validation and are not included in this
handoff commit; no new experimental results are asserted here.

## Teammate quick start

From repository root:

```bash
python3 tools/make_fixture.py --rows 500 --seed 0 --out schema/fixture_sleep.csv
```

Requires NumPy. Fixture is synthetic, git-ignored, suitable for loader plumbing.
It approximates some marginal ranges and missingness; it does NOT preserve real
joint distributions, labels, participant-day structure or every dtype. Its complete
night block is coherent, but independently filled fields elsewhere may not be.
`StartDate` can be empty; all-empty columns can be inferred as float by CSV readers.
Do not use it as ground truth for clinical invariants or any reported result.

Night ordering and TST/TIB/SE identities are intended validation targets for valid
records, not claims that all raw/erroneous records satisfy them. Definitions such as
WASO computation must be checked against the source pipeline; the external
`splsleep/SCHEMA.md` referenced by older docs is not included in this repository.

Acceptance: loader preserves all 39 header names/order; missing values remain
missing; durations keep minutes; booleans parse correctly; labels never silently
become features; no fixture-derived number enters a slide.
