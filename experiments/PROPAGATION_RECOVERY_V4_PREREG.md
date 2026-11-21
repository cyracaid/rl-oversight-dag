# Propagation recovery v4: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and tiny runs only.
**No v4 numbers exist and none are asserted here.** The user executes the full runs.

History. v1: base error rate estimated from selectively reviewed roots (failed). v2: random audit drawn from the nodes
left after policy selection (failed; audit-root b̂ 0.017 vs 0.104). v3: audit drawn first and uniformly, width removed
from the label, negative control added. v3 primary gate not passed, negative control passed. v3 exposed a second
selection effect: under confidence-ordered review the children an estimator may use are depleted of source errors
(hidden rate 0.063 vs 0.104), so the population base rate over-corrects, and the label rule did not notice. An
estimator conditioning on the child's logged posterior (E4) was unbiased in every v3 cell. Details:
`PROPAGATION_RECOVERY_V{1,2,3}_INTERPRETATION.md`. All earlier code and results are unchanged.
**v4 was designed after seeing v1–v3**; only a pass on this unseen seed is new evidence.

## Discipline

Same as v1–v3: every claim traces to saved raw results, configuration and source hashes; tables come from saved JSON;
never hide a failed replicate, choose the best seed, overwrite a run or rewrite a hypothesis after seeing results.
**Agents run only `--smoke` and unit tests.** Each output directory must be new.

## What changes from v3

| item | v3 | v4 |
|---|---|---|
| estimator under the gate | E3b (population b from the random audit) | **E4**: changed / Σ(1 − child posterior), single-parent children not reviewed before; sandwich interval; no base-error-rate source |
| E4 label | never labelled | needs: audit frame verified, ≥ 100 audited roots, **posterior calibration check** |
| population-b label (E2, E3a, E3b) | frame, audit size, flag rate vs prior | adds a **covariate-balance check** |
| controls | flawed audit mislabelled as sound | **miscalibrated logged posterior** (`--post-shift 1.5`); the v3 control is kept as a regression and is not rerun |
| replicates | 100 | 150 |

Unchanged: worlds, three edge families (true p 0.30 / 0.60 / 0.85 by child layer), three policies (`random`,
`confidence`, `blast`), catch rate 0.9, budget 16 = 12 policy + 4 audit with the audit drawn first and uniformly from
all nodes, 800 graphs per replicate, Beta(1,1) posterior with 2,000 draws for the Beta-based estimators.

## The two new checks (both computed from the random audit, observable in a real chain)

- **Posterior calibration.** Audited roots have no parents, so a flag is a base-error detection. The observed base-error
  rate (flags / audited roots / assumed catch) must be within `--calib-tol` (0.04) of the mean **logged** posterior of
  those roots. Calibration is checked on roots and then assumed for the children the estimate uses; that is a stated
  limitation.
- **Covariate balance.** For the population-b estimators the mean logged posterior of the children they use, divided by
  the mean logged posterior of the audited roots, must lie in [1/1.25, 1.25]. Under confidence-ordered review the
  children's mean posterior is far below the population's, so these estimators are refused there.

Calibrated-label rules never use interval width; `usable` (width < 0.15) is reported separately.

## Hypotheses

- **V4-H1 (gate, E4).** In all 3 policies and all 3 families: |bias| ≤ 0.05; coverage ≥ 0.90; mean usable events ≥ 100;
  no missing replicate; calibrated rate ≥ 0.80; Wilson 95% upper bound of wrong-given-calibrated ≤ 0.20.
- **V4-H2 (gate, label discrimination).** For E3b: calibrated rate ≤ 0.10 in every family under `confidence` (the biased
  case) and ≥ 0.80 in every family under `random` and `blast` (the unbiased cases).
- **V4-H3 (gate, miscalibration control, separate run).** With `--post-shift 1.5` the E4 calibrated rate is ≤ 0.10 in all
  9 policy-family cells.
- **V4-H4 (diagnostic).** In the primary run the posterior calibration check passes in at least 95% of replicates under
  every policy (shown in each policy heading of `results.md`); with the shift it passes in at most 5%.
- **V4-H5 (diagnostic).** The hidden child base-error rate under `confidence` is below 0.09 again (replication of v3).

## Verdict rule

**v4 passes only if V4-H1 and V4-H2 hold on the primary run and V4-H3 holds on the miscalibration-control run.**
V4-H4 and V4-H5 are reported and interpreted, not gated. Tolerances are not relaxed after seeing results; they may be
revised only before the first v4 full run, with the reason committed. If the gate fails, diagnose with the saved counts
and the oracle diagnostics, change one thing, and write a v5 protocol before running.

The control strength was set before any v4 run, from a one-off harness check on one small synthetic world: a logit
shift of 0.8 moves the mean logged posterior of audited roots by about 0.03 (not detectable at tolerance 0.04, and it
biases E4 by well under the 0.05 tolerance, so it is harmless), while a shift of 1.5 moves it by about 0.06 (detectable,
and it biases E4 by up to about 0.07 at the highest true propagation probability). Shifts below 1.0 in absolute value are
therefore not treated as controls.

## Commands (run from the repository root)

Primary run:

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v4.py --out-dir runs/propagation-recovery-v4
```

Miscalibration control (required for the verdict):

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v4.py --post-shift 1.5 --out-dir runs/propagation-recovery-v4-miscal
```

Exploratory runs (not gated; each in a new directory):

```bash
cd ~/Documents/강화학습
python3 -u experiments/rl_propagation_recovery_v4.py --post-shift -1.5 --out-dir runs/propagation-recovery-v4-miscal-neg
python3 -u experiments/rl_propagation_recovery_v4.py --audit-fraction 0.125 --out-dir runs/propagation-recovery-v4-audit0125
python3 -u experiments/rl_propagation_recovery_v4.py --audit-fraction 0.5 --out-dir runs/propagation-recovery-v4-audit05
python3 -u experiments/rl_propagation_recovery_v4.py --assumed-catch 0.7 --out-dir runs/propagation-recovery-v4-catch07
python3 -u experiments/rl_propagation_recovery_v4.py --obs-miss 0.2 --out-dir runs/propagation-recovery-v4-miss02
python3 -u experiments/rl_propagation_recovery_v4.py --prior-b 0.20 --out-dir runs/propagation-recovery-v4-prior020
```

No time estimate is promised: v4 uses 1.5 times the replicates of v3. Tiny harness check: `--smoke` (not evidence).

## Reading the output

1. The gate table (primary or miscalibration control), then `missing` and `mean n`.
2. E4 bias, RMSE and coverage per policy and family; then the E3b label rates (V4-H2).
3. The posterior-calibration pass rate in each policy heading (V4-H4) and the hidden child base-rate diagnostic (V4-H5).
4. `usable` versus `cal. rate`: width and calibration are different questions.
5. Check `provenance` (git status, source hashes) before quoting any number.

## What a pass means and does not mean

A pass means: in this synthetic world, with every child re-derived and changes observed exactly, a known catch rate,
known families, an honestly recorded random audit, and a logged selection score that is the only driver of review
selection, the posterior-conditioned estimator recovers the generating propagation probability under random, blast-radius
and confidence-ordered review, and the label refuses both the biased population-b estimator and a miscalibrated
posterior. It does **not** show it works on a real audit chain: real review selection has several drivers (including
human judgement that is not logged as a score), the node posterior is not yet calibrated, re-derivation may be partial,
observations noisy, families unknown and confounding present. Real records are never used here, never committed, and
are processed locally by the data owner only after the gate passes and the OpenSpec change is accepted.

## Related

- OpenSpec change `add-belief-review-ranking`: tasks 1.4–1.6 and 4.1; requirements on logging the selection score,
  the covariate-balance check and the posterior-calibration check.
