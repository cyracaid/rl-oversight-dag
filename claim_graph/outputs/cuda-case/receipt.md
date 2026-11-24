# Review coverage receipt — CUDA case

Case `zx070326-hash/sciforge-lean-cuda-cases` at commit `2538d5716c065cb290e8851910da210afb6f1ff5`.
Table digests: `comparisons` 93a71d3b6904, `metrics` 87ddd3d00ba4, `raw_numbers` e47938c8ce4c
1728 of 2016 claims had their per-batch
ratios rebuilt bit-exactly from the raw batch table before use. The rest are
within-method contrasts, whose ratios the raw table does not contain.

## Inventory

- claims: **2016** across 72 cells, 7 contrast types, 5 metrics
- presented as supported by the case's own screen: 1057
- weak (at least one batch on the other side of unity): **1112**
- weak and presented: **230**
- weak but filtered out by the screen: 882

Batches on the minority side of unity: 0 → 904, 1 → 542, 2 → 570

### Where the case's own screen puts each claim

| | unanimous | weak |
|---|---:|---:|
| presented | 827 | 230 |
| filtered out | 77 | 882 |

70 of the 77 filtered-but-stable claims were dropped
for measurement spread above 5 percent, not for direction. The two criteria
are not separable from these tables alone, so the rejected column says what
the screen did, not what it should have done.

## Coverage by budget

Share of weak *presented* claims inspected. A review spent on a stable
claim is a wasted review under this budget model.

| budget | cell_diverse | queue | random | spread | stability |
|---:|---:|---:|---:|---:|---:|
| 8 | 3.5% | 1.3% | 0.4% | 1.7% | 3.5% |
| 16 | 7.0% | 1.7% | 1.3% | 2.6% | 7.0% |
| 32 | 13.5% | 3.5% | 2.6% | 4.3% | 13.9% |
| 64 | 27.0% | 4.8% | 4.8% | 9.1% | 27.8% |
| 128 | 48.7% | 13.9% | 10.4% | 17.8% | 55.6% |

## What this receipt does not say

- It does not say a weak claim is wrong. Fewer than five batches agreeing
  means the reported ratio hides a disagreement; it does not mean the
  authors erred, and this file must not be quoted as an error count.
- It does not cover `D/P` contrasts by independent recomputation. Those
  ratios are within a method, so only the published per-batch values were
  available; the recomputation check applies to the A/B contrasts.
- It does not model what a re-measurement would cost in wall clock. The
  budget is a count of claims, which is the unit a reviewer chooses.
