---
title: "Review Scheduling on a Dependency Graph — Project Document (English)"
layout: default
---

# Review Scheduling on a Dependency Graph — Project Document (English)

> STA3145 Reinforcement Learning · Group project · Deepened 2026-11-09
> Sleep data: one year of collaboration with Maia ten Brink (Stanford Psychophysiology Lab)
> Application: SciForge, developed by Zhangyang Gao (AI4Science, Shanghai AI Lab)
> Companion versions: 한국어 `PROJECT_KO.md` · 中文 `PROJECT_CN.md`
> Repo: https://github.com/cyracaid/rl-oversight-dag

**Verification status.** Experiment code and numbers were produced by an AI agent and have not been independently re-run by teammates. Unverified items are in Section 12.

**One-liner.** When AI outputs depend on one another and a human can review only a few, we use reinforcement learning to learn which node to review next, so that fewer errors reach the final conclusion.

---

## 1. What changed from the first version

1. **From bandit to MDP.** V1 decided pass-or-review per item. That flattens the graph: a calibrated threshold (2.81) beat tabular Q-learning (3.38). Now the agent picks the next node of a dependency graph; a review changes what happens downstream.
2. **From a proxy dataset to our own data + a synthetic graph.** Real corrections (75 rows) motivate the problem; the main experiments use a synthetic graph.
3. **From a plan to results, then to an upgrade and an honest negative.** We have numbers, controls, a reported failure, a method upgrade whose single-run win does not survive multi-seed (see §8), and an ablation that locates the remaining error in the confidence signal.

## 2. Topic
Under a limited review budget, learn which node of a dependency graph to review first.

## 3. Problem and motivation
AI does much research work (cleaning, labeling). Part of it has no answer key — only a human can judge whether an item is wrong, and a human cannot check everything. Two facts make *what to review* matter more than *how much*:

- **Errors cluster by type.** In our real data, one type (`order_error`) is 76% of corrections (57/75).
- **Unreviewed errors are reused downstream; harm shows only at the conclusion.**

So evidence is a dependency graph. Fixing a node stops its error from spreading; an early upstream review can be worth several downstream reviews.

## 4. Inside SciForge: which part of the evidence chain

SciForge already has an evidence DAG (claim–evidence provenance), human-review receipts, and an audit layer. This proposal adds a **review-priority suggester on top**, changing no record-keeping rules.

| Concept | SciForge | Notes |
|---|---|---|
| Dependency graph | Evidence DAG | nodes = claims, conclusions, dataset versions, analysis runs |
| Error propagation | `derived_from`, `supports` edges | `contradicts` is not a propagation direction |
| Conclusion (sink) | the conclusion node to deliver | keep errors from reaching it |
| One review | one human review → a receipt | fields set by the evidence-chain owner |
| Review budget | items a human can review per cycle | — |
| RL output | ranking of "review next" | suggestion only; no stamp, no receipt |

**Three boundaries (not relaxed by adding RL):** the machine never stamps; the suggester is read-only / append-only; comments and receipts are separate.

**Unconfirmed:** whether nodes have a usable confidence field; whether the real graph matches the synthetic assumptions (≈80 nodes, type-clustered errors).

## 5. How RL is used

A sequential-decision MDP with sparse, delayed reward — not a bandit.

| Element | Definition |
|---|---|
| State | per node: type, confidence, downstream influence, reviewed?, flagged?, posterior P(error) (particle filter, updated after every review) + remaining budget |
| Action | choose next node to review (+ stop) |
| Transition | reviewing fixes the node, downstream recomputed (propagation cut) |
| Reward | sparse terminal = −(sink errors) |
| Discount | γ < 1, encourages early upstream review |

**Methods**

| Method | Role | Result |
|---|---|---|
| Calibrated per-type threshold | static baseline | 2.30 (graph setting) |
| Structural greedy (fan-out × likelihood) | hand-crafted heuristic | 1.80 |
| **Belief greedy (adaptive, particle-filter belief)** | **deployable baseline to beat** | **0.85; held-out 1.14** |
| Bandit + tabular Q-learning | first version (negative) | loses to the threshold |
| REINFORCE / PPO (MLP scorer) | preliminary | 1.60 / 1.35 |
| GNN scorer + REINFORCE (fixed budget) | main learned method | static state 1.51 ± 0.41, observed state 1.68 ± 0.56; held-out 1.56 — loses to belief greedy |
| CMDP + PPO-Lagrangian (soft budget) | upgrade, in progress | naive 2.15, seed-sensitive |
| DQN (value-based) | control | 5.05 (degenerate) |

The node scorer is a **GNN**: each node's (type, confidence, downstream influence) is encoded with its neighborhood, following Mattick et al. (arXiv:2310.00112). The soft-budget extension (FALCON's CMDP + PPO-Lagrangian) is in progress.

### 5.1 Mathematical formalization (scaled experiments)

Let the evidence graph be a DAG \(G=(V,E)\). Node \(v\)'s true state \(X_v \in \{0,1\}\) (1 = correct).

**Causal propagation.** For an edge \((u,v)\) with dependency weight \(w_{uv}\):

\[
P(X_v = 0 \mid X_u = 0) = 1 - \exp(-\lambda \, w_{uv}),
\]

with infection coefficient \(\lambda\) and \(w_{uv}\sim U(0.5, 1.5)\). A review of node \(v\) is a **causal intervention**: force \(X_v = 1\), cutting outgoing infection on that edge.

**Heavy-tailed types.** Base error rates follow a Zipf law \(p_t \propto t^{-s}\) mapped into \([0.02, 0.40]\): a few deadly types cause most crashes (the 76% `order_error` analogue at scale).

**Scaled graphs (N = 500, budget = 50 ≈ 10%).**
- *Modular*: 10 clusters × 50 nodes; intra-cluster propagation high, inter-cluster only via interface nodes.
- *Barabási–Albert* scale-free (hubs), oriented low→high index.
- *Erdős–Rényi* sparse, oriented low→high index.

On scale-free graphs, reviewing the few hubs blocks most propagation — the same reason hub defense works on real networks.

**Information-gain view of the reward.** Instead of only \(-\#\text{sink errors}\), one can write

\[
R = \alpha \, \Delta H_v - \beta \, \mathrm{Cost}(v), \qquad
\Delta H_v = H(\text{conclusion}) - H(\text{conclusion} \mid \text{review } v),
\]

i.e. remove the most uncertainty with the fewest reviews. Our belief greedy is a Monte-Carlo proxy for this: under a particle-filter belief, pick the node with the largest expected drop in sink errors, then update the belief with the review outcome.

**CMDP.** Maximize correctness \(J(\pi)\) subject to \(C(\pi) \le B\):

\[
\max_\pi \min_{\lambda \ge 0} \mathcal{L}(\pi,\lambda) = J(\pi) + \lambda\,(B - C(\pi)).
\]

**Adaptive greedy.** Choosing the review that most reduces *expected* reachable sink errors, and re-planning after each observed outcome, is adaptive greedy in the sense of adaptive submodularity (Golovin & Krause 2011). Our **belief greedy** implements it with a particle filter (`experiments/belief.py`) that sees only structure, edge probabilities, calibrated confidence and review outcomes. It is the deployable baseline a learned policy must beat. The same rule applied to the *true* error state is the **oracle greedy**: a ceiling, not a policy.

## 6. Data and controls

- **Real data (motivation, internal, never committed).** `deidentified_intervalvars_forCD_111325.rds` = **13,990 rows / 237 participants** of daily sleep logs. **75 corrections (0.54%)**, of which `order_error` = **57/75 = 76%** (the old 85.1% was 57/67, 8 rows unlabeled), entropy 0.612, p < 0.0001. Per SciForge raw-data protection, the CSV never enters git and is never handed whole to an agent.
- **Synthetic graph (main experiments).** ≈80 nodes, type-clustered errors, downstream propagation. Scaled: **N=500** modular / BA / ER; deployable belief greedy 80.6→12.8 on scale-free (oracle 3.6). **Transfer (specified, not yet run):** KAIST HRV diary (1,372 rows / 49 adults, Figshare 28509740, CC BY) and Manchester diary — adapt scripts in `splsleep/validation/external/`. Frozen GNN vs retrained GNN, both reported.
- **Broader-bio (specified, teammates to search):** GO molecular-function slice — nodes = GO MF terms (a real DAG), items = gene-term annotations, AI = IEA, human = biocurator. Same review-scheduling task, broader bio. **Not protein-function prediction.** Search first whether GO-annotation review scheduling already exists.
- **Controls.** Shuffle which items are wrong → advantage disappears. Flatten the graph → advantage disappears. The advantage comes from clustering + propagation, not a rigged simulator.

## 7. Results so far

All numbers are sink errors (lower is better). **The two tables are different settings — do not compare across them** (threshold 2.81 vs 2.30; no-review 5.62 vs 5.90).

**V1 bandit (reported negative)**

| Strategy | sink errors |
|---|---:|
| No review / Random 16 / Calibrated threshold / Q-learning / Review-all | 5.62 / 4.19 / 2.81 / 3.38 / 0.56 |

Diagnosis: per-item review flattens the graph; with one type at 76%, the optimal policy collapses into a static rule.

**After reframing as active node selection**

| Method | sink errors | Type |
|---|---|---:|
| No review | 5.90 | traditional |
| Confidence threshold | 2.30 | traditional |
| Structural greedy | 1.80 | traditional |
| **Belief greedy (adaptive, deployable)** | **0.85** | **baseline to beat** |
| REINFORCE (MLP) | 1.60 | ours, preliminary |
| PPO (MLP) | 1.35 | ours, preliminary |
| GNN + REINFORCE, static state | 1.51 ± 0.41 | ours |
| GNN + REINFORCE, observed state | 1.68 ± 0.56 | ours |
| DQN | 5.05 (degenerate) | control |
| CMDP soft-budget (naive) | 2.15 | in progress |
| Oracle | 0.00 | upper bound |

These are the 20 legacy graphs (seeds 1–20), which turned out easier than average. **Main comparison — 200 held-out graphs, paired** (`experiments/final_table.md`):

| Policy | sink errors (95% CI) |
|---|---|
| Confidence threshold | 1.41 ± 0.25 |
| Structural greedy | 1.45 ± 0.22 |
| **Belief greedy** | **1.14 ± 0.20** |
| GNN, static state | 1.56 ± 0.29 |
| GNN, observed state | 1.56 ± 0.15 |

- **Belief greedy beats every learned policy**: GNN − belief greedy = +0.42 ± 0.15.
- Giving the GNN its review outcomes did not help (observed − static = −0.00 ± 0.08).
- On held-out graphs structural greedy ≈ threshold. The old "structure beats the threshold by 22%" only holds on the 20 legacy graphs; graph value shows up through belief greedy instead.
- DQN degenerates: under sparse terminal reward a value function gets no per-step credit → policy gradient is the right tool.
- CMDP soft budget, naive: 2.15 with a fixed seed (an earlier unseeded run gave 4.85). Seed-sensitive and still worse than the fixed-budget GNN; stop-action credit assignment is coarse, a FALCON-style dual critic is the next step.

Figures: `experiments/results_bar.png`, `experiments/learning_curves.png`, `experiments/ablation_conf.png`.

![Method comparison](experiments/results_bar.png)

![Learning curves](experiments/learning_curves.png)

Learning curves are real training logs (`rl_gnn_multiseed.py`, `rl_methods_compare.py`), plotted by `rl_final.py`. An earlier version of this figure was a hand-drawn placeholder.

## 8. Ablation: the confidence signal is the bottleneck

GNN + REINFORCE under three confidence conditions (3 seeds × 12k episodes):

| Condition | mean | per-seed | Meaning |
|---|---|---|---|
| noise (conf = uniform noise) | **3.78** | 3.30 / 5.20 / 2.85 | destroying the signal destroys performance (worse than the threshold; approaching no-review) |
| normal (learned conf) | **1.38** | 1.30 / 1.95 / 0.90 | matches the multi-seed mean |
| oracle (conf reveals the true error) | **0.72** | 0.80 / 0.70 / 0.65 | nearly reaches the oracle bound 0.00 |

![Ablation: confidence signal is the bottleneck](experiments/ablation_conf.png)

Two system-level insights:

1. **The model uses the confidence signal.** Destroy it and RL is *worse* than a static rule.
2. **The noisy predictor is the bottleneck, not the scheduler.** With a perfect signal, errors drop from 1.38 to 0.72. **Do not keep tuning the policy — invest in the confidence signal.** We located where the remaining error lives.

This is a trade-off engineering victory: we did not pretend RL always wins; we located the remaining error.

**Worst-of-n reliability** (one unreviewed error can invalidate a conclusion — HealthBench lens; `rl_ablation.py`, 3 training seeds):

| | mean | worst seed (of 3) |
|---|---|---|
| normal conf | 1.38 | 1.95 |
| noise conf | 3.78 | 5.20 |
| oracle conf | 0.72 | 0.80 |

A noisy signal hurts the tail more than the mean (worst − mean: noise 1.42 vs oracle 0.08).

**Decision guide**

| Setting | Use |
|---|---|
| Confidence well calibrated, graph known | Belief greedy (beats our GNN) |
| Confidence noisy / uncalibrated | **Do not use RL** — a static threshold is more robust (noise 3.78 > threshold 2.30) |
| Tight budget, no belief model available | Confidence threshold ≈ structural greedy on unseen graphs; threshold is simpler |
| You can improve the predictor | Improving conf calibration buys more than improving the policy |

## 8b. Scaled experiments: N = 500, three graph families

Same intervention model (P(X_v=0 | X_u=0) = 1 − e^(−λw)), Zipf type rates, budget 50 (10%). Five seeds. Policies: no review, random, confidence threshold, hub (highest out-degree), **belief greedy** (deployable, adaptive), **oracle greedy** (reads the true error state; ceiling only). Every policy replays the same catch-randomness stream.

| family | no review | random | threshold | hub | **belief greedy** | oracle greedy |
|---|---|---|---|---|---|---|
| modular (10×50) | 24.0 | 22.6 | 9.2 | 21.0 | **8.4** | 2.0 |
| scale-free (BA) | 80.6 | 78.2 | 37.6 | 29.2 | **12.8** | 3.6 |
| sparse (ER) | 42.6 | 42.0 | 21.4 | 34.0 | **19.2** | 7.8 |

Figure: `experiments/scale500.png`. Script: `graph_scale.py`.

![Scaled experiments](experiments/scale500.png)

**What the scale says (the X-factor at 500 nodes):**

1. **Structure pays most on scale-free graphs** — deployable belief greedy cuts sink errors 81→13 (84%), versus 53% for the threshold. On modular and sparse graphs it is only slightly better than the threshold; 5 seeds cannot separate them. The old "95% reduction" was the oracle greedy, which reads the true error state.
2. **Random ≈ no review** everywhere. Attention without a structure-aware rule does nothing at this scale.
3. **The confidence threshold is unstable on scale-free graphs** (per-seed 6 to 76). A static rule that ignores topology either wins big or does nothing.
4. **Hub defense helps on scale-free but is still far from belief greedy.** Degree is a good prior; expected sink reduction under a belief is better.

**Honest scope:** these 500-node numbers are **heuristics, not RL**. RL on this scale has not been trained. The claim is: the problem is interesting at scale, belief greedy is the deployable baseline, and any learned policy must beat it — which our GNN does not do even at 80 nodes.

## 8c. Real sleep-pipeline DAG (application)

Encoded from splsleep SCHEMA (`real_pipeline_graph.py`): raw diary leaves → pairwise diffs → SOL/WASO/TST/TIB/SE → validity/conclusion sinks. N=21, budget 8, λ=0.9, types matched to the 75 corrections. 8 seeds:

| policy | sink errors |
|---|---|
| no review | 2.12 |
| random | 1.88 |
| **conf threshold** | **0.50** |
| hub | 1.75 |

![Real sleep-pipeline DAG](experiments/real_pipeline.png)

On the *actual* lab pipeline, a calibrated confidence threshold nearly clears conclusion errors. The 500-node result says what to do when the evidence graph is large; this 21-node result says what to do on our data today.

## 9. Related work

- **Learning to defer:** Mozannar & Sontag (ICML 2020); FALCON (arXiv:2604.00904, closest components, no graph propagation); SLTD (arXiv:2109.06312); Reid et al. (arXiv:2409.20489); KL-PBD (arXiv:2610.15128); Oversight Has a Capacity (arXiv:2606.08919, closest scheduling framing, flat trajectories); Too Much of the Same (arXiv:2608.28050, class bias ↔ our 76% clustering).
- **Budgeted / delayed bandits:** Bandits with Knapsacks (FOCS 2013); Delayed Feedback (ICML 2013).
- **Error cascades:** Data Cascades (CHI 2021); Finkel et al. (EMNLP 2006); From Spark to Fire (arXiv:2603.04474); DN-ILDL (arXiv:2405.16474).
- **Budget + node selection / GNN:** WS-option (arXiv:2502.05537); Mattick & Mutschler (arXiv:2310.00112).

### 9.1 Compared with HealthBench (OpenAI, 2025-05)

HealthBench is the closest *evaluation-philosophy* precedent, not a scheduling precedent.

| | HealthBench | Ours |
|---|---|---|
| Question | Is this LLM health reply good enough, by physician rubrics? | Given dependent AI outputs and a human who can check only a few, which check first? |
| Human standard | 262 physicians, 48,562 weighted criteria | 75 lab corrections (27 consensus / 48 agree) |
| What is scored | Quality of an open-ended reply | Allocation of finite attention over a DAG |
| Error dynamics | Per-reply rubric; no propagation | Errors propagate; penalty delayed to the conclusion |
| Reliability | worst-of-n | worst seed (of 3): normal 1.95 / noise 5.20 / oracle 0.80 |
| Consensus / Hard | 3,671 consensus; 1,000 Hard | 27 consensus / 48 agree — split planned, not yet evaluated |
| Non-saturation | HealthBench Hard still unsolved | even oracle conf leaves 0.72 |
| RL scheduling | not part of the benchmark | the entire project |

**Adopted:** three principles — *meaningful* (sink errors on a real pipeline), *trustworthy* (75 human corrections; machine never stamps), *non-saturated* (oracle still leaves 0.72) — plus worst-of-n and the consensus/hard split as a next step.

**Not copied:** community-scale physician crowdsourcing; LLM-as-grader for open-ended text; the medical-dialogue task.

**For the talk.** HealthBench asked whether an LLM reply meets physician standards on a real health conversation. We ask where finite human attention should go first over a chain of dependent AI outputs. They taught the field to evaluate with meaningful, trustworthy, non-saturated rubrics and worst-of-n reliability. We apply those lessons to a problem they do not solve: scheduling that attention over a dependency graph. Their grading signal is exactly the kind of confidence signal our ablation says is the bottleneck — improving the signal buys more than improving the policy.

**BioBasicsBench (OpenAI + Ligo, 2026-11-06) is the everyday-science sibling.** 100 wet-lab tasks on raw evidence (gels, plates, microscopy); top model 66.7%; failures are assumption-overrides-control, discounted contradictions, miscounts. Our 76% `order_error` is the same species (a familiar time-order assumption overrides the recorded timestamps). Adopt: partial-credit rubrics on receipts, error detection as a first-class skill, and an explicit "evidence cannot support this conclusion" action. We add what they did not build: budgeted sequential review over a dependency graph.

**Broader-bio (specified, teammates to search):** GO molecular-function slice — nodes = GO MF terms (a real DAG), items = gene-term annotations, AI = IEA, human = biocurator. Same review-scheduling task, broader bio. Not protein-function prediction. Search first whether GO-annotation review scheduling already exists.

## 10. Differentiation, limits, feasibility

**Where we stand.** Each ingredient has prior work, but the combination **"error propagation on a dependency graph + a human review budget + learning which node to review" has no direct precedent** (not found, not nonexistent). Closest: Oversight (flat actions) + WS-option (budget + node selection). We differ by **dependency-graph error propagation + sparse delayed reward**. Learning to defer mostly decides item by item (a bandit); we choose nodes on a graph.

**Experiments add.** An explainable negative result, the reframe that fixes it, a method comparison, controls showing the gain comes from structure, and an ablation locating the remaining error in the confidence signal.

**Limits.** Synthetic main experiments (≈80 nodes; scaled heuristics at 500 nodes, RL not yet trained at that scale; KAIST/Manchester transfer specified not run); the GNN loses to deployable belief greedy, and giving it observations did not help; real data is 75 rows (motivation only); CMDP soft budget not solved.

**Feasibility.** Simulator, baselines, REINFORCE, PPO, DQN, GNN scorer already run. Remaining: a learned policy that beats belief greedy (e.g. under a misspecified belief model), dual-critic CMDP, slides. Next: larger graphs, the real evidence graph, consensus/hard split.

## 11. SciForge deployment (phased idea) and AI4Science

1. **Offline evaluation.** Synthetic graph + an exported, de-identified real evidence graph; suggester vs sort-by-confidence. No app integration.
2. **Read-only suggestion.** "Review these nodes first" + reasons, next to the review interface; humans may ignore it.
3. **Receipt-contract handshake.** Recording "was this review suggestion-followed" needs the evidence-chain owner; not pre-decided.

**AI4Science positioning.** This suggester is the **review layer of a research evidence chain**: front end (highlight-and-ask on code) produces review traces; the middle (this policy) decides where finite human attention goes first; the back end (SciForge DAG + receipts) guarantees the machine never stamps. Together they answer: **when AI assists research, where should finite human attention be spent.**

**Decisions needed.** Professor: bandit → MDP direction and a synthetic main experiment. Evidence-chain owner: may suggester output enter the audit chain. Teammates: Section 12 division.

## 12. Verification status

**Checked:** citations against abstracts; Section 7 numbers against `experiments/final_table.md`; real-data numbers recomputed 2026-11-09.

**Not verified — teammates must check:**
1. All simulation numbers, learning curves, both controls.
2. Simulator design (graph, clustering, greedy, hyperparameters); why no-review differs across tables (5.62 vs 5.90).
3. "No direct precedent" — search again; phrase as "we did not find one."
4. Full texts of cited papers (we read abstracts only).
5. Whether BestReject in arXiv:2409.20489 equals our calibrated threshold (claim dropped as unverified).
6. Belief greedy assumes the confidence model and edge probabilities are known exactly; test it under misspecification.
7. GNN vs belief greedy on held-out graphs (done: GNN worse by 0.42 ± 0.15); a stronger learner (deeper GNN, per-step credit) is untested.
8. GNN + PPO convergence.
9. Dual-critic CMDP.
10. SciForge: confidence field on nodes; real graph size / edge types.
11. Consensus / Hard split of the 75 corrections (27 / 48) — labels exist, evaluation not run.

## 13. Roles and timeline

| Member | Primary | Backup | Deliverable |
|---|---|---|---|
| 1 | PM + timeline + L2D classics (Mozannar / FALCON / SLTD) | proposal + timeline |
| 2 | Policy gradient (REINFORCE → PPO-Lagrangian) | 3 | code + learning curves |
| 3 | Environment + value-based (DQN) + GNN scorer | 2 | env module + GNN results |
| 4 | Baselines + controls | 2 | comparison table + shuffle/flatten |
| 5 (동채하) | Narrative + 郑心 liaison + literature synthesis + writing + presenting (English) | 1 | related work + motivation + slides |


| Date | Milestone | Owner |
|---|---|---|
| ~11/12 | Freeze env + baselines; reproduce REINFORCE / GNN | 3, 4 |
| ~11/19 | PPO-Lagrangian + dual critic; method table | 2, 3 |
| ~11/26 | Controls + curves + negative-result section; related work final; consensus/hard split | 4, 5 |
| ~12/03 | Slides + ≥2 rehearsals | 5, all |
| ~12/05 | Final presentation | all |

## 14. Presentation outline (condensed)

1. Title
2. Motivation: errors cluster (76%) + propagate to conclusions
3. Classic L2D formulation
4. V1 bandit: honest negative (threshold 2.81 > Q 3.38)
5. Diagnosis: flattening kills RL
6. Reframe: active node selection = real MDP
7. Methods: GNN scorer + policy gradient; CMDP in progress
8. Results table + figures
8b. **Ablation: conf signal is the bottleneck** (noise 3.78 / normal 1.38 / oracle 0.72) + worst-of-n
9. Controls
10. Related work + HealthBench comparison + positioning
11. AI4Science: review layer of an evidence chain
12. Roles + Q&A

**Likely Q&A.**
- Why not the threshold? It cannot see the graph; deployable belief greedy beats it (held-out 1.14 vs 1.41; BA at N=500 12.8 vs 37.6). Our RL does not beat belief greedy yet — and the ablation says invest in the signal.
- Real gain or tuning? Shuffle/flatten kill the advantage.
- Difference from L2D? Per-item bandit vs graph node selection (MDP + sparse delayed reward).
- Scale? Methodology demo; extendable to the real evidence graph.
- Real data? One motivation slide; core experiments synthetic (standard for RL courses).
