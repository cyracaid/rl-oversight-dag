# Standard-library belief: equivalence and latency (synthetic)

## Gate: **NOT PASSED**

| part | passed | detail |
|---|---|---|
| equivalence: 95% CI of (stdlib - numpy) within +-0.10 | NO | mean -0.065, CI [-0.175, +0.045] |
| latency: rank every node at N=80 within 0.5s | yes | median 0.000s (numpy 0.000s) |
| latency: rank every node at N=500 within 5.0s | yes | median 0.001s (numpy 0.001s) |

## Equivalence (200 graphs, 1024 particles, budget 16)

| implementation | mean residual sink errors | degenerate observations | seconds per graph |
|---|---:|---:|---:|
| numpy | 1.100 | 0 | 0.00 |
| stdlib | 1.035 | 1 | 0.07 |

Paired difference (stdlib - numpy): mean -0.065, 95% bootstrap CI [-0.175, +0.045] (pairs share the graph and reviewer randomness, not the particles). First chosen action agrees on 0.95 of graphs.

## Latency (median seconds)

| nodes | implementation | build | rank every node | one observation |
|---:|---|---:|---:|---:|
| 80 | numpy | 0.001 | 0.000 | 0.000 |
| 80 | stdlib | 0.001 | 0.000 | 0.004 |
| 200 | numpy | 0.002 | 0.000 | 0.001 |
| 200 | stdlib | 0.003 | 0.000 | 0.010 |
| 500 | numpy | 0.006 | 0.001 | 0.002 |
| 500 | stdlib | 0.007 | 0.001 | 0.024 |
