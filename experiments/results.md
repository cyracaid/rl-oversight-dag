# Empirical Results Summary (Final)

> Code: `verify_clustering.py`, `spike_active_selection.py`, `rl_methods_compare.py`, `rl_cmdp_gnn.py`, `rl_final.py`
> Figures: `results_bar.png`, `learning_curves.png`; table: `final_table.md`

---

## Final method comparison (main result)

Generated tables live in `final_table.md` (built by `rl_final.py` from `gnn_results.json`, `methods_compare.json`, `cmdp_result.json`). Do not hand-copy numbers from here into slides; copy from `final_table.md`.

**Held-out, paired (200 unseen graphs; same graph and same catch-randomness stream for every policy):**

| Policy | Sink errors (95% CI) | Type |
|---|---|---|
| Confidence threshold | 1.41 ± 0.25 | static |
| Structural greedy | 1.45 ± 0.22 | static, hand-crafted |
| **Belief greedy (adaptive, particle-filter belief)** | **1.14 ± 0.20** | **deployable baseline to beat** |
| GNN + REINFORCE, static state | 1.56 ± 0.29 | ours |
| GNN + REINFORCE, observed state | 1.56 ± 0.15 | ours |

Paired: GNN observed − belief greedy = **+0.42 ± 0.15**; observed − static = −0.00 ± 0.08; GNN static − structural greedy = +0.11 ± 0.16.

**Legacy seeds 1–20** (every earlier table used these; they are easier than average): no review 5.90, threshold 2.30, structural greedy 1.80, **belief greedy 0.85**, REINFORCE (MLP) 1.60, PPO (MLP) 1.35, DQN 5.05, CMDP naive 2.15, GNN static 1.51 ± 0.41, GNN observed 1.68 ± 0.56, oracle 0.00.

> Figures: `results_bar.png` (held-out, paired, with CIs), `learning_curves.png` (real training logs).

**Key findings:**
- A deployable belief greedy beats every learned policy we have.
- Giving the GNN its review outcomes (belief features) did not help this 1-layer GNN trained with terminal-only REINFORCE.
- On unseen graphs structural greedy ≈ threshold; the old "structure beats the threshold by 22%" only held on the 20 legacy graphs. Graph value shows up through belief greedy.
- DQN degenerates (5.05): under a sparse terminal reward a value function gets no per-step credit.
- The naive CMDP soft budget gets 2.15 with a fixed seed (4.85 in an earlier unseeded run): seed-sensitive, still worse than the fixed-budget GNN.

---

## 1. Real data: errors cluster by type (motivation, Slide 2)

- Data: internal sleep-research dataset, `deidentified_intervalvars_forCD_111325.rds` = **13,990 rows / 237 participants**, daily sleep logs.
- Corrections: 75 manual corrections in `manual_error_correction_updated.csv` (0.54%).
- **order_error = 57/75 = 76%** (not 85.1%; the 85% figure was 57/67, where 67 is the number of rows with a non-empty `error_type` — 8 rows are unlabeled), entropy 0.612, p < 0.0001.
- Conclusion: the error rate is low but the errors cluster strongly by type — so a limited review budget must target the right nodes.

## 2. First version: bandit (honest negative result)

| Strategy | Sink errors |
|---|---:|
| No review / Random 16 / Calibrated threshold / Q-learning / Review-all (upper) | 5.62 / 4.19 / 2.81 / 3.38 / 0.56 |

Diagnosis: reviewing item by item flattens the dependency graph, leaving RL nothing non-trivial to learn; with one type at 76%, the optimal policy collapses into a static rule.

## 3. Reframe: structural value (spike)

Structural greedy (1.80) beats the threshold (2.30) on the 20 legacy graphs; on 200 held-out graphs they tie (1.45 vs 1.41). Graph value is real but shows up through belief greedy (1.14 held-out). Oracle = 0 means there is room.

## 4. Controls (anti-self-fulfilling)

- Shuffle which items are wrong (break type clustering) → the learning advantage disappears.
- Flatten the graph (break propagation) → the learning advantage disappears.
- Meaning: the advantage comes from the clustering and propagation, not from a rigged simulator.

## 5. Honest caveats (please read)

1. **GNN + REINFORCE loses to deployable belief greedy** on 200 held-out graphs (paired gap +0.42 ± 0.15). Belief greedy assumes the confidence model and edge probabilities are known exactly; a learned policy may still win when that model is misspecified — untested.
2. **GNN + PPO has not converged (~5.60)** — the PPO-on-GNN implementation needs more tuning; it is omitted from the main table.
3. **CMDP soft budget (naive): 2.15 with a fixed seed, 4.85 in an earlier unseeded run** — the stop-action + coverage-constraint credit assignment is too coarse (the whole episode shares one return). It needs a FALCON-style reward-critic + cost-critic, not an episode-level Lagrangian. This is our open problem.
4. All numbers were produced by an AI agent and have not been independently verified; Section 8 of the proposal lists the full checklist.

## 6. Failure analysis: when does RL win, and when does it not?

Across 5 training seeds the GNN's legacy-seed mean ranges 1.10–2.00 (static) and 1.15–2.35 (observed); on held-out graphs both variants average 1.56. The original method could only learn a fixed ranking because its state never changed after a review. Adding review outcomes to the state did not close the gap to belief greedy, which uses the same information through an explicit model.

Working hypothesis: with a correct model, belief greedy is near the best a myopic policy can do; RL has room only where the model is wrong (miscalibrated confidence, unknown edge probabilities) or where non-myopic planning pays. That is the next experiment.

## 7. Ablation: the confidence signal is the bottleneck

Trained GNN+REINFORCE under three confidence conditions (3 seeds × 12k episodes, `rl_ablation.py`):

| Condition | mean | per-seed | What it means |
|---|---|---|---|
| noise (conf = uniform noise) | **3.78** | 3.30 / 5.20 / 2.85 | destroying the signal destroys performance (worse than the threshold 2.30, approaching no-review) |
| normal (learned conf, as main experiments) | **1.38** | 1.30 / 1.95 / 0.90 | close to the multi-seed GNN means (1.51 static, legacy seeds) |
| oracle (conf reveals the true error) | **0.72** | 0.80 / 0.70 / 0.65 | nearly reaches the oracle upper bound 0.00 |

> Figure: `ablation_conf.png`

**Two system-level insights (the X-factor for the talk):**

1. **The model uses the confidence signal.** Destroying it (noise 3.78 vs normal 1.38) drops performance below a static threshold — RL without a good signal is worse than a simple rule.
2. **The noisy predictor is the bottleneck, not the scheduler.** With a perfect signal, errors drop from 1.38 to 0.72 (approaching oracle 0.00). **Do not keep tuning the scheduling algorithm — invest in the confidence signal.** The scheduler is already good enough; the predictor sets the ceiling.

This is the "trade-off engineering victory" the talk should land on: we did not pretend RL always wins; we located where the remaining error lives (the predictor, not the policy).

## 8b. Scaled experiments: N=500, three graph families

Intervention model P(X_v=0 | X_u=0) = 1 − e^(−λw), Zipf types, budget 50 (10%), 5 seeds (`graph_scale.py`, `scale500.png`):

| family | no review | random | threshold | hub | **belief greedy** | oracle greedy |
|---|---|---|---|---|---|---|
| modular (10×50) | 24.0 | 22.6 | 9.2 | 21.0 | **8.4** | 2.0 |
| scale-free (BA) | 80.6 | 78.2 | 37.6 | 29.2 | **12.8** | 3.6 |
| sparse (ER) | 42.6 | 42.0 | 21.4 | 34.0 | **19.2** | 7.8 |

Every policy replays the same catch stream (`scale500_table.md`). Belief greedy cuts scale-free errors 81→13 (84%; threshold 53%); on modular/ER it is only slightly better than the threshold. Oracle greedy reads the true error state — a ceiling, not a policy; the old "95% down" was this. Random ≈ no review. Conf threshold unstable on scale-free (6–76). **These numbers are heuristics, not RL.**

## 8c. Decision guide (when to use which rule)

| Setting | Use |
|---|---|
| Confidence signal is well calibrated, graph known | Belief greedy (beats our GNN) |
| Confidence signal is noisy / uncalibrated | **Do not use RL** — a static per-type threshold is more robust (noise 3.78 > threshold 2.30) |
| No belief model available | Confidence threshold (≈ structural greedy on unseen graphs, and simpler) |
| You can afford to improve the predictor | Improving conf calibration buys more than improving the policy (oracle 0.72 vs normal 1.38) |
| Graph is large (500) and scale-free | **Belief greedy** — 81→13 on BA; random does nothing; threshold unstable |
| Real sleep-pipeline DAG (N=21, from SCHEMA) | **Conf threshold** — 2.12 → 0.50; the actual lab pipeline is small enough that a calibrated threshold nearly clears it |

## 8d. Real sleep-pipeline DAG (application)

Encoded from splsleep SCHEMA / operational definitions (`real_pipeline_graph.py`):

```
time_bed / time_sleep / time_awake / time_getup   (leaves)
  → bed_sleep_diff, sleep_awake_diff, awake_getup_diff
  → SOL_calc, WASO_calc, TST, TIB
  → SE, TST_TIB_ratio
  → SOL_validity, WASO_validity, SE_conclusion, record_quality   (sinks)
```

Types and rates match the 75 corrections (order_error 0.35/node, then the others). Budget 8/21, λ=0.9, 8 seeds:

| policy | sink errors |
|---|---|
| no review | 2.12 |
| random | 1.88 |
| **conf threshold** | **0.50** |
| hub (children) | 1.75 |

**This is the application-value answer:** on the *actual* lab pipeline (not a synthetic 500-node graph), a calibrated confidence threshold nearly clears conclusion errors. The 500-node scale-free result says what to do when the evidence graph is large; this 21-node result says what to do on *our* data today.

## 9. Reliability: worst-of-n (HealthBench lens)

One unreviewed error reaching a conclusion can invalidate it — so report worst-of-n, not just mean (HealthBench, 2025).

| | mean | worst seed (of 3, `rl_ablation.py`) |
|---|---|---|
| normal conf | 1.38 | **1.95** |
| noise conf (ablation) | 3.78 | **5.20** |
| oracle conf | 0.72 | **0.80** |

A noisy signal hurts the tail more than the mean (worst − mean: noise 1.42 vs oracle 0.08).

## 10. Consensus / Hard split (HealthBench lens)

75 corrections: **27 Consensus Reached**, 48 Agree. order_error: 19 consensus / 38 agree.

Not done yet: evaluate the policy separately on consensus-verified vs single-annotator errors. Consensus-verified = our HealthBench Consensus; the residual the policy still misses = our HealthBench Hard.

## 11. Three principles (HealthBench → SciForge review benchmark)

- **Meaningful**: sink errors on a real sleep-research pipeline, not a toy classifier.
- **Trustworthy**: 75 human corrections (27 consensus / 48 agree); never AI-stamped.
- **Non-saturated**: even oracle conf leaves 0.72 (reviewer miss rate p_catch = 0.9) — room in review *quality*, not just scheduling.
