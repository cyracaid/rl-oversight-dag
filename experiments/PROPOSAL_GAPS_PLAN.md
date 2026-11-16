# Proposal gap experiments: implementation and run plan

2026-11-12. User authorized implementation and repository publication. Full training remains a user-run job.

## Design

Preserve existing boundary results. Add a separate runner sharing the existing N=80,
budget=16 simulator, particle belief and message-passing GNN. Compare observed inputs
with observed plus normalized one-step gain. Compare terminal REINFORCE with a learned
state critic using full-horizon returns and 3/5-step bootstrapped returns (gamma=1).
All methods use terminal reward only; there is no hidden-state reward shaping.
Critic inputs pool only policy-visible features over unreviewed nodes.

Confidence conditions normal/noise/oracle each train their own model and evaluate
with genuine nonzero adjacency. Oracle reveals source errors as an explicitly
privileged ceiling. Noise replaces confidence; belief still uses its frozen
calibration, so this condition disrupts both confidence and derived belief features.
It is a joint input/model intervention, not a pure direct-confidence-channel ablation.

Nonstationarity is a chronological stream of independent episodes. True per-type
source-error odds increase linearly from x1 to x2 across evaluation episodes.
The planner retains nominal type priors; conditional confidence likelihood remains
unchanged. Policies are frozen: this measures robustness to drift, not online adaptation.
Within an episode source errors remain fixed except for review repairs. Matched and
drift comparisons replay the same graph and uniform draws across policies.

## Tasks and acceptance

- [x] Add deterministic tests for bootstrapped returns, gain features, adjacency,
  drift generation and policy-blind environment replay; observe initial failure.
- [x] Implement `proposal_gaps.py`: environment, features, critic, rollout,
  training, checkpoint saving, paired evaluation and JSON-to-Markdown output.
- [x] Validate CLI arguments, refuse output-directory reuse, save configuration,
  source hashes, environment versions, checkpoints, seed-by-graph raw outcomes,
  degeneracy counts and crossed-bootstrap intervals.
- [x] Run existing boundary/semantics tests and new tests; run a tiny end-to-end
  job through every optimizer, gain features, confidence modes and drift.
- [x] Add full-run and clean-clone reproduction commands, explicit status matrix,
  and run manifest instructions. Smoke evidence is not full experimental evidence.
- [ ] Commit only scoped files and publish branch to origin; no unrelated edits.

## Full experiment sequence

1. Normal confidence: observed/gain × reinforce/ac/nstep3/nstep5, five training
   seeds, 20,000 episodes; evaluate paired development graphs 1000–1199.
2. Confidence control: same factorial for noise and oracle, separately labelled;
   no direct causal claim about credit assignment from an optimizer improvement.
3. Inspect matched/drift raw arrays and paired CI. Drift is one predeclared
   linear schedule, not a comprehensive nonstationarity benchmark.
4. Freeze selected method and criterion before a separate confirmation on
   graph seeds 2000–2199. Merely changing CLI range is not preregistration.
5. A teammate runs from a clean clone, records commit, command, environment,
   artifact hashes and discrepancies. Never mark independent reproduction done
   merely because commands exist.

## Out of scope

SciForge production integration needs a separate real-system interface and acceptance
run. This runner does not implement it. No private records, API credentials, API
generation, production deployment or automatic full training is involved.
