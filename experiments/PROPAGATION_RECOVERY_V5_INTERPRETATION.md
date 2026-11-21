# Propagation recovery v5: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/propagation-recovery-v5/`).
No rerun, no change to the pre-registered hypotheses or gate (`PROPAGATION_RECOVERY_V5_PREREG.md`).

## Integrity

- Source SHA256 of `rl_propagation_recovery_v5.py`, `_v3.py`, `_v2.py`, `rl_propagation_recovery.py`,
  `spike_active_selection.py` and `belief.py` in the saved provenance match the current files; run commit `f1567cf`.
- 150 replicates, 800 graphs per replicate, budget 16 (12 policy + 4 audit, audit drawn first), assumed catch 0.9,
  tolerance 0.04, seed 20261125 (independent of v1–v4). No replicate had a missing estimate. Synthetic data only.
- v5 was designed after seeing v1–v4 and the protocol discloses that the author saw the check outcome (no estimate) for
  one replicate while writing a test. Only the gate on this unseen seed is new evidence.

## Verdict against the pre-registered gate: **passed**

| hypothesis | result |
|---|---|
| **V5-H1** E4 correctly specified, 9 cells: \|bias\| ≤ 0.05, coverage ≥ 0.90, mean n ≥ 100, no missing, calibrated rate ≥ 0.80, Wilson ub ≤ 0.20 | **Supported in all 9 cells** (below) |
| **V5-H2** calibration check passes in ≥ 0.90 of replicates under `cal` | **Supported**: 1.00 under all three policies (no false refusal in 450 replicate-policy combinations) |
| **V5-H3** every harmful mode refused (check pass rate ≤ 0.10 under every policy) | **Supported**: harmful modes by the pre-registered rule are `shift+1.5` (max \|bias\| 0.067) and `scale0.5` (0.0504); pass rates 0.00 / 0.00 / 0.00 and 0.00 / 0.00 / 0.01 |
| V5-H4 references reproduce the v3/v4 pattern | **Supported**: under `confidence` E2 +0.221 / +0.391 / +0.150, E3a +0.015 / +0.029 / +0.037, E3b +0.015 / +0.029 / +0.036; unbiased under `random` and `blast` (within 0.009); E0 biased low everywhere |
| V5-H5 refusal-reason table | Every refusal in the run came from the **global** equivalence test; the **bin** check never fired (see limits) |

E4 under `cal`, by policy and family 1 / 2 / 3:

| policy | bias | coverage | mean n | calibrated rate | wrong\|cal Wilson ub95 |
|---|---|---|---|---|---|
| random | +0.003 / +0.000 / +0.002 | 0.93 / 0.93 / 0.92 | 133 / 130 / 120 | 0.99 / 0.98 / 0.92 | 0.12 / 0.12 / 0.13 |
| confidence | +0.001 / +0.002 / −0.001 | 0.96 / 0.96 / 0.98 | 595 / 584 / 551 | 1.00 / 1.00 / 1.00 | 0.08 / 0.08 / 0.06 |
| blast | +0.001 / −0.001 / +0.000 | 0.94 / 0.94 / 0.94 | 458 / 364 / 180 | 1.00 / 1.00 / 1.00 | 0.11 / 0.11 / 0.11 |

This repeats the v4 result for E4 on a second unseen seed.

## The calibration check, measured (pass rate by mode: random / confidence / blast)

| mode | max E4 \|bias\| | min coverage | check pass rate | harmful by rule |
|---|---:|---:|---|---|
| cal | 0.003 | 0.92 | 1.00 / 1.00 / 1.00 | - |
| shift+1.5 | 0.067 | 0.09 | 0.00 / 0.00 / 0.00 | yes |
| scale0.5 | 0.050 | 0.18 | 0.00 / 0.00 / 0.01 | yes |
| type+1.5 | 0.041 | 0.53 | 0.03 / 0.03 / 0.06 | no |
| shift-1.5 | 0.037 | 0.58 | 0.07 / 0.06 / 0.03 | no |
| shift+0.8 | 0.032 | 0.71 | 0.29 / 0.30 / 0.35 | no |
| shift-0.8 | 0.022 | 0.87 | 0.65 / 0.73 / 0.67 | no |
| scale2 | 0.014 | 0.92 | 0.98 / 0.97 / 0.99 | no |
| noise1 | 0.006 | 0.93 | 1.00 / 1.00 / 0.99 | no |

The check separates the modes in the order of their effect on the estimate: it accepts a correct posterior, a
noisy one and an over-confident one (all with negligible bias), partly accepts mild shifts (0.8), and refuses larger
shifts, an under-confident posterior and a posterior miscalibrated for some node types in 93–100% of replicates. The
mean residual used by the check is stable across replicates (sd about 0.0075 with about 800 audited roots), which is what
makes the equivalence test reliable at this audit size.

## Limits and observations the verdict does not cover

1. **The harmful-mode rule is bias-based, and coverage is more sensitive.** `shift-1.5`, `shift+0.8` and `type+1.5` are not
   harmful by the pre-registered rule (bias 0.032–0.041) yet their E4 interval coverage falls to 0.53–0.71 in some cells,
   and `shift-0.8` to 0.87. The check refused the first and third almost always, but accepted `shift+0.8` in 29–35% and
   `shift-0.8` in 65–73% of replicates. Had harm been defined by coverage (post hoc, not the registered rule), those two
   modes would not have met the 0.10 acceptance ceiling. The tolerance (0.04) protects against bias beyond 0.05, not
   against under-covering intervals; a design that needs nominal coverage needs a tighter tolerance or intervals that
   account for posterior uncertainty.
2. **`scale0.5` sits on the edge of the rule** (max \|bias\| 0.0504 against 0.05). It was refused 99–100% of the time either way.
3. **The bin check was not exercised.** The modes in this run were all caught by the global test (including
   `type+1.5`), so the within-bin check has no measured false-refusal or miss rate. Whether it is needed is open.
4. **Calibration is checked on roots and assumed for children.** In this simulator node types are exchangeable across layers.
5. All earlier idealisations still apply: children re-derived and changes observed exactly, known catch rate, known
   families, an honestly recorded random audit, a logged selection score that is the only driver of review selection.
   The exploratory runs (audit fraction, assumed catch, tolerance, observation miss) were not run.

## Design implications for the OpenSpec change (to be recorded)

- A posterior-conditioned estimator with a random-audit calibration check is a viable, single canonical path. The random
  audit is needed for the check; about 800 audited roots per run gave a false-refusal rate of 0 and refused every
  harmful mode. The number of audited nodes should be treated as a design parameter, not a constant.
- The equivalence-test form of the check (evidence required to accept, with a tolerance tied to estimate impact) behaved
  as intended. Its tolerance should be set from the maximum acceptable effect on the estimate **and on interval coverage**.
- The estimate's interval should reflect uncertainty from the posterior's calibration, since accepted but imperfect
  posteriors (shift 0.8) lowered coverage.
- Real-record use remains gated by the OpenSpec acceptance and by the prerequisites below, not by this result alone.

## What this does and does not show

It shows, in this synthetic world, that the whole chain works: a randomly drawn audit recorded with its frame, a
logged selection score, a posterior-conditioned estimator, and an evidence-based calibration check that rarely refuses
a correct posterior and refuses the posteriors that would bias the estimate. It does not show it works on a real audit
chain: real review selection has several drivers (including human judgement that is not logged as a score), the node
posterior is not yet calibrated, re-derivation may be partial, observations noisy, families unknown and confounding
present.

## Next

- Record the result in the OpenSpec change (task 1.4 parameter-recovery precondition met on synthetic data; limits above).
- Optional exploratory runs in `PROPAGATION_RECOVERY_V5_PREREG.md`; the audit-fraction runs are the most informative for design.
- Before any real record is touched: calibrated node posterior and logged selection score available in the chain, a random
  audit drawn from the full eligible set with a recorded frame, and the calibration check passing on the real audit.
  Real records stay local and uncommitted.
