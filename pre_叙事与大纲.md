# Presentation Outline (slide by slide)

> Build slides directly from this. Each slide: key points + numbers + what to say.

---

## Slide 1 — Title
- "Review Scheduling on a Dependency Graph under Budget: learning which item to review"
- 5 members + course name

## Slide 2 — Motivation
- Fact 1: AI errors are not random — they cluster by type (real data: order_error = 76%, p < 0.0001)
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
| REINFORCE (MLP) | 1.40 |
| PPO (MLP) | 1.60 |
| **GNN + REINFORCE** | **1.54 ± 0.46 (5 seeds)** |
| DQN (value-based) | 5.10 (degenerate) |
| CMDP soft-budget (naive) | 4.85 ⏳ |
| Oracle (upper) | 0.00 |
- Figures: `results_bar.png` + `learning_curves.png`
- Say: the GNN scorer's mean is comparable to structural greedy (1.54 vs 1.80) and beats the threshold (2.30); single best seed hits 1.00; **DQN degenerates** — under a sparse terminal reward a value function gets no per-step credit, which is exactly why policy gradient is the right tool here

## Slide 9 — Controls (anti-self-fulfilling)
- Shuffle errors (break clustering) → advantage gone; flatten graph (break propagation) → advantage gone
- Say: the advantage comes from structure, not from a rigged simulator

## Slide 10 — Related work + positioning
- learning-to-defer (Mozannar, FALCON, SLTD, Reid et al., KL-PBD, Oversight); budget/delayed bandits; error cascades (Data Cascades, Finkel, From Spark to Fire); budget + node selection (WS-option); GNN node selection (Mattick)
- Our difference: active node selection on a dependency graph + sparse delayed reward (combination novelty)

## Slide 11 — AI4Science positioning + conclusion
- This is the **review layer of a research evidence chain**: front-end review tool → RL suggester → SciForge evidence DAG (machine never stamps, append-only)
- Conclusion: flatten the problem and RL loses; give RL the graph, and policy gradient wins
- Limits: synthetic data, small graph, single-run GNN; future: GNN at scale, real evidence graph

## Slide 12 — Roles + Q&A
- 5-person role table
- Prepared Q: why not just the threshold / why not deeper networks / what about real data

---

## Likely Q&A (top 5)

1. **"Why not just the per-type threshold?"** → the threshold cannot see graph structure; graph-aware greedy beats it by 22%, proving the graph has value; RL adds ~33% more.
2. **"Real gain or a tuned artifact?"** → shuffle-errors / flatten-graph kill the advantage, proving it is not rigged.
3. **"Difference from learning-to-defer?"** → L2D defers per item independently (bandit); we select nodes on a graph (MDP + sparse delayed reward).
4. **"Meaningful at this scale?"** → admit the limitation; it is a methodology demo, extendable to a real evidence graph and GNN at scale.
5. **"What about real data?"** → one motivation slide (76% clustering, 13,990 rows); core experiments are synthetic (standard for RL courses).
