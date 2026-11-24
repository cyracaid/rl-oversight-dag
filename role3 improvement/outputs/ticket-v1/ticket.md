# ticket-v1 — hypothetical ticketing pipeline (synthetic)

Built 2026-11-24. **Not a real ticketing dataset.** No ticket records exist in this
repository and none were used. Topology is fixed; error rates are a stated prior.

## What it is

A 21-node, 4-stage ticket pipeline, structurally parallel to `real` (sleep):

| Stage | Nodes | Count |
|---|---|---:|
| Collect (raw fields) | created / first_response / resolved timestamps, reporter, channel, priority, queue, SLA policy, assignee | 9 |
| Preprocess (derived) | `response_minutes`, `resolution_minutes`, `priority_norm`, `assignee_team`, `sla_target_minutes` | 5 |
| Analyze (metrics) | `response_ratio`, `resolution_ratio`, `breach_minutes` | 3 |
| Conclude (sinks) | `ticket_validity`, `priority_consistency`, `sla_compliance`, `assignment_validity` | 4 |

Type mapping uses the same six-type scheme as `real`:

| Type | Meaning on tickets | Prior |
|---|---|---:|
| 0 `order_error` | resolved before created; negative first response | 0.35 |
| 1 `duration_error` | negative / unit-mixed duration | 0.15 |
| 2 `mapping_error` | priority or queue→team mapping wrong | 0.12 |
| 3 `policy_error` | wrong SLA policy version, target off by 2× | 0.10 |
| 4 `ratio_spike` | ratio > 10, NaN | 0.08 |
| 5 `zero_equal_error` | created=resolved treated as valid | 0.05 |

Review budget **8 / 21**, matching the `real` setting. `spike` uses 16, so ticket
and spike means are not comparable.

## Result

Command:

```bash
cd "role3 improvement"
python3 run_benchmark.py --families ticket --seeds 100 --start-seed 90000 --out outputs/ticket-v1
```

100 held-out graphs, seeds 90000–90099, paired episodes.

| policy | mean sink errors | zero-error rate | vs confidence |
|---|---:|---:|---|
| none | 1.87 | 0.11 | −1.55 [−1.79, −1.33] |
| random | 1.39 | 0.22 | −1.07 [−1.29, −0.86] |
| hub | 1.29 | 0.21 | −0.97 [−1.16, −0.79] |
| confidence | 0.32 | 0.77 | — |
| structural | 0.30 | 0.78 | +0.02 [−0.02, +0.08] |
| marginal | **0.29** | **0.79** | +0.03 [0.00, +0.08] |

Differences are `confidence − policy`, so positive is better.

## Interpretation

- On the ticket structure, **the graph-aware rule does not clearly beat confidence
  ordering**: +0.03 sink errors with 98 ties in 100 graphs. The interval touches 0.
- This is the opposite of `spike` (marginal 0.66 vs confidence 1.03) and weaker than
  `real` (+0.03 [0.00, 0.07], 8 seeds). It matches the `real` pattern: on small,
  shallow, hand-built graphs a good confidence threshold is hard to beat.
- The honest sentence: *on a hypothetical ticketing pipeline, the marginal-value rule
  ties static confidence ordering; we do not claim a cross-domain advantage.*

## Boundaries

- No ticket data, no measured per-stage error rate; the prior is assumed.
- Only the six public rules were run. No learned policy: checkpoints are keyed by
  family and were not trained on this graph.
- Single topology, 100 graphs. No seed-level replication beyond that.
- Ticket numbers must not be averaged with `real` or `spike`.

## Reproduce

```bash
cd "role3 improvement"
python3 -m unittest discover -s tests          # 27 tests, includes ticket DAG invariants
python3 run_benchmark.py --families ticket --seeds 100 --start-seed 90000 --out outputs/ticket-v1
```

Artifacts: `benchmark_role3.csv` (per graph × policy), `benchmark_summary.csv`, plots.
