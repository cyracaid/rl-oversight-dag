# Phase 1 Report — receipts, replay, and recall@minutes

> Every number below is recomputed from the receipts on disk, not from
> the simulator's memory. Synthetic N=21; not the paper's simulator.

## What changed from Phase 0

- A session now writes one `review.receipt.v1` per submission, bound to
  a node and an immutable artifact version.
- `recall@minutes` is computed by joining receipts with the offline truth
  table and re-applying the minute budget from receipt durations.
- Every receipt chain is verified after the run.

## Receipt integrity

- chains written and verified: **360/360**
- coverage (synthetic): known=21, flagged=21, reviewed=15, unreachable=0
- real queue anchor: 17 of 85 broad corrections were never flagged (20%); no ranking can reach them

## Results (20 seeds, paired truth per policy)

| policy | mode | budget (min) | reviews | spent (min) | recall | errors/hour |
|---|---|---:|---:|---:|---:|---:|
| queue order | row | 4 | 3.0 | 3.1 | 0.109 | 11.6 |
| type prior | row | 4 | 3.0 | 3.1 | 0.109 | 11.6 |
| belief greedy | row | 4 | 3.0 | 3.1 | 0.109 | 11.6 |
| queue order | row | 8 | 7.0 | 7.2 | 0.277 | 12.0 |
| type prior | row | 8 | 7.0 | 7.2 | 0.404 | 17.0 |
| belief greedy | row | 8 | 7.0 | 7.2 | 0.404 | 17.0 |
| queue order | row | 16 | 15.0 | 15.5 | 0.499 | 10.1 |
| type prior | row | 16 | 15.0 | 15.5 | 0.819 | 15.9 |
| belief greedy | row | 16 | 15.0 | 15.5 | 0.811 | 15.7 |
| queue order | witness | 4 | 7.0 | 3.6 | 0.277 | 24.1 |
| type prior | witness | 4 | 7.0 | 3.6 | 0.404 | 34.0 |
| belief greedy | witness | 4 | 7.0 | 3.6 | 0.404 | 34.0 |
| queue order | witness | 8 | 15.0 | 7.8 | 0.499 | 20.1 |
| type prior | witness | 8 | 15.0 | 7.8 | 0.819 | 31.7 |
| belief greedy | witness | 8 | 15.0 | 7.8 | 0.811 | 31.4 |
| queue order | witness | 16 | 21.0 | 10.9 | 0.859 | 23.8 |
| type prior | witness | 16 | 21.0 | 10.9 | 0.859 | 23.8 |
| belief greedy | witness | 16 | 21.0 | 10.9 | 0.859 | 23.8 |

## Sample receipt

```json
{
  "node_id": "time_bed",
  "artifact_version": "pipeline-n21-v1",
  "verdict": "corrected",
  "actor_hash": "reviewer:sim",
  "opened_at": "2026-11-10T09:00:00+00:00",
  "submitted_at": "2026-11-10T09:00:31+00:00",
  "field_path": "witness_pair",
  "reason_code": "order_error"
}
```

## Caveats

- The truth table is synthetic and paired by seed; this is a harness test,
  not an estimate of the real queue.
- The reviewer catches a true source error with p=0.9; a missed error is
  recorded as `accepted`, which is why receipts alone never prove truth.
- Re-running the same seed reproduces the same receipts; the chain digest
  is deterministic for the same sequence.
