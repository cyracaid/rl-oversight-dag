# v2 gate

Pre-registration: `PREREGISTER_ORDERED_BENCHMARK.md` (including the same-day amendment).
Blocks: graphs `{'real': (5160, 12), 'ticket': (5172, 12)}`, episodes `(5600, 40)`, q = 0.5.

| family | mode | G1a node-level AUC | G1b relational AUC | transposed episodes |
|---|---|---:|---:|---:|
| real | normal | 0.599 [0.504, 0.703] | 0.822 [0.745, 0.894] | 21/40 |
| real | noise | 0.587 [0.490, 0.689] | 0.822 [0.745, 0.894] | 21/40 |
| ticket | normal | 0.986 [0.970, 0.999] | 0.901 [0.845, 0.950] | 17/40 |
| ticket | noise | 0.989 [0.973, 1.000] | 0.901 [0.845, 0.950] | 17/40 |

## Decision value, `real`, K=8

| policy | sink errors |
|---|---:|
| none | 2.500 |
| marginal | 0.750 |
| truth_reader | 0.650 |

`truth_reader - marginal` = **-0.100** [-0.250, +0.025]. Threshold 0.15.

## Verdicts

- `G1a_not_local`: **holds**
- `G1b_global`: **holds**
- `G2_decision_value`: **contradicted**
- `G3_noise_control_not_local`: **holds**

Gate is **closed**.

Ticket is a length-3 chain with one eligible pair and is reported as the smaller case: G1a contradicted, G1b holds, G2 contradicted.
