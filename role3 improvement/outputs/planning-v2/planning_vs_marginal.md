# Depth-two planning against the one-step rule, block 5200-5399

Pre-registration: `PREREGISTER_PLANNING_V2.md`. Verdict code: `report_planning.py`.

`marginal` and `oracle` share rule, budget and horizon, so their gap is the value of truth under a *one-step* rule and cannot contain the value of planning. This experiment changes the policy instead of the prior: a depth-two expectimax on the same mean-field model, width 6 then 4, using only public inputs.

| family | marginal | oracle | gap | policy | mean errors | recovery [95% CI] | aggregate closed | W/T/L | verdict |
|---|---:|---:|---:|---|---:|---|---:|---|---|
| modular | 8.915 | 4.300 | 923 | `plan2_catch` | 8.940 | -0.009 [-0.023, +0.001] | -5 | 2/191/7 | informational |
| modular | 8.915 | 4.300 | 923 | `plan2_full` | 11.340 | -0.833 [-1.071, -0.621] | -485 | 10/82/108 | informational-strong |
| spike | 0.860 | 0.615 | 49 | `plan2_catch` | 0.855 | +0.031 [+0.000, +0.094] | +1 | 1/199/0 | informational |
| spike | 0.860 | 0.615 | 49 | `plan2_full` | 2.155 | -1.188 [-1.646, -0.755] | -259 | 1/76/123 | informational-strong |

## How to read the two variants

- `modular`: `catch` -0.009, `full` -0.833. The two variants do not separate: the miss branch is not what moves the result.
- `spike`: `catch` +0.031, `full` -1.188. The two variants do not separate: the miss branch is not what moves the result.

## What this settles and what it does not

Together with `outputs/value-v1/` (the one-step value estimate, sampled exactly, is worse) and `outputs/belief-v1/` (the belief's numbers, rescaled with ranking held fixed, give nothing), this leaves the gap with no cheap explanation left: not the score's numbers, not the probability scale, and — at this width and this depth — not the horizon.

The honest residual is information. The public belief ranks the truth at about 0.96 AUC, not 1.0, and the review decision needs the *mass* on the right nodes, not just the order. Nothing here measures how much of the gap a better belief could remove; that would need a belief with more information, which the confidence channel does not provide.

Limits, stated because the numbers are easy to over-read: depth two with width 6/4 is a truncated greedy planner, not an optimal policy, so `informational` means 'one more step at this width does not pay', not 'no plan exists'. The two families tested are `modular` and `spike`; `ba` and `er` are not measured.

