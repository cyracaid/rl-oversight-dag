# Propagation recovery v1: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/propagation-recovery-v1/`).
No rerun, no change to the pre-registered hypotheses or gate (`PROPAGATION_RECOVERY_PREREG.md`).

## Integrity

- Source SHA256 of `rl_propagation_recovery.py`, `spike_active_selection.py` and `belief.py` in the saved
  provenance match the current files; the run's commit is `5109063`.
- 50 replicates, 200 graphs per replicate, budget 16, assumed catch 0.9, true catch 0.9, no observation miss.
  No replicate had a missing estimate. Synthetic data only.

## Verdict against the pre-registered gate: **not passed**

| item | result |
|---|---|
| H1: E0 biased low in every family under `random` | **Supported**: bias −0.040, −0.085, −0.174 |
| H2: E2 under `random` within tolerance (|bias| ≤ 0.05, coverage ≥ 0.90) | Bias +0.016, −0.021, −0.017 and coverage 0.94, 1.00, 0.94 meet the tolerances, **but mean usable events are 35, 33, 31 (< 100), so the sample criterion fails** |
| H3: E2 stays within tolerance under `confidence` and `blast` | `blast`: holds (bias +0.022, −0.008, +0.011; coverage 0.94). **`confidence`: refuted** (bias +0.261, +0.387, +0.150; coverage 0.00) |
| Gate: E2 within tolerance in all 3 policies and all 3 families with mean_n ≥ 100 | **Fails** (confidence; random all families; blast family 3 has mean_n 67) |

Consequence under the protocol: the estimator does not proceed to real records and OpenSpec task 4.1 stays
blocked. The tolerances are not relaxed. The `random` shortfall in events is addressed by more graphs in a
new run; the `confidence` failure is not a sample-size problem.

## Why `confidence` fails: the base-error-rate estimate, not the propagation signal

E1 and E2 divide the change rate by (1 − b̂), where b̂ is estimated from reviewed root nodes.

| policy | root flag rate | b̂ (catch 0.9) | true mean base error rate |
|---|---:|---:|---:|
| random | 0.097 | 0.107 | 0.104 |
| blast | 0.105 | 0.116 | 0.104 |
| confidence | 0.434 | 0.483 | 0.104 |

The confidence policy reviews the nodes most likely to be wrong, so reviewed roots are a biased sample for
the base error rate; b̂ is inflated about 4.6 times and the adjustment pushes estimates up (family 3 reaches
the cap of 1.000). The pre-registered concern that selection changes which children were already cleared (what E2
removes relative to E1) was not the dominant effect: E1 and E2 are nearly identical in every policy. E0, which
does not adjust, is only mildly biased under `confidence` (−0.021, −0.055, −0.108).

## A second finding: narrow intervals can be wrong

Under `confidence`, E1/E2 mean interval widths are 0.272/0.279, 0.076/0.079 and 0.000/0.000 while coverage is
0.00 in every family. A narrow interval is therefore not evidence of correctness. A rule that marks an estimate
calibrated because its interval is narrow would have accepted these wrong estimates.

## What this does and does not show

- It shows that, in this synthetic world, estimating the base error rate from selectively reviewed nodes breaks
  the adjusted estimators, and that interval width alone cannot certify calibration.
- It does not show the estimator is unusable in general: the `random` and `blast` runs are within tolerance
  on bias and coverage apart from the event-count shortfall, and the failing component (b̂ source) is identified.
- All idealisations in the protocol still apply (children re-derived and changes observed exactly, known catch
  rate, known families). The sensitivity runs (`--assumed-catch`, `--obs-miss`, `--true-catch`) were not run.

## Next

A v2 protocol, written and frozen before running, with a base-error-rate source that does not depend on
selectively reviewed nodes (for example reviews drawn at random, or an external type prior), more graphs so that
each family has at least 100 usable events, and the same gate. v1 results stay as they are.
