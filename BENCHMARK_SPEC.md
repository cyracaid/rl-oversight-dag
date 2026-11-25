# Benchmark specification — budgeted review scheduling on a dependency DAG

Status: **frozen for reporting** (2026-11-24). Canonical code: `role3 improvement/` (environment tag
`role3-env-v3`). Canonical measurements: `role2_규리/results/`. Read
`CROSS_IMPLEMENTATION_VALIDATION.md` before quoting a number from another line.

This file exists because "run a benchmark" is ambiguous in this repo. Three different artefacts have been
called a benchmark; only the first is a runnable result.

| Artefact | What it is | Runnable | May be reported |
|---|---|---|---|
| `role3 improvement/run_benchmark.py` | the synthetic DAG suite below | yes | **yes — primary** |
| `triage_bench/` | real sleep review queue, recall@k | yes (private data) | yes — external validity / ceiling only |
| `SCIFORGE_TRUST_BENCHMARK_DEBATE.md` | proposed claim-verification benchmark | no | no — design draft |

---

## 1. Task

**Budgeted node-review scheduling on a fixed dependency DAG.**

Given a graph with public confidence scores and a review budget `B`, a policy selects `B` distinct nodes,
one per step, without replacement. A reviewed node that carries a *local source error* is corrected with
probability `p_catch = 0.9`; inherited errors persist until their upstream source is corrected. Sink values
are recomputed after every correction with the same edge coins (Common Random Numbers across policies).

**Objective:** minimise the number of errors remaining at the declared sink nodes after the budget is spent.
Lower is better. Reward is terminal only: `-sink_errors`.

The policy sees only public state: node type, published confidence, normalised sink reach, posterior source
probability, mean-field propagated error probability, reviewed/flagged flags, remaining budget, geometry.
Source errors, edge coins, reviewer uniforms and sink truth are hidden.

## 2. Frozen suite

| family | n | budget | sink set | purpose |
|---|---:|---:|---|---|
| `spike` | 80 | 16 | last layer (20) | primary study |
| `modular` | 500 | 50 | childless nodes | scale / community structure |
| `ba` | 500 | 50 | childless nodes | scale / hubs |
| `er` | 500 | 50 | childless nodes | scale / random |
| `real` | 21 | 8 | 4 declared sinks | sleep pipeline (fixed topology, prior rates) |
| `ticket` | 21 | 8 | 4 declared sinks | hypothetical ticketing pipeline (synthetic prior, no real data) |

Do not change `n` or budget per family when reporting. A run at another budget is a different benchmark and
must be labelled as such.

## 3. Splits

Test graphs are generated from the family generator; episodes are sampled from the test seed.

| block | seeds | use |
|---|---|---|
| test | 90000–90099 | the reported table (`run_benchmark.py --start-seed 90000 --seeds 100`) |
| validation | 60000–60029 | model selection only (`BestValidation`); never reported; 60000–60023 since shared with the DP block, see note |
| training | 1–3 (seed), disjoint ranges | the `--seed` flag, not a graph block |
| calibration | 70000–70099 | rank-restoration reference distribution only |
| development | 1000–1999 | development |
| confirmation A | 2000–2199 | untouched confirmation (role 2 confidence study) |
| corruption dev | 3000–3199 | corruption boundary sweep |
| probe confirmation | 3200–3399 | pre-registered probe-then-decide |
| repair (per-node) | 3400–3599 | `shrink-v1`, node-level posterior |
| repair (per-graph) | 3600–3799 | `scope-v1`, one shared δ per graph |
| repair boundary | 3800–3899 | `scope-robust-v1`, off-grid δ and two δ |
| reviewer hit rate | 4000–4199 | pre-registered `p_catch` sweep |
| third architecture | 4200–4399 | pre-registered PPO (`outputs/ppo-v1/`) |
| sampled counterfactual value | 4400–4599 | pre-registered one-step value check, `outputs/value-v1/` |
| void | 4600–4799 | smoke runs only (4600–4603); excluded from every result |
| belief values | 4800–4999 | pre-registered logit-temperature grid (`outputs/belief-v1/`) |
| depth-two planning | 5200–5399 | pre-registered planner, `outputs/planning-v2/` |
| exact DP ceiling | 5000–5023 | `outputs/dp-ceiling-fresh/` (rerun; the first run sat on the validation block) |
| label-free contrastive pilot | train 5024–5119, eval 5120–5159 | `outputs/contrastive-v1/`, `PREREGISTER_CONTRASTIVE.md` |
| coverage receipt | 5400–5599 | pre-registered receipt / deletion test, `outputs/supervisor-v1/` |
| prohibited-loop ablation | graphs 5730–5829 | pre-registered `PREREGISTER_DRIFT.md`, confirmatory run `outputs/drift-v1/` |
| prohibited-loop replication | graphs 5600–5699 | run of the same frozen code, kept as `outputs/drift-v1-blocka/` and labelled replication: the block was already spent as episode seeds by ordered v2 / v2.1, so it cannot carry the confirmatory claim |
| order-aware benchmark (v2) | graphs 5160–5183, episodes 5600–5639 | `PREREGISTER_ORDERED_BENCHMARK.md`; gate read 2026-11-25, **both AUC verdicts void**, see `outputs/ordered-gate-v2/CORRECTION.md` |
| order benchmark v2.1 | graphs 5184–5195, episodes 5640–5699 (60, q=1.0) | `PREREGISTER_ORDERED_BENCHMARK_V21.md`; H1 holds, **H3 contradicted**, `outputs/ordered-gate-v21/CORRECTION.md` |
| order benchmark v3 | none consumed | **not built**: `k ≥ 2` transpositions are solved exactly by rank-vs-index, `role3 improvement/outputs/ordered-v3-design/DESIGN.md` |
| information accounting | none consumed | closed form, no sampling: `role3 improvement/analyse_information_budget.py`, `outputs/information-v1/` |

Note on 60000 (2026-11-24): `role3 improvement/PREREGISTER_DP.md` calls 60000–60023 "never used by anything in
the repo", and that sentence is wrong — `dag_role3/training.py` draws `BestValidation` graphs from 60000 onward.
The overlap does not touch the DP claim, because the exact optimum solves a fixed belief model with nothing fitted,
but the validation block must be treated as partly spent: future validation uses **60100–60129**, and no DP number
may be cited as coming from a block that was clean. The ceiling was therefore rerun on 5000–5023
(`outputs/dp-ceiling-fresh/`); the 60000–60023 run stays as a sensitivity check and is labelled as such everywhere.

Reading rule (adopted 2026-11-25, after three separate numbers were shaped by it): any quantity about a defect
that affects only some episodes is computed **inside the affected episodes**, and reported next to its
unconditional version, never instead of it. A pooled mean over mostly-clean episodes dilutes the effect; a pooled
AUC over them measures incidence detection, not localisation.

Rules: a seed block is spent once it has been used to choose a method or a threshold. Never re-tune on the
reporting block. Do not report a mean from one block next to a mean from another block — raw means differ
across blocks (confirmation A is an easier set: marginal 1.130 → 0.885) while paired deltas transfer.

## 4. Metric

Primary endpoint: **mean residual sink errors**.

Secondary (must accompany the primary, not replace it):

- `p95_sink_errors`, `zero_error_rate`
- `mean_saved_vs_none`
- paired difference against `confidence`: `gain_vs_confidence` with a 95 % interval
- `wins / ties / losses` against `confidence`

Interval procedure (as implemented in `run_benchmark.py::interval`): resample complete paired episodes in
20 batches × 100 draws at fixed seed 411; take the 2.5 / 97.5 quantiles of the concatenated means. Episodes
are paired across policies, so graph-level variation cancels. Quote the interval, never the mean alone.

## 5. Baseline matrix

Five layers. A table that omits a layer must say so.

| layer | policy | reads hidden truth | deployable | status |
|---|---|---|---|---|
| L0 reference | `oracle` | **yes** | no | truth-reading `marginal`; a reference point, not a guaranteed bound |
| L0 lower bound | `none` (no review) | no | reference | in table |
| L1 no information | `random` | no | yes | in table |
| L2 static heuristic | `confidence` (lowest first) | no | yes | in table |
| L2 static heuristic | `hub` (max out-degree) | no | yes | in table |
| L2 static heuristic | `structural` (confidence × sink reach) | no | yes | in table |
| L2 external-method proxy | `structural` ≈ influence-weighted uncertainty sampling (ActiveClean family) | no | yes | **name it as the external proxy in text** |
| L3 type-only | `type_prior` (highest base rate for the node type) | no | yes | added 2026-11-24 |
| L4 graph-aware rule | `marginal` (mean-field expected sink-error reduction) | no | yes | in table — **current best** |
| L4 graph-aware rule | `adaptive_marginal` (choose signal model from public confidence, then `marginal`) | no | yes | role 2 only |
| L4 belief | particle-filter belief greedy (`OversightEnv(..., particles=1024)`; not wired into `run_benchmark.py`) | no | yes | available in env, not in the suite table |
| L5 learned | `dqn`, `gnn` (static and observed state), BC+FT | no | yes | all 6 families, 3 training seeds (`outputs/v3-learned/`) |
| L5 learned | `ppo` (GNN actor, clipped surrogate, value baseline) | no | yes | `spike` only, 3 training seeds, fresh block 4200–4399 (`outputs/ppo-v1/`) |

Learned-baseline coverage is complete as of 2026-11-24: 3 training seeds × 6 families, same budget as the
original `spike` runs (GNN 1,000 episodes, DQN 300). The comparison against `marginal` is in
`outputs/v3-learned/learned_vs_marginal.md`. Result: no learned seed beats `marginal` on any family.

## 6. Current standing (2026-11-24, test block 90000–90099, 100 graphs per family)

Rules + truth-reading reference, `outputs/v3-baselines/benchmark_summary.csv`:

| family | `marginal` | `confidence` | `type_prior` | `oracle` | headroom (marginal − oracle) |
|---|---:|---:|---:|---:|---:|
| spike | 0.66 | 1.03 | 3.76 | 0.52 | 0.14 |
| modular | 8.78 | 10.59 | 26.09 | 3.78 | 5.00 |
| ba | 20.13 | 29.65 | 67.76 | 13.28 | 6.85 |
| er | 16.76 | 21.75 | 37.60 | 9.84 | 6.92 |
| real | 0.47 | 0.50 | 1.79 | 0.39 | 0.08 |
| ticket | 0.29 | 0.32 | 0.90 | 0.28 | 0.01 |

`oracle` is truth-reading `marginal`: a reference point, not a bound and not deployable. Its gap to
`marginal` is the part of the rule that the mean-field approximation loses. That gap is small at N=80 and
N=21 and **large at N=500** (5–7 sink errors). Improving the rule, not the learner, is where the measurable
headroom is.

Pairwise against `confidence` on `spike` (paired 95 % interval, 100 episodes):

| policy | mean | Δ vs confidence | interval | W/T/L |
|---|---:|---:|---|---|
| `oracle` | 0.52 | +0.51 | [+0.33, +0.71] | 26/74/0 |
| `marginal` | 0.66 | +0.37 | [+0.20, +0.56] | 21/77/2 |
| `structural` | 1.11 | −0.08 | [−0.26, +0.12] | 10/64/26 |
| `type_prior` | 3.76 | −2.73 | [−3.12, −2.34] | 2/8/90 |
| `hub` | 4.21 | −3.18 | [−3.53, −2.81] | 2/4/94 |

`type_prior` losing by 2.7 errors shows the published confidence score carries real information; dropping it
is not a neutral ablation.

Warning case: on `ba` the mean gain is +9.52 but the split is 39 W / 16 T / 45 L — mean and win rate tell
different stories, so quote both.

`spike` learned policies: GNN 0.96 / 1.06 / 1.17 across training seeds, DQN 1.23 / 1.34 / 1.53. No learned
seed beats `marginal`.

### Learned baselines on all six families

`outputs/v3-learned/learned_vs_marginal.md`. Δ = learned − marginal; negative means the learner is better.
3 training seeds averaged per graph, paired bootstrap, 10,000 draws.

| family | `marginal` | GNN Δ [95 % CI] | W/T/L | DQN Δ [95 % CI] | W/T/L |
|---|---:|---|---:|---|---|
| spike | 0.66 | +0.403 [+0.260, +0.587] | 0/60/40 | +0.707 [+0.533, +0.903] | 0/38/62 |
| real | 0.47 | +0.080 [+0.023, +0.147] | 2/88/10 | +0.193 [+0.123, +0.270] | 1/71/28 |
| ticket | 0.29 | +0.037 [−0.003, +0.090] | 1/93/6 | +0.200 [+0.123, +0.287] | 0/73/27 |
| modular | 8.78 | +6.257 [+5.513, +7.057] | 1/1/98 | +5.227 [+4.553, +5.920] | 1/1/98 |
| er | 16.76 | +8.947 [+7.557, +10.393] | 4/2/94 | +5.633 [+4.733, +6.597] | 0/3/97 |
| ba | 20.13 | +16.970 [+12.817, +21.557] | 1/0/99 | +14.450 [+12.563, +16.730] | 0/0/100 |

All 36 (family, learner, seed) cells have a positive point estimate. 34 of 36 intervals exclude zero on the
losing side; the exceptions are `ticket` `gnn_s1` and `gnn_s3`, which are ties rather than wins (93–97 of 100
graphs identical). The gap **grows with graph size**: +0.04 to +0.08 at N=21, +5.2 to +17.0 at N=500.

That ordering argues against a pure sample-size explanation (the 500-node families give the learner more nodes
per episode, not fewer), but it does not identify the cause. The candidate mechanism is that the observation
carries per-node confidence plus local geometry, and the mean-field propagation over multi-hop paths has to be
re-derived from terminal reward alone — the same quantity that separates `marginal` from `oracle`. This is a
hypothesis consistent with the numbers, not a measured decomposition.

This closes the last table asymmetry. The headline is now stated as measured: **the rule beats both learned
architectures on every family, in every training seed, at equal budget.**

Provenance: this is a table fill, not an improvement claim. Checkpoints were selected on validation seeds
only (60,000+), training used seeds 1–3, and the reporting block (90000–90099) was spent once. Any future
method claiming a win here needs a block that has not been read; see §7 rule 4.

### PPO, on a fresh block (4200–4399)

Two learned architectures were already losing, and both are REINFORCE or value-based. A fair objection is
that the optimizer, not the information, decided it. `PREREGISTER_PPO.md` fixed every hyperparameter before
`train_ppo.py` existed; the block 4200–4399 had not been read by any experiment. Same model class, same
1,000 episodes, same three training seeds, clipped surrogate plus a value baseline.

Δ = PPO − `marginal`, paired over 200 graphs, 10,000 bootstrap draws:

| seed | PPO | `marginal` | Δ [95 % CI] | W/T/L |
|---|---:|---:|---|---|
| `gnn_s1` | 1.225 | 0.875 | +0.350 [+0.230, +0.480] | 2/160/38 |
| `gnn_s2` | 1.335 | 0.875 | +0.460 [+0.335, +0.600] | 3/138/59 |
| `gnn_s3` | 1.340 | 0.875 | +0.465 [+0.325, +0.620] | 2/148/50 |

Verdict `third-loss`: three seeds, all positive, all intervals exclude zero, no sign flip.

P2 missed. The preregistered prediction was that PPO would land between `marginal` and the REINFORCE GNN,
i.e. inside (0, +0.403); the observed mean is +0.425, and two of three seeds sit above the bound. The
difference from REINFORCE (+0.403) is far inside the noise of either interval, so the honest statement is
**PPO is indistinguishable from the REINFORCE GNN, not better than it**, and both are worse than the rule.
The pre-registered falsifier (interval excluding zero on the negative side) did not fire.

One detail worth reading rather than smoothing: 138–160 of 200 graphs are ties. PPO rarely beats `marginal`
and rarely loses badly; it mostly reproduces the outcome. That is a statement about terminal errors, not
about the policy's internal ordering, which this block does not measure.

Absolute means here are not comparable with the table above: different graph seed block. Only the paired
deltas travel, per §7 rule 4.

### Sampled counterfactual value, tested and rejected (4400–4599)

The one-step score in `marginal` is mean-field: it multiplies per-parent probabilities as if parents were
independent, so a shared ancestor is counted once per open path. That is a real approximation error, and the
obvious fix is to replace the score with the true expected gain of a review. That quantity is network
reliability, #P-hard, and the graphs here reach 500 nodes, so it cannot be computed exactly. What *can* be
computed is an unbiased estimate: draw particles of source errors and edge coins, replay each particle with
the candidate's source error removed, and take the within-particle difference. Shared draws make the
difference the gain, not two noisy estimates subtracted.

`PREREGISTER_EXACT_VALUE.md` fixed the block (4400–4599), particles (256), shortlist (16, a compute ceiling)
and the metric before the script existed. `recovery = (marginal − policy) / (marginal − oracle)` per graph:

| family | `marginal` | `oracle` | policy | recovery [95 % CI] | W/T/L | verdict |
|---|---:|---:|---:|---|---|---|
| modular (N=500) | 8.780 | 4.070 | 8.785 | −0.049 [−0.087, −0.015] | 15/155/30 | `worse` |
| spike (N=80) | 0.890 | 0.650 | 0.900 | +0.038 [+0.000, +0.103] | 2/195/3 | `null` |

This is the experiment the §7 gap called for, and it came back negative. On `modular` the policy changed the
action on 45 of 200 graphs and lost 30 of those, so the estimator was not too noisy to move — it moved and
the mean-field ordering was better. On `spike` the ratio mean is positive while the aggregate gap moved
backwards by 4.2 %, because the ratio mean is carried by one-or-two-error graphs; the report prints both
rather than choosing.

What this rules out is narrow and worth stating precisely: improving the *one-step* value estimate with the
right correlation structure does not recover the `oracle` gap. That leaves two mechanical explanations — the
belief's numbers, or what a myopic policy cannot see. The first was tested next; the second is still open.

Known limit of the estimate: 256 particles with a 16-node shortlist. Both numbers were frozen by the
pre-registration as a compute ceiling, so this is evidence against the *approach at this budget*, not a proof
that exact values would not help.

### Belief values: the gap is not a probability scale error (pre-registered, 4800–4999)

`PREREGISTER_BELIEF_DECOMPOSITION.md` fixed the cheapest remaining test. `marginal` and `oracle` share rule,
budget and horizon; only the prior differs. So keep the belief's **ranking** bit-identical (one strictly
monotone map on every node, so per-graph AUC cannot change) and distort only its **values** with
`q_i(γ) = sigmoid(γ · logit(belief_i))`. `γ = 1` reproduces `marginal` exactly, which the run checks per graph.

| family | `marginal` | `oracle` | belief AUC | best γ | recovery there [95 % CI] | aggregate errors closed | W/T/L | verdict |
|---|---:|---:|---:|---:|---|---:|---|---|
| modular (N=500, 200 graphs) | 8.820 | 3.930 | 0.966 | 1.25 | +0.016 [−0.055, +0.072] | −1 of 978 | 46/142/12 | `policy-bound` |
| spike (N=200 graphs) | 1.030 | 0.785 | 0.971 | 1.50 | +0.105 [+0.026, +0.211] | +0 of 49 | 4/192/4 | `calibration-partial` |

On `modular` — where the 5–7-error gap actually lives — the verdict is **`policy-bound`**, and the interval is
still inside zero after a Bonferroni correction over the grid ([−0.082, +0.088]). The positive ratio at
`γ = 1.25` is reshuffling, not recovery: it wins 46 graphs, loses 12, and moves the aggregate by one error in
978. On `spike` the pointwise interval excludes zero, but four wins and four losses close **zero** of a 49-error
gap; the frozen label is `calibration-partial`, and the honest reading is "no net gain at this size".

What this rules out: the gap is not "the forward pass is fed wrong numbers". Within a one-parameter family of
value rescalings, `marginal` sits at the optimum. What it does not rule out: the belief ranks only 0.97, so a
distortion that changes the order (a different belief, not a temperature) is still untested, as is everything
multi-step. The exact-DP ceiling on the rule's own model is pre-registered but has not been run.

### Depth-two planning: the gap is not the horizon (pre-registered, 5200–5399)

`marginal` and `oracle` share rule, budget and *one-step* horizon, so their difference is the value of truth and
cannot contain the value of planning. Pricing the horizon therefore requires changing the policy, not the prior.
`PREREGISTER_PLANNING_V2.md` fixed a depth-two expectimax on the *same* mean-field model, using public inputs
only (belief column, edge probabilities, sinks, mask, hit rate), width 6 then 4 — and two variants, because the
environment's miss update is itself approximate and a planner can profit from that instead of from lookahead.

| family | `marginal` | `oracle` | gap | policy | mean errors | recovery [95 % CI] | aggregate closed | W/T/L | verdict |
|---|---:|---:|---:|---|---:|---|---:|---|---|
| modular (200 graphs) | 8.915 | 4.300 | 923 | `plan2_catch` | 8.940 | −0.009 [−0.023, +0.001] | −5 | 2/191/7 | `informational` |
| modular | | | | `plan2_full` | 11.340 | −0.833 [−1.071, −0.621] | −485 | 10/82/108 | `informational-strong` |
| spike (200 graphs) | 0.860 | 0.615 | 49 | `plan2_catch` | 0.855 | +0.031 [+0.000, +0.094] | +1 | 1/199/0 | `informational` |
| spike | | | | `plan2_full` | 2.155 | −1.188 [−1.646, −0.755] | −259 | 1/76/123 | `informational-strong` |

Three facts, kept apart on purpose.

1. **One more step at this width does not pay.** `plan2_catch` leaves the action unchanged on 191 of 200 modular
   graphs and closes −5 of 923 errors; on spike its interval starts exactly at zero. The frozen label is
   `informational`, the same conclusion the spike-only replay reached in `role2_규리/results/planning-v1/`
   (+0.035, interval through zero). P1 held; **P2 (full ≥ catch) and P4 (myopia-bound) both failed**, and the
   failure of P2 is the informative one.
2. **The miss branch is a trap, and its size is new.** `plan2_full` weights the second step by the environment's
   update `q ← q(1 − p_catch)/(1 − p_catch·e_v)`. That update is a heuristic, not a belief, and a depth-two
   planner reads "this node will probably be missed, so its belief will drop" as an improvement. It costs
   **485 of the 923** available modular errors and 259 of 49 on spike — worse than not planning at all. Nothing
   earlier in this repository measured how exploitable that update is by a planner; this is a statement about
   the update, and it is why the catch-only variant is the one that prices the horizon.
3. **The one-step score is exact for its own objective.** `ES` is multilinear in the beliefs, so
   `ES(B) − ES(B | v fixed) = b_v · ∂ES/∂b_v` exactly; the planner shares that adjoint pass with the rule
   (max difference 4.4e-16, pinned by a test). Depth two is a genuine lookahead on the same model, not a
   reweighted one-step score.

What this rules out: with the value estimate (4400–4599) and the belief's values (4800–4999) already negative,
the three mechanical explanations *inside the mean-field model* are gone — not the number, not the scale, not
the horizon at this width. What it does not rule out: `myopia-bound` was defined as "a second step recovers
more than 40 % of the gap", and width 6/4 with greedy truncation is a compute ceiling rather than an optimum,
so the honest claim is "one more step at this width does not pay", not "no plan exists". `ba` and `er` are not
measured.

**The in-model ceiling, measured where the model is solvable.** A depth-two probe is not a ceiling, so
`exact_dp.py` (`PREREGISTER_DP.md`) solves the same belief MDP exactly on `real` and `ticket` — 21 nodes,
12 graphs, budgets 1–5, block 5000–5023. Two numbers matter here. The *exact* one-step lookahead equals the
rule's derivative score on 12/12 graphs (mean +0.0006), which is the multilinear identity of item 3 above,
measured again through a different code path. And the optimal five-step policy is worth
`dp5 − marginal` = −0.030 [−0.065, −0.008] on `real` (4.2 % of the rule's 0.705) and −0.002 [−0.003, −0.000]
on `ticket` (0.5 % of 0.404). The entire horizon inside the model is therefore worth single-digit percent,
while the `oracle` gap asks for a third to a half of the rule's errors.

Read with the same care as everything else: the DP's miss update uses the local risk instead of the inherited
one (a declared deviation, so that delta is planning *plus* the difference), the graphs are 21 nodes at budget
≤5, and `modular` at N=500 cannot be solved this way — its ceiling stays unmeasured, with the depth-two probe
as the only evidence. `outputs/dp-ceiling-fresh/report.md` (block 5000–5023); the first run on the model-selection
block 60000–60023 is kept as a sensitivity check and moves nothing, and a signed-comparison error in its own P2
check was amended after the run, in the direction that makes the result worse.



### Reviewer hit rate `p_catch` (pre-registered, seeds 4000–4199)

Every run in this repository holds the reviewer hit rate at `p_catch = 0.9`. `PREREGISTER_P_CATCH.md` fixed the
grid and the four outcomes before the sweep ran; `outputs/p-catch-v1/` holds the result, `report_p_catch.py` the
frozen verdict code.

Verdict: **`inverted`**. The sign holds — `marginal` beats `confidence` on all four cells, and all four paired
intervals exclude zero — but the size moves the wrong way against the prediction:

| `p_catch` | `confidence` | `marginal` | `oracle` | Δ marginal − confidence |
|---:|---:|---:|---:|---|
| 0.60 | 3.105 | 2.850 | 2.750 | +0.255 [+0.150, +0.375] |
| 0.75 | 2.300 | 1.950 | 1.775 | +0.350 [+0.220, +0.490] |
| 0.90 | 1.440 | 1.025 | 0.785 | +0.415 [+0.275, +0.570] |
| 1.00 | 0.820 | 0.290 | 0.000 | +0.530 [+0.370, +0.705] |

The mechanism visible in the same table is that `oracle` follows the identical trajectory (+0.355 to +0.820).
So the scaling is a property of the environment, not of `marginal`: fewer hits means fewer corrections actually
land, and every policy's spread contracts with the number of corrections available. This is a description of
the table, not a decomposition experiment.

What may be claimed: the **direction** is robust to the hit rate. What may not be claimed: that the advantage
grows when reviewers are less reliable. The pre-registered prediction said it would, and it does not.

Learned checkpoints were evaluated without retraining, so those rows answer only what a deployed policy does
when the assumed hit rate is wrong. Their intervals stop separating from `confidence` at `p_catch = 0.60`
(+0.080, +0.045, −0.035, all intervals containing zero), which is consistent with the same contraction rather
than with a second, independent finding.

### Corrupted confidence: the repair family (pre-registered, seeds 3000–3899)

This is a different axis from the standing table above. Here the confidence *signal* is shifted, and the policies below try to
decide whether to trust it. All numbers are paired differences against plain trust inside one run; positive
means more remaining errors than trusting. Each step was frozen in a `PREREGISTER_*.md` before its first seed.

| step | policy | fresh graphs | verdict | result vs trusting |
|---|---|---|---:|---|
| global gate | `gate` | 3000–3199 | boundary measured | −1 shift: fires 195/200, **+1.82**; masked +3: 0/200, **+3.21** |
| gate repair | `verify` | 3200–3399 | **failure** | −0.015 on −1, but 5 of 13 fired cells worse than trusting |
| per-node posterior | `shrink` | 3400–3599 | success | +0.105 on −1; **−0.370** where errors are masked; +0.45 / +0.72 on a harmless global +2 / +3 |
| per-graph posterior | `scope` | 3600–3799 | success | +0.005 at +3 (per-node +0.81); 112-cell mean 1.303 → **1.203**; −4 returns to the clean oracle (0.94 vs 3.86) |
| boundary | `scope` | 3800–3899 | **partial success** | off-grid δ: mean \|δ error\| 0.174, 12/12 cells beat per-node; two δ: −0.016 vs per-node, all three policies within 2.15/1.89/1.87 |

Do not read this table as a method win. The last row is the important one: with two simultaneous δ, neither
single-δ family recovers. The declared claim is "the decision variable is the node, then the graph", not
"`scope` is the best repair".


### Order channel (v2, v2.1, v3): built, priced, closed — a monotone chain cannot host the question (5160–5195 / 5600–5699; no block for v3)

The contrastive pilot left one question it could not ask: 40 of 53 replayed human corrections are `order_error`,
and the simulator samples source errors independently, so no ordering structure existed to represent.
`PREREGISTER_ORDERED_BENCHMARK.md` priced the smallest environment in which the question exists and rejected, in
writing, the cheapest way to build it. Two more rejections followed the same day, both recorded before the block
was read: a transposition between *adjacent* positions violates one constraint and leaves both members consistent
with their outer neighbours, and — the one that matters — a transposition at distance ≥ 2 is still solvable from
each node's own two adjacent residual signs, because a single transposition of a monotone chain puts the exchanged
positions exactly at the endpoints of the inverted interval. First-descent / last-ascent recovers the pair
**21/21** at `q = 0.5` and **60/60** at `q = 1.0`, across all three eligible pairs.

The gate was read before that was noticed, and it read **backwards**:

| gate | as read | frozen rule | as read | what it actually measured |
|---|---|---|---|---|
| G1a not local | node AUC 0.599 [0.504, 0.703] | ≤ 0.65 | holds → **void** | within-episode AUC 0.512; 0.767 of it was clean-vs-transposed |
| G1b global | order AUC 0.822 [0.745, 0.894] | ≥ 0.75 | holds → **void** | within-episode AUC 0.500; 1.000 clean-vs-transposed; one distinct feature row per episode |
| G3 noise control | 0.587 | ≤ 0.65 | holds, uninformative | the signal is in the clocks, so ablating confidence moves nothing |
| G2 decision value | −0.100 [−0.250, +0.025] | ≥ 0.15 | contradicted | stands as measured |

Both AUCs were pooled over episodes of which only half were damaged, so they answered "is this episode broken"
rather than "which position is misplaced" — the same dilution that G2's own endpoint suffered. The correction is
`outputs/ordered-gate-v2/CORRECTION.md`; the within-episode split is `outputs/ordered-gate-v2/locality.json`; the
pre-registration's own record is Amendment 2, which withdraws the relational claim rather than the numbers.
Commit `19ebb3f`'s message ("relational and real") is wrong and is contradicted there, since history is not
rewritable.

The conditional-endpoint retry (`PREREGISTER_ORDERED_BENCHMARK_V21.md`, 5184–5195 / 5640–5699) then produced the
result that settles it:

| # | prediction | result | verdict |
|---|---|---|---|
| H1 | recovery `R ≥ 0.50` of the oracle-readable gap | **0.821** [0.630, 0.964] | holds |
| H2 | symptom repair is not the source | **+0.183** [+0.050, +0.350] | holds |
| H3 | not locally solvable (node ≤ 0.65, order ≥ 0.75) | node **0.800**, order **0.500** | **contradicted** |

H1 and H3 are true together, and H3 is the stricter statement: the pair information recovers 82 % of the
oracle-readable gap, and it is reachable from adjacent comparisons. So the gain is "a two-line localisation rule
beats a heuristic that ignores order", not relational state, and **no model experiment is licensed**. Two design
faults are recorded with it: the endpoint's denominator was mostly zero (45 of 60 episodes had no oracle-readable
gap, so the power sentence in that pre-registration was wrong when written), and `run.log` was lost to a `tee`
before `mkdir` — the numbers come from `gate.json`, whose rerun hash is identical, a determinism check rather than
a second sample.

A design study then closed the line without spending a seed (`role3 improvement/outputs/ordered-v3-design/`,
4000 draws per mechanism at `n = 4`). `k ≥ 2` disjoint transpositions do defeat the descent-ascent rule — 0.000 —
and are recovered exactly (1.000) by a third statistic that was never tested: `rank(clock) − position`. That is
not a heuristic. If the truth is strictly increasing and the record is a permutation of the same values, a position
holds its own value iff its value's rank equals its index, so the culprit set is `{p : rank(c_p) ≠ p}` — three
lines, no search, exact for every permutation mechanism, noise-robust at the sampler's own settings (0.998–1.000).
The complementary defect, a ±12 h offset rather than a permutation, is not a permutation at all, and the derived
durations then break at exactly the two nodes that name the shifted segment. Both families of order defect in a
monotone chain are one-pass statistics, so the order channel is **information, not latent structure**: there is
nothing here for a representation to learn, and a third mechanism would have failed the same way with a different
rule. `PREREGISTER_ORDERED_BENCHMARK.md` amendment 3 records the closure and spends no block.

What this settles, therefore, is not "the testbed is hard to build" but the opposite: the simulator can only
express order defects that a two-line rule inverts, which is why v2's gate read what it read. What remains — and
what no file prices — would require corrupting the derived differences themselves, turning the question into robust
estimation with a new family and a different claim, no longer "the real data's failure mode in this simulator".

Nothing in v1 moved: `tests/test_ordered.py` asserts that the v2 sampler with `q = 0` returns the v1 episode
tuple-for-tuple, and the full suite passes (154 tests, including `tests/test_information_budget.py`); `tests/test_ordered_locality.py` pins the defect itself (the two-line local rule scores 100 %, and the relational feature set is broadcast to one row per episode), so neither can be forgotten.

### Information accounting (closed form, no block): the budget is smaller than the repairable entropy

The remaining objection to the null is a framing one: reviews are an *information acquisition* problem, so maybe
the policies are allocating a fixed information budget badly. `role3 improvement/analyse_information_budget.py`
answers it arithmetically — no sampling, no policy run, no block. Every number below is conditional on the
simulator's assumed model (rate table, `p_catch = 0.9`, nominal edge weight `1 − exp(−λ)`, with 0.6 / 1.4 as
sensitivity).

**A review reports `e_j` but repairs `b_j`.** `P(flag | e_j=1) = 0.9`, `P(flag | e_j=0) = 0` is a Z-channel: only
"not flagged" carries information, and it is ambiguous. The repair, however, clears the node's *own* value, so
`P(flag | b_j=0) = 0.9 · inherited_j`. Median `I(B_j;O_j)/I(E_j;O_j)` is **0.33** (`real`) and **0.35**
(`ticket`), 0.16 on node 19: about two thirds of the bits a review delivers are about a variable the review
cannot repair.

**The budget is below the repairable entropy.** `sum H(B) = 14.31` bits (`real`, 12.09 `ticket`); eight reviews at
the per-node ceiling of 0.735 bits total 5.88 — an upper bound of **41 %** (49 %). Sequential reviews correlate, so
the bound is loose, but it is a ceiling, not an estimate.

**Three rankings disagree, and the disagreement is measurable.** With `VoI_j = 0.9 · b_j · Δ_j` and `Δ_j` the exact
finite difference on the forward OR recursion (not the derivative), `real` at the nominal edge weight:

| ranked by | first | value | that node's VoI |
|---|---|---:|---:|
| error probability `p_j` | node 20 | 0.801 | 0.0337 |
| entropy `H(E_j)` | node 10 | 0.997 bits | **0.0000** |
| review information `I(E_j;O_j)` | node 8 | 0.763 bits | 0.0043 |
| repairable information `I(B_j;O_j)` | node 0 | 0.735 bits | 0.0292 |
| `VoI` | node 17 | 0.0735 | — |

Node 10 has the highest entropy *and* the highest review information with exactly zero value of information: it
reaches no conclusion (`sink_reach = 0`). Node 17 is 11th by `I(E)` (0.687 bits) and first by `VoI`. Across the six
settings, Spearman against `VoI` runs −0.16…+0.65 for `H(E)`, −0.18…+0.31 for `I(E)`, −0.04…+0.62 for `I(B)`. So
"information gain ≠ error reduction" is not a possible conflict here; it is a measured mismatch whose sign is not
stable.

Two reporting rules follow, and both are prohibitions:

1. **`H(F)` for the verdict vector `F` is not identified by this environment.** It supplies per-node marginals (the
   forward OR recursion is exact for marginals) and exactly one joint (mean field), while the reward needs only the
   marginals. Entropy is a functional of the joint, so any "residual entropy of the final verdict" is a property of
   the chosen approximation.
2. **`marginal_scores` is a derivative, not an action value.** Its per-node magnitude differs from the exact
   one-step `VoI` by up to 0.21 while the largest exact `VoI` anywhere is 0.098; only the ordering survives
   (ρ = 0.68–1.00). Quote
   it as a ranking, never as an error reduction and never as bits.

What this adds is explanatory, not experimental: the `oracle` gap survives the one-step value estimate, the belief
scale and the horizon because the shortfall is **evidence about the repairable variable**, and the 8-review budget
cannot supply it. That is also the argument for the cheapest real-data action — more annotations, not another
scheduler.

## 7. What counts as progress on this benchmark

A claim of improvement requires all four:

1. Same family, same budget, same sink set, paired episodes.
2. Paired 95 % interval excluding zero against **`marginal`**, not against `confidence`.
3. More wins than losses (the `ba` mean/win-rate split is the warning case).
4. Replicated on a seed block not used to design the method, pre-registered before the run.

A new baseline is not progress. A new benchmark axis is progress only after it is frozen and pre-registered.

## 8. Known dead ends (pre-registered or replicated nulls — do not retry)

| direction | result | source |
|---|---|---|
| two-step planning | +0.035 [−0.025, +0.100] vs one-step | `role2_규리/results/planning-v1/` |
| residual GNN on top of the rule | +0.022 [−0.018, +0.072] | `role2_규리/results/residual-v1/` |
| 10× training budget | still loses: +0.262 [+0.165, +0.365] | `role2_규리/results/confirm-10x/` |
| learned scheduler on all 6 families (3 seeds, equal budget) | loses everywhere: +0.04 (N=21) to +17.0 (N=500) vs `marginal`; 34/36 intervals exclude zero | `outputs/v3-learned/learned_vs_marginal.md` |
| GNN with review outcomes | −0.00 ± 0.08 | `experiments/gnn_vs_greedy_table.md` |
| global corruption gate | fires where harm is smallest; blind to masking | `role2_규리/results/corruption-v1/` |
| probe-then-decide with a global statistic | −0.015 [−0.055, +0.025]; 5/13 fired cells worse than trust | `role2_규리/results/verify-v1/` |
| participant ranking on the real queue | +7.3 % [−8.6 %, +10.0 %] | `triage_bench/CEILING.md` |
| sampled counterfactual value inside the mean-field shortlist | worse: recovery −0.049 [−0.087, −0.015]; 30 graphs worse, 15 better | `role3 improvement/outputs/value-v1/` |
| belief values, order preserved (logit temperature) | `policy-bound` on modular (+0.016 [−0.055, +0.072]; −1 of 978 errors); `calibration-partial` on spike but 0 of 49 closed | `role3 improvement/outputs/belief-v1/` |
| depth-two planning on the mean-field model | closes −5 of 923 `modular` errors (−0.009 [−0.023, +0.001]); spike +1 of 49, interval from zero | `role3 improvement/outputs/planning-v2/` |
| a planner that trusts the environment's miss update | costs 485 of 923 errors on `modular`, 259 of 49 on `spike` | `role3 improvement/outputs/planning-v2/` |
| exact optimal policy inside the rule's own model | closes ≤4.2 % of the rule's errors (`dp5 − marginal` −0.030 [−0.065, −0.008] on `real`, −0.002 on `ticket`; 21 nodes, budget 5, block 5000–5023) | `role3 improvement/outputs/dp-ceiling-fresh/` |

## 9. Open gaps

1. `type_prior` and `oracle` were missing from the role 3 table while present in role 2. Fixed 2026-11-24:
   the suite is regenerated in `outputs/v3-baselines/`. `type_prior` is far worse (3.76 on spike); `oracle`
   is better (0.52), and its 5–7-error gap at N=500 is now the largest measured headroom.
2. No learned baseline outside `spike`. **Closed 2026-11-24**: `run_learned_baselines.py` trained 3 seeds ×
   5 families at the same budget (GNN 1,000 / DQN 300 episodes), evaluated into `outputs/v3-learned/`.
   `marginal` wins on all six families; the gap widens with `n` (+0.04 to +0.08 at N=21, +5 to +17 at N=500).
3. `marginal` uses a mean-field approximation that drops shared-ancestor correlation. **Measured
   2026-11-24, negative four times**: an exact value is #P-hard here, and (a) a sampled counterfactual value
   (paired particles, block 4400–4599) is *worse* than mean-field on `modular` (−0.049 recovery, CI
   [−0.087, −0.015]); (b) an order-preserving rescaling of the belief's values (block 4800–4999) is
   `policy-bound` on `modular` (+0.016 [−0.055, +0.072], one error of 978) and closes nothing on `spike`;
   (c) depth-two planning on the same model (block 5200–5399) closes −5 of 923 `modular` errors
   (−0.009 [−0.023, +0.001]) and +1 of 49 on `spike`, with the action unchanged on 191 of 200 graphs;
   (d) an exact DP ceiling, where the model is small enough to solve, is worth 4.2 % of the rule's errors on
   `real` and 0.5 % on `ticket` (block 5000–5023, 21 nodes, budget ≤5), so the rule is within single-digit percent
   of the optimum *of its own model* while the `oracle` gap asks for a third to a half of its errors. The
   mechanical explanations inside the mean-field model are therefore exhausted, and the residual is attributed
   to the belief's **information**: the public belief ranks the truth at 0.966 AUC while the rule needs the
   mass on the right nodes, which the confidence channel does not carry. Untested and not claimed: a belief
   with more information; and the `modular` ceiling itself, which no DP can reach at N=500. See §6.
4. Confidence is synthetic, and the gap is now understood as a **signal-class** result rather than a data
   gap (Gap D). Entropy is invariant under relabelling, so it cannot separate "the right answer holds the
   mass" from "the wrong answer holds the mass"; every confidence quantity in this family measures
   distance from the uniform distribution, never distance from the truth. Consequences, in order:
   (a) no calibration map repairs it, because the inversion is between subgroups and calibration is a
   marginal operation; (b) raising coverage does not lower the resulting error floor, because the floor is
   set by the reference and new vertices add pairs of the same kind; (c) the measured `false_inspected`
   bucket is the discrete analogue of that floor, priced — 10.2 % under `marginal` and 14.9 % under
   `oracle` on `modular`
   (`outputs/supervisor-v1/`), i.e. better coverage makes it **larger**. The confidence channel is
   therefore routing-only by construction, and the delivery layer's refusal to let it drive status is the
   intended shape, not a missing dataset. Full argument, incl. the permutation-invariance lemma and what
   is *not* claimed: `ENTROPY_LIMITS.md`.

5. Coverage and correctness are orthogonal, and a delivery that reports only coverage overstates itself
   **more** the more it reviews. Do not present a coverage number as a correctness number; the two have a
   measured negative relation on `modular`.

6. Audit objects are narrower than the governance requirement. `p_catch` (independence threshold),
   `inspected` vs `clean` (construct mapping), family membership (perspective set), and the status set
   itself were implicit constants, not adjudicated objects. **Named and frozen 2026-11-25**:
   `AUDIT_POLICY.md` v1 plus `dag_role3/audit_policy.py` (20 tests) — machine may route and propose, only
   a versioned human ratification may move any of the four, and the policy is frozen while an evaluation
   window is open. Note what this changes: the coverage arithmetic in `outputs/supervisor-v1/` now
   produces *proposals*, and no re-run under a different policy is allowed without a fresh block (≥ 5600).
7. `triage_bench` proves an information ceiling (7 of 72 corrections are never flagged), not a scheduling
   win. Do not put it in the same table as the synthetic means.

## 10. Reproduction

```bash
cd "role3 improvement"

# full suite, all six rules plus the frozen spike checkpoints
python3 run_benchmark.py --seeds 100 --start-seed 90000 \
  --checkpoints outputs/v3/train_{1,2,3}/{gnn_spike_observed,dqn_spike}.pt \
  --out outputs/v3-baselines

# rules only (no checkpoints), any family subset
python3 run_benchmark.py --families spike real ticket --seeds 100 --start-seed 90000 \
  --out outputs/rules-only

python3 -m unittest discover -s tests -v

# learned baselines on the other five families, then the rule comparison
python3 run_learned_baselines.py --jobs 4
python3 report_learned_baselines.py

# reviewer hit-rate sweep (16 s, owns graph seeds 4000-4199)
python3 sweep_p_catch.py && python3 report_p_catch.py

# PPO, third learned architecture (3 seeds x 1000 episodes, ~5 min/seed)
for s in 1 2 3; do python3 train_ppo.py --seed $s --out outputs/ppo-v1; done
python3 evaluate_ppo.py --checkpoints outputs/ppo-v1/train_{1,2,3}/ppo_spike_observed.pt
python3 report_ppo.py

# sampled counterfactual value (block 4400-4599, ~6 min)
python3 run_value_check.py && python3 report_value.py
```

`outputs/v3/` is frozen at tag `role3-env-v3` and must not be overwritten.
