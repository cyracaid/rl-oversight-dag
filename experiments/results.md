# Empirical Results Summary (Final)

> **Canonical numbers live elsewhere since 2026-11-24.** `role3 improvement/` (tag `role3-env-v3`) is the
> frozen environment; `role2_규리/results/` holds the canonical measurements. This file is the earlier,
> smaller replica: keep it for provenance, the real-data replays and the N=21 sleep DAG, and do not mix its
> raw means with the other two lines. See `../CROSS_IMPLEMENTATION_VALIDATION.md`.

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
| hub (children) | 1.88 |

Hub equals random: degree-based selection carries no gain on this DAG (the
earlier 1.75 came from an edge-counting bug, fixed 2026-11-23). Threshold is the
only policy that separates: paired against random it gains 1.38 sink errors
(95 % CI 0.12–2.63, t on 8 paired seeds), and one seed still ends at 3 errors, so
the mean hides a real spread.

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

---

## 12. Real-data replays (2026-11-23): the graph is smaller than the simulator assumed

Two replays now use our own records instead of a simulator with copied type rates.
Both are pilots on our own records (12a: 53 corrected rows / 36 participants; 12b: the
full 13,990-row panel), not package-official output.

### 12a. Within record: 75 human corrections

`replay_manual_corrections.py` → `runs/replay-manual-corrections/results.json`,
written up in `REPLAY_MANUAL_CORRECTIONS_INTERPRETATION.md`.

53 of 75 rows have four complete timestamps (22 dropped); 36 participants; 14-node
reduction of the 21-node DAG. Validation gate: our recomputed `bed_sleep_diff_h`,
`sleep_awake_diff_h`, `awake_getup_diff_h` match the CSV's own columns in **159/159
cells** (0.02 h tolerance). No error is sampled — node values come from the record,
truth from `column_to_correct` + `correct_value`.

| statistic | value |
|---|---|
| wrong nodes per record | 5.92 / 14 (42 %) |
| sink errors before review | 1.53 / 4 |
| sink errors, rows with exactly one source defect (n = 37) | **1.84 / 4** |

Sink errors by budget (root-cause reviewer, mean of 30 seeds):

| budget | random | threshold | structural | oracle |
|---|---|---|---|---|
| 1 | 0.90 | 0.42 | **0.19** | 0.14 |
| 2 | 0.52 | 0.08 | 0.10 | 0.01 |
| 8 | 0.01 | 0.00 | 0.00 | 0.00 |

* Propagation is real and now measured on our data (1 source defect → 1.84 of 4 conclusions).
* **Within a record there is almost no scheduling problem**: two reviews clear it, so the
  budget of 8/21 is 4–8× the requirement.
* Structure pays only at budget ≈ 1 (0.19 vs 0.42); it disappears at budget 2.
* If the reviewer cannot trace root cause (local model), `leaf_first` wins at every budget
  (b1 0.56 vs threshold 1.36): open the raw fields first.

### 12b. Across records: does one bad night survive aggregation?

`cross_record_replay.py` → `runs/cross-record-replay/results.json`,
written up in `CROSS_RECORD_REPLAY_INTERPRETATION.md`.

2,652 nights / 237 participants (196 with ≥ 10 nights, median 12); 4 conclusions per
participant (short sleep, low efficiency, irregular midpoint, data quality).

| corruption | C1 | C2 | C3 | C4* | QC flags it |
|---|---|---|---|---|---|
| visible (±12 h, order_error) | 0.2 % | 25.3 % | 0.6 % | 89.1 % | **99.8 %** |
| silent (WASO→0) | 0.2 % | 0.5 % | 0.0 % | 0.0 % | 2.9 % |

\* definitional: the corruption breaks the order rules by construction.

Sink errors, budget 1 of ~12 nights: none 0.582, random 0.524, extreme-value 0.472,
**QC rule 0.014**, oracle 0.000.

* A one-line rule on the existing QC flags is within 0.014 of the oracle; anything
  adaptive has to beat *that*, not random.
* Systematic bias is the real risk: 25 % of a participant's nights corrupted →
  80.7 % of participants change a conclusion; 50 % → 94.0 %.
* Default population cuts do not discriminate in this cohort: 82.7 % / 79.1 % / 80.6 %
  of participants already meet the short-sleep / low-efficiency / irregular cuts.

**Consequence for the proposal.** Per-node review scheduling is not supported by our
own data at either level. The defensible formulation is *block* review: given a
participant's nights and a small budget, choose which contiguous block to open,
because a defect that matters is shared. That experiment has now been run at pilot
scale — §12d — and the short answer is that the **unit** (night vs block) is not the
bottleneck: the **score** is. Block actions pay off only when the budget is smaller
than the corrupted run and the score is a cross-night one.

### 12c. Numbers that must not be reused

* `order_error` = **57/75 = 76 %**, not 85.1 % (85.1 % = 57/67, 8 rows unlabeled).
* REINFORCE 1.40 / PPO 1.60 / threshold 2.30 / structural 1.80 are **legacy seeds 1–20**.
  On 200 held-out graphs: threshold 1.41, structural 1.45, **belief greedy 1.14**,
  GNN+REINFORCE 1.56. Do not quote the legacy column as the method comparison.

### 12d. Block review MDP: the unit is not the bottleneck, the score is

`block_review_mdp.py` (11/11 tests) → `runs/block-review-mdp/`;
full write-up and the bug that invalidated the first pass in `BLOCK_REVIEW_NOTE.md`.

196 participants / 2,372 nights (median 12); one contiguous 4-night run corrupted;
20 paired seeds (every policy sees the identical corrupted record); 178–188 usable
records per cell. **Budget unit = nights read**, so a 3-night window costs 3.
Reward = −(number of the 4 conclusions that disagree with the truth).

| corruption | budget | none | night QC | night mid | block3 QC | block3 mid | oracle |
|---|---|---|---|---|---|---|---|
| visible ±12 h (57/75 real) | 2 | 1.73 | 0.20 | 1.06 | **0.15** | 1.35 | 0.16 |
| | 4 | 1.73 | **0.00** | 1.06 | 0.00 | 1.08 | 0.00 |
| | 6 | 1.73 | **0.00** | 0.54 | 0.01 | 0.59 | 0.00 |
| silent 90 min offset (hypothetical) | 2 | 0.23 | 0.18 | 0.12 | 0.13 | **0.09** | 0.09 |
| | 4 | 0.23 | 0.08 | 0.05 | 0.10 | 0.06 | 0.03 |
| | 6 | 0.23 | 0.04 | **0.02** | 0.05 | 0.04 | 0.02 |
| silent WASO→0 (2/75 real) | 4 | 0.05 | 0.03 | 0.03 | 0.04 | 0.03 | 0.01 |
| | 6 | 0.05 | **0.02** | 0.02 | 0.02 | 0.02 | 0.01 |

\* At a 2-night budget a "block3" policy can only afford a 2-night window, so the
budget-2 block rows are really block2. Everywhere else the window is 3 nights.

Paired deltas vs night QC (bootstrap over 20 seeds, 95 % CI):

* visible, budget 2: block3 QC **−0.050 [−0.08, −0.03]**; budget 4: +0.002 [0.00, 0.00].
* silent 90 min, budget 2: block3 mid **−0.050 [−0.06, −0.04]**; budget 4: +0.016.
* WASO→0: every delta inside ±0.005.

Reading:

1. **Visible defects (the real 76 %):** one line on the existing QC flags is already
   at the oracle. A contiguous window of the affordable length buys 5 points of sink
   errors at budget 2 (0.15 vs 0.20, oracle 0.16) and nothing from budget 4 on,
   where both are 0.00.
2. **Silent, consequence-bearing defects:** at budget 2 the block + cross-night score
   is *exactly* the oracle (0.09) where per-night QC gets 0.18. But at budget 4 the
   per-night mid policy overtakes it (0.05 vs 0.06) and at 6 it ties the oracle.
   The advantage is a **budget < run-length** effect, not a structural one.
3. **Silent, no-consequence defects:** every policy lands in 0.02–0.05 and even the
   oracle only reaches 0.01. Nothing to schedule — that defect has to be fixed at
   capture time.
4. **Cost unit matters more than the action unit:** if an "attempt" (opening the
   record) reveals 3 adjacent nights, block3 QC reaches 99.5 % clean at 2 attempts vs
   86.6 % for night QC (`results_attempts.json`). That is the assumption doing the
   work, so it is reported as a sensitivity analysis, never as a finding.

**Correction-log check.** Do real corrections cluster? `correction_clustering.py`:
1 adjacent corrected-night pair vs 0.97 expected if scattered — but only 13 corrected
nights of the 12 multi-night records fall inside the export's day window, so the test
has no power. It neither supports nor refutes the block hypothesis.

**Verdict.** Neither "node" nor "block" is the right headline. The review scheduler
needs a **cross-night consistency score**; once it has one, the action unit is a free
parameter that only matters when the budget is below the run length. This is the same
conclusion as §7 (the confidence signal is the bottleneck), reached from different data.

## 13. Credit assignment: one training result, one deployment null (not one withdrawal)

Earlier revisions of this file said credit assignment had been "withdrawn". That was too coarse, and the
Role 2 experiments now separate the two claims:

| Claim | Evidence | Verdict |
|---|---|---|
| Per-review reward allocation improves the trained model | `role2_규리/results/credit-v1/`: 4.549 → 2.926 errors, −1.623 [−2.136, −1.033], same direction in 5/5 training seeds | **supported** |
| The improved model beats the simple rule in the field | Same study, held-out 200 graphs: model 2.945 vs two-step rule 2.765, rule ahead by 0.180 [0.021, 0.377] | **contradicted** |

Both statements are true at once. The training change works; the learned policy still loses to a deterministic
two-step rule. Any slide that says only one of them is wrong.

Adjacent nulls from the same line, which belong in the same paragraph:

* Two-step planning vs one-step mixture: +0.035 [−0.025, +0.100] — not supported
  (`role2_규리/results/planning-v1/`).
* Residual GNN on top of `marginal`: +0.022 [−0.018, +0.072] — not supported
  (`role2_규리/results/residual-v1/`).
* Two nights per participant on the public KAIST diaries: +0.000014 [−0.0014, +0.0012] vs the existing QC rule
  — not supported (`role2_규리/results/sleep-v1/`).

