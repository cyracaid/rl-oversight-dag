# Propagation recovery v2: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and a tiny smoke run only.
**No v2 numbers exist and none are asserted here.** The user executes the full runs.

v1 (`PROPAGATION_RECOVERY_PREREG.md`, results and verdict in `PROPAGATION_RECOVERY_V1_INTERPRETATION.md`) did
not pass its gate. Its code and results are unchanged and remain the reference. v2 changes **one** thing, the
source of the children's own source-error rate `b`, and adds a test of the proposed `calibrated` label rule.

## Discipline

Same as v1 and `BOUNDARY_PREREG.md`: every claim traces to saved raw results, configuration and source hashes;
tables are generated from saved JSON; never hide a failed replicate, choose the best seed, overwrite a run or
rewrite a hypothesis after seeing results. Negative results remain results. **Agents run only `--smoke` and unit
tests.** Each output directory must be new. The v2 default seed differs from v1, so the run is independent.

## What changes from v1

| item | v1 | v2 |
|---|---|---|
| source of `b` for E1/E2 | all reviewed root nodes | E2 keeps it (reference); **E3b uses only roots reviewed in a random audit**; E3a uses an external prior |
| review budget per graph | 16 policy reviews | 16 in total: 12 policy reviews + 4 random-audit reviews (`--audit-fraction 0.25`) |
| graphs per replicate | 200 | 800 (v1 had too few usable events) |
| label rules | not evaluated | `width` and `robust` calibrated-label rules evaluated per replicate |

**v2 was designed after seeing the v1 results.** Its choices (audit share, graph count, the `robust` rule, V2-H1) are
not independent of v1; V2-H1 is a replication of a failure already observed, and only a pass on the gate under an
unseen seed is new evidence.

Unchanged: world generator, three edge families (true p 0.30 / 0.60 / 0.85 by child layer), three policies
(`random`, `confidence`, `blast`), catch rate 0.9, 50 replicates, the log contents, the Beta(1,1) posterior with
2,000 draws and a 95% equal-tail interval. Audit nodes are drawn uniformly from the nodes the policy did not pick.

## Estimators

| id | children used | `b` source |
|---|---|---|
| E0 | all children of corrected nodes | none (naive; lower-bound reference) |
| E2 | single-parent, not reviewed before | all reviewed roots (v1 source; expected to fail under `confidence`) |
| E3a | single-parent, not reviewed before | external prior `--prior-b` (default 0.104, the true mean type rate; ablation) |
| E3b | single-parent, not reviewed before | **roots reviewed in the random audit only** |

## Calibrated-label rules (tests the rule proposed in `add-belief-review-ranking`)

- `width`: calibrated iff the 95% interval is narrower than 0.15.
- `robust`: `width` **and** a selection check. For E2: the flag rate of the b source divided by the assumed catch
  must not exceed the prior by more than a factor of 2. For E3b: at least 100 audited roots.

Both rules are reported per cell as the share labelled calibrated and the share of those whose interval misses the
truth (`wrong|cal`).

## Hypotheses

- **V2-H1 (replication).** E2 reproduces the v1 failure under `confidence`: bias above +0.10 in every family.
- **V2-H2 (gate).** E3b is within tolerance in all 3 policies and all 3 families: |bias| ≤ 0.05, coverage ≥ 0.90,
  mean usable events ≥ 100, no missing replicate, and, among replicates labelled calibrated by the `robust` rule,
  at most 5% have an interval that misses the truth.
- **V2-H3 (ablation).** E3a, the same adjustment with an exact external `b`, is also within the V2-H2 tolerances. If
  E3a passes and E3b fails, the failure is noise in estimating `b` from the audit, not the structural adjustment.
- **V2-H4 (label rule).** Under `confidence`, the `width` rule labels E2 calibrated while wrong more than half of the
  time, and the `robust` rule keeps `wrong|cal` at or below 5% for E2 and E3b in every cell.

## Gate

The estimator passes only if **E3b meets V2-H2 in every policy and family**. V2-H1, V2-H3 and V2-H4 are reported
and interpreted but are not part of the gate, **except** that a failure of the `robust` rule (V2-H4 second half) for
E2 or E3b means the proposed `calibrated` rule in the OpenSpec change must be revised before any use.

If the gate fails: the estimator still does not proceed to real records and OpenSpec task 4.1 stays blocked. Do not
relax tolerances; diagnose from the ablation, change one thing, and write a v3 protocol before running.

The tolerances and thresholds are fixed now. They may be revised only before the first v2 full run, and the
revision must be committed with its reason.

## Commands (run from the repository root)

Primary run:

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v2.py --out-dir runs/propagation-recovery-v2
```

Exploratory sensitivity runs (not part of the gate; each in a new directory):

```bash
cd ~/Documents/강화학습
# prior for b is wrong in either direction (true mean 0.104)
python3 -u experiments/rl_propagation_recovery_v2.py --prior-b 0.20 --out-dir runs/propagation-recovery-v2-prior020
python3 -u experiments/rl_propagation_recovery_v2.py --prior-b 0.05 --out-dir runs/propagation-recovery-v2-prior005
# less or more random audit
python3 -u experiments/rl_propagation_recovery_v2.py --audit-fraction 0.125 --out-dir runs/propagation-recovery-v2-audit0125
python3 -u experiments/rl_propagation_recovery_v2.py --audit-fraction 0.5 --out-dir runs/propagation-recovery-v2-audit05
# assumed catch rate wrong (true 0.9, assumed 0.7)
python3 -u experiments/rl_propagation_recovery_v2.py --assumed-catch 0.7 --out-dir runs/propagation-recovery-v2-catch07
# some true changes are not observed
python3 -u experiments/rl_propagation_recovery_v2.py --obs-miss 0.2 --out-dir runs/propagation-recovery-v2-miss02
```

No time estimate is promised: v2 uses four times the graphs of v1. Tiny harness check: `--smoke` (not evidence).

## Reading the output

1. The gate table first, then `missing` and `mean n`.
2. Then bias, RMSE, coverage per policy, estimator and family; quote failures with successes.
3. Compare E2 and E3b under `confidence` (the v1 failure) and use E3a to attribute any remaining error.
4. Compare `wrong|cal.width` and `wrong|cal.robust`; a narrow interval is not evidence of correctness.
5. Check `provenance` (git status, source hashes) before quoting any number.

## What a pass means and does not mean

A pass means: in this synthetic world, with every child re-derived and changes observed exactly, a known catch
rate, known families and a random audit that really is selection-independent, the estimator recovers the
generating propagation probability under non-random review, and the proposed `robust` label rule keeps wrong
estimates from being labelled calibrated. It does **not** show it works on a real audit chain: real audits may not
be random, re-derivation may be partial, observations noisy, families unknown and confounding present. Real
records are never used here, never committed, and are processed locally by the data owner only after the gate
passes and the OpenSpec change is accepted.

## Related

- OpenSpec change `add-belief-review-ranking`: tasks 1.4–1.6 and 4.1; requirements "Propagation estimated from
  audit-chain records", "Base error rate source", "Review selection recorded".
- `PROPAGATION_RECOVERY_V1_INTERPRETATION.md`: why v1 failed (b estimated from selectively reviewed roots).
