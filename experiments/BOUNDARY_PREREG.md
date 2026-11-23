# Boundary experiments: protocol frozen before full execution

Date: 2026-11-12. Status: implementation validated on tiny smoke runs only.
No full-run numbers are asserted here. Historical dist_table.md conflicts with
dist_results.json and is not admissible evidence until reproduced.

## Highest discipline

Every claim must trace to saved raw results, explicit configuration and source
hashes. Tables are generated from saved JSON. Never hide failed seeds, choose the
best seed, overwrite runs, or rewrite hypotheses after seeing results. Public
policies see graph, confidence and their own observations; hidden errors and
propagation coins are available only to the simulator, never action selection.
Negative results remain results. No agents execute full experiments.

## Implementation plan and completion

- [x] Fix BC initialization/shuffling seeds and masked KL; save BC/FT checkpoints.
- [x] Add independent output directories, per-graph arrays, provenance and reports.
- [x] Implement fixed-environment model perturbations and separate catch shifts.
- [x] Implement all-action, observation-adaptive particle depth-2 lookahead.
- [x] Validate pairing, branch non-mutation, checkpoint roundtrip and tiny CLI runs.
- [ ] User executes full runs; inspect every requested seed before interpretation.

## Fixed protocol

N=80, budget=16, propagation probability=0.6, catch=0.9, 1024 particles.
Training seeds 1–5; 20,000 REINFORCE/FT episodes; BC 800 graphs × 4 epochs.
BC LR=.001; FT/REINFORCE LR=.003. Primary BC+FT uses no KL; KL=.5 is
an explicitly separate exploratory intervention. Retain failures and rerun reasons.

All new runs use node-indexed common reviewer uniforms (`crn=True`). This changes
the evaluation protocol: rerun every comparator; do not splice in historical means.
Graph seeds 1000–1199 are a development set already inspected in earlier work.
Final independent confirmation uses 2000–2199, after locking one candidate and
one condition; do not inspect confirmation data during candidate selection.

Primary outcome: final sink errors, lower is better. Report candidate minus belief
greedy and candidate minus the corresponding control. 10,000 crossed bootstrap
draws, fixed bootstrap seed 20261112, independently resampling training seeds and
graph IDs while preserving graph pairing across policies. Paired BC+FT minus BC
preserves matching training-seed rows too. Planner intervals resample graphs only.
The bootstrap conditions on the deterministic belief seed per graph; it does not
estimate extra particle-filter RNG uncertainty. Five training seeds are limited.

## Conditions and hypotheses

| condition | true environment | assumed model | diagnostic |
|---|---|---|---|
| matched | p=.6, catch=.9 | correct | baseline |
| prop_odds_x0.5 | unchanged | propagation odds ×.5 → p=3/7 | propagation model error |
| prop_odds_x2 | unchanged | propagation odds ×2 → p=.75 | propagation model error |
| conf_logit_minus0.5 | unchanged | posterior input logit offset −.5 | calibration model error |
| conf_logit_plus0.5 | unchanged | posterior input logit offset +.5 | calibration model error |
| catch0.7_known | catch=.7 | catch=.7 | known environment shift |
| catch0.7_unknown | catch=.7 | catch=.9 | unrecognized environment shift |

Confidence offset affects assumed posterior only, not raw confidence features.
Observed RL, BC and greedy receive the SAME perturbed model. Static RL receives
raw unchanged features. All checkpoints are trained in the matched environment;
this tests frozen-policy robustness, not adaptation or training on shifted data.
Uniform catch reduction tests robustness, not avoidance of heterogeneous reviewers.

Two-step: gain(a) + sum_o P(o|a) max_b gain(b|a,o), budget-1 remaining,
all available first/second actions; both observation branches integrated; receding
horizon; final step is one-step greedy. Existing particle resampling approximates
branch posteriors; report runtime and degeneracy counts. No truth, top-k pruning,
or extra training. Two-step improvement supports planning value; failure does not
rule out longer-horizon planning or particle approximation error.

## Decision rules

Development comparisons across conditions are exploratory, not six independent
opportunities to claim significance. Select and lock one candidate/condition
before independent confirmation. Option 1 requires 5 complete training seeds,
candidate−belief upper CI <0 and candidate−2-step upper CI <0 in that condition
on confirmation graphs. State the condition; do not generalize niche robustness.

Operational near parity: candidate−teacher upper 95% bound < +0.10 sink errors.
This is a preselected noninferiority margin, not evidence of superiority or exact
equivalence. BC near parity supports representability of comparable performance,
not a unique causal diagnosis. FT−BC is a matched-seed intervention contrast.

Option 2 remains provisional until a mechanism has independent diagnostics and
an intervention supports it. BC alone does not distinguish credit assignment,
exploration, optimizer issues or teacher ceiling. Gain/AC/n-step diagnostics are
future work, not implemented or claimed by this change. Do not claim that model
misspecification is the only regime where RL could help.
