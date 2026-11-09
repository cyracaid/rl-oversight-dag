# Field-level review: half the reading, most of the recall

M1-bearing rows: **140**, of which **58** have a recorded
corrected field. The rule's witness names the conflicting pair.

- at least one corrected field inside the witness pair: **56/58 = 96.5%**
- *all* corrected fields inside the pair (strict): 39/58

| witness pair | rows | covered | strict | coverage |
|---|---:|---:|---:|---:|
| awake_getup | 14 | 14 | 14 | 100.0% |
| bed_sleep | 17 | 16 | 16 | 94.1% |
| sleep_awake | 26 | 25 | 9 | 96.2% |
| sleep_awake+awake_getup | 1 | 1 | 0 | 100.0% |

## Cost model

Row review reads 4 timestamps. Pair-scoped review reads the witness pair
(2 fields in 139 of 140 rows). Reads needed to reach a fraction of the
covered positives, in queue order:

| recall of covered positives | rows reviewed | row reads | pair reads |
|---|---:|---:|---:|
| 50pct | 29 | 116 | 58 |
| 75pct | 44 | 176 | 88 |
| 90pct | 53 | 212 | 106 |
| 100pct | 58 | 232 | 117 |

To cover every positive it can reach, row review spends **232** field-reads and pair-scoped spends **117** — a 50% reduction.

This moves **cost**, not recall: the type ceiling is unchanged, and the
strict column shows multi-field corrections that spill outside the pair.
It is still the only escape that survives: under a time budget, halving
the reads per review doubles what the queue can buy.
