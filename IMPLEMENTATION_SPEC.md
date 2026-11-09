# Review Scheduling on a Dependency Graph — Implementation Specification

> STA3145 RL group project · implementation design (not a measured result) · 2026-11-09
> Companion: `PROJECT_EN.md` (narrative) · `PROJECT_CN.md` (中文) · `PROJECT_KO.md` (한국어)
> Style note: this document fixes the choices and assumptions needed to *build* the thing. Speed, memory, episode counts, and rewards below are starting values, not measured findings, unless a Section says "already run."

---

## 1. Research goal and scope

AI (a classifier, an LLM annotator, a diary-cleaning pipeline) produces a chain of dependent items. A human can review only a few. Errors are not random: they cluster by type, and an unreviewed error contaminates everything built on it. The harm shows up at the conclusion, not at the item.

**What we train:** a policy that decides *which node to review next* (or stop), under a budget.

**What we do not train:** the underlying AI classifier, an LLM, a vision model, or the sleep-cleaning R package. Those are frozen environments.

**Core distinction:** results are reported as **simulation performance** on (a) a synthetic DAG, (b) a real sleep-pipeline DAG encoded from splsleep SCHEMA, and (c) motivation numbers from 75 human corrections. They are not claims about production LLM servers or clinical deployment.

**Research questions**

- **RQ1.** Does a learned policy (REINFORCE / PPO / GNN scorer) beat the best *fixed* rule (per-type calibrated threshold, structural greedy) on mean sink errors?
- **RQ2.** Does the advantage depend on graph family (modular / scale-free / sparse / real pipeline), budget, and confidence-signal quality?
- **RQ3.** When RL does *not* win, can we locate the remaining error (policy vs predictor vs reviewer miss rate)?

**Already run (AI agent, unreproduced):** 80-node reframe (bandit negative result; GNN mean 1.54 ± 0.46); ablation (noise 3.78 / normal 1.38 / oracle 0.72); N=500 greedy baselines; real-pipeline threshold 2.12 → 0.50. This spec is what teammates run to reproduce and extend those numbers.

---

## 2. Environment specification (frozen choices)

### 2.1 Three graph families + one real pipeline

| Family | N | Edges (typical) | Generator | Use |
|---|---|---|---|---|
| `spike` (main RL) | 80 | ~2 parents/node, 4 layers | layered DAG, 5 types | GNN / REINFORCE / PPO / DQN |
| `modular` | 500 | ~750 | 10 clusters × 50; intra high, inter via 3 interface nodes | scale baselines |
| `ba` | 500 | ~1491, max_deg ~64 | Barabási–Albert `m=3`, oriented low→high index | scale-free / hub story |
| `er` | 500 | ~1850, max_deg ~14 | Erdős–Rényi `p=0.015`, oriented low→high | sparse control |
| `real` | 21 | 4 sinks | hand-encoded splsleep SCHEMA | application |

**DAG orientation rule (BA / ER):** every undirected edge `{u,v}` becomes `u→v` if `u<v`, else `v→u`. Self-loops dropped. Kahn's algorithm must return exactly N nodes or the seed is discarded.

**Modular interfaces:** only the last 3 nodes of cluster *c* may point into the first 5 nodes of cluster *c+1*, with probability 0.5.

### 2.2 Types and base error rates

**80-node main (K=5).** `P_TYPE = [0.01, 0.03, 0.08, 0.15, 0.25]` (deadly→mild after the 500-node fix; earlier 80-node runs used `[0.02,0.05,0.12,0.22,0.35]` — report which one a table used).

**500-node (K=10).** Zipf `p_t ∝ t^{-1.2}`, mapped to `0.02 + 0.38 * normalized_weight`. Deadly type ≈ 0.17, mildest ≈ 0.03.

**Real pipeline (K=6).** Rates matched to the 75 corrections:

```
order_error             0.35   # 76% of human corrections
awake_getup_diff_error  0.15
bed_sleep_diff_error    0.12
sleep_awake_equal_error 0.10
sleep_awake_24h_error   0.08
metric_spike            0.05
```

### 2.3 Propagation (causal intervention form)

For each edge `(u,v)` draw `w_uv ~ U(0.5, 1.5)` once per episode (baked into `coins`), then

```
P(X_v = 0 | X_u = 0) = 1 - exp(-λ * w_uv)
λ = 0.8   (500-node)     λ = 0.9   (real pipeline)
```

A review of node `v` is a **do-operator**: force `X_v = 1`. If the reviewer catches the error (`P_catch = 0.9`), recompute all descendants. Otherwise the error stays.

**Information leakage rule (hard):** the policy never sees `X_v`, `base[]`, or future coins. It sees only `type`, `confidence`, `sink_reach`, `reviewed`, `budget`. True errors are used *only* to (i) decide whether a review fixes the node and (ii) compute terminal reward.

### 2.4 Confidence signal (the predictor)

```
logit = (−1.5 if X_v=0 else +1.5) − 0.4·(P_TYPE[type] − 0.15) + N(0, 1.2)
conf = sigmoid(logit)
```

Ablation replaces this with `conf ~ U(0,1)` (noise) or `conf = −1.5 if X_v=0 else +1.5` (oracle). **Never feed true `X_v` into the policy except through these three conditions.**

### 2.5 Real-pipeline DAG (N=21)

```
layer 0 (leaves): time_bed, time_sleep, time_awake, time_getup,
                  sol_self, waso_self, waso_count, nap
layer 1:          bed_sleep_diff ← {time_bed, time_sleep}
                  sleep_awake_diff ← {time_sleep, time_awake}
                  awake_getup_diff ← {time_awake, time_getup}
                  SOL_calc ← {bed_sleep_diff, sol_self}
                  WASO_calc ← {waso_self, waso_count}
layer 2:          TST ← {sleep_awake_diff, WASO_calc}
                  TIB ← {time_bed, time_getup}
                  SE ← {TST, TIB}
                  TST_TIB_ratio ← {TST, TIB}
layer 3 (sinks):  SOL_validity ← {SOL_calc, bed_sleep_diff}
                  WASO_validity ← {WASO_calc, nap}
                  SE_conclusion ← {SE, TST_TIB_ratio}
                  record_quality ← {SOL_validity, SE_conclusion, WASO_validity}
```

Budget 8/21 (38%), λ = 0.9. This DAG is domain knowledge, not fitted.

---

## 3. Data

| Source | What | Used for | Never used for |
|---|---|---|---|
| `deidentified_intervalvars_forCD_111325.rds` | 13,990 rows / 237 participants | motivation counts only (N, 237) | never committed, never handed whole to an agent |
| `manual_error_correction_updated.csv` | 75 corrections; `order_error` 57/75 = 76%; 27 Consensus / 48 Agree | type rates, consensus/hard split (planned) | never committed; summary numbers only in docs |
| synthetic DAG | generated in code | all RL and scale experiments | — |

**Preprocessing of the 75:** count `error_type` and `agreement_cd_mtb`; drop nothing; report unlabeled (8 rows) separately. **Leakage:** do not fit the policy on the 75; they set type rates and the real-pipeline DAG.

**Train / val / test (synthetic):** seeds 1–5 train, seeds 1–16 evaluate (same evaluation seeds across policies). Time-split does not apply (i.i.d. graphs per episode). For a real-trace extension, split by `pid` 60/20/20 and never reuse a participant across splits.

---

## 4. MDP definition (exact)

### 4.1 Episode

One episode = one graph + one error draw + one confidence draw + one review trajectory.

```
for t in 1..T:
    observe s_t
    a_t = π(s_t)            # node index, or STOP if the action space has stop
    if a_t == STOP: break
    budget -= 1
    if err[a_t] and rng() < P_CATCH:
        base[a_t] = False
        err = recompute_downstream(base)
r_T = -sink_errors(err)
```

`T = budget` for fixed-budget policies (80-node main, GNN main). `T` is learned for the stop-action CMDP (naive version, not recommended for the main table).

### 4.2 State (GNN scorer, 80-node main)

Per node feature vector `F[i] ∈ R^{K+2}`:

```
F[i, 0:K]   = one-hot(type_i)
F[i, K]     = conf_i
F[i, K+1]   = log1p(sink_reach_i) / log1p(N)
```

GNN layer (1 message-passing, child → parent):

```
agg = A @ F                # A = row-normalized children adjacency
h   = tanh(F @ W_self + agg @ W_neigh)      # H = 32
s   = (h @ w + b).squeeze()                 # score per node
```

Masked softmax over unreviewed nodes. **No stop action in the main method** (fixed budget R=16 on N=80; R=50 on N=500). Stop action is only in the CMDP naive variant.

### 4.3 Action

Fixed-budget main method: pick the unreviewed node with the highest score (greedy eval) or sample from softmax (training). Equivalent to choosing one of N remaining nodes.

CMDP naive (do not use for the main table): `N` node actions + 1 STOP.

### 4.4 Reward

```
r_T = − sink_errors          # number of sink nodes still erroneous at the end
```

No per-step reward. Discount γ = 0.97 (REINFORCE MC uses the terminal directly, so γ matters only for the ablated TD variants).

CMDP naive (failed, keep for the report as a negative result):

```
G = r_T − λ_u · max(0, c − d_u) − λ_l · max(0, d_l − c)
d_u = 16, d_l = 8   (80-node)
λ update: λ ← clip(λ + α_λ · violation, 0, 2.0),  α_λ = 8e-4
```

### 4.5 Information-gain alternative (not yet run)

```
R = α · ΔH_v − β · Cost(v)
ΔH_v = H(conclusion) − H(conclusion | review v)
```

Implement as a Monte-Carlo proxy: `ΔH_v ≈ (sink errors before − after) / n_MC`. Use only if the main terminal-reward runs are too sparse; do not add this on top of the already-run numbers without a new seed protocol.

---

## 5. Training configuration (the numbers we actually used)

### 5.1 GNN + REINFORCE (main method)

| Item | Value | Source |
|---|---|---|
| Optimizer | Adam | `rl_cmdp_gnn.py` / 80-node isolated run |
| Learning rate | 0.003 | same |
| Hidden | 32 | same |
| Episodes | 20000 (the 1.20 run) / 12000 (the 2.05 run) — **use 20000** | training-sensitive |
| Temperature | `max(0.3, 2.0 · 0.9993^ep)` | same |
| Baseline | EMA `0.95·old + 0.05·r` | same |
| Budget | 16 | 20% of 80 |
| P_catch | 0.9 | same |
| Train seeds | 1, 2, 3, 4, 5 | multi-seed script |
| Eval seeds | 1..16 (`CFG["seeds"]`) | same |

**Multi-seed result (already run):** per-seed `[1.85, 1.60, 1.35, 1.00, 1.90]`, mean **1.54**, std 0.37, 95% CI **[1.08, 2.00]** (t_{0.025,4}=2.776). Do not cite 1.20 without this CI.

### 5.2 GNN + PPO (not in the main table)

lr 0.001, clip 0.2, epochs 2–3, 8k–20k episodes — **has not converged (~5.60)**. Owners may retry with (i) value normalization, (ii) advantage whitening, (iii) smaller lr. Do not put unconverged PPO in Slide 8.

### 5.3 CMDP naive (negative result, keep as ablation)

PPO-Lagrangian + STOP + coverage ∈ [8, 16]. lr 0.003, α_λ 8e-4, λ clip 2.0, 20k episodes. Result **4.85**. Diagnosis: one terminal return for the whole trajectory cannot credit the STOP decision. Next implementation, if anyone builds it: **separate reward-critic and cost-critic** (FALCON style), GAE for both, then Lagrangian on the cost advantage. Do not call 4.85 "RL fails"; call it "our naive CMDP fails."

### 5.4 DQN (control)

MLP Q-network on (ctx, features), replay 20k, target update 200, γ=0.98, ε 1.0→0.05. Result **5.10** on 80-node active selection. Keep as the value-based control. Do not tune it into a win — the degeneracy is the teaching point.

### 5.5 MLP REINFORCE / PPO (preliminary 80-node)

Hidden 32, lr 0.003 / 0.001, 12k–20k episodes, conf_bins = 8 for the tabular variants. Results 1.40 / 1.60. These are the bridge from the bandit negative result to the GNN upgrade.

---

## 6. Comparison policies (run these on every graph family)

| Policy | Rule | Purpose |
|---|---|---|
| No review | never review | floor |
| Random | uniform R nodes | attention without a rule |
| Confidence threshold | review the R lowest-conf nodes | static, ignores the graph |
| Hub | review the R highest out-degree / children | topology prior, ignores conf |
| Structural greedy | each step, pick the currently erroneous node that most reduces sink errors | (1−1/e)-style influence maximization |
| Oracle conf | GNN or greedy with true `X_v` in the features | signal ceiling |
| **GNN + REINFORCE** | learned scorer, fixed budget | **main method** |
| Oracle SJF / true-error greedy | know `X_v`, review truly wrong nodes in greedy order | unrealistic ceiling |

**Hard rules for a fair comparison**

1. Same evaluation seeds, same graph seeds, same coins.
2. Same budget R.
3. Same P_catch.
4. Greedy and oracle are marked separately from the learned policies.
5. If a policy uses validation data to pick a threshold, every policy gets the same tuning budget.

**Already-run N=500 means (5 seeds, budget 50, λ=0.8):**

| family | no review | random | threshold | hub | greedy |
|---|---|---|---|---|---|
| modular | 24.0 | 22.6 | 8.6 | 19.0 | **2.0** |
| BA | 80.6 | 79.2 | 29.8 | 53.8 | **3.8** |
| ER | 42.6 | 42.0 | 16.4 | 34.6 | **8.2** |

Real pipeline (8 seeds, budget 8, λ=0.9): no review 2.12, random 1.88, hub 1.75, **threshold 0.50**.

---

## 7. Metrics and success criteria

| Metric | How | Why |
|---|---|---|
| Mean sink errors | primary | the objective |
| Worst-of-n | max over train seeds on the shared eval set | one unreviewed error can invalidate a conclusion (HealthBench lens) |
| 95% CI | t-distribution over train seeds | GNN 1.54 ± 0.46 already computed |
| P99 sink errors | if n_sinks is large enough (500-node) | tail, not just mean |
| Ablation gap | normal − noise; normal − oracle | is the signal used; is the predictor the ceiling |
| Graph-family gap | greedy − threshold on BA vs ER | does topology change the best rule |
| Reviewer miss | 1 − P_catch = 0.1 residual | non-saturation |

**Do not claim a win if** the CI of the learned policy includes the greedy mean. Current honest sentence: *GNN mean 1.54 is comparable to structural greedy (1.80) and MLP REINFORCE (1.40); best seed 1.00 shows headroom; the ablation says the confidence signal, not the scheduler, is the remaining error.*

**Must-show figures (same spirit as the LLM spec's four figures):**

1. Method-comparison bars (all families / all policies) — `results_bar.png`, `scale500.png`
2. Ablation bars (noise / normal / oracle) — `ablation_conf.png`
3. Learning curves — `learning_curves.png`
4. Real-pipeline bars — `real_pipeline.png`
5. (add if time) GNN attention / chosen-node heatmap by layer and type

---

## 8. Controls (break the structure, watch the advantage die)

| Control | What it breaks | Expected |
|---|---|---|
| Shuffle `base[]` | type clustering | learned advantage disappears |
| Clear all `parents[]` | propagation | advantage disappears; problem becomes independent bandits |
| noise conf | predictor | RL worse than a static threshold (already: 3.78 > 2.30) |
| oracle conf | predictor ceiling | large gap vs normal (already: 0.72 vs 1.38) |
| Flatten + shuffle together | both facts | RL ≈ random |

Run each control with the *same* trained policy and the *same* eval seeds. Do not retrain on the control unless the section is labelled "retrained under control."

---

## 9. Four-week plan (implementation, not narrative)

| Week | Build | Done looks like |
|---|---|---|
| 1 | Freeze `spike_active_selection.py` + `graph_scale.py` + `real_pipeline_graph.py`; reproduce: bandit negative (threshold 2.81 > Q 3.38), GNN multi-seed CI, N=500 table, real-pipeline table | numbers in `experiments/` match this spec's tables within seed noise |
| 2 | Dual-critic CMDP (FALCON-style) **or** GNN+REINFORCE on N=500 subsample (e.g. 200 nodes) — pick one, do not do both badly | either "CMDP beats naive 4.85" or "GNN at 200 nodes" |
| 3 | Consensus/hard split of the 75 (27/48); ablation on each; controls on N=500 | two-row table: consensus vs agree |
| 4 | Slides from `presentation_outline.md` with the four/five figures embedded; ≥2 rehearsals | talk |

**Code layout (already mostly true):**

```
experiments/
  spike_active_selection.py   # 80-node env + greedy/threshold
  graph_scale.py              # N=500 modular/BA/ER
  real_pipeline_graph.py      # N=21 SCHEMA DAG
  rl_active_selection.py      # REINFORCE on active selection (early)
  rl_methods_compare.py       # REINFORCE/PPO/DQN MLP
  rl_cmdp_gnn.py              # GNN + CMDP naive
  rl_gnn_multiseed.py         # 5-seed GNN
  rl_ablation.py              # noise/normal/oracle
  rl_final.py                 # figures from frozen numbers
  plot_*.py                   # figures
  verify_clustering.py        # real-data counts (skips if file missing)
```

Do not add a new method without a new file and a new seed protocol.

---

## 10. Expected difficulties and the honest response

| Difficulty | Response |
|---|---|
| GNN does not stably beat greedy at N=500 | Report it. The 500-node claim is *greedy nearly clears the graph*; RL at that scale is future work. Do not force a win. |
| GNN 1.20 vs 1.54 CI includes greedy 1.80 | The claim is "comparable, high variance, best seed 1.00 shows headroom." The ablation (conf is the bottleneck) is the X-factor, not "RL wins." |
| Dual-critic CMDP still fails | Report the naive 4.85 and the reason (terminal-only credit). Cite FALCON as the recipe we did not finish. |
| Real pipeline is too small (N=21) for GNN | That is fine. It is the application-value table, not the RL table. Threshold 0.50 is the result. |
| Consensus/hard split has only 27 consensus rows | Report as a split of the motivation data, not as a powered experiment. |
| Reviewer miss 10% means we never reach 0 | Non-saturation. Say so. Next lever is P_catch / review quality, not the scheduler. |
| Teammate cannot reproduce 1.54 | Re-run `rl_gnn_multiseed.py`; if the CI moves, update every doc. Never hand-edit a table. |

**Information-leakage checklist (run before every table):**

- [ ] Policy features do not contain `base`, `err`, `coins`, or future finish times
- [ ] Oracle / true-error greedy is visually separated in every table and figure
- [ ] Validation thresholds (if any) are tuned on train/val seeds only
- [ ] The 75-row CSV is not in the repo and was not pasted whole into a prompt
- [ ] Worst-of-n uses the same eval episodes as the mean

---

## 11. Evaluation philosophy (HealthBench + BioBasicsBench, applied)

- **Meaningful:** sink errors on the real sleep pipeline and on structured DAGs, not a toy classifier accuracy.
- **Trustworthy:** 75 human corrections (27 consensus / 48 agree); the machine never stamps a SciForge receipt.
- **Non-saturated:** oracle conf 0.72 ≠ 0; BioBasicsBench top model 66.7% — both have room.
- **Partial-credit rubric (SciForge receipts, not yet in the simulator):** which downstream metric, severity, certainty.
- **Error detection is a first-class skill**, same as BioBasicsBench.
- **"Evidence cannot support this conclusion"** is an allowed suggester action, not only "review node 17."

---

## 12. What "better than the LLM-scheduling spec" means

The LLM spec (BurstGPT + Llama KV + PPO weights) is a tighter *systems* sandbox. Ours is a tighter *evidence-chain* sandbox. We do not beat them on token/s or KV GiB. We beat them — if we execute this spec — on:

1. A **negative result with a diagnosis** (bandit loses because the graph is flattened);
2. An **ablation that locates the remaining error** in the predictor, not the policy;
3. **Scale + topology** (BA hubs, modular clusters, real SCHEMA DAG);
4. **Honest multi-seed** (1.54 ± 0.46, not a cherry-picked 1.20);
5. **A decision guide** (noisy conf → do not use RL; large scale-free → greedy hubs; our real pipeline → threshold);
6. **Three-language project documents** a teammate can actually read.

That is the A+ version. It is not "we beat PPO on BurstGPT." It is "we used the same implementation discipline on a problem that spec does not touch, and we did not hide the failures."
