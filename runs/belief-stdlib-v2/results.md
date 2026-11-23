# Standard-library belief v2: equivalence against a noise floor, and latency (synthetic)

## Gate: **PASSED**

| part | passed | detail |
|---|---|---|
| E1 equivalence: 95% CI of (stdlib - numpy) within +-0.10 | yes | mean -0.012, CI [-0.046, +0.022] |
| E2 noise floor: share of graphs whose outcome differs, port vs original, at most reseed + 0.05 | yes | port 0.143, reseed 0.147 |
| L rank_all_s at 80 nodes / 10 layers within 0.5s | yes | median 0.000s (numpy 0.000s) |
| L rank_all_s at 500 nodes / 20 layers within 5.0s | yes | median 0.007s (numpy 0.007s) |
| L observe_s at 500 nodes / 20 layers within 0.5s | yes | median 0.028s (numpy 0.002s) |

## Equivalence (1000 graphs, 1024 particles, budget 16)

| run | mean residual sink errors | degenerate observations |
|---|---:|---:|
| numpy | 1.079 | 1 |
| numpy_reseed | 1.073 | 1 |
| stdlib | 1.067 | 1 |

| comparison | mean difference | 95% bootstrap CI | paired sd | graphs whose outcome differs |
|---|---:|---|---:|---:|
| stdlib - numpy (implementation) | -0.012 | [-0.046, +0.022] | 0.548 | 0.143 |
| numpy reseed - numpy (noise floor) | -0.006 | [-0.042, +0.030] | 0.571 | 0.147 |

## Latency (median seconds; nodes x layers)

| graph | mean descendants | implementation | build | rank every node | one observation |
|---|---:|---|---:|---:|---:|
| 80x4 | 2.5 | numpy | 0.001 | 0.000 | 0.000 |
| 80x4 | 2.5 | stdlib | 0.001 | 0.000 | 0.004 |
| 80x10 | 11.2 | numpy | 0.001 | 0.000 | 0.000 |
| 80x10 | 11.2 | stdlib | 0.001 | 0.000 | 0.004 |
| 80x20 | 22.6 | numpy | 0.001 | 0.000 | 0.000 |
| 80x20 | 22.6 | stdlib | 0.001 | 0.000 | 0.004 |
| 200x4 | 3.2 | numpy | 0.002 | 0.000 | 0.001 |
| 200x4 | 3.2 | stdlib | 0.003 | 0.000 | 0.010 |
| 200x10 | 16.0 | numpy | 0.002 | 0.001 | 0.001 |
| 200x10 | 16.0 | stdlib | 0.003 | 0.001 | 0.011 |
| 200x20 | 39.8 | numpy | 0.003 | 0.002 | 0.001 |
| 200x20 | 39.8 | stdlib | 0.003 | 0.002 | 0.011 |
| 500x4 | 3.1 | numpy | 0.006 | 0.001 | 0.002 |
| 500x4 | 3.1 | stdlib | 0.006 | 0.001 | 0.024 |
| 500x10 | 24.3 | numpy | 0.007 | 0.003 | 0.002 |
| 500x10 | 24.3 | stdlib | 0.008 | 0.003 | 0.028 |
| 500x20 | 68.2 | numpy | 0.008 | 0.007 | 0.002 |
| 500x20 | 68.2 | stdlib | 0.008 | 0.007 | 0.028 |
