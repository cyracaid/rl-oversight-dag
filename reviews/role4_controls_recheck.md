# role 4 structural controls — independent recheck

- run: 2026-11-26 14:36, commit `a535a4c`
- machine: Darwin 24.4.0, Python 3.14.7
- clean room: `reviews/role4_independent/` — protocol in `PROTOCOL.md`, ambiguities in `NOTES.md`

## A. Anchor for the fresh block 7100–7199

`role4_controls/reproduce.py` states that this block has no frozen rows to check against, so its
`intact` rows were unanchored. Recomputed here from the environment only.

- compared rows: **1500** (100 graphs × 5 families × 3 policies)
- sink-error mismatches: **0**
- action-sequence mismatches: **0**
- rows missing on either side: **0**

**PASS**

## B. Clean-room agreement (block 90000–90099)

| comparison | compared | mismatches |
|---|---:|---:|
| summary cells (6 float fields) | 45 | 0 |
| verdict labels the author assigned | 20 | 0 |
| worst-of-n rows (3 fields) | 36 | 0 |
| diagnostics (aggregate) | 8 | 0 |
| row-level records (errors + actions) | 4500 | 0 |

key sets differ by 0 summary / 0 worst-of-n / 0 diagnostics keys.


**PASS** — the v1 control tables follow from the written protocol.

## What this does not cover

1. **Environment.** Both implementations import `dag_role3`; a bug shared by every user of it is
   invisible here.
2. **Intervals are not independent.** The clean room was not allowed to read
   `run_benchmark.interval`; it recovered the procedure from the frozen summary and matched every
   frozen bound to <1e-9 (`NOTES.md`, ambiguity 1). Point estimates are independent, intervals are
   calibrated, and the verdicts read interval signs.
3. **v2 is not reimplemented.** `rewire_order`, the ten draws, the three-level verdict and the
   20 % margin are role 4's code only. The `inconclusive` label rests on it.
4. **`flatten` and `rewire` have no ground truth.** Only `intact` can be anchored; the controls can
   be shown to be *implemented as specified*, not to be *the right experiment*.
