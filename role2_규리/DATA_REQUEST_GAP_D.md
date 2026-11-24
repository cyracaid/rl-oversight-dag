# Gap D — what to export so the error model stops being invented

Written 2026-11-24. `CROSS_IMPLEMENTATION_VALIDATION.md` §7 still lists Gap D: *no measured
confidence signal*. The harness that will consume it now exists —
`role2_규리/signal_calibration_real.py` — so the only remaining blocker is the data.

## Why this is the one gap that matters

`dag_role3.environment.initial_belief` uses three numbers that were chosen, not measured:

```python
mu_err, mu_good, sigma = -1.5, +1.5, 1.2
bias = -0.4 * (prior - 0.15)
```

Every result in the paper — the rule's lead, the corruption boundary, the gate's two
failure modes, the per-node and per-graph repairs — sits downstream of those constants.
A reviewer is entitled to ask what happens when they are wrong, and today the honest
answer is "we measured the sensitivity to a *simulated* perturbation, not to a real one".

## What to export

One row per **audited** node in one record. CSV, UTF-8, no participant identifiers.

| column | type | meaning | required |
|---|---|---|---|
| `record_id` | string | pseudonymous record key, stable per row | yes |
| `node` | string | pipeline node name, must match the N=21 DAG (`experiments/real_pipeline_graph.py`) | yes |
| `node_type` | string | one of the six error types (`order_error`, `awake_getup_diff_error`, `bed_sleep_diff_error`, `sleep_awake_equal_error`, `sleep_awake_24h_error`, `metric_spike`) | yes |
| `confidence` | float in (0,1) | the score the pipeline emitted **before** any human touched it | yes |
| `is_error` | 0/1 | human verdict: 1 = the value was wrong | yes |
| `audited_by` | string | `human:<initials>` — used to reject simulated rows | yes |
| `review_seconds` | float | wall-clock time the reviewer spent on this node | optional, unlocks cost |

`confidence` may be the existing binary `suspicion()` flag or any continuous score the
package already produces; the fit only needs it to be the score that was available
**before** review. If the node emits nothing, leave the record out rather than filling
a constant.

## The trap that would waste the export

Exporting only the 75 corrected rows gives a dataset with **no negatives**, and a
calibration fitted on positives alone is not a calibration. The export must include
audited nodes that were **found correct**, sampled at a stated rate, so the base rate is
recoverable. Recommended: for every record, audit a random 5-node sample plus every
flagged node, and record the sampling rule in the manifest.

## Minimum

| requirement | value | why |
|---|---|---|
| audited node-reviews | **≥ 200** | 75 corrections is enough to report, not to deploy |
| distinct records | ≥ 30 | the bootstrap must resample records, not nodes |
| both classes present | ≥ 20 each | AUC is undefined otherwise |
| types represented | ≥ 4 of 6 | the per-type fit is the part that replaces the prior bias |

The script refuses to run below 30 rows and warns below 200, so an underpowered export
cannot quietly become a claim.

## What it unlocks, and what it can destroy

**Unlocks.** Fitted `mu_err / mu_good / sigma` replace the constants;
`results/calibration-v1/calibration.json` lands in the manifest; the §3 claim "per-node
scheduling is saturated" moves from simulation to a measured base rate; the corruption
study gets a real error distribution to corrupt.

**Can destroy.** If the fitted AUC against human verdicts is near 0.5, the confidence
signal carries no information on real data, and the whole signal-trust line is void
outside the simulator. That is a real possibility and should be written down before the
data arrives — see `signal_calibration_real.py --human-audited`, which will report it
without softening.

## Ownership and boundary

The data belongs to the sleep collaboration (Maia ten Brink, Stanford Psychophysiology
Lab). Aggregate-only reporting per `TRACKS.md`; IRB decides what may leave the lab. This
request asks for a de-identified node-level table, nothing else. No participant
identifiers, no raw `*.rds`, nothing committed to the repo — the CSV stays local and only
`calibration.json` + `calibration.md` are committed.

## Run once the file exists

```bash
cd role2_규리
python3 signal_calibration_real.py --csv /path/to/audit_nodes.csv \
    --human-audited --out results/calibration-v1
```

Then quote it as `role2_규리/results/calibration-v1/` in the canonical table, and delete
the Gap D bullet from §7 of `CROSS_IMPLEMENTATION_VALIDATION.md`.

---

## 2026-11-24 update — the ask is narrower than "more negatives"

The all-positive trap was measured, not assumed: `experiments/REAL_CONFIDENCE_RANKING.md`
replays the 53 usable corrections and asks whether the pipeline's own signal ranks the
wrong node above the right ones inside a record. Pooled AUC is 0.807, but on the four raw
timestamps it is **0.569**, and the top-ranked node is a downstream sink in 51 of 53
records. The signal is consequence-driven.

So the export above is still needed for a *record-level* calibration, and the minimum
counts stand. It is **not** sufficient for node-level localisation: that additionally
needs direct evidence on the raw timestamps (`raw_field` / `raw_confidence` /
`raw_source`). Fillable template and sampling rule: `AUDIT_SHEET_TEMPLATE.md`.
