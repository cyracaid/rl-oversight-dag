# Boundary experiment

Generated from `results.json`.
Negative difference = fewer sink errors than belief greedy.

| condition | policy | sink errors | paired Δ | bootstrap 95% CI |
|---|---|---:|---:|---|
| matched | conf threshold | 1.440 | +0.340 | [+0.200, +0.495] |
| matched | belief greedy | 1.100 | +0.000 | [+0.000, +0.000] |
| matched | reinforce/static | 1.517 | +0.417 | [+0.161, +0.766] |
| matched | reinforce/observed | 1.709 | +0.609 | [+0.404, +0.829] |
| matched | bc/observed | 1.201 | +0.101 | [+0.007, +0.197] |
| matched | bc_ft/observed | 1.525 | +0.425 | [+0.240, +0.650] |
| prop_odds_x0.5 | conf threshold | 1.440 | +0.280 | [+0.140, +0.430] |
| prop_odds_x0.5 | belief greedy | 1.160 | +0.000 | [+0.000, +0.000] |
| prop_odds_x0.5 | reinforce/static | 1.517 | +0.357 | [+0.098, +0.710] |
| prop_odds_x0.5 | reinforce/observed | 1.714 | +0.554 | [+0.347, +0.768] |
| prop_odds_x0.5 | bc/observed | 1.216 | +0.056 | [-0.060, +0.170] |
| prop_odds_x0.5 | bc_ft/observed | 1.540 | +0.380 | [+0.198, +0.600] |
| prop_odds_x2 | conf threshold | 1.440 | +0.360 | [+0.220, +0.510] |
| prop_odds_x2 | belief greedy | 1.080 | +0.000 | [+0.000, +0.000] |
| prop_odds_x2 | reinforce/static | 1.517 | +0.437 | [+0.184, +0.784] |
| prop_odds_x2 | reinforce/observed | 1.712 | +0.632 | [+0.433, +0.841] |
| prop_odds_x2 | bc/observed | 1.188 | +0.108 | [+0.011, +0.207] |
| prop_odds_x2 | bc_ft/observed | 1.490 | +0.410 | [+0.230, +0.615] |
| conf_logit_minus0.5 | conf threshold | 1.440 | +0.450 | [+0.295, +0.615] |
| conf_logit_minus0.5 | belief greedy | 0.990 | +0.000 | [+0.000, +0.000] |
| conf_logit_minus0.5 | reinforce/static | 1.517 | +0.527 | [+0.264, +0.881] |
| conf_logit_minus0.5 | reinforce/observed | 1.612 | +0.622 | [+0.413, +0.841] |
| conf_logit_minus0.5 | bc/observed | 1.167 | +0.177 | [+0.079, +0.278] |
| conf_logit_minus0.5 | bc_ft/observed | 1.398 | +0.408 | [+0.234, +0.613] |
| conf_logit_plus0.5 | conf threshold | 1.440 | +0.190 | [+0.060, +0.325] |
| conf_logit_plus0.5 | belief greedy | 1.250 | +0.000 | [+0.000, +0.000] |
| conf_logit_plus0.5 | reinforce/static | 1.517 | +0.267 | [+0.006, +0.618] |
| conf_logit_plus0.5 | reinforce/observed | 1.866 | +0.616 | [+0.382, +0.839] |
| conf_logit_plus0.5 | bc/observed | 1.196 | -0.054 | [-0.185, +0.067] |
| conf_logit_plus0.5 | bc_ft/observed | 1.687 | +0.437 | [+0.212, +0.684] |
| catch0.7_known | conf threshold | 2.615 | +0.265 | [+0.135, +0.405] |
| catch0.7_known | belief greedy | 2.350 | +0.000 | [+0.000, +0.000] |
| catch0.7_known | reinforce/static | 2.675 | +0.325 | [+0.148, +0.577] |
| catch0.7_known | reinforce/observed | 2.778 | +0.428 | [+0.267, +0.595] |
| catch0.7_known | bc/observed | 2.442 | +0.092 | [+0.014, +0.167] |
| catch0.7_known | bc_ft/observed | 2.640 | +0.290 | [+0.144, +0.474] |
| catch0.7_unknown | conf threshold | 2.615 | +0.270 | [+0.145, +0.400] |
| catch0.7_unknown | belief greedy | 2.345 | +0.000 | [+0.000, +0.000] |
| catch0.7_unknown | reinforce/static | 2.675 | +0.330 | [+0.144, +0.574] |
| catch0.7_unknown | reinforce/observed | 2.806 | +0.461 | [+0.301, +0.633] |
| catch0.7_unknown | bc/observed | 2.450 | +0.105 | [+0.033, +0.178] |
| catch0.7_unknown | bc_ft/observed | 2.651 | +0.306 | [+0.164, +0.486] |

## Additional paired controls

| condition | contrast | paired Δ | bootstrap 95% CI |
|---|---|---:|---|
