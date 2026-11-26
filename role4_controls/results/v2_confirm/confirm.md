# v2 confirmation on fresh block 7100–7199 — results (Person 4)

Pre-registered in commit `c07aedc` (README, "v2 confirmation on a fresh block") before this run.
Command: `python3 run_controls_v2.py --start-seed 7100 --jobs 2 --out results/v2_confirm/`. Same code and rules
as v2 (`7f58534`). Every number below is a cell of `results/v2/controls_v2_summary.csv` (block 90000) or
`results/v2_confirm/controls_v2_summary.csv` (block 7100). Block 7100–7199 is now spent.

## Endpoint — primary cells (`marginal` vs confidence, mean [95 % CI], frozen label)

**11 of 11 primary cells replicated** (same label on both blocks).

| family | control | block 90000–90099 | block 7100–7199 | |
|---|---|---|---|---|
| spike | flatten | +0.09 [+0.03, +0.15] `survives` | +0.15 [+0.08, +0.22] `survives` | replicated |
| spike | rewire_index | -0.97 [-1.18, -0.76] `inconclusive` · worse than confidence | -0.84 [-1.07, -0.62] `inconclusive` · worse than confidence | replicated |
| modular | flatten | +0.01 [-0.10, +0.13] `removed` | -0.01 [-0.18, +0.16] `removed` | replicated |
| modular | rewire_index | -7.19 [-8.15, -6.24] `inconclusive` · worse than confidence | -7.80 [-8.87, -6.78] `inconclusive` · worse than confidence | replicated |
| modular | rewire_order | -7.97 [-8.89, -7.11] `inconclusive` · worse than confidence | -8.97 [-10.12, -7.88] `inconclusive` · worse than confidence | replicated |
| ba | flatten | -0.58 [-0.77, -0.38] `removed` | -0.57 [-0.75, -0.39] `removed` | replicated |
| ba | rewire_index | +6.99 [+1.74, +13.42] `survives` | +14.44 [+7.44, +22.40] `survives` | replicated |
| ba | rewire_order | -19.41 [-25.20, -13.03] `inconclusive` · worse than confidence | -16.08 [-22.48, -8.89] `inconclusive` · worse than confidence | replicated |
| er | flatten | -0.35 [-0.48, -0.23] `removed` | -0.43 [-0.58, -0.29] `removed` | replicated |
| er | rewire_index | +1.54 [+0.40, +2.86] `survives` | +1.33 [+0.35, +2.29] `survives` | replicated |
| er | rewire_order | -11.63 [-13.04, -10.21] `inconclusive` · worse than confidence | -11.94 [-13.59, -10.50] `inconclusive` · worse than confidence | replicated |

As in v2, a CI entirely below −margin is labelled `inconclusive` by the frozen rule; every such cell is marked
"worse than confidence": the wrong map makes `marginal` clearly worse than sort-by-confidence, on both blocks.

## Intact advantage on each block (context, not an endpoint)

| family | block 90000 | block 7100 |
|---|---|---|
| spike | +0.37 [+0.20, +0.56] | +0.35 [+0.20, +0.51] |
| modular | +1.81 [+1.10, +2.56] | +1.47 [+0.84, +2.14] |
| ba | +9.52 [+4.25, +15.99] | +17.25 [+10.15, +25.23] |
| er | +4.99 [+3.52, +6.61] | +4.19 [+3.03, +5.35] |
| real | +0.03 [+0.00, +0.07] | +0.05 [-0.03, +0.14] |

The BA intact gain is larger on 7100 (+17.25) than on 90000 (+9.52); BA graphs vary a lot from graph to graph,
and the 20 % margin scales with each block's own intact gain, as frozen. `real` has no intact advantage on either block.

## Reading (scoped to what was observed)

The v2 labels hold on graphs no run had touched (block 7100–7199 is the confirmation block; 90000–90099 was
the v2 design block). Removing propagation shrinks the advantage to within ±20 % of the intact gain on
modular, BA and ER; on spike a small gain remains. A wrong map makes `marginal` worse than confidence on spike
and modular. With the index rule the gain kept is about 84 % of intact on BA (+14.44 of +17.25) and about 32 % on
ER (+1.33 of +4.19); with the hub-breaking rule it reverses on both. `rewire_order` changes paths and sink
reachability as well as hub rank, so this is consistent with hub information mattering, not a test of hub
rank alone.
