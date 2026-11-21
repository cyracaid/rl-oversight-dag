# Propagation recovery v5: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and tiny runs only.
**No v5 numbers exist and none are asserted here.** The user executes the full run.

History (details in `PROPAGATION_RECOVERY_V{1,2,3,4}_INTERPRETATION.md`; all earlier code and results unchanged):
v1 estimated the base-error rate from selectively reviewed roots (failed). v2 drew the random audit from the nodes left
after policy selection (failed). v3 drew the audit first, dropped interval width from the label and added a negative
control (primary failed, control passed) and exposed that unreviewed children are depleted of source errors under
confidence-ordered review. v4 gated an estimator conditioning on the child's logged posterior (E4): it met every
criterion in all nine policy-family cells and a miscalibrated posterior was refused, but the gate failed on the label
discrimination of the population-rate estimators, whose fixed-band balance check was noise-limited.

**v5 was designed after seeing v1–v4.** Only a pass on this unseen seed is new evidence. Disclosure: while writing a unit
test the author inspected the calibration-check outcome (not any estimate or gate quantity) for one replicate of the
default seed under the `random` policy; it showed that `shift-1.5` can pass the check there, which is consistent with the
harmful-mode rule below.

## Discipline

Same as v1–v4: every claim traces to saved raw results, configuration and source hashes; tables come from saved JSON;
never hide a failed replicate, choose the best seed, overwrite a run or rewrite a hypothesis after seeing results.
**Agents run only `--smoke` and unit tests.** The output directory must be new.

## What v5 changes

- **One canonical estimator.** E4 (changed / Σ(1 − logged child posterior), single-parent children not reviewed before,
  sandwich interval) is the only gated estimator. The population-rate estimators E0, E2, E3a, E3b stay as **references with
  no labels**; the balance check is dropped with them.
- **The question v5 answers:** how reliable is the posterior-calibration check? Its false-refusal and false-acceptance
  rates are **measured** across several miscalibrations of the logged posterior, all analysed from the same simulated logs
  (the world and policies use the true posterior; only the posterior the audit chain would record is distorted).
- **Evidence-based check.** On the audited roots (no parents, so a flag is a base-error detection), per-node residual
  d = flag / assumed catch − logged posterior. *Global:* accept only if the 90% interval of mean(d) lies inside
  ±`calib_tol` = 0.04 (an equivalence test, so evidence is needed to accept). *Bins:* in the low (< 0.5) and high (≥ 0.5)
  logged-posterior bins with at least 30 roots, refuse if the 95% interval of mean(d) lies entirely outside ±0.15.
  `calib_tol` is tied to impact: a mean posterior error d shifts E4 by about d/0.9 in relative terms, so 0.04 corresponds to
  an absolute bias of at most about 0.04 at the largest true propagation probability.
- **E4 label** (never uses interval width): audit frame verified (all_eligible), ≥ 100 audited roots, calibration check
  passed, ≥ 100 usable events.

Unchanged: three edge families (true p 0.30 / 0.60 / 0.85 by child layer), three policies (`random`, `confidence`, `blast`),
catch rate 0.9, budget 16 = 12 policy + 4 audit with the audit drawn first and uniformly from all nodes, 800 graphs per
replicate, 150 replicates. New seed 20261125.

## Miscalibration modes (logged posterior only)

| mode | distortion of the logged posterior |
|---|---|
| `cal` | none (correctly specified; false refusal measured here) |
| `shift+1.5`, `shift-1.5` | logit shift by ±1.5 |
| `shift+0.8`, `shift-0.8` | logit shift by ±0.8 |
| `scale2`, `scale0.5` | logit × 2 (over-confident), × 0.5 (under-confident) |
| `type+1.5` | logit shift +1.5 only for node types ≥ 3 |
| `noise1` | logit plus N(0, 1) noise per node (deterministic per node) |

**Harmful-mode rule (fixed now, applied to the saved results):** a mode other than `cal` is *harmful* if the mean E4 |bias|
exceeds 0.05 in at least one policy-family cell. Modes that are not harmful (by this rule) carry no refusal requirement.

## Hypotheses

- **V5-H1 (gate, E4 correctly specified).** In all 3 policies and 3 families under `cal`: |bias| ≤ 0.05; coverage ≥ 0.90;
  mean usable events ≥ 100; no missing replicate; calibrated rate ≥ 0.80; Wilson 95% upper bound of wrong-given-calibrated ≤ 0.20.
- **V5-H2 (gate, false refusal).** Under `cal`, the calibration check passes in at least 0.90 of replicates under every policy.
- **V5-H3 (gate, harmful modes refused).** For every harmful mode, the calibration check passes in at most 0.10 of replicates
  under every policy.
- **V5-H4 (diagnostic).** The population-rate references reproduce the v3/v4 pattern: biased under `confidence`, unbiased
  under `random` and `blast`.
- **V5-H5 (diagnostic).** The refusal-reason table shows which sub-check (global or bin) refuses which mode.

## Verdict rule

**v5 passes only if V5-H1, V5-H2 and V5-H3 all hold on the single run.** V5-H4 and V5-H5 are reported and interpreted, not
gated. Tolerances are not relaxed after seeing results; they may be revised only before the first v5 full run, with the reason
committed. If the gate fails, diagnose from the saved counts and the refusal reasons, change one thing, and write a v6
protocol before running. A harmful mode that the check accepts is a finding about the check, not a reason to change the rule.

## Commands (run from the repository root)

Primary run (the only run needed for the verdict):

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v5.py --out-dir runs/propagation-recovery-v5
```

Exploratory runs (not gated; each in a new directory). The audit size sets the check's power and false-refusal rate, so it
is the most informative lever for design:

```bash
cd ~/Documents/강화학습
python3 -u experiments/rl_propagation_recovery_v5.py --audit-fraction 0.125 --out-dir runs/propagation-recovery-v5-audit0125
python3 -u experiments/rl_propagation_recovery_v5.py --audit-fraction 0.5 --out-dir runs/propagation-recovery-v5-audit05
python3 -u experiments/rl_propagation_recovery_v5.py --assumed-catch 0.7 --out-dir runs/propagation-recovery-v5-catch07
python3 -u experiments/rl_propagation_recovery_v5.py --calib-tol 0.03 --out-dir runs/propagation-recovery-v5-tol003
python3 -u experiments/rl_propagation_recovery_v5.py --obs-miss 0.2 --out-dir runs/propagation-recovery-v5-miss02
```

No time estimate is promised. Tiny harness check: `--smoke` (not evidence).

## Reading the output

1. The gate table, then the harmful-mode table (which modes the rule classified as harmful).
2. The calibration-check pass rates by mode and policy, with refusal reasons.
3. E4 by mode (bias, coverage, label rate); then the references.
4. Check `provenance` (git status, source hashes) before quoting any number.

## What a pass means and does not mean

A pass means: in this synthetic world, with every child re-derived and changes observed exactly, a known catch rate, an
honestly recorded random audit, and a logged selection score as the only driver of review selection, the posterior-
conditioned estimator is unbiased under three review policies, the calibration check seldom refuses a correct posterior,
and it refuses every miscalibration that would bias the estimate beyond tolerance. It does **not** show the estimator works on
a real audit chain: real review selection has several drivers (including human judgement that is not logged as a score), the
node posterior is not yet calibrated, re-derivation may be partial, observations noisy, families unknown and confounding
present. Real records are never used here, never committed, and are processed locally by the data owner only after the gate
passes and the OpenSpec change is accepted.

## Related

- OpenSpec change `add-belief-review-ranking`: tasks 1.4–1.6 and 4.1; requirements "Canonical estimator conditions on the
  logged selection score" and "Checks respect their own sampling noise".
