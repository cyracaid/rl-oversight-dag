# v2.1 gate — conditional endpoint

Pre-registration: `PREREGISTER_ORDERED_BENCHMARK_V21.md`. Blocks: graphs `(5184, 12)`, episodes `(5640, 60)`, q = 1.0, K = 8.

Episodes with an oracle-readable gap: **15/60** (dropped 45).

| policy | sink errors |
|---|---:|
| marginal | 0.933 |
| truth_reader | 0.583 |
| symptom_reader | 1.117 |
| oracle | 0.467 |

`marginal − oracle` = 0.467.

**Recovery R = 0.821** [0.630, 0.964] — fraction of the oracle-readable gap recovered by the pair information.

## Verdicts

- `H1 recovery ≥ 0.50`: **holds**
- `H2 symptom repair is not the source`: **holds** (+0.183 [+0.050, +0.350])
- `H3 still not locally solvable`: node-level 0.800, order pattern 0.500 → NOT ok
