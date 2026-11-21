# Propagation recovery v3: primary run results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/propagation-recovery-v3/`).
No rerun, no change to the pre-registered hypotheses or gate (`PROPAGATION_RECOVERY_V3_PREREG.md`).
**The negative-control run (`--audit-order after --attest-frame all_eligible`) has not been run yet.** The primary
gate already failed, so v3 as a whole does not pass whatever the negative control shows; its result is still needed
to know whether the label rule refuses a mislabelled flawed audit.

## Integrity

- Source SHA256 of `rl_propagation_recovery_v3.py`, `_v2.py`, `rl_propagation_recovery.py`,
  `spike_active_selection.py` and `belief.py` in the saved provenance match the current files; run commit `4c644c1`.
- 100 replicates, 800 graphs per replicate, budget 16 (12 policy + 4 audit, audit drawn first), assumed catch 0.9,
  prior b 0.104, seed 20261123 (independent of v1 and v2). No replicate had a missing estimate. Synthetic data only.
- v3 was designed after seeing v1 and v2 (stated in the protocol): only the gate on an unseen seed is new evidence.

## Verdict against the pre-registered gate (E3b): **not passed**

All six cells under `random` and `blast` pass every gate part. All three `confidence` cells fail coverage, and
families 2 and 3 also fail the label wrong-rate bound.

| policy | family | bias | coverage | mean n | calibrated rate | wrong\|cal (Wilson ub95) | gate |
|---|---:|---:|---:|---:|---:|---|---|
| random | 1 / 2 / 3 | +0.006 / +0.001 / +0.003 | 0.96 / 0.93 / 0.94 | 134 / 130 / 120 | 0.99 / 0.97 / 0.90 | 0.04 (0.10) / 0.07 (0.14) / 0.07 (0.14) | pass |
| blast | 1 / 2 / 3 | +0.005 / +0.001 / −0.003 | 0.93 / 0.98 / 0.96 | 457 / 363 / 179 | 1.00 / 1.00 / 1.00 | 0.07 (0.14) / 0.02 (0.07) / 0.04 (0.10) | pass |
| confidence | 1 / 2 / 3 | +0.014 / +0.027 / +0.038 | **0.88 / 0.82 / 0.64** | 594 / 583 / 551 | 1.00 / 1.00 / 1.00 | 0.12 (0.20) / **0.18 (0.27)** / **0.36 (0.46)** | fail |

| hypothesis | result |
|---|---|
| V3-H1 audit-root b̂ in [0.08, 0.13] under all policies | **Supported**: 0.105 (random), 0.102 (confidence), 0.103 (blast); v2 had 0.017 under confidence |
| V3-H2 primary gate | **Not passed** (confidence cells) |
| V3-H3 negative control | **Not run yet** |
| V3-H4 hidden child base-error rate < 0.09 under `confidence`; oracle `Eo` \|bias\| ≤ 0.02 | **Supported**: children's hidden base rate 0.064 / 0.063 / 0.063 under `confidence` (0.098–0.105 under random and blast; population 0.104); `Eo` bias +0.001, +0.000, −0.001 |
| V3-H5 E4 \|bias\| ≤ 0.05 and coverage ≥ 0.90 under all policies | **Not fully met by the literal criterion**: bias within 0.003 everywhere and coverage 0.92–0.98 except `random` family 3 at **0.89** |

## What this shows

1. **The v2 audit flaw is fixed.** With the audit drawn first and uniformly, the audit-root b̂ is 0.102–0.105 in
   all three policies. Under `random` and `blast` review, the data-driven estimator E3b recovers the truth (bias
   ≤ 0.006, coverage 0.93–0.98) and the new label rule is both non-vacuous (labels 90–100%) and safe (Wilson upper
   bound of wrong-given-calibrated ≤ 0.14).
2. **The label rule's frame and flag-rate checks work on the thing they check.** E2, whose b comes from all
   reviewed roots, is refused under `confidence` (flag-rate-implied b̂ 0.458): calibrated rate 0.00.
3. **A second selection effect exists and is now identified.** Under `confidence`, the children that E2/E3 use
   (single-parent and not reviewed before) are depleted of source errors: hidden base rate 0.063 against a
   population 0.104, because the policy reviews the likely-wrong nodes first. Adjusting by the population b
   over-corrects (E3a and E3b are both biased +0.014, +0.027, +0.038; E3a and E3b are almost identical because
   the audit now estimates b correctly). The oracle estimator, using the children's actual rate, removes the bias
   (|bias| ≤ 0.001), which confirms the mechanism rather than only suggesting it.
4. **Conditioning on the child's observed posterior fixes it without any b source.** The exploratory estimator E4
   (changed / Σ(1 − child posterior), sandwich interval) is unbiased in all nine cells (|bias| ≤ 0.003) with
   coverage 0.92–0.98 apart from one cell at 0.89 (`random` family 3). This is exploratory: it presupposes a
   calibrated node posterior, which a real chain does not have.

## What went wrong

- **The label rule does not see the child-selection bias.** Under `confidence`, E3b is labelled calibrated in 100% of
  replicates while 12–36% of those intervals miss the truth. The rule checks the source of b, not whether the
  children used were selected on the same covariate that drove the review policy.
- **The gate was designed around the estimator that cannot handle risk-ordered selection.** This was foreseen in
  the protocol (the planned next step if the failure were confined to `confidence` and E4 met its criterion). E4
  missed the literal coverage criterion in one cell by 0.01, within Monte Carlo noise (about ±0.03 at 100
  replicates), so it is reported as not met rather than rounded up.

## Design implications for the OpenSpec change (to be recorded)

- An estimator from review logs must **condition on every covariate that drove review selection**. That means the
  selection score available at the moment of selection (here the node posterior or risk score) must be **logged with
  each review**, not only the selection method.
- The `calibrated` label needs a **covariate-balance check**: compare the observed selection covariate of the nodes
  used in the estimate (here the children's posterior) with the population, taken from the random audit. In this world
  that observable difference signals the problem the current checks miss.
- A covariate-conditioned estimator such as E4 depends on the posterior being calibrated, so it must be accompanied
  by a **calibration check against the random audit** (observed flag rate versus mean posterior of audited nodes).
- Random audit, drawn from the full eligible set before policy selection with logged inclusion probability, remains
  necessary (v2) and sufficient for the base-error rate (v3 H1).

## What this does and does not show

It shows, in this synthetic world, that a properly random audit recovers the base-error rate and that the
propagation estimate is unbiased under random and blast-radius review, and it isolates and confirms the remaining
bias under confidence-ordered review. It does not show the estimator works on a real audit chain: real audits may not
be random, re-derivation may be partial, observations noisy, families unknown, and the node posterior is not
calibrated. All protocol idealisations still apply; the sensitivity runs were not run.

## Next

1. Run the negative control (command in `PROPAGATION_RECOVERY_V3_PREREG.md`) to complete the v3 record.
2. A v4 protocol, written and frozen before running: gate an estimator that conditions on the logged selection
   covariate (E4-type) together with a posterior-calibration check from the random audit and a covariate-balance
   label rule; add a sensitivity run with a deliberately miscalibrated posterior. v1, v2 and v3 results stay as they
   are.
