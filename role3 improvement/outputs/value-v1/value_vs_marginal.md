# Sampled counterfactual value vs mean-field, block 4400-4599

Pre-registration: `PREREGISTER_EXACT_VALUE.md`. Verdict code: `report_value.py`.

`recovery = (marginal - policy) / (marginal - oracle)` per graph, then
averaged; 1.0 would mean the policy equals the truth-reading reference.

| family | marginal | oracle | policy | recovery [95% CI] | aggregate gap closed | W/T/L | verdict |
|---|---:|---:|---:|---|---:|---|---|
| modular | 8.780 | 4.070 | 8.785 | -0.049 [-0.087, -0.015] | -0.1% | 15/155/30 | worse |
| spike | 0.890 | 0.650 | 0.900 | +0.038 [+0.000, +0.103] | -4.2% | 2/195/3 | null |

Graphs where `marginal` and `oracle` coincide have no gap to divide by;
they are excluded from the recovery mean and counted here: modular 9/200, spike 161/200.

Read the tie column before the means. On `modular` the policy changed the
action on 45 of 200 graphs and lost more often than it won, so this is not a case of
the estimator being too noisy to move: it moved, and the mean-field
ordering was already the better one at this horizon.


Where the two columns disagree, say so rather than picking one:

- `spike`: ratio mean +0.038 but aggregate -4.2%. The ratio mean is carried by graphs with a gap of one or two errors; across all graphs the policy closed -2 of a 48-error total gap.

