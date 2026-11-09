# Proposal (Final): Review Scheduling on a Dependency Graph under Budget — an AI4Science application for SciForge

Team course project proposal · STA3145 Reinforcement Learning · Deepened version 2026-11-09
> This version restates the proposal inside SciForge's evidence chain and merges all second-round results (GNN scorer, CMDP soft budget, the 76% correction, and the 2026 literature). Sections 3 and 9 are new for SciForge.

**Verification status**: the experiment code and results were produced by an AI agent and have not been independently checked. Unverified items are in Section 8.

**One-liner**: When an AI's outputs depend on one another and a human can review only a few, we use RL to learn which node to review next, so that fewer errors reach the final conclusion.

---

## 0. What changed from the first version

1. **From bandit to MDP.** The first version decided pass-or-review per item. Experiments showed this flattens the structure, and a calibrated threshold (2.81) beat tabular Q-learning (3.38). Now the agent picks the next node of a dependency graph to review, and a review changes what happens downstream.
2. **From a proxy dataset to our own data + a synthetic graph.** We now use our real error-correction data (75 rows) to motivate the problem, and a synthetic graph for the main experiments.
3. **From a plan to results, then to an upgrade.** We now have numbers, controls, a reported failure, a method upgrade whose single-run 1.20 does not hold across seeds (mean 1.54 ± 0.46), and an honestly-labelled open problem (the CMDP soft budget, naive version, fails).

## 1. Topic
Under a limited review budget, learn which node of a dependency graph to review first.

## 2. Problem and motivation
AI now does much research work (cleaning data, labeling literature). Part of it has no answer key — only a human can judge whether an item is wrong, and a human cannot check everything. Two facts make *what to review* matter more than *how much*:

- **Errors are not random; they cluster by type.** In our real data, one error type (`order_error`) makes up **76%** of corrections (57/75).
- **Unreviewed errors are reused downstream, and the harm shows only at the conclusion.** Items depend on one another, so a wrong item contaminates everything built on it.

So we treat evidence as a dependency graph. Given a review budget, the agent picks which node to review. Fixing a node stops its error from spreading, so an early review of an upstream node can be worth several reviews downstream.

## 3. Inside SciForge: which part of the evidence chain it is

SciForge already has: an evidence DAG storing "claim–evidence" provenance, human reviews that leave a "human-review receipt", and receipts entering the audit layer. This proposal adds a **review-priority suggester on top of that chain**, changing none of the existing record-keeping rules.

| Proposal concept | SciForge counterpart | Notes |
|---|---|---|
| Dependency graph | Evidence DAG (project-dag / evidence-dag) | nodes = claims, conclusions, dataset versions, analysis runs |
| Errors propagate downstream | along `derived_from`, `supports` edges | `contradicts` edges are not an error-propagation direction; keep them distinct in modelling |
| Conclusion (sink) | the conclusion node to deliver | the goal is to keep errors from reaching it |
| One review | one human review producing a receipt | receipt fields / verdict enum are set by the evidence-chain owner |
| Review budget | how many items a human can review in a cycle | — |
| RL output | a ranking of "which node to review next" | a suggestion only; produces no receipt, no stamp |

**Three boundaries (inherited design principles, not relaxed by adding RL):**
1. **The machine does not stamp.** Only a human clicking "verdict" produces a receipt; a suggestion can never become a verdict automatically.
2. **Read-only, append-only.** The suggester only reads the evidence graph and outputs a ranking; it modifies no nodes and no existing receipts.
3. **Comments and receipts are separate.** Receipts store references only, no bodies; the suggester does not read comment bodies.

**Must confirm before landing (not checked):**
- Whether SciForge evidence-graph nodes have a usable "confidence"-like field. If not, the "per-node confidence" in our state has no source yet in the real system.
- Whether the real graph's size and edge-type distribution match the synthetic assumptions (≈80 nodes, type-clustered errors).

## 4. How RL is used
A sequential-decision MDP with sparse, delayed reward — not a bandit.

| RL element | Definition |
|---|---|
| State S | graph knowledge (per node: type, confidence, downstream influence, reviewed?) + remaining budget |
| Action A | choose the next node to review (+ stop) |
| Transition P | reviewing a node fixes it, then downstream is recomputed (propagation cut) |
| Reward R | sparse terminal reward = −(sink errors) |
| Discount γ | γ < 1, encourages early upstream review |

**Methods compared:**

| Method | Role | Status |
|---|---|---|
| Calibrated per-type threshold | static-rule baseline | — |
| Structural greedy (fan-out × error likelihood) | hand-crafted heuristic baseline | — |
| Bandit + tabular Q-learning | first version (negative) | — |
| REINFORCE / PPO (MLP scorer) | preliminary policy gradient | 1.40 / 1.60 |
| **GNN scorer + REINFORCE (fixed budget)** | **main method** | **mean 1.54 ± 0.46 (single best 1.20)** |
| CMDP + PPO-Lagrangian (soft budget) | upgrade direction | ⏳ naive fails (4.85) |
| DQN (value-based) | control | 5.10 (degenerate) |

The node scorer is a **GNN**: each node's (type, confidence, downstream influence) is encoded together with its graph neighborhood, following Mattick et al. (arXiv:2310.00112). The soft-budget extension (FALCON's CMDP + PPO-Lagrangian, budget as a coverage constraint) is still in progress.

**Formalization.** On DAG \(G=(V,E)\), with \(X_v\in\{0,1\}\) (1 = correct):

\[
P(X_v = 0 \mid X_u = 0) = 1 - \exp(-\lambda\, w_{uv}),
\]

a causal intervention: reviewing \(v\) forces \(X_v=1\) and cuts outgoing infection. Types follow a Zipf law (a few deadly types). The budget is a CMDP constraint \(C(\pi)\le B\), Lagrangian \(\max_\pi \min_{\lambda\ge0} J(\pi)+\lambda(B-C(\pi))\). Greedy review that most reduces reachable sink errors is a \((1-1/e)\)-style influence-maximization baseline.

## 5. Data and controls

- **Real data (motivation, internal, not public):** `deidentified_intervalvars_forCD_111325.rds` = **13,990 rows / 237 participants** of daily sleep logs (bed / sleep / wake / get-up times → automated SOL, WASO, sleep efficiency). 75 corrections (0.54%), of which `order_error` = **57/75 = 76%** (not 85.1%; the 85% was 57/67, 8 rows unlabeled), entropy 0.612, p < 0.0001.
  - Per SciForge's raw-data protection, this CSV **never enters git and is never handed whole to an agent**; the document cites summary numbers only.
- **Synthetic dependency graph (main experiments):** ≈80 nodes, errors clustered by type and propagating downstream. Scaled follow-up (**N=500**, budget 50, Zipf types, exponential propagation 1−e^(−λw)): modular / scale-free (BA) / sparse (ER). Greedy influence maximization: modular 24→**2**, scale-free 81→**4**, ER 43→**8**; random ≈ no review; conf threshold unstable on scale-free (6–76). Script `graph_scale.py`, figure `scale500.png`. These 500-node numbers are **greedy, not RL**. On the *actual* lab pipeline DAG (N=21, from splsleep SCHEMA, `real_pipeline_graph.py`), a confidence threshold nearly clears conclusion errors: 2.12 → **0.50**.
- **Controls (proving the advantage is not baked in):** shuffle which items are wrong (break clustering) → advantage disappears; flatten the graph (break propagation) → advantage disappears. → the advantage comes from clustering + propagation.

## 6. Results so far (AI-generated, not re-run, see Section 8)

All numbers are sink errors (lower is better). **The two tables are different experimental settings — the threshold baseline (2.81 vs 2.30) and the no-review baseline (5.62 vs 5.90) differ, so do not compare across tables.**

**First version (bandit): a reported negative result**

| Strategy | sink errors |
|---|---:|
| No review / Random 16 / Calibrated threshold / Q-learning / Review-all (upper) | 5.62 / 4.19 / 2.81 / 3.38 / 0.56 |

Diagnosis: per-item review flattens the graph, and with one type at 76%, the optimal policy collapses into a static rule.

**After reframing as active node selection on the graph**

| Method | sink errors | Type |
|---|---|---:|
| No review | 5.90 | traditional |
| Confidence threshold | 2.30 | traditional |
| Structural greedy | 1.80 | traditional (hand-crafted) |
| REINFORCE (MLP) | 1.40 | ours (preliminary) |
| PPO (MLP) | 1.60 | ours (preliminary) |
| **GNN + REINFORCE** | **1.54 ± 0.46 (best seed 1.00)** | **ours (upgrade)** |
| DQN | 5.10 (degenerate) | control |
| CMDP soft-budget (naive) | 4.85 ⏳ | in progress |
| Oracle | 0.00 | upper bound |

- The graph itself has value: structural greedy beats the threshold by 22%.
- The GNN scorer's mean (1.54) is comparable to MLP REINFORCE (1.40) and structural greedy (1.80); the single best seed hits 1.00. High variance, not a stable win.
- DQN degenerates to near-random: under a sparse terminal reward a value function gets no per-step credit → policy gradient beats value-based.
- The CMDP soft budget, naive version, fails (4.85): the stop-action credit assignment is too coarse; it needs a FALCON-style dual critic — our open problem.

## 7. Related work (checked against abstracts 2026-11-09; abstracts only)

- **Learning to defer:** Mozannar & Sontag (ICML 2020); **FALCON** (arXiv:2604.00904, fatigue + budget + PPO-Lagrangian CMDP, closest but no graph propagation); **SLTD** (arXiv:2109.06312); Reid et al. (arXiv:2409.20489); **KL-PBD** (arXiv:2610.15128); **Oversight Has a Capacity** (arXiv:2606.08919, which actions to review under finite human attention — closest scheduling framing but gates flat trajectories); **Too Much of the Same** (arXiv:2608.28050, L2D class bias — connects to our 76% single-type clustering).
- **Budgeted / delayed-feedback bandits:** Bandits with Knapsacks (FOCS 2013); Delayed Feedback (ICML 2013).
- **Error cascades and propagation:** Data Cascades (CHI 2021); Finkel et al. (EMNLP 2006); **From Spark to Fire** (arXiv:2603.04474, directed dependency graph + cascades); DN-ILDL (arXiv:2405.16474).
- **Budget + node-selection RL / GNN encoding:** **WS-option** (arXiv:2502.05537, budget allocation + node selection two-layer MDP); **Mattick & Mutschler** (arXiv:2310.00112, GNN + RL node selection — our scorer follows it).

### 7.1 Compared with HealthBench (OpenAI, 2025-05)

HealthBench is the closest *evaluation-philosophy* precedent, not a scheduling precedent. Side by side:

| | HealthBench | Ours |
|---|---|---|
| Question | Is this LLM health-conversation reply good enough, by physician rubrics? | Given dependent AI outputs and a human who can check only a few, which check first so the conclusion is least contaminated? |
| Human standard | 262 physicians, 48,562 weighted criteria | 75 lab corrections (27 consensus / 48 agree), 76% one type |
| What is scored | Quality of an open-ended reply | Allocation of finite attention over a DAG |
| Error dynamics | Per-reply rubric; no propagation | Errors propagate; penalty delayed to the conclusion |
| Reliability | worst-of-n (one unsafe reply cancels many good ones) | worst-of-5: GNN 1.90 / noise 5.20 / oracle 0.80 — noisy signal hurts the tail more than the mean |
| Consensus / Hard | 3,671 consensus cases; 1,000 Hard | 27 consensus / 48 agree — split planned, not yet evaluated |
| Non-saturation | HealthBench Hard still unsolved | even oracle conf leaves 0.72 (p_catch = 0.9) |
| RL scheduling | not part of the benchmark | the entire project |

**Adopted:** three principles (*meaningful* — sink errors on a real pipeline; *trustworthy* — 75 human corrections, machine never stamps; *non-saturated* — oracle still leaves 0.72), worst-of-n, and the consensus/hard split as a next step.

**Not copied:** community-scale physician crowdsourcing; LLM-as-grader for open-ended text; the medical-dialogue task.

**One paragraph for the talk.** HealthBench asked whether an LLM reply meets physician standards on a real health conversation. We ask where finite human attention should go first over a chain of dependent AI outputs. They taught the field to evaluate with meaningful, trustworthy, non-saturated rubrics and worst-of-n reliability. We apply those lessons to a problem they do not solve: scheduling that attention over a dependency graph. Their grading signal (rubrics + a model grader) is exactly the kind of confidence signal our ablation says is the bottleneck — improving the signal buys more than improving the policy.

## 8. Verification status

**Checked while writing:** paper titles/authors/venues; the Section 6 percentages against the table numbers (39.1% / 30.4% / 22.2% / 22.2% / 11.1%).

**Not verified — teammates must check:**
1. All simulation results (sink numbers, learning curves, both controls).
2. Real data — **recomputed 2026-11-09**: 13,990 rows / 237 participants / 75 corrections / order_error 76% (57/75), not 85.1% (85% was 57/67, 8 rows unlabeled). Report p as p < 0.0001.
3. Simulator design (graph construction, error clustering/propagation, structural-greedy definition, hyperparameters); why the no-review baseline differs across experiments (5.62 vs 5.90).
4. "No direct precedent" — not an exhaustive search; phrase as "we did not find one". **Closest are Oversight (flat actions) + WS-option (budget + node selection); we differ by dependency-graph error propagation + sparse delayed reward.**
5. What the papers actually say (abstracts only).
6. **GNN + REINFORCE multi-seed: mean 1.54 ± 0.46 (5 seeds)**. Single-run 1.20 was one seed's good luck; at 12k episodes it is 2.05. Report with CI; do not claim a stable win.
7. **GNN + PPO has not converged (~5.60)**, omitted from the main table.
8. **CMDP soft budget, naive version, fails (4.85)** — needs a dual critic.
9. Cross-file inconsistency: an outline says "19%", the results say "22%" (1.80 → 1.40 is 22.2%).
10. New for SciForge, unverified: whether evidence-graph nodes have a confidence field; the real graph's size / edge-type distribution.

## 9. Differentiation, feasibility, SciForge deployment, and the AI4Science positioning

**Where we stand.** Each ingredient has prior work (FALCON / Reid / SLTD / KL-PBD / type-clustered errors / graph propagation), but the combination **"error propagation on a dependency graph + a human review budget + learning which node to review" has no direct precedent**. The closest are Oversight (gates flat action trajectories) and WS-option (budget + node selection, in influence maximization); we differ by **dependency-graph error propagation + sparse delayed reward**. Our contribution is the combination, not any single component.

**What the experiments add.** An explainable negative result (bandit loses because the graph is flattened), the reframe that fixes it, a method comparison (policy gradient beats value-based under sparse reward), and controls showing the gain comes from structure.

**Limits (stated plainly).** Main experiments are synthetic (≈80 nodes; scaled greedy baselines at 500 nodes, RL not yet trained at that scale); the GNN scorer is multi-seed but high-variance; real data is 75 rows (motivation only); "no direct precedent" = not found, not nonexistent.

**SciForge deployment (phased idea):**
1. **Offline evaluation.** On the synthetic graph and an exported, de-identified real evidence graph, compare the suggester vs "sort by confidence". No app integration, no change to record-keeping.
2. **Read-only suggestion.** Show "review these nodes first" + reasons (downstream influence, error likelihood) next to the review interface. Humans may ignore it; it does not affect receipts.
3. **Receipt-contract handshake.** To record "was this review suggestion-followed", the evidence-chain owner must confirm whether to add such a field; this proposal does not pre-decide.

**AI4Science positioning (the point of the whole proposal).**
This suggester is not an isolated RL toy — it is the **review layer of a research evidence chain**. The front end (the team's "highlight-and-ask on code" tool) produces review traces; the middle (this suggester) uses RL to decide where finite human attention should go first; the back end (SciForge's evidence DAG + human-review receipts) guarantees the machine never stamps and everything is append-only. Together they answer one AI4Science question: **when AI assists research, where should finite human attention be spent.**

**Evaluation design, after HealthBench (OpenAI, 2025).** Three principles: *meaningful* (sink errors on a real pipeline), *trustworthy* (75 human corrections, 27 consensus / 48 agree; machine never stamps), *non-saturated* (even oracle confidence leaves 0.72, because reviewer miss rate is 10%). Report **worst-of-n** next to the mean: one unreviewed error can invalidate a conclusion, and a noisy confidence signal hurts the tail more than the mean (worst-of-5: noise 5.20 vs oracle 0.80). Next step, not done: split consensus-verified vs single-annotator errors (our Consensus / Hard).

**Decisions needed from others:**
- Professor: whether the bandit → MDP direction and a synthetic main experiment are acceptable in scope.
- Evidence-chain owner (Zhenxing): whether suggester output may be recorded in the audit chain, and the receipt fields.
- Teammates: the division of the Section 8 verification items.
