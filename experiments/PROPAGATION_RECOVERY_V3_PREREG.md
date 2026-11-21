# Propagation recovery v3: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and a tiny smoke run only.
**No v3 numbers exist and none are asserted here.** The user executes the full runs.

History. v1 did not pass (base error rate estimated from selectively reviewed roots). v2 added a random audit and
did not pass: the audit was drawn from the nodes the policy had not picked, so under confidence-ordered review the
audit roots were depleted of errors (audit-root b̂ 0.017 vs true 0.104), and the label rule could not see it.
Findings and numbers: `PROPAGATION_RECOVERY_V1_INTERPRETATION.md`, `PROPAGATION_RECOVERY_V2_INTERPRETATION.md`.
All earlier code and results are unchanged. **v3 was designed after seeing v1 and v2**; only a pass on this
unseen seed is new evidence.

## Discipline

Same as v1/v2: every claim traces to saved raw results, configuration and source hashes; tables come from saved
JSON; never hide a failed replicate, choose the best seed, overwrite a run or rewrite a hypothesis after seeing
results. **Agents run only `--smoke` and unit tests.** Each output directory must be new.

## What changes from v2

| item | v2 | v3 |
|---|---|---|
| audit draw | uniform over the nodes the policy did not pick | **drawn first, uniform over all nodes**; the policy chooses among the rest |
| `calibrated` label | interval width plus a check that only counted audited roots | **no width**; usable events, verified sampling frame, audited roots, and an audit flag rate consistent with the prior **in both directions** (prior/2 to prior×2). Width is reported separately as `usable` |
| label criterion | wrong-given-calibrated ≤ 5% (noise-sensitive) | **Wilson 95% upper bound ≤ 0.20**, and the rule must label at least 80% of replicates (a rule that never labels cannot pass) |
| replicates | 50 | 100 |
| negative control | none | audit drawn after the policy (the v2 flaw) but **attested as all-eligible**; the label rule must refuse |
| diagnostics | none | hidden child base-error rate (oracle, never read by estimators except `Eo`); E4 and `Eo` estimators |

Unchanged: worlds, three edge families (true p 0.30 / 0.60 / 0.85 by child layer), three policies (`random`,
`confidence`, `blast`), catch rate 0.9, budget 16 = 12 policy + 4 audit, 800 graphs per replicate, Beta(1,1)
posterior with 2,000 draws and a 95% equal-tail interval.

## Estimators

| id | role | b source / adjustment |
|---|---|---|
| E0 | naive lower-bound reference | none |
| E2 | v1/v2 reference | all reviewed roots |
| E3a | ablation | external prior (default 0.104) |
| **E3b** | **under the gate** | roots reviewed in the random audit only |
| E4 | exploratory | changed / Σ(1 − child posterior); sandwich interval; no b source; **never labelled** |
| Eo | diagnostic | oracle child base-error rate (reads hidden simulator state); **never labelled** |

E4 uses only observable fields (the child's posterior). It is exploratory because it presupposes a calibrated node
posterior, which a real chain does not yet have.

## Hypotheses

- **V3-H1 (frame fix).** With the audit drawn first, the audit-root b̂ (flags / audited roots / 0.9, from `counts`)
  is between 0.08 and 0.13 under all three policies (true 0.104).
- **V3-H2 (primary gate, E3b).** In all 3 policies and all 3 families: |bias| ≤ 0.05; coverage ≥ 0.90; mean usable
  events ≥ 100; no missing replicate; calibrated rate ≥ 0.80; Wilson upper bound of wrong-given-calibrated ≤ 0.20.
- **V3-H3 (negative control, separate run).** With `--audit-order after --attest-frame all_eligible`, the share of
  replicates for which E3b is labelled calibrated is ≤ 0.10 in every family under `confidence`.
- **V3-H4 (residual mechanism, diagnostic).** Under `confidence`, the hidden base-error rate of the children used by
  the adjusted estimators is below 0.09 (under `random` it is about 0.104), and the oracle estimator `Eo` has
  |bias| ≤ 0.02 in every cell. If `Eo` is still biased, the proposed mechanism (unreviewed children are less
  error-prone) is wrong.
- **V3-H5 (exploratory).** E4 has |bias| ≤ 0.05 and coverage ≥ 0.90 under all policies.

## Verdict rule

**v3 passes only if V3-H2 passes on the primary run and V3-H3 passes on the negative-control run.** V3-H1, V3-H4,
V3-H5 and the E3a ablation are reported and interpreted, not gated. Tolerances are not relaxed after seeing results;
they may be revised only before the first v3 full run, with the reason committed.

If the primary gate fails only in `confidence` cells and E4 meets V3-H5, the finding is: a population-level b cannot
be corrected under confidence-ordered selection, and the next protocol should gate an estimator that conditions on the
child's observed posterior, together with a check that the posterior is calibrated (for example against the random
audit). This is a plan for what to write next, not a license to switch estimators after the fact.

## Commands (run from the repository root)

Primary run:

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v3.py --out-dir runs/propagation-recovery-v3
```

Negative control (required for the verdict):

```bash
cd ~/Documents/강화학습 && python3 -u experiments/rl_propagation_recovery_v3.py --audit-order after --attest-frame all_eligible --out-dir runs/propagation-recovery-v3-negcontrol
```

Exploratory sensitivity runs (not gated; each in a new directory):

```bash
cd ~/Documents/강화학습
python3 -u experiments/rl_propagation_recovery_v3.py --prior-b 0.20 --out-dir runs/propagation-recovery-v3-prior020
python3 -u experiments/rl_propagation_recovery_v3.py --prior-b 0.05 --out-dir runs/propagation-recovery-v3-prior005
python3 -u experiments/rl_propagation_recovery_v3.py --audit-fraction 0.125 --out-dir runs/propagation-recovery-v3-audit0125
python3 -u experiments/rl_propagation_recovery_v3.py --audit-fraction 0.5 --out-dir runs/propagation-recovery-v3-audit05
python3 -u experiments/rl_propagation_recovery_v3.py --assumed-catch 0.7 --out-dir runs/propagation-recovery-v3-catch07
python3 -u experiments/rl_propagation_recovery_v3.py --obs-miss 0.2 --out-dir runs/propagation-recovery-v3-miss02
```

No time estimate is promised: v3 uses twice the replicates of v2. Tiny harness check: `--smoke` (not evidence).

## Reading the output

1. The gate table (primary or negative control), then `missing` and `mean n`.
2. Bias, RMSE, coverage per policy, estimator and family; quote failures with successes.
3. `counts` for audit-root b̂ (V3-H1); the diagnostic table for the hidden child base-error rate (V3-H4).
4. `usable` versus `cal. rate`: width and calibration are different questions.
5. Check `provenance` (git status, source hashes) before quoting any number.

## What a pass means and does not mean

A pass means: in this synthetic world, with every child re-derived and changes observed exactly, a known catch rate,
known families and a random audit whose sampling frame is honestly recorded, the estimator recovers the generating
propagation probability under non-random review, and the label rule refuses a flawed audit even when it is
mislabelled as sound. It does **not** show it works on a real audit chain: real audits may not be random,
re-derivation may be partial, observations noisy, families unknown and confounding present. Real records are never
used here, never committed, and are processed locally by the data owner only after the gate passes and the OpenSpec
change is accepted.

## Related

- OpenSpec change `add-belief-review-ranking`: tasks 1.4–1.6 and 4.1; requirements on the base error rate source,
  review selection and inclusion probability, randomised share and sampling-frame verification.
