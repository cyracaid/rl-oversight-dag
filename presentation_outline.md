---
title: "Presentation Outline (slide by slide)"
layout: default
---

# Presentation Outline (slide by slide)

> Build slides directly from this. Each slide: key points + numbers + what to say.

---

## Slide 1 — Title
- "Review Scheduling on a Dependency Graph under Budget: learning which item to review"
- 5 members + course name

## Slide 2 — Motivation
- Fact 1: the corrections are not random — they cluster by type (real data: order_error = 76%, p < 0.0001). Say "corrections to automated output": the file records the fix type, not whether the participant or the parser caused it.
- Fact 2: unreviewed errors are reused downstream, surfacing only at the conclusion (graph propagation)
- Say: *what* to review matters more than *how much*

## Slide 3 — Problem formulation
- Under a review budget R, decide pass/review per item to minimize errors reaching the conclusion
- This is the classic learning-to-defer formulation

## Slide 4 — First version: bandit (honest negative result)
- First version: contextual bandit + tabular Q-learning
- Table: calibrated threshold 2.81 **beats** Q-learning 3.38 (across all binning)
- Say: the learned policy did not win

## Slide 5 — Diagnosis: why did it fail?
- Per-item pass/review flattens the graph; RL has nothing non-trivial to learn
- 76% single type → a single `if order_error then review` rule captures most of the gain
- Say: the problem structure killed the method — it's a modelling problem, not a tuning problem

## Slide 6 — Reframe: active node selection = a real MDP
- Show the MDP five-tuple (S / A / P / R / γ)
- Action changes from pass/review to choose-which-node-next
- Say: this is what RL should do — explore over the graph

## Slide 7 — Methods
- Learn a node-scoring **GNN**(type, confidence, downstream influence + graph neighborhood) → score
- REINFORCE (policy gradient + baseline + temperature annealing); PPO (clipping + importance sampling)
- CMDP + PPO-Lagrangian (soft budget) as the in-progress extension

## Slide 8 — Results (main)
| Method | sink errors |
|---|---:|
| No review | 5.90 |
| Confidence threshold | 2.30 |
| Structural greedy | 1.80 |
| **Belief greedy (adaptive, deployable)** | **0.85** |
| REINFORCE (MLP) | 1.60 |
| PPO (MLP) | 1.35 |
| GNN + REINFORCE, static / observed state | 1.51 ± 0.41 / 1.68 ± 0.56 (5 seeds) |
| DQN (value-based) | 5.05 (degenerate) |
| CMDP soft-budget (naive) | 2.15 |
| Oracle (upper) | 0.00 |
- Figures: `results_bar.png` + `learning_curves.png`
- Held-out, paired (200 unseen graphs): threshold 1.41, structural greedy 1.45, **belief greedy 1.14**, GNN 1.56 (static) / 1.56 (observed). GNN − belief greedy = +0.42 ± 0.15.
- Say: the seeds-1–20 table is on easy graphs; on unseen graphs a deployable belief greedy beats every learned policy, and giving the GNN its review outcomes did not help; **DQN degenerates** — under a sparse terminal reward a value function gets no per-step credit, which is exactly why policy gradient is the right tool here

## Slide 8b — Ablation: the confidence signal is the bottleneck
| Condition | mean |
|---|---:|
| noise (destroy the conf signal) | 3.78 |
| normal (learned conf) | 1.38 |
| oracle (true error revealed) | 0.72 |
- Figure: `ablation_conf.png`
- Say: (1) the model uses the signal — destroy it and RL is *worse* than a static threshold. (2) The noisy predictor is the bottleneck, not the scheduler — **do not keep tuning the policy; invest in the confidence signal.** We located where the remaining error lives.
- Reliability (HealthBench worst-of-n): one unreviewed error can invalidate a conclusion. Worst seed of 3: normal 1.95, noise 5.20, oracle 0.80 — **a noisy signal hurts the tail more than the mean.**

## Slide 8c — Scale: N=500, three graph families
| family | no | threshold | **belief greedy** | oracle greedy |
|---|---|---|---|---|
| modular | 24 | 9.2 | **8.4** | 2.0 |
| scale-free (BA) | 81 | 38 | **12.8** | 3.6 |
| sparse (ER) | 43 | 21 | **19.2** | 7.8 |
- Figure: `scale500.png`
- Say: deployable belief greedy cuts scale-free errors by 84% (threshold 53%); on modular/ER it is only slightly better than the threshold. Oracle greedy reads the true errors — a ceiling, not a policy (the old "95%" was this). Random ≈ no review; threshold unstable on scale-free. **These are heuristics, not RL** — any learned policy must beat belief greedy. Math: P(X_v=0|X_u=0)=1−e^(−λw); CMDP Lagrangian; Zipf types.

## Slide 9 — Controls (anti-self-fulfilling)
- Shuffle errors (break clustering) → advantage gone; flatten graph (break propagation) → advantage gone
- Say: the advantage comes from structure, not from a rigged simulator

## Slide 10 — Related work + positioning
- learning-to-defer (Mozannar, FALCON, SLTD, Reid et al., KL-PBD, Oversight); budget/delayed bandits; error cascades (Data Cascades, Finkel, From Spark to Fire); budget + node selection (WS-option); GNN node selection (Mattick)
- Our difference: active node selection on a dependency graph + sparse delayed reward (combination novelty)

## Slide 11 — AI4Science positioning + conclusion
- This is the **review layer of a research evidence chain**: front-end review tool → RL suggester → SciForge evidence DAG (machine never stamps, append-only)
- Conclusion: flatten the problem and RL loses; give the scheduler the graph and a belief, and adaptive greedy wins; our GNN does not beat it yet
- Limits: synthetic data, small graph, belief greedy assumes a known model; future: beat belief greedy under a misspecified model, GNN at scale, real evidence graph

## Slide 12 — Roles + Q&A
- 5-person role table
- Prepared Q: why not just the threshold / why not deeper networks / what about real data

---

## Likely Q&A (top 5)

1. **"Why not just the per-type threshold?"** → the threshold cannot see graph structure; deployable belief greedy beats it (held-out 1.14 vs 1.41; scale-free N=500 12.8 vs 37.6), proving the graph has value. Our RL does not beat belief greedy yet.
2. **"Real gain or a tuned artifact?"** → shuffle-errors / flatten-graph kill the advantage, proving it is not rigged.
3. **"Difference from learning-to-defer?"** → L2D defers per item independently (bandit); we select nodes on a graph (MDP + sparse delayed reward).
4. **"Meaningful at this scale?"** → admit the limitation; it is a methodology demo, extendable to a real evidence graph and GNN at scale.
5. **"What about real data?"** → one motivation slide (76% clustering, 13,990 rows); core experiments are synthetic (standard for RL courses).
