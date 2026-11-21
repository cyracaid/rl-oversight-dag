# Propagation recovery v2: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/propagation-recovery-v2/`).
No rerun, no change to the pre-registered hypotheses or gate (`PROPAGATION_RECOVERY_V2_PREREG.md`).

## Integrity

- Source SHA256 of `rl_propagation_recovery_v2.py`, `rl_propagation_recovery.py`, `spike_active_selection.py` and
  `belief.py` in the saved provenance match the current files; run commit `4ec1913`.
- 50 replicates, 800 graphs per replicate, budget 16 (12 policy + 4 audit), assumed catch 0.9, prior b 0.104,
  seed 20261122 (independent of v1). No replicate had a missing estimate. Synthetic data only.
- v2 was designed after seeing v1 (stated in the protocol): only the gate on an unseen seed is new evidence.

## Verdict against the pre-registered gate (E3b): **not passed**

All E3b cells meet the bias tolerance (|bias| ≤ 0.05), mean usable events (minimum 122) and the no-missing
requirement. The gate fails on two other parts:

| failed part | cells |
|---|---|
| coverage ≥ 0.90 | `confidence`, all three families (0.82, 0.72, 0.40) |
| robust-label wrong rate ≤ 0.05 | 7 of 9 cells (see below) |

| hypothesis | result |
|---|---|
| V2-H1 E2 reproduces the v1 failure under `confidence` (bias > +0.10) | **Supported**: +0.209, +0.389, +0.150 |
| V2-H2 gate | **Not passed** |
| V2-H3 E3a (exact external prior) within tolerance | **Not supported**: under `confidence` coverage is 0.94, 0.82, 0.50 |
| V2-H4 width rule accepts wrong E2 under `confidence` | **Supported**: labelled calibrated 98–100% of the time, wrong 100% |
| V2-H4 `robust` rule keeps wrong-given-calibrated ≤ 5% for E2 and E3b | **Not supported** (E3b under `confidence`: 0.18, 0.28, 0.60) |

Consequence under the protocol: the estimator does not proceed to real records, OpenSpec task 4.1 stays
blocked, and because the `robust` label rule failed, the `calibrated` rule in the OpenSpec change must be revised
before any use. Tolerances are not relaxed.

## What went right

- Under `random` and `blast` review, E2, E3a and E3b all recover the truth: biases within ±0.011, coverage 0.92–0.98
  (random family 3: 0.92–0.96), with 122–457 usable events per family. The v1 sample-size problem is solved.
- The v1 failure mechanism is confirmed. Under `confidence`, the root flag rate used by E2 gives b̂ = 0.453 against
  a true 0.104, and E2 is biased by +0.150 to +0.389 with narrow, wrong intervals.
- The `robust` rule's selection check did block E2 under `confidence`: it was never labelled calibrated there
  (flag rate 4.4 times the prior).
- The naive estimator E0 is biased low in every cell (−0.023 to −0.166) and its intervals are narrow, so a width-only
  rule labels it calibrated while it is wrong (36–100% under `random`).

## What went wrong, with the cause identified from the saved counts

**1. The audit was not selection-independent.** v2 drew audit nodes uniformly from the nodes the policy did not pick.
Under `confidence`, the policy removes the most likely wrong nodes first, so what is left is depleted of errors:

| policy | audit-root b̂ | all-reviewed-root b̂ | true mean b |
|---|---:|---:|---:|
| random | 0.105 | 0.105 | 0.104 |
| confidence | **0.017** | 0.453 | 0.104 |
| blast | 0.096 | 0.115 | 0.104 |

E3b therefore divides by (1 − 0.017) instead of about (1 − 0.104) and is biased low (−0.017, −0.029, −0.038).
This is a design flaw in the v2 audit draw, not in the idea of a random audit. The `robust` selection check for
E3b (at least 100 audited roots) could not see it because it only counted roots.

**2. A second selection effect remains even with an exact b.** E3a, with the true prior, is positively biased under
`confidence` (+0.010, +0.026, +0.039; coverage 0.94, 0.82, 0.50) but not under `random` or `blast`. A plausible
cause, not tested here: children not yet reviewed under a confidence-ordered policy are those the policy
considered less likely to be wrong, so their own error rate is below the population b used in the adjustment.
Nothing in this run isolates it.

**3. The robust-label criterion is noise-sensitive as pre-registered.** "At most 5% wrong among labelled
replicates" is evaluated on few replicates (for example 3 of 50 in `random` family 3) and a correct 95% interval
misses the truth about 5% of the time, so with 50 replicates the observed rate exceeds 5% about half the time by
chance alone (`blast` E3b: 0.08, 0.08, 0.07 with coverage 0.92 in each family). Part of the 7 failures is Monte Carlo noise and
part is real (`confidence`). The criterion should have had a noise allowance; it is not changed here.

**4. Interval width is a poor calibration signal even under random review.** Estimates closer to the boundary have
narrower intervals, so conditioning on narrow width selects replicates that are more often wrong
(`random` family 3, E3b: 0.67 wrong among the 6% labelled). This is a hypothesis consistent with the numbers.

## Design implications for the OpenSpec change (to be recorded)

- A "random spot check" must sample from the **full eligible set before any policy selection**, and record each
  review's **inclusion probability**. Sampling "among the remaining nodes" is not random.
- A deterministic risk-ranked policy gives unreviewed nodes inclusion probability 0 or 1, so selection effects cannot
  be corrected afterwards; keeping a randomised review share with logged inclusion probabilities is necessary for
  any later estimation from the logs.
- The selection check must verify the sampling frame (and compare the audit flag rate with the prior), not only the
  number of audited roots.
- Label rules must not rely on interval width; width is also confounded with where the estimate lies.

## What this does and does not show

It shows, in this synthetic world, that a random audit helps only if it is truly selection-independent, that the
failure modes are identifiable from logged counts, and that the proposed `robust` rule needs a stronger selection
check. It does not show the estimator fails in general: under random and blast-radius review it recovers the truth.
All protocol idealisations still apply; the sensitivity runs were not run.

## Next

A v3 protocol, written and frozen before running: draw the audit **first, uniformly from all nodes**, then let the
policy choose among the rest; strengthen the selection check to verify the sampling frame; replace the 5% criterion
with a noise-aware one; keep E3a as the ablation and add a test for the residual child-selection effect. v1 and v2
results stay as they are.
