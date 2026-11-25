# Structural controls — results (Person 4)

Run: `python3 run_controls.py --out results/` on branch `p4/role4-controls`. Rules frozen in commit
`af29f1c` (README, "Frozen before outcomes") before any flatten/rewire outcome was computed.
Every number below is a cell of `controls_summary.csv`, `benchmark_worst_of_n.csv` or (section 3)
`diagnostics.csv`, written by `diagnostics.py`.

**Reproduction check passed:** the `intact` condition reproduces `outputs/v3/benchmark_role3.csv`
for all 1,500 shared rows (5 families × 100 graphs × 3 policies) — same sink errors *and* the same
action sequences — and the intact summary rows equal `benchmark_summary.csv`.

## 1. Main table — `marginal` vs sort-by-confidence

`gain` = errors(confidence) − errors(marginal), paired on the same 100 graphs, mean [95 % CI].
Positive = marginal leaves fewer conclusion errors. `removed` = gain(intact) − gain(control).

| family | intact gain | flatten gain | removed by flatten | flatten verdict | rewire gain | removed by rewire | rewire verdict |
|---|---:|---:|---:|---|---:|---:|---|
| spike | +0.37 [+0.20, +0.56] | +0.09 [+0.03, +0.15] | +0.28 [+0.12, +0.46] | `survives` | -0.72 [-1.07, -0.40] | +1.09 [+0.76, +1.46] | `removed` |
| modular | +1.81 [+1.10, +2.56] | +0.01 [-0.10, +0.13] | +1.80 [+1.10, +2.53] | `removed` | -7.15 [-8.17, -6.19] | +8.96 [+7.79, +10.16] | `removed` |
| ba | +9.52 [+4.25, +15.99] | -0.58 [-0.77, -0.38] | +10.10 [+4.80, +16.68] | `removed` | +7.09 [+1.70, +13.54] | +2.43 [+1.55, +3.35] | `survives` |
| er | +4.99 [+3.52, +6.61] | -0.35 [-0.48, -0.23] | +5.34 [+3.90, +6.94] | `removed` | +0.84 [-0.38, +2.15] | +4.15 [+2.81, +5.59] | `removed` |
| real | +0.03 [+0.00, +0.07] | +0.03 [+0.00, +0.08] | +0.00 [-0.05, +0.04] | `no-intact-advantage` | -0.56 [-0.75, -0.38] | +0.59 [+0.42, +0.77] | `no-intact-advantage` |

## 2. What each control rules out

- **flatten** (errors stop travelling; the policy still believes they travel) — on modular, BA and ER
  the advantage disappears or reverses (+0.01, −0.58, −0.35), so there **the gain comes from error
  propagation, not from a better error prior.** On spike it shrinks from +0.37 to +0.09 [+0.03, +0.15]
  and does **not** vanish (`survives`): about a quarter of the spike gain does not need propagation.
- **rewire** (the policy plans on a wrong map of the same size; errors travel on the true graph) — on
  spike and modular a wrong map makes `marginal` clearly *worse* than confidence (−0.72, −7.15), so
  **the gain depends on the true structure, not on any ordering over the same number of nodes.**
  On ER the gain falls from +4.99 to +0.84 [−0.38, +2.15]: not distinguishable from zero, so labelled
  `removed` by the frozen rule, but the point estimate keeps about a sixth of the gain.
- **On BA the advantage survives rewire: +7.09 [+1.70, +13.54], down from +9.52. This is a real problem
  for the claim on BA and is reported as one, not as a pass.**
- **real** is uninformative, as expected before the run: the intact gain is +0.03 [+0.00, +0.07],
  so there is nothing for a control to remove.
- `structural` has no intact advantage on any family (its CI touches or is below zero everywhere),
  so neither control says anything about it. Its rows are in the CSV.

## 3. Post-hoc diagnostics (not pre-registered; hypotheses, not findings)

Numbers from `results/diagnostics.csv` (`python3 diagnostics.py`). Correction: the first version of this
section quoted them from an uncommitted script; they are unchanged, now reproducible.

- **BA rewire.** The frozen rewire draws parents from lower-index nodes, and in BA/ER low index means
  "old node". The rewired map therefore keeps much of *who the hubs are*: median Spearman correlation
  of out-degree, original vs rewired, is 0.63 on BA and 0.62 on ER, against 0.05 on modular (where the
  advantage is removed most completely). A plausible reading is that on BA part of `marginal`'s gain
  comes from hub position, which this rewire preserves. This is untested. (Correction: a degree-preserving
  rewire would keep the hubs *exactly*, so it cannot test this; a rewire that breaks the index–hub link
  can. That is the pre-registered v2 below.)
- **spike flatten.** Without propagation only a conclusion's own error counts. `marginal` spends 31 %
  of its reviews on conclusion nodes, confidence 24 %. A plausible reading is that the surviving
  +0.09 comes from knowing *which nodes are conclusions* — graph information, but not propagation.

## 4. Mean sink errors, all cells

| family | condition | confidence | structural | marginal |
|---|---|---:|---:|---:|
| spike | intact | 1.03 | 1.11 | 0.66 |
| spike | flatten | 0.30 | 0.51 | 0.21 |
| spike | rewire | 1.03 | 2.24 | 1.75 |
| modular | intact | 10.59 | 21.53 | 8.78 |
| modular | flatten | 2.99 | 10.67 | 2.98 |
| modular | rewire | 10.59 | 25.59 | 17.74 |
| ba | intact | 29.65 | 32.24 | 20.13 |
| ba | flatten | 2.89 | 11.55 | 3.47 |
| ba | rewire | 29.65 | 33.40 | 22.56 |
| er | intact | 21.75 | 23.43 | 16.76 |
| er | flatten | 1.08 | 3.92 | 1.43 |
| er | rewire | 21.75 | 27.00 | 20.91 |
| real | intact | 0.50 | 0.57 | 0.47 |
| real | flatten | 0.07 | 0.13 | 0.04 |
| real | rewire | 0.50 | 0.75 | 1.06 |

## 5. worst-of-n — fraction of graphs with at least one conclusion error left

From the frozen `benchmark_role3.csv` (groupby, no rerun); equals `1 − zero_error_rate` in
`benchmark_summary.csv` for every row (checked).

| family | none | random | confidence | hub | structural | marginal | dqn_s1 | gnn_s1 | dqn_s2 | gnn_s2 | dqn_s3 | gnn_s3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| spike | 0.98 | 0.96 | 0.47 | 0.98 | 0.57 | 0.34 | 0.62 | 0.45 | 0.55 | 0.53 | 0.62 | 0.48 |
| modular | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 | 0.99 | — | — | — | — | — | — |
| ba | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — | — | — | — | — | — |
| er | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — | — | — | — | — | — |
| real | 0.96 | 0.88 | 0.30 | 0.93 | 0.33 | 0.28 | — | — | — | — | — | — |


On the 500-node families almost every policy leaves at least one error on almost every graph, so this
measure saturates there; it separates policies only on spike and real. On spike `marginal` leaves an
error on 34 % of graphs against 47 % for confidence; on real 28 % against 30 %.

## 6. Blocked

27/48 consensus split: waiting for P5's labels. Not attempted.
