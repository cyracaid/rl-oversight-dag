# Replay of the 75 real manual corrections on the sleep DAG

2026-11-23. Code: `experiments/replay_manual_corrections.py`.
Output: `runs/replay-manual-corrections/results.json`.

Purpose: replace "synthetic graph whose type rates were copied from the correction
file" with an actual per-record replay. Every node value here comes from that
record's own timestamps, and the ground truth comes from the human correction
stored in `manual_error_correction_updated.csv`. No error is sampled.

---

## 1. What was actually run

| item | value |
|---|---|
| rows in the correction file | 75 |
| rows replayed (four complete timestamps) | **53** |
| rows dropped (a timestamp is missing) | 22 (bed 8, sleep 11, getup 2, awake 1) |
| participants | 36 |
| nodes | 14 (4 leaves → 3 diffs → 3 metrics → 4 sinks), a reduction of the 21-node `real_pipeline_graph.py` |
| validation gate | our computed `bed_sleep_diff_h` / `sleep_awake_diff_h` / `awake_getup_diff_h` vs the CSV's own columns: **159/159 cells match** (tolerance 0.02 h) |

Node error = the node's value disagrees with the value after applying the human's
`correct_value` to `column_to_correct`. Sink errors = how many of the four
conclusion flags disagree with the truth flags. Thresholds are taken from
`splsleep/inst/config_default.yaml` (bed→sleep > 7 h, awake→getup > 7 h,
sleep→awake > 24 h, SOL > 120 min, WASO > 90 min, SE outside [0,100] or
TST/TIB outside [0.5, 1.0]).

Limits: the DAG is recomputed in Python, not produced by the R package; the
reviewer is simulated (catch = 0.9); 22 rows are excluded; this is a pilot, not a
reproduction of the pipeline.

## 2. What the real records show

| statistic | value |
|---|---|
| rows with 1 defective source field | 37 |
| rows with 2 defective source fields | 16 |
| wrong nodes per record | **5.92 / 14 (42%)** |
| sink errors per record before review | **1.53 / 4** |
| rows with 0 sink errors before review | 7 |

**Propagation is real, and measurable without a simulator.** Among the 37 rows
with exactly one defective source field, that single defect still corrupts
**1.84 of 4 conclusions** on average (0: 4 rows, 1: 11, 2: 9, 3: 13). This is the
premise of the project, now measured on our own data rather than assumed.

By error type (sink errors before review): order_error 1.62 (n=40),
bed_sleep_diff_error 2.33 (n=3), awake_getup_diff_error 1.00 (n=2),
sleep_awake_equal_error 2.00 (n=1), unlabeled 0.71 (n=7).

## 3. Policy comparison (sink errors, lower is better; mean over 30 seeds, sd in parentheses)

Two reviewer models, because the answer depends on which one is true:

* **root_cause** — inspecting any wrong node lets the reviewer name the defective
  source field. This is what the `problem_humanidentified` column actually shows
  ("Participant initially wrote 00::05 …").
* **local** — inspecting a node only fixes a defect at that node or at its direct
  parents, so a depth-3 sink needs a walk up the graph.

### root_cause reviewer

| budget | none | random | threshold | structural | leaf_first | oracle |
|---|---|---|---|---|---|---|
| 1 | 1.53 | 0.90 (0.11) | 0.42 (0.13) | **0.19 (0.09)** | 0.53 (0.07) | 0.14 (0.07) |
| 2 | 1.53 | 0.52 (0.14) | 0.08 (0.06) | 0.10 (0.08) | 0.37 (0.07) | 0.01 (0.02) |
| 4 | 1.53 | 0.16 (0.09) | 0.00 (0.01) | 0.02 (0.03) | 0.13 (0.07) | 0.00 (0.00) |
| 8 | 1.53 | 0.01 (0.01) | 0.00 (0.00) | 0.00 (0.00) | 0.00 (0.01) | 0.00 (0.00) |

### local reviewer

| budget | none | random | threshold | structural | leaf_first | oracle |
|---|---|---|---|---|---|---|
| 1 | 1.53 | 1.34 (0.17) | 1.36 (0.16) | 1.08 (0.11) | **0.56 (0.07)** | 0.92 (0.08) |
| 2 | 1.53 | 1.16 (0.15) | 0.99 (0.12) | 0.88 (0.11) | **0.43 (0.07)** | 0.17 (0.09) |
| 4 | 1.53 | 0.75 (0.14) | 0.33 (0.11) | 0.45 (0.10) | 0.30 (0.13) | 0.00 (0.01) |
| 8 | 1.53 | 0.15 (0.07) | 0.08 (0.05) | 0.03 (0.04) | 0.03 (0.03) | 0.00 (0.00) |

95% bootstrap CIs over rows (seed 0) for the cells that matter:
root_cause b1 structural [0.02, 0.19], threshold [0.21, 0.66], random [0.60, 1.13];
local b1 leaf_first [0.32, 0.75], threshold [0.94, 1.58].

## 4. Findings

1. **The premise survives the replay.** One human-verified source error corrupts
   ~42% of the reduced graph and 1.8 of 4 conclusions. Propagation is not a
   simulator artefact.
2. **Within a record there is almost no scheduling problem.** With a root-cause
   reviewer, two reviews clear essentially every record (0.08). The team's budget
   of 8 of 21 nodes is 4–8× more than the task needs, because each corrected
   record carries only 1–2 source defects.
3. **Structure still pays when the budget is ~1.** At budget 1, structural greedy
   gets 0.19 vs threshold 0.42 and random 0.90. So the graph ordering matters only
   in the tight-budget regime; it disappears by budget 2.
4. **If the reviewer cannot trace root cause, review raw inputs first.**
   Under the local reviewer, leaf_first beats threshold at every budget
   (b1 0.56 vs 1.36). That is a concrete process recommendation for the lab,
   and it matches the semantics audit: a review only helps where the error is
   at the source.
5. **Consequence for the proposal.** The 80-node synthetic graph overstates what
   our own corrections contain. On real records the interesting graph is
   *across* records — days inside a participant, participants inside a study —
   where a mis-ordered night propagates into weekly/monthly summaries and the
   conclusion, and where the budget is smaller than the number of records. That
   is the graph the RL should be trained on; the within-record DAG is too small.

## 5. Honest caveats

* 22 of 75 rows dropped; 53 rows, 36 participants, 1–2 defects each.
* 14-node reduction, Python implementation, not the R package's output. The
  validation gate only checks the three diff columns.
* Reviewer catch = 0.9 assumed, not estimated from annotator data.
* Review cost is one unit per node regardless of depth; if tracing a sink costs
  more than reading a leaf, structure would pay more than this table shows.
* 7 rows have no sink error before review, so our reduced DAG misses part of why
  they were flagged.
* The observable suspicion signal and the sink definitions share the same
  thresholds, so "the top-suspicion node is wrong in 53/53 rows" is close to
  circular. It says the existing QC flags are informative, not that a learned
  scorer would be.

## 6. 한 줄 요약 (KO)

실제 정정 53건을 되돌려 재생하면, 오류 하나가 노드의 42%와 결론 4개 중 1.8개를
오염시킨다(전파는 실재). 그러나 원인 추적형 검토에서는 검토 2회면 레코드가
정리되므로 **레코드 내부에는 스케줄링 문제가 거의 없다**. 그래프의 가치는
레코드 사이(일→주→결론) 집계에 있고, 그쪽이 RL을 훈련할 진짜 그래프다.
