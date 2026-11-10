---
title: "Proposal (STA3145): Review Scheduling on a Dependency Graph"
layout: default
---

# Proposal — STA3145 Reinforcement Learning (team project)

<p><b>Language:</b> <b>English</b> · <a href="https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE_KO.html">한국어</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE_CN.html">中文</a></p>

> Yonsei University · team 6 · v1 2026-11-09
> Phases and the pre-registered decision gate: §8 below. Operational detail:
> [`RL_PLAN.md`](RL_PLAN.html) (with the correction in its §0) · track split: [`TRACKS.md`](TRACKS.html).
> Full narrative: [`PROJECT_EN.md`](PROJECT_EN.html). Course mapping: [`COURSE_ALIGNMENT.md`](COURSE_ALIGNMENT.html).

---

## 1. One paragraph

A research evidence chain is a DAG of dependent AI outputs: a parse feeds a derived variable,
which feeds a metric, which feeds a conclusion. When a human can only check a few nodes, the
question is *which one first*. We formalise that as a finite-horizon MDP with a review budget,
a sparse terminal penalty for errors that reach the conclusion, and a belief over the hidden
error state. The course tools apply directly: bandit (our negative result), MDP (the reframe),
Monte Carlo policy gradient and function approximation (the main method), DQN and PPO as
controls. We instantiate on a real sleep-EMA pipeline (13,990 diary rows, 237 participants,
75 human corrections, 1,048 flagged reviews) and target SciForge's evidence chain as the second
instance. **The headline so far is a negative one, and that is part of the proposal:** a
deployable one-step posterior greedy currently beats every learned policy (1.14 vs 1.56 sink
errors on 200 held-out graphs, paired +0.42 ± 0.15). The project is to find out whether that is
a representation/credit-assignment artefact we can fix, or a real boundary of when RL pays —
and to say which, on a pre-registered test.

---

## 2. The question

### 2.1 Setting

- Nodes produce **dependent** outputs; an error at an upstream node propagates to the sinks.
- A human can review a fixed number of nodes (**budget**); reviewing a node may reveal and fix
  an error there (with a miss rate), which cuts propagation downstream.
- The harm is **delayed and sparse**: it materialises only as wrong sink values, at the end.
- The reviewer cannot see the true error state — only structure, calibrated confidence, and
  the outcomes of reviews already performed.

### 2.2 The first real instance, and what its labels actually are

The sleep pipeline turns daily diary entries (bed / sleep / wake / get-up times) into derived
sleep metrics (SOL, WASO, TST, TIB, efficiency) and a validity verdict per row.

| | count | where |
|---|---:|---|
| rows processed | 13,990 | 237 participants |
| rows the automated audit flagged (rules M1–M6/M7) | 1,048 | `audit_m1_m7_decision.csv` |
| humans confirmed an error in the queue | 68 | 6.5% precision |
| manual corrections in the file | 75 (72 unique keys) | `manual_error_correction_updated.csv` |
| broad label: `human_review == "corrected"` | 85 | 68 of them inside the queue |
| consensus-verified vs single-annotator | 27 / 48 | |

Correction types are heavy-tailed: **`order_error` = 57/75 = 76%** (p < 0.0001), then
`awake_getup_diff`, `bed_sleep_diff`, `sleep_awake_equal`, `24h`.

### 2.3 Provenance caveat — what "AI output" means here

This matters for how the motivation is worded, so it is stated explicitly.

- The 75 corrections are **human corrections to the automated pipeline's per-row output**
  (parsed fields + derived values + audit verdict), not participants correcting themselves.
- But `order_error` is a *field-level* condition: the recorded timestamps violate the expected
  order (get-up before wake, an AM/PM slip, a 24h wrap). The correction restores consistency;
  **the file does not record whether the bad value came from the participant's entry or from
  the parser**.
- Therefore the honest phrasing is **"corrections to automated output"**, not "AI reasoning
  errors". 76% is a fact about *correction types*; it is not yet evidence about *whose* mistake
  it was.

**Action (1 hour, no new data):** ask Maia ten Brink / 동채하 whether a `source` column
(participant entry vs parser vs downstream computation) can be added to the 75-row file. If it
can, the motivation becomes much stronger and the "AI errors cluster" claim becomes defensible.
If it cannot, the talk says "corrections cluster by type" and stops there.

### 2.4 Second instance

SciForge (Zhangyang Gao, AI4Science, Shanghai AI Lab): an evidence DAG of claims, datasets and
runs. The ask is deliberately small — **review receipts** (`reviewed_at`, `verdict`,
`duration_min`, `reviewer_hash`), not the graph, and not write access
(`triage_bench/SCIFORGE_ASK.md`). The sleep side has `resolved_at` on one row only, so review
*timing* and cost cannot be reconstructed from it.

---

## 3. Why this is an RL question (and where the bandit stops)

A per-item bandit treats reviews as independent pulls and **flattens the graph**. Our V1
negative result is exactly that: tabular Q-learning 3.38 vs a confidence threshold 2.81. The
graph is the whole point — a review upstream cuts propagation to many sinks; a review on a sink
fixes one row. Sequential state, delayed reward, and budget coupling are what make it an MDP
rather than a ranking problem.

The real-data queue sharpens the same point: a *static type rule* reaches 83.8% of reachable
errors at k=200 and that is the ceiling for type information. Ordering is not a bandit problem,
and — on this queue — it is barely a ranking problem either: the residual sits in the detector
(17 corrections never flagged at all).

---

## 4. MDP

| element | definition |
|---|---|
| state $s_t$ | per node: type, calibrated confidence, sink reach, reviewed?, flagged?, $P(\text{base error})$, $P(\text{error})$ from the particle filter; plus remaining budget |
| action $a_t$ | review an unreviewed node (and, in the CMDP variant, stop) |
| transition | reviewing reveals an error with probability $p_{catch}$; a fix removes the base error and recomputes propagation |
| reward | terminal only: $-\#\{\text{sink errors}\}$ (CMDP variant: cost per review, Lagrange multiplier) |
| horizon / discount | $H = B$ (budget, 16 in the main setting); $\gamma < 1$ to bias early upstream reviews |

Belief: a particle filter (1,024 particles) over base errors and edge coins; it updates on every
review outcome and is the only error-state information a deployable policy gets
(`experiments/belief.py`).

---

## 5. Methods

| family | method | role |
|---|---|---|
| static | calibrated per-type confidence threshold | baseline (1.41 held-out) |
| static | structural greedy (likelihood × downstream influence) | baseline (1.45) |
| adaptive, model-based | **belief greedy**: argmax of exact expected sink-error reduction under the posterior, re-planned after each outcome | **the bar to beat** (1.14) |
| tabular | Q-learning bandit | negative result (V1) |
| value-based | DQN | control (degenerate, 5.05) |
| policy gradient | REINFORCE with an MLP scorer | preliminary (1.60) |
| policy gradient + FA | GNN scorer + REINFORCE, static state | main learned method (1.56) |
| policy gradient + FA | GNN + REINFORCE, **observed state** (belief features) | test of "features are the gap" (1.56, −0.00 ± 0.08 vs static) |
| constrained | CMDP + PPO-Lagrangian, soft budget | in progress (naive 2.15, seed-sensitive) |
| ceiling | oracle greedy (reads the true error state) | not a policy — a bound |

**The comparison that matters.** Belief greedy is not a featureless heuristic: it evaluates the
exact one-step value under the same posterior the policy sees. Competing with it is competing
with a planner that has the model — which is why the project is framed as "when does learning
pay", not "can we fit a policy".

---

## 6. Evaluation protocol

| setting | scale | protocol |
|---|---|---|
| synthetic main | N≈80, budget 16, 80-node graphs | 200 held-out graphs (1000–1199), 5 training seeds × 20k episodes, **paired per graph** on the same catch-randomness stream |
| synthetic scaled | N=500, budget 50 (10%), modular / BA / ER | heuristics + belief greedy; RL not yet trained at this scale (stated as a limit) |
| real pipeline DAG | N=21, budget 8 | 8 seeds, threshold vs hub vs random vs no-review (belief greedy not run at this size) |
| real review queue | 1,048 flags / 68 positives | recall@k with participant-clustered bootstrap; **no simulator** |
| reliability | — | worst-of-n next to the mean; paired CIs; seed spread |

Every number must be reproducible from a script; tables are generated, never hand-typed.

---

## 7. What we have so far

### 7.1 Synthetic main result (held-out, n=200, paired)

| policy | mean sink errors | 95% CI |
|---|---:|---:|
| no review | 5.90 | — |
| confidence threshold | 1.41 | ± 0.25 |
| structural greedy | 1.45 | ± 0.22 |
| **belief greedy** | **1.14** | ± 0.20 |
| GNN + REINFORCE (static) | 1.56 | ± 0.29 |
| GNN + REINFORCE (observed) | 1.56 | ± 0.15 |

### 7.2 Real data — already run (aggregate only; no row-level data in the repo)

**(a) The lab's own pipeline.** Encoded from the splsleep SCHEMA: N=21 nodes, budget 8, λ=0.9,
8 seeds, error types matched to the 75 corrections.

| policy | sink errors |
|---|---:|
| no review | 2.12 |
| random | 1.88 |
| hub (highest child count) | 1.75 |
| **calibrated confidence threshold** | **0.50** |

This is the application result: on the *actual* pipeline a threshold nearly clears conclusion
errors. It also says the 21-node graph is tabular-sized — value iteration is still an unrun
baseline we can add.

**(b) The real review queue.** 1,048 flagged rows, 68 human-confirmed errors (6.5% precision),
participant-clustered bootstrap:

| policy | R@50 | R@100 | R@200 | R@400 |
|---|---:|---:|---:|---:|
| the pipeline's own order | 4.4% | 5.9% | 13.2% | 23.5% |
| random | 4.4% | 11.8% | 19.1% | 39.7% |
| one rule: M1-bearing flags first | 23.5% | 54.4% | **83.8%** | 83.8% |
| oracle (needs the labels) | 73.5% | 100% | 100% | 100% |

The pipeline's own order is **worse than random** at k=400. One type rule reaches 84% of all
reachable errors in 13% of the queue — and that is the **type-only ceiling**, not a victory: no
type-only policy can pass it, because the remaining block is exchangeable at 1.2%. Ranking
participants reaches 91.2% at k=400 but is not significantly better than the row rule
(+7.3% [−8.6%, +10.0%]). Errors do cluster inside participants (variance/mean 1.998 vs a
label-shuffle null of 1.097, p = 0.0005; 203 participants, 46 with at least one error, max 7).

**(c) The 75 corrections — what the real errors look like.**

| | value |
|---|---|
| corrections | 75 rows (72 unique keys); 0.54% of 13,990 |
| agreement | 27 consensus / 48 single-annotator |
| dominant type | `order_error` 57/75 = **76%** (entropy 0.612, p < 0.0001) |
| what that type is | timestamps in an impossible order (get-up before wake, AM/PM slip, 24h wrap) |

**Caveat (§2.3):** the file records the *type of fix*, not whether the participant or the parser
produced the bad value. Say "corrections to automated output", not "AI errors".

### 7.3 Bottleneck ablation

Confidence **noise 3.78 / normal 1.38 / oracle 0.72** — the signal, not the policy, is the
binding constraint. The real queue shows the same shape: the ceiling is type information, 17
corrections are never flagged at all, and inside the residual block a grouped model reaches
AUC 0.467 (no headroom).

**Current honest reading:** the learned policy loses to a model-based greedy; the posterior is
already in its state; the remaining error mass is in the signal/detector.

---

## 8. The decision point — one week, two gates, one decision

The whole decision runs inside **one week: Mon 11/09 → Sun 11/15**, numbers frozen 11/16.
The two gates run **in parallel the same night**; they are not sequential, and nobody waits
for a "phase" to end before starting the next one.

### 8.0 What is already run (do not run it twice)

The "observed state" GNN already receives the belief posterior — `P(base error)`, `P(error)`,
`reviewed`, `flagged`, budget fraction — refreshed after every review
(`rl_gnn_multiseed.py:features`). It changed nothing: 1.56 vs 1.56 static, paired
**−0.00 ± 0.08**. So *"feed the belief into the policy"* is not an open experiment
(despite how `RL_PLAN.md` §0 first framed G0). The open variables are narrower:

- **(a) the value, not the belief** — the greedy argmaxes `gain(i)`, the exact expected
  sink-error reduction under the posterior; the policy never sees that quantity.
- **(b) credit assignment** — terminal-only REINFORCE over 16 steps with a sparse reward.
- **(c) the regime** — a one-step exact-posterior greedy is hard to beat when the generative
  model is correct. Learning's advantage has to be shown where the model is wrong.

### 8.0b Preliminary: the policy can represent the rule

Run on 11/10 with `experiments/rl_distill.py` (belief greedy as teacher → behaviour cloning → REINFORCE fine-tune), 1,200 teacher graphs, 5 BC epochs, 200 held-out graphs, 3 seeds:

| policy | held-out sink errors |
|---|---:|
| belief greedy (teacher) | 1.15 ± 0.21 |
| BC only | **1.21 ± 0.05** |
| BC + REINFORCE, lr 3e-3, 20k episodes | 1.62 ± 0.41 |
| BC + REINFORCE, lr 1e-4, 5k episodes | 1.24 ± 0.10 |

**Reading.** Representation is not the gap: when the policy only imitates, it matches the teacher. Aggressive fine-tuning destroys that policy (and is unstable across seeds); gentle fine-tuning keeps it. That is credit assignment, and it points at Option A — initialise from the teacher, regularise the update, then try to pass it.

**Caveat.** One configuration family, 3 seeds, not yet rerun by a second person. Preliminary, not a table for the paper.

### 8.1 Gate 0 — representation (code 11/09, run 11/10, ~30 min of compute)

Add `gain(i)` (and optionally the 2-step gain) to the node features; retrain the observed
variant; same 200 held-out graphs, same paired protocol, 5 seeds.

| result | reading | next |
|---|---|---|
| policy matches greedy (≤ 1.14 or non-inferior) | the gap was representational | Option A now has to *beat* a one-step planner — depth or model error (8.3) |
| still ≈ 1.5 | the gap is credit assignment | Gate 1 (8.2) has already run the same night — read it together, do not queue it |

Also report held-out error against training episodes: if it is still falling at 20k, the gap is
data/compute, not architecture — and that changes Gate 1.

### 8.2 Gate 1 — credit assignment (same night, second lane)

Runs **with** 8.1, not after it. One-week cut: the only new variant is **(1A) n-step /
actor-critic with `gain` as the baseline**, so the advantage is `G_t − gain(a_t)`.
Behaviour cloning (1B) and the PPO retune (1C, existing PPO did not converge at ~5.60) are
dropped unless 1A is inconclusive on the first night.

**Pre-registered decision rule** (same 200 held-out graphs, paired, 5 seeds).
**Decision: Wed 11/11, 18:00, one page, numbers only.**

- **PASS → Option A** if the best variant has mean **≤ 1.14**, or is non-inferior (paired CI
  contains 0 and point estimate < +0.05), **and** it wins in at least one condition where the
  greedy's model is wrong (8.3).
- **FAIL → Option B** if the paired gap is still **≥ +0.20 with a CI excluding 0**. Stop there:
  no fourth variant.

### 8.3 Option A requires beating the planner, not matching it

Matching a planner that has the model proves nothing about learning. Three conditions, all
cheap in the existing simulator, plus one control that decides the story:

| condition | breaks for greedy | exploitable by learning |
|---|---|---|
| edge probabilities off by ±50% | `gain` uses the wrong propagation | outcomes reveal the true rate |
| non-stationary type rates | the fixed prior goes stale | online adaptation from flags |
| reviewer miss rate 30% | belief updates over-trust negative evidence | learned discounting |

**Control: 2-step greedy.** If deeper lookahead also wins, the result is "planning depth", not
"learning" — and it must be reported as such.

### 8.4 Option B — four claims, each falsifiable

| # | claim | test | disproof |
|---|---|---|---|
| C1 | gap is representational | Gate 0 | gain features leave it unchanged |
| C2 | gap is credit assignment | learning curves; 1A/1B | a variant reaches greedy without extra structure |
| C3 | with a correct model, 1-step posterior greedy is near-optimal | oracle − greedy gap; 2-step gain | 2-step greedy is much better (greedy is myopic, not optimal) |
| C4 | the binding constraint is the signal, not the policy | ablation (3.78 / 1.38 / 0.72); real-queue ceiling 83.8% | a better policy closes the gap at fixed signal |

Either branch produces a complete course project. Branch B is not a fallback narrative: it is a
measured boundary on when model-free learning pays, and it is checked against a stronger
planner than most course baselines.

---

## 9. Course coverage

| course week | topic | where it appears |
|---|---|---|
| W1–2 | bandit, regret | V1 negative result (Q-learning loses to a threshold) |
| W2 | finite MDP, Bellman, delayed reward | the reframe (§4) |
| W3 | DP / policy evaluation | optional N=21 tabular baseline (not run yet) |
| W4 | Monte Carlo returns | GNN + REINFORCE |
| W5 | TD, Q-learning | V1 Q-learning; DQN control |
| W8 | function approximation | MLP scorer → GNN |
| W9 | policy gradient, REINFORCE, baseline | main learned method; paired held-out evaluation |
| — | PPO / CMDP + Lagrangian | policy-gradient variant and the soft-budget extension |
| — | exploration, multi-seed, worst-of-n | evaluation protocol (§6) |

Not used: VAE / diffusion (different module) — deliberately not forced in.

---

## 10. Deliverables and timeline — one week, seven days

Everything lands by **Sun 11/15**; 11/16 is freeze only. The talk is **Mon 11/23** — the week
in between (11/17–11/22) is rehearsal and polish, not more scope.

| day | date | lane 1 (env / RL, people 2–3) | lane 2 (baselines / write-up, people 4–5) | gate |
|---|---|---|---|---|
| D0 | Mon 11/09 | freeze env; land `gain` feature, n-step/AC, misspecification hooks; 1-seed smoke test | verify every number regenerates from scripts; data-absent path | code merged |
| D1 | Tue 11/10 | **run both gates overnight**: static / observed / gain (5 seeds), terminal vs n-step vs AC-baseline (5 seeds) | table shell + figure scripts; provenance question to Maia | — |
| D2 | Wed 11/11 | **read-out, decide A/B by 18:00**, one-page memo | — | **decision** |
| D3 | Thu 11/12 | branch work: A = misspecification (λ ±50%, drift, catch 0.7) · B = diagnostics (advantage/contribution, return variance, curve slope) | implement **2-step greedy** control (needed by both branches) | — |
| D4 | Fri 11/13 | branch runs (5 seeds each, overnight) | controls: shuffle / flatten; worst-of-n table | — |
| D5 | Sat 11/14 | numbers frozen; learning curves; paired CIs | figures + table regeneration; clean-clone rerun of one seed | numbers frozen |
| D6 | Sun 11/15 | draft §results, negative-result section | slides + one rehearsal | draft |
| D7 | Mon 11/16 | buffer only — fix anything the clean-clone rerun breaks | second rehearsal | freeze |
| — | Tue 11/17 – Sun 11/22 | polish only; no new experiments | slides, ≥2 full rehearsals, timing | talk ready |
| — | **Mon 11/23** | — | — | **final presentation** |

**Deliverables:** code that runs from a clean clone (data auto-skips if absent), a generated
results table, the held-out paired evaluation, the negative-result or Option-A section, and the
talk.

**If the week slips, cut in this order** (never cut the control): (1) the transfer set,
(2) the drift condition, (3) PPO/CMDP, (4) the N=500 rerun. The 2-step greedy control and the
paired CIs are not optional — without them neither branch is interpretable.

---

## 11. Risks

| risk | mitigation |
|---|---|
| gate fails and the talk reads as "we failed" | branch B is specified up front with falsifiable claims; the gate is pre-registered, so the decision is evidence, not mood |
| RL does not converge in time (PPO at ~5.60) | Phase 1 has a stop rule; the deliverable never depends on a single run |
| real data unavailable on presentation day | everything is reproducible from synthetic + aggregates; data auto-skips |
| teammates' time | phases are sized in days, each with a named owner |
| someone over-claims "AI errors" | §2.3 provenance caveat; wording fixed in the docs |

---

## 12. Honest limits

- Main experiments are **synthetic**; real data motivates the problem and supplies one
  application result (N=21) plus one real queue analysis.
- The 75 corrections are 0.54% of rows — enough for a motivation, not for training.
- The GNN is not trained at N=500; the scaled results are heuristics.
- The learned policy currently loses; the CMDP variant is seed-sensitive; the dual-critic
  version is not built.
- All numbers were produced by an AI agent and have not been independently reproduced by a
  teammate yet. `PROJECT_EN.md` §12 lists the checklist.
