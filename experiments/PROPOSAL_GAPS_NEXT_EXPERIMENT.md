# Proposed next development comparison

Status: implementation authorized; full comparison not yet executed.
Written after inspecting full-v1 and replay diagnosis. This is a post-result
development study, not confirmation or preregistration.

## Question and competing explanation

Under uniformly random confidence, the learned three-step policies concentrate
77–83% of reviews on the highest base-error-rate type. Can a simple type-prior
policy explain their descriptive advantage over nominal belief greedy?

## Proposed controls

1. Original nominal belief greedy, unchanged.
2. Type-prior belief greedy: replace only the confidence-derived initial base-error
   prior with `P_TYPE[node_type]`; retain particle count, graph, propagation model,
   catch model, observation updates, budget and greedy decision rule.
3. Type-prior ranking: rank unreviewed nodes by `P_TYPE[node_type]`, breaking ties
   by node index. No posterior or graph planning. Freeze this rule before running.
4. Frozen observed/nstep3 and gain/nstep3 checkpoints, all five training seeds.

New baseline priors must never read latent errors. Truth may be used only for
diagnostics. Do not alter `belief.py`, the original training code, or frozen
analysis protocol. Implement controls in a separate opt-in script.

## Scope and reporting

Use existing development graphs 1000–1199, all six original confidence/schedule
conditions, 16 reviews, original graph-specific catch draws and drift odds
`1 + index/199`. Preserve all conditions, seeds, graph-level outcomes and source
hashes. No fresh training is needed. Do not inspect graphs 2000–2199.

Report residual sink errors and paired differences against original greedy and
each new baseline, separately by condition and learned seed. Preserve action/type
frequencies, realized terminal benefit and unsupported-positive counts, normalized
per episode/review. Distinguish a single baseline trajectory from five learned
seed trajectories. Never interpret policy-dependent degeneracy subsets causally.

Analysis fixed before implementation and execution: descriptive means only, no
confidence intervals, significance tests, equivalence margin or success threshold.
For each condition and each learned seed report the graph-paired mean error
difference against each of the three baselines. Also report an equal-weight
five-seed aggregate, clearly distinguished from individual seeds. Baselines have
one trajectory per graph and are not duplicated to manufacture sample size.
Smoke runs use the first N original graphs and retain drift odds index/199.
Do not change the full-v1 frozen analysis to accommodate new controls.

Type-prior belief uses the original graph-specific particle seed (graph+10000),
particle count and independent type rates even under drift (no true odds access).
Simple type ranking has no posterior: degeneracy fields are null, not zero.
Save stepwise records for all policies and preserve truth only as diagnostic
fields. Source/checkpoint mismatch or reference replay mismatch must abort; never
mark partially completed output as completed. Existing output reuse is refused.

If inexpensive controls match or improve learned performance, describe the noise
finding as consistent with a type-prior/model-specification explanation. A remaining
learned advantage would motivate additional tests; it does not itself demonstrate
long-horizon planning. No equivalence claim follows from a small mean difference.

## Subsequent work

Small graphs and short horizons: compare greedy, short lookahead and feasible
exact planning under explicitly matched information to measure available planning
benefit. Specify separately before execution. Only after development decisions
are settled should an independent confirmation design freeze candidate, criteria,
fresh training seeds if needed, and reserved graph use. Clean-clone teammate
reproduction and SciForge real-system acceptance remain separate outstanding tasks.
