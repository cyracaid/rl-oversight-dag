# Sleep diary — schema card (for code, not for analysis)

13,990 rows × 39 columns · grain: **one row per participant-day** · key: `(pid, day_num, row_id)`

> Aggregates only. No row, no participant id, no exact date. `tools/make_fixture.py` turns this file into a synthetic table with the same headers.

| column | type | unit / range | missing | note |
|---|---|---|---:|---|
| `pid` | key | — | — | opaque integer id; the number of distinct participants is reported, not the values |
| `day_num` | number | 1.00–15.00 | 0% | study day 1..15 |
| `row_id` | key | — | — | row key; unique per row |
| `bedtime_selfreport_ts` | timestamp | YYYY-MM-DD HH:MM:SS | 81% | period 2020-08 .. 2022-03 |
| `sleeponset_selfreport_ts` | timestamp | YYYY-MM-DD HH:MM:SS | 81% | period 2020-08 .. 2022-03 |
| `awakening_selfreport_ts` | timestamp | YYYY-MM-DD HH:MM:SS | 80% | period 2020-08 .. 2022-03 |
| `getup_selfreport_ts` | timestamp | YYYY-MM-DD HH:MM:SS | 80% | period 2020-08 .. 2022-03 |
| `tst_minutes` | number | 65.00–715.00 | 88% | minutes |
| `sol_computed_minutes` | number | 0.00–360.00 | 80% | minutes |
| `se_percent` | number | 50.00–100.00 | 88% | percent 0–100 |
| `tib_minutes` | number | 145.00–990.00 | 80% | minutes |
| `sleepperiod_minutes` | number | 75.00–840.00 | 80% | minutes |
| `waso_computed_minutes` | number | 0.00–384.00 | 80% | minutes |
| `waso_avg_bout_selfreport_minutes` | number | 0.00–180.00 | 88% | minutes |
| `sol_selfreport_minutes` | number | 0.00–180.00 | 80% | minutes |
| `waso_selfreport_minutes` | number | 0.00–210.00 | 88% | minutes |
| `num_waso_bouts_selfreport` | number | 0.00–20.00 | 80% | count |
| `nap_selfreport_totalminutes` | number | 0.00–220.00 | 80% | minutes |
| `exercise_light_minutes` | number | 0.00–390.00 | 80% | minutes |
| `exercise_moderate_minutes` | number | 0.00–210.00 | 80% | minutes |
| `exercise_vigorous_minutes` | number | 0.00–210.00 | 80% | minutes |
| `exercise_strength_minutes` | number | 0.00–150.00 | 80% | minutes |
| `has_correction` | category | `none`, `algorithmic`, `manual`, `both` | 0% | 4 distinct |
| `is_error` | boolean | true 0% | 0% | |
| `error_type` | number | — | 100% |  |
| `is_unusual` | boolean | true 0% | 0% | |
| `unusual_type` | category | `bed_sleep_suspicious`, `awake_getup_suspicious`, `sleep_awake_suspicious` | 100% | 3 distinct |
| `record_status` | category | `not_reported`, `clean`, `equal_time`, `reasonable_unusual` | 0% | 4 distinct |
| `flag_severity` | category | `Clean`, `Minor issues (1 flag)`, `Major issues (2+ flags)` | 0% | 3 distinct |
| `human_review` | category | `none`, `waiting`, `accepted`, `corrected` | 0% | 4 distinct |
| `caffeine_num` | number | 0.00–5.00 | 89% | count |
| `alcohol_num` | number | 1.00–6.00 | 99% | count |
| `nicotine_doses` | number | — | 100% | count |
| `cannabis_doses` | number | — | 100% | count |
| `StartDate` | key | — | — | calendar date of the diary entry |
| `sol_selfreport_raw` | category | `00:10`, `00:05`, `00:15`, `00:20`, `00:30`, `00:01` | 80% | 69 distinct |
| `sol_selfreport_ambiguous` | boolean | true 0% | 0% | |
| `waso_selfreport_raw` | category | `00:05`, `00:10`, `00:15`, `00:01`, `00:20`, `00:30` | 88% | 45 distinct |
| `waso_selfreport_ambiguous` | boolean | true 0% | 0% | |

## Conventions the code must assume

- `pid` is an integer id; it is **not** ordered and carries no information.
- `day_num` is 1-based within a participant.
- All durations are **minutes**; `se_percent` is 0–100.
- Timestamps are `YYYY-MM-DD HH:MM:SS`, local wall-clock, no timezone.
- Missing is an empty cell in the CSV (NaN after parsing).
- Label columns are listed in `label_columns`; never use them as features.

## What is deliberately absent

- any row or row-derived example;
- the participant id list (only the count is reported);
- exact diary dates (only the year-month range);
- free text.
