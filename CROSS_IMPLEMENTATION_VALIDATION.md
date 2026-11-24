# Three implementations, one finding — and which numbers are canonical

Written 2026-11-24 after the Role 2 and Role 3 work landed on `main`. Purpose: state plainly what is now
authoritative, what each table may and may not be compared with, and what the convergence of three
independent implementations actually buys the argument.

**Short version.** The canonical environment is `role3 improvement/` at tag `role3-env-v3`; the canonical
measurements are `role2_규리/results/`; `experiments/` is the earlier, smaller replica kept for provenance. All
three agree: a deterministic marginal-value rule beats the learned policy, and on real data the per-node
scheduling problem has almost no headroom left to win.

The result that survives is therefore not the scheduler. It is the measurement of **which signal to trust**:
a global gate that fails in both directions, a per-node repair that wins exactly where errors are masked, a
per-graph repair that costs +0.005 errors on a harmless global shift where the per-node repair loses +0.81, and
a measured boundary where both single-δ repairs collapse to plain trust. Two of those steps are self-declared
failures and are kept as failures.

---

## 1. The three lines

| Line | Environment | Simple rule | Learned policy | Verdict |
|---|---|---|---|---|
| `experiments/` (earlier) | Spike N=80, 4 layers, 20 sinks, budget 16, 200 held-out graphs | belief greedy **1.14** | GNN+REINFORCE **1.56** | rule wins by 0.42 |
| `role2_규리/` | Role 3 v3 Spike, 200 held-out graphs, paired CIs | adaptive marginal **1.130** | GNN 1.410 / 1.590 / 1.455 (3 training seeds) | rule wins; no learned seed beats it |
| `role3 improvement/` | v3 env, 100 graphs per family, 5 families | marginal **0.66** | GNN 0.96 / 1.17 / 1.06 | rule wins on spike; GNN CIs contain 0 |

Three codebases, three people, different seeds, different sink definitions, different budgets. Same ordering.
That is the useful part: the result is not a property of one generator.

## 2. What each line is good for

| Line | Use it for | Do not use it for |
|---|---|---|
| `role3 improvement/` | the environment everyone runs; baselines per family; the frozen checkpoints | real-data claims; cross-family comparison of raw means |
| `role2_규리/` | the robustness results (misspecified confidence), the planning and credit-assignment studies, the KAIST two-night check | anything at N=500; anything claiming the learned policy wins |
| `experiments/` | provenance of the first result; the real sleep-pipeline DAG (N=21) and the real-data replays | scale claims; the final numbers in a slide |

## 3. The four independent nulls on real data

This is the part that should change how the project is pitched.

| Evidence | Source | Result |
|---|---|---|
| Real sleep DAG N=21, budget 8 | `experiments/real_pipeline_table.md` | confidence threshold 0.50 vs random 1.88; supervision is nearly saturated |
| Within-record replay, 75 human corrections | `experiments/results.md` §12a | two reviews already clear the record — the budget 8 is 4–8× what the task needs |
| Cross-record replay | `experiments/results.md` §12b | one row-level QC rule reaches 0.014 vs oracle 0.000 |
| Public sleep diaries (KAIST), two nights per participant | `role2_규리/results/sleep-v1` | feedback-driven two-night choice +0.000014 [−0.0014, +0.0012] vs the QC rule |

Four different data views, one conclusion: **per-node review scheduling is not where the remaining error is.**
The proposal should say so, and move the contribution to (a) estimating which signal can be trusted and
(b) behaving safely when it cannot.

## 4. What survives, and it is not "RL wins"

Differences below are **policy − comparison**, paired inside one run; negative means fewer remaining errors.

| Claim | Evidence | Status |
|---|---|---|
| A graph-aware value rule beats static confidence ordering | role3: marginal 0.66 vs 1.03 on spike, gains on all five shapes; role2: 1.130 vs 1.545 | supported |
| Selecting the model when the confidence signal may be corrupted | role2: 4.415 → 3.150 under unrecognised uniform noise, −1.265 [−1.545, −0.985] | supported |
| Updating trust in the signal from review outcomes | role2: 3.075 vs 3.820 under within-type permutation, −0.745 [−0.975, −0.520] | supported |
| Repairing corruption at the node level | role2: +0.105 [+0.040, +0.175] vs trust on the rank-preserving −1 shift; −0.370 [−0.520, −0.235] where errors are masked; +0.45/+0.72 on a harmless global +2/+3 | supported, with a boundary |
| Repairing it at the graph level — one shared δ per graph | role2: +0.005 [+0.000, +0.015] vs trust at +3 (node repair +0.81); 112-cell mean 1.303 → 1.203; at −4 it lands on the clean oracle (0.94 vs 3.86) | supported |
| The graph repair holds off its own δ grid | role2 boundary: mean \|δ error\| 0.174, map_q 0.991 at full coverage, 12/12 off-grid cells beat the node repair (mean −0.57) | supported |
| One shared δ covers two layers moving by different amounts | role2 boundary: −0.016 vs the node repair, 3/8 cells better; absolute levels trust 2.15 / node 1.89 / graph 1.87 — both repairs fall back to trust | **contradicted** (prediction withdrawn) |
| The rule's lead over confidence ordering survives a lower reviewer hit rate | role2 `p_catch`: sign holds at 0.60/0.75/0.90/1.00, +0.255 [+0.150, +0.375] … +0.530 [+0.370, +0.705] | supported |
| …and the lead grows as the hit rate falls | pre-registered prediction P2 | **contradicted** (`inverted`) |
| Planning two reviews ahead | role2: +0.035 [−0.025, +0.100] vs one-step mixture | **not supported** |
| Residual GNN on top of the rule | role2: +0.022 [−0.018, +0.072] | **not supported** |
| A third architecture (PPO) on the same environment | role3 `outputs/ppo-v1/`, 200 fresh graphs, seeds 4200–4399: +0.350 / +0.460 / +0.465 vs `marginal`, every CI excludes 0, inside the pre-registered REINFORCE bound | **third loss** — indistinguishable from REINFORCE, not better |
| Per-review credit assignment improves the trained model | role2: 4.549 → 2.926 across 5 seeds | supported *as a training result* |
| …therefore the trained model is deployable | role2 field comparison: 2.945 vs two-step rule 2.765 | **contradicted** |
| Per-node scheduling helps on real data | §3 above, four nulls | **not supported** |

`experiments/results.md` §12c used to read as if credit assignment had been withdrawn outright. It had not:
the training effect is real and replicated, the deployment claim is what fails. Both statements now appear
together in §13 of that file.

## 5. Reproduction receipts (run 2026-11-24)

| Check | Command | Result |
|---|---|---|
| Published role3 table vs regenerated CSV | `run_benchmark.py` with the 6 frozen checkpoints | 5 families × (confidence, marginal, gain, CI) all match `변경내역.md` to printed precision |
| role2 confidence study | `evaluate_conditions.py --graphs 200` | 21/21 cells identical to `results/confidence-v1/episodes.csv` |
| role2 planning study | `evaluate_planning.py --graphs 200` | 12/12 cells identical; adaptive − mixture = +0.035 in both |
| role2 boundary report (byte-level) | `report_scope_robust.py`, rendered twice from `episodes.csv` | identical sha256 (`ba2a2fc5…`); 6,400 rows, every row `reviews = 16` |

role2 scripts now import the environment through `role2_규리/_env.py`, which prefers an installed
`dag_role3` and falls back to the in-repo directory. `pip install -e "role3 improvement"` removes the
directory-name-with-a-space dependency entirely.

## 6. Rules for the next document that quotes a number

1. Name the line: `experiments/`, `role2_규리/`, or `role3 improvement/`. A table without a line label is not
   evidence.
2. Never put two lines in one column. Raw means are not comparable across sink sets and budgets — the `real`
   family alone differs (2.12 in `experiments/`, 2.26 in role3, different sink definitions).
3. A number that has no CSV under `outputs/` or `results/` does not go in a slide.
4. Quote the paired interval, not just the mean. `ba` in role3 is 39 wins / 16 ties / 45 losses with a positive
   mean improvement — the mean and the win rate tell different stories.
5. If a result is a null, write "not supported", not "no effect". Two of the six claims above are nulls and
   they are the most reviewer-resistant part of the work.

## 7. Gaps that are still open

- Role 4 (baselines/controls) and Role 5 have committed no code. The control set that exists is ours, not theirs.
- No CI. Tests are run by hand: `role3 improvement` 29 pass, `role2_규리` 4 pass (checked 2026-11-24).
- `experiments/` and `role2_규리/` disagree on the sink definition for the sleep DAG (4 declared sinks vs
  childless nodes). Harmless while the tables stay separate; fatal if merged.
- No measured confidence signal. Everything above assumes the confidence score has a known error model; the
  real RDS calibration is still Gap D. The harness now exists
  (`role2_규리/signal_calibration_real.py`: fits `mu_err / mu_good / sigma` on human-audited rows, refuses
  simulated labels, warns below 200 rows) and the exact export is specified in
  `role2_규리/DATA_REQUEST_GAP_D.md`. Blocked on data, not on code.
