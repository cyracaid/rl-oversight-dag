# Structural controls v2 — results (Person 4)

Rules: README section **"v2 — frozen before outcomes"**, pushed in commit `7f58534` before this run.
Run: `python3 run_controls_v2.py --jobs 2` (20 min on 2 cores). Every number below is a cell of
`controls_v2_summary.csv`. v1 (`../controls.md`) is unchanged and keeps its own labels.

**Acceptance passed:** `intact` equals the frozen benchmark, and `flatten` and `rewire_index` draw 0
equal v1 `controls.csv`, errors and action sequences, row by row.

## 1. Main table — `marginal` vs sort-by-confidence

gain = errors(confidence) − errors(marginal), paired over 100 graphs; for rewire, each graph's gain is the
mean over its 10 draws. Mean [95 % CI] and the frozen three-level label.

| family | intact gain | margin ±20 % | flatten | rewire_index (10 draws) | rewire_order (10 draws) |
|---|---|---:|---|---|---|
| spike | +0.37 [+0.20, +0.56] | ±0.07 | +0.09 [+0.03, +0.15] `survives` | -0.97 [-1.18, -0.76] `inconclusive` | — |
| modular | +1.81 [+1.10, +2.56] | ±0.36 | +0.01 [-0.10, +0.13] `removed` | -7.19 [-8.15, -6.24] `inconclusive` | -7.97 [-8.89, -7.11] `inconclusive` |
| ba | +9.52 [+4.25, +15.99] | ±1.90 | -0.58 [-0.77, -0.38] `removed` | +6.99 [+1.74, +13.42] `survives` | -19.41 [-25.20, -13.03] `inconclusive` |
| er | +4.99 [+3.52, +6.61] | ±1.00 | -0.35 [-0.48, -0.23] `removed` | +1.54 [+0.40, +2.86] `survives` | -11.63 [-13.04, -10.21] `inconclusive` |
| real | +0.03 [+0.00, +0.07] | ±0.01 | +0.03 [+0.00, +0.08] `no-intact-advantage` | -0.58 [-0.72, -0.44] `no-intact-advantage` | — |

**How to read `inconclusive` here.** The frozen rule calls a CI that lies entirely *below* −m
`inconclusive`, not `removed` (README, v2 §3). Every `inconclusive` cell in this table is of that kind:
with a wrong map, `marginal` becomes clearly **worse** than sort-by-confidence. The advantage is not just
gone; the wrong map actively misleads it. We keep the frozen label and state the direction.

## 2. What v2 shows

- **flatten.** With an equivalence margin the result is sharper than v1: on modular, BA and ER the gain
  under flatten lies inside ±20 % of the intact gain (`removed`). **Without propagation the advantage is
  gone.** On spike a small part survives (+0.09 [+0.03, +0.15], margin ±0.07), as in v1.
- **BA — the v1 problem is explained, not dissolved.** Under the index rule the advantage survives on all
  ten draws (+6.99 [+1.74, +13.42]; every draw between +6.58 and +7.26), so v1's single draw was not luck.
  Under the hub-breaking rule it reverses to −19.41 [−25.20, −13.03]. **On BA the gain rests on knowing who
  the hubs are; with the hub information removed, a wrong map makes `marginal` much worse.** That is still
  graph information, but at the level of hubs, not of exact edges. We report the index-rule survival as
  what it is: the exact wiring is not what BA's gain needs.
- **ER — v1's `removed` was a single low draw.** With ten draws the index-rule gain is +1.54 [+0.40, +2.86]
  (`survives`); v1's draw 0 (+0.84) sits near the low end of the ten draws (+0.50 … +2.34). Under the
  hub-breaking rule it reverses to −11.63 [−13.04, −10.21]. Same story as BA, weaker.
- **spike and modular.** A wrong map makes `marginal` clearly worse under every draw (spike −0.97, modular
  −7.19 with the index rule; modular −7.97 with the hub-breaking rule). The gain needs the true structure.
- **real.** No intact advantage (+0.03 [+0.00, +0.07]); nothing to test, as stated before the run.
- `structural` has no intact advantage on any family; its rows are in the CSV.

**One-line summary.** The advantage of graph-aware review comes from error propagation (flatten removes it
on every 500-node family) and from the true structure (a wrong map hurts); on BA and ER the part of the
structure that matters is who the hubs are, not the exact edges.

## 3. Draw-to-draw variation (rewire)

| family | rule | 100-graph mean gain, lowest … highest of the 10 draws | within-graph SD (across draws) | between-graph SD |
|---|---|---|---:|---:|
| spike | rewire_index | -1.30 … -0.72 | 1.47 | 1.50 |
| modular | rewire_index | -7.64 … -6.82 | 3.22 | 7.37 |
| modular | rewire_order | -8.67 … -7.28 | 4.43 | 7.34 |
| ba | rewire_index | +6.58 … +7.26 | 2.88 | 28.98 |
| ba | rewire_order | -25.37 … -16.19 | 23.11 | 35.28 |
| er | rewire_index | +0.50 … +2.34 | 4.44 | 7.95 |
| er | rewire_order | -12.28 … -10.75 | 4.97 | 6.84 |
| real | rewire_index | -0.69 … -0.48 | 0.59 | 0.82 |

Within-graph SD is the spread of a policy's errors across the ten rewires of the same graph; between-graph
SD is the spread across graphs of its draw-averaged errors. Between-graph SD is the larger of the two in
every row, but not by much on spike (1.47 vs 1.50) and on BA `rewire_order` (23.11 vs 35.28): there a
single draw per graph, as in v1, would have been noticeably noisier. The 100-graph mean, however, moves
little from draw to draw except on BA `rewire_order` (−25.37 … −16.19) and ER `rewire_index`.

## 4. Limits

- The v2 rules were written after reading v1; they are an amendment, not the original plan.
- Ten draws per graph; the bootstrap resamples graphs, not draws.
- About a dozen labelled cells, each at 95 % without multiplicity correction.
- The 20 % margin is a convention we chose, not a value from the literature.
