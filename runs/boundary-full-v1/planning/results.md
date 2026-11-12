# Boundary experiment

Generated from `results.json`.
Negative difference = fewer sink errors than belief greedy.

| condition | policy | sink errors | paired Δ | bootstrap 95% CI |
|---|---|---:|---:|---|
| matched | conf threshold | 1.440 | +0.340 | [+0.200, +0.495] |
| matched | belief greedy | 1.100 | +0.000 | [+0.000, +0.000] |
| matched | 2-step greedy | 1.020 | -0.080 | [-0.160, -0.010] |
| matched | reinforce/static | 1.517 | +0.417 | [+0.161, +0.766] |
| matched | reinforce/observed | 1.709 | +0.609 | [+0.404, +0.829] |
| matched | bc/observed | 1.201 | +0.101 | [+0.007, +0.197] |
| matched | bc_ft/observed | 1.525 | +0.425 | [+0.240, +0.650] |

## Additional paired controls

| condition | contrast | paired Δ | bootstrap 95% CI |
|---|---|---:|---|
| matched | reinforce/static − 2-step greedy | +0.497 | [+0.234, +0.849] |
| matched | reinforce/observed − 2-step greedy | +0.689 | [+0.482, +0.909] |
| matched | bc/observed − 2-step greedy | +0.181 | [+0.089, +0.283] |
| matched | bc_ft/observed − 2-step greedy | +0.505 | [+0.315, +0.733] |
