# Propagation recovery v4: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/propagation-recovery-v4/`).
No rerun, no change to the pre-registered hypotheses or gate (`PROPAGATION_RECOVERY_V4_PREREG.md`).
Two runs: the primary run (`runs/propagation-recovery-v4/`, run commit `07e6483`) and the miscalibration control
(`runs/propagation-recovery-v4-miscal/`, `--post-shift 1.5`, run commit `193b7ec`), both read here with provenance
matching the current sources. **Overall verdict: v4 not passed** (V4-H2 failed on the primary run); **the
miscalibration control passed.**

## Integrity

- Source SHA256 of `rl_propagation_recovery_v4.py`, `_v3.py`, `_v2.py`, `rl_propagation_recovery.py`,
  `spike_active_selection.py` and `belief.py` in the saved provenance match the current files; run commit `07e6483`.
- 150 replicates, 800 graphs per replicate, budget 16 (12 policy + 4 audit, audit drawn first), assumed catch 0.9,
  prior b 0.104, seed 20261124 (independent of v1–v3). No replicate had a missing estimate. Synthetic data only.
- v4 was designed after seeing v1–v3 (stated in the protocol): only the gate on an unseen seed is new evidence.

## Verdict against the pre-registered gate: **not passed**, but the gated estimator itself passes

| hypothesis | result |
|---|---|
| **V4-H1** E4 in all 9 cells: \|bias\| ≤ 0.05, coverage ≥ 0.90, mean n ≥ 100, no missing, calibrated rate ≥ 0.80, Wilson ub ≤ 0.20 | **Supported in all 9 cells** (table below) |
| **V4-H2** E3b label: ≤ 0.10 under `confidence`; ≥ 0.80 under `random` and `blast` | **Not supported**: refusal under `confidence` works (0.03, 0.01, 0.01) but acceptance under `random` (0.70, 0.67, 0.71) and `blast` family 3 (0.73) is below 0.80; `blast` families 1 and 2 pass (0.83, 0.81) |
| V4-H3 miscalibration control (`--post-shift 1.5`): E4 calibrated rate ≤ 0.10 in all 9 cells | **Supported**: 0.00 in all 9 cells (see below) |
| V4-H4 posterior calibration check passes in ≥ 95% of replicates (primary) and ≤ 5% (shifted) | **Supported**: 1.00 under all three policies in the primary run; 0.00 under all three with the shift |
| V4-H5 hidden child base-error rate under `confidence` below 0.09 | **Supported**: 0.064 / 0.063 / 0.063 (random 0.102–0.103, blast 0.097–0.105; population 0.104) |

E4 (the estimator under the gate), by policy and family 1 / 2 / 3:

| policy | bias | coverage | mean n | calibrated rate | wrong\|cal Wilson ub95 |
|---|---|---|---|---|---|
| random | +0.003 / +0.000 / +0.002 | 0.93 / 0.93 / 0.92 | 133 / 130 / 120 | 0.99 / 0.98 / 0.92 | 0.12 / 0.12 / 0.13 |
| confidence | +0.001 / +0.002 / −0.001 | 0.96 / 0.96 / 0.98 | 594 / 584 / 551 | 1.00 / 1.00 / 1.00 | 0.08 / 0.08 / 0.06 |
| blast | +0.001 / −0.001 / +0.000 | 0.94 / 0.94 / 0.94 | 458 / 364 / 180 | 1.00 / 1.00 / 1.00 | 0.11 / 0.11 / 0.11 |

## What this shows

1. **A posterior-conditioned estimator recovers the propagation probability under all three review policies on an
   unseen seed.** Bias is within 0.003 in every cell, coverage 0.92–0.98, and under confidence-ordered review (the case
   where the population-b estimators fail, E3b bias +0.015 / +0.029 / +0.037, coverage 0.88 / 0.81 / 0.63) E4 is
   unbiased. The v3 near-miss (coverage 0.89 in one cell at 100 replicates) did not recur at 150 replicates.
2. **The posterior calibration check is not a false alarm source here**: it passed in 100% of replicates under every
   policy when the logged posterior is calibrated. Whether it detects a miscalibrated posterior is what the unrun
   control answers.
3. **The balance check does its job where the bias is real.** Under `confidence` it refuses E3b/E3a/E2 almost always
   (calibrated rate 0.01–0.03; E2 additionally 0.00 by its flag-rate check). The mean ratio of the children's posterior
   to the audited roots' posterior is 0.62 there (sd 0.08), against 0.94–1.02 under `random` and `blast`.

## Miscalibration control (separate run): passed

With the logged posterior shifted by +1.5 on the logit scale (ranking unchanged), the audited roots' observed base-error
rate is 0.102–0.105 while their mean logged posterior is 0.167–0.170. The posterior calibration check passes in 0.00 of
replicates under all three policies, and the E4 label is refused in all nine cells (calibrated rate 0.00). Refusing was
right: E4 is biased there (+0.027 / +0.046 / +0.068 under `random`, +0.022 / +0.044 / +0.060 under `confidence`,
+0.023 / +0.045 / +0.065 under `blast`; coverage as low as 0.09), growing with the true propagation probability as
anticipated in the protocol. So the check detects a posterior miscalibration large enough to matter, and the shift
size chosen before the run (1.5, with 0.8 deemed too weak to matter) behaved as intended.

A side finding: the balance check uses the same logged posterior, so a miscalibrated posterior also degrades it. Under
`confidence` the biased E3b label rate rose from 0.01–0.03 (calibrated posterior) to 0.22–0.25 (shifted), i.e. the check
refuses the biased estimator much less reliably when the posterior is wrong. Another reason to drop the population-rate
path and to gate any use of the posterior on its calibration.

## What went wrong: the balance check is noise-limited

Under `random` and `blast` the unbiased population-b estimators are labelled calibrated only 67–83% of the time. The
saved data show why: the balance ratio is centred on 1 (mean 0.94–1.02) but has a standard deviation of 0.20 (random,
120–133 events per family) to 0.14–0.19 (blast, 180–458 events), because the children's mean posterior is computed from
a few hundred values of a skewed variable. A fixed band of [0.8, 1.25] therefore rejects 22–31% (random) and 17–27%
(blast) of replicates whose estimate is correct. These are false refusals (safe but wasteful), not false acceptances.
The band was pre-registered and is not changed here. Nothing in this run indicates that a population-b estimator was
accepted while biased.

## Design implications for the OpenSpec change (to be recorded)

- **Make the posterior-conditioned estimator the single canonical one.** E4 passes everywhere without a base-error-rate
  source, so the population-b path (random audit as b source, flag-rate check, balance check) is no longer needed for
  estimation. The random audit is still required, now for the **posterior calibration check**. This also removes a
  parallel path, consistent with the repository's one-canonical-path rule.
- **Check checks against their own sampling noise.** A fixed-ratio band mislabels correct estimates when it is evaluated on
  a few hundred observations. A balance or calibration check should refuse on evidence (for example when an interval for
  the ratio excludes the tolerated band) rather than accept only when a noisy point estimate falls inside it, and its
  false-refusal and miss rates should be measured.
- The conditioning score (here the child's posterior) must still be **logged at selection time**, and its calibration
  against the random audit must pass for the label.

## What this does and does not show

It shows, in this synthetic world, that conditioning on the logged selection score removes the selection bias under
random, blast-radius and confidence-ordered review, and that the label machinery behaves as intended where bias is
real. It does not show the estimator works on a real audit chain: real review selection has several drivers (including
human judgement that is not logged as a score), the node posterior is not yet calibrated, re-derivation may be partial,
observations noisy, families unknown and confounding present. All protocol idealisations still apply.

## Next

1. A v5 protocol, written and frozen before running, that gates E4 with the posterior calibration check and drops the
   population-b estimators from the gate (kept as references), replaces the fixed-band balance check with an
   evidence-based one whose false-refusal and miss rates are measured, and tests a posterior that is miscalibrated in
   different ways (shift, scale, and miscalibration confined to some node types). v1–v4 results stay as they are.
