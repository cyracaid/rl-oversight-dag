# Structural controls v2 — results (Person 4)

Rules: README section **"v2 — frozen before outcomes"**, pushed in commit `7f58534` before this run.
Run: `python3 run_controls_v2.py --jobs 2` (20 min on 2 cores). Every number below is a cell of
`controls_v2_summary.csv`. v1 (`../controls.md`) is unchanged and keeps its own labels.

**Acceptance passed:** `intact` equals the frozen benchmark, and `flatten` and `rewire_index` draw 0
equal v1 `controls.csv`, errors and action sequences, row by row.

## 1. Main table — `marginal` vs sort-by-confidence

gain = errors(confidence) − errors(marginal), paired over 100 graphs; for rewire, each graph's gain is the
mean over its 10 draws. Mean [95 % CI] and the frozen three-level label. Margin m = 20 % of this block's
intact mean gain — the decision threshold of this experiment, not a value from the literature.

| family | intact gain | margin ±20 % | flatten | rewire_index (10 draws) | rewire_order (10 draws) |
|---|---|---:|---|---|---|
| spike | +0.37 [+0.20, +0.56] | ±0.07 | +0.09 [+0.03, +0.15] `survives` | -0.97 [-1.18, -0.76] `inconclusive` · worse than confidence | — |
| modular | +1.81 [+1.10, +2.56] | ±0.36 | +0.01 [-0.10, +0.13] `removed` | -7.19 [-8.15, -6.24] `inconclusive` · worse than confidence | -7.97 [-8.89, -7.11] `inconclusive` · worse than confidence |
| ba | +9.52 [+4.25, +15.99] | ±1.90 | -0.58 [-0.77, -0.38] `removed` | +6.99 [+1.74, +13.42] `survives` | -19.41 [-25.20, -13.03] `inconclusive` · worse than confidence |
| er | +4.99 [+3.52, +6.61] | ±1.00 | -0.35 [-0.48, -0.23] `removed` | +1.54 [+0.40, +2.86] `survives` | -11.63 [-13.04, -10.21] `inconclusive` · worse than confidence |
| real | +0.03 [+0.00, +0.07] | ±0.01 | +0.03 [+0.00, +0.08] `no-intact-advantage` | -0.58 [-0.72, -0.44] `no-intact-advantage` | — |

**How to read `inconclusive` here.** The frozen rule calls a CI that lies entirely *below* −m
`inconclusive`, not `removed` (README, v2 §3). Every `inconclusive` cell in this table is of that kind:
with a wrong map, `marginal` becomes clearly **worse** than sort-by-confidence. We keep the frozen label and
write "worse than confidence" next to it in the table (as P5 asked).

## 2. What v2 shows

- **flatten.** With an equivalence margin the result is sharper than v1: on modular, BA and ER the gain
  under flatten lies inside ±20 % of the intact gain (`removed`). **Without propagation the advantage is
  gone.** On spike a small part survives (+0.09 [+0.03, +0.15], margin ±0.07), as in v1.
- **BA.** Under the index rule the advantage survives on all ten draws (+6.99 [+1.74, +13.42]; every draw
  between +6.58 and +7.26), about **73 %** of the intact gain (+9.52), so v1's single draw was not luck.
  Under the hub-breaking rule it reverses to −19.41 [−25.20, −13.03].
- **ER.** With ten draws the index-rule gain is +1.54 [+0.40, +2.86] (`survives`), about **31 %** of the
  intact gain (+4.99) — a much smaller share than on BA, so the two are not "mostly kept" alike. v1's draw 0
  (+0.84) sits near the low end of the ten draws (+0.50 … +2.34). Under the hub-breaking rule it reverses
  to −11.63 [−13.04, −10.21].
- **What the two rewires do and do not show (BA, ER).** The index rule keeps hub positions (rank correlation
  0.63 / 0.62); the hub-breaking rule removes them (0.01). But `rewire_order` also changes paths and which
  nodes can reach which conclusions, not only hub rank. So the contrast is **consistent with** hub
  information mattering; it does not isolate hub rank as the only cause.
- **spike and modular.** A wrong map makes `marginal` clearly worse under every draw (spike −0.97, modular
  −7.19 with the index rule; modular −7.97 with the hub-breaking rule). The gain needs the true structure.
- **real.** No intact advantage (+0.03 [+0.00, +0.07]); nothing to test, as stated before the run.
- `structural` has no intact advantage on any family; its rows are in the CSV.

**One-line summary (scoped to what was observed).** Removing propagation shrinks the advantage to within
±20 % of the intact gain on modular, BA and ER; on spike a small gain remains. A wrong map makes `marginal`
worse than confidence on spike and modular. A wrong map that keeps hub positions keeps about 73 % of the gain
on BA and about 31 % on ER; one that breaks hub positions reverses it on both — consistent with hub
information mattering, not a test of hub rank alone.

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

- The v2 rules were written after reading v1; they are an amendment, not the original plan. Block 90000–90099
  is the **v2 design block**; block 7100–7199 is the **confirmation block**, run after the rules were frozen
  (`../v2_confirm/confirm.md`).
- `rewire_order` changes paths and sink reachability as well as hub rank (see §2).
- Ten draws per graph; the bootstrap resamples graphs, not draws.
- About a dozen labelled cells, each at 95 % without multiplicity correction.
- The 20 % margin is this experiment's decision threshold, applied to each block's own intact mean gain; it is
  a convention we chose, not a value from the literature.
