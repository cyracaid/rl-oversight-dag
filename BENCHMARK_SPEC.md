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
| validation | 60000–60029 | model selection only (`BestValidation`); never reported |
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

This is a different axis from §6 above. Here the confidence *signal* is shifted, and the policies below try to
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

## 9. Open gaps

1. `type_prior` and `oracle` were missing from the role 3 table while present in role 2. Fixed 2026-11-24:
   the suite is regenerated in `outputs/v3-baselines/`. `type_prior` is far worse (3.76 on spike); `oracle`
   is better (0.52), and its 5–7-error gap at N=500 is now the largest measured headroom.
2. No learned baseline outside `spike`. **Closed 2026-11-24**: `run_learned_baselines.py` trained 3 seeds ×
   5 families at the same budget (GNN 1,000 / DQN 300 episodes), evaluated into `outputs/v3-learned/`.
   `marginal` wins on all six families; the gap widens with `n` (+0.04 to +0.08 at N=21, +5 to +17 at N=500).
3. `marginal` uses a mean-field approximation that drops shared-ancestor correlation. An exact
   intervention value is the cheapest honest way to strengthen the rule; it is unmeasured.
4. Confidence is synthetic. No measured calibration exists for the real pipeline (Gap D).
5. `triage_bench` proves an information ceiling (7 of 72 corrections are never flagged), not a scheduling
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
```

`outputs/v3/` is frozen at tag `role3-env-v3` and must not be overwritten.
