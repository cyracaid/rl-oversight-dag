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

## Exploratory run: audit fraction 0.125 (`runs/propagation-recovery-v5-audit0125/`)

Not part of the verdict (the protocol lists it as exploratory, gated only in the sense that the same gate code runs on it).
Provenance matches the current sources (run commit `6bf7669`). It uses the same seed as the primary run, so the simulated
worlds are the same and only the split of the 16 reviews per graph changes (14 policy + 2 audit instead of 12 + 4); it is
therefore not an independent replication. About 400 audited roots per run instead of about 800.

- **The gate code reports PASSED again.** E4 under `cal`: bias within 0.003, coverage 0.91–0.97, mean n 119–627, calibrated
  rate 0.87–0.99. Both harmful modes (`shift+1.5` 0.065 and `scale0.5` 0.051, same classification) are still refused
  (pass rate 0.00–0.01).
- **Halving the audit makes the check more conservative, not more permissive.** The mean residual's spread across replicates
  grows from about 0.0075 to about 0.0105, and the equivalence test needs the whole interval inside the tolerance, so
  more uncertainty means more refusals. False refusal under `cal` rises from 0.00 to 0.05 / 0.01 / 0.02 (random /
  confidence / blast; all refusals global). Mild distortions are accepted less often than with the larger audit:
  `shift+0.8` 0.17 / 0.18 / 0.25 (was 0.29 / 0.30 / 0.35), `shift-0.8` 0.47 / 0.45 / 0.45 (was 0.65 / 0.73 / 0.67),
  `scale2` 0.84 / 0.82 / 0.79 (was 0.98 / 0.97 / 0.99), `noise1` 0.90 / 0.94 / 0.96 (was 1.00 / 1.00 / 0.99).
- **The cost shows up as fewer usable labels, not wrong ones.** The E4 label rate under `cal` falls (random family 3:
  0.92 → 0.87) because more correct posteriors are refused. A smaller audit than this would eventually make the label
  rate fall below the 0.80 non-vacuity requirement; where that happens was not measured.
- **Reading for design.** In this synthetic world about 400 audited roots per 800 graphs (2 of the 16 reviews per graph) kept every pre-registered property while accepting fewer benign
  distortions. Whether that holds for a real chain depends on its error rate, its audit size and its posterior quality.
  The 0.5 audit-fraction run (more audit) has not been run.

## Exploratory run: audit fraction 0.5 (`runs/propagation-recovery-v5-audit05/`) and the audit-size curve

Same status and caveats as the 0.125 run: exploratory, provenance matches the current sources (run commit `ba72a39`), same
seed and worlds as the primary run (not independent), about 1,600 audited roots (8 of the 16 reviews per graph).

- **The gate code reports PASSED.** E4 under `cal`: |bias| ≤ 0.004, coverage ≥ 0.93; the check passes a correct posterior in
  100% of replicates; the same two harmful modes (`shift+1.5` 0.070, `scale0.5` 0.051) are refused (0.00–0.01).
- **More audit does not make the check stricter; it makes it sharper.** The mean residual's spread falls to about 0.0059, so
  the acceptance region approaches the tolerance itself (|mean residual| ≤ 0.04) and mild distortions inside the tolerance
  are accepted more often.

Pass rate of the calibration check (random / confidence / blast) by audit size:

| mode | ~400 roots (fraction 0.125) | ~800 (0.25, primary) | ~1,600 (0.5) |
|---|---|---|---|
| cal | 0.95 / 0.99 / 0.98 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| shift+1.5 (harmful) | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 |
| scale0.5 (harmful) | 0.01 / 0.01 / 0.01 | 0.00 / 0.00 / 0.01 | 0.01 / 0.00 / 0.00 |
| type+1.5 | 0.04 / 0.02 / 0.05 | 0.03 / 0.03 / 0.06 | 0.07 / 0.05 / 0.05 |
| shift-1.5 | 0.06 / 0.05 / 0.03 | 0.07 / 0.06 / 0.03 | 0.05 / 0.06 / 0.02 |
| shift+0.8 | 0.17 / 0.18 / 0.25 | 0.29 / 0.30 / 0.35 | 0.54 / 0.54 / 0.56 |
| shift-0.8 | 0.47 / 0.45 / 0.45 | 0.65 / 0.73 / 0.67 | 0.84 / 0.89 / 0.91 |
| scale2 | 0.84 / 0.82 / 0.79 | 0.98 / 0.97 / 0.99 | 1.00 / 1.00 / 1.00 |
| noise1 | 0.90 / 0.94 / 0.96 | 1.00 / 1.00 / 0.99 | 1.00 / 1.00 / 1.00 |

E4 under `cal` across the three audit sizes: |bias| ≤ 0.003 / 0.003 / 0.004; minimum coverage 0.91 / 0.92 / 0.93; minimum
mean usable events per cell 119 / 120 / 115; minimum label rate 0.87 / 0.92 / 0.85.

What the curve shows, for design:

1. **Harmful modes are refused at every audit size tested** (0.00–0.01), and a correct posterior is accepted at 800 and 1,600
   roots; only the smallest audit costs a few percent false refusal.
2. **The audit size controls how sharply the tolerance acts.** With a small audit the check also refuses mild distortions
   (conservative); with a large audit it accepts distortions that stay within 0.04. Because accepted mild shifts lowered
   interval coverage (limit 1 above), a larger audit does **not** protect coverage better; only a tighter tolerance, or
   intervals that carry the tolerated calibration uncertainty, does.
3. **Audit and policy reviews compete for the same budget.** The mean number of correction events shrinks as the audit grows
   under the ranked policies (confidence 5,897 → 5,722 → 5,095; blast 3,379 → 3,113 → 2,564), and the lowest label rates
   (0.87 at 400 roots, 0.85 at 1,600 roots) show both ends of the trade-off: too little audit refuses more correct
   posteriors, too much leaves fewer usable events. The best audit share in this world is therefore in the middle of the
   range tested; this was not optimised and may differ for a real chain.
4. The comparison uses one seed and one world set, so differences of a few points between audit sizes are not independent
   evidence; the direction of the trends is what is reported.
