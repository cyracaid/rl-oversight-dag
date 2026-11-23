# Cross-record replay: does one bad night survive aggregation?

2026-11-23. Code: `experiments/cross_record_replay.py`.
Output: `runs/cross-record-replay/results.json`.

The within-record replay (`REPLAY_MANUAL_CORRECTIONS_INTERPRETATION.md`) showed the
graph is real but tiny: 1–2 source defects per record, cleared by 1–2 root-cause
reviews. Its own conclusion was that the interesting graph is *between* records.
This is the test of that claim, on the actual 13,990-row daily panel.

Input: a de-identified daily export of `pid`, `day_num`, the four clock times, and
the self-reported SOL / WASO estimates, written to `${TMPDIR}` by R and never
committed. 2,652 nights from 237 participants; 196 participants have ≥ 10 nights
(median 12). 178 nights dropped (implausible duration: TST > TIB, or TIB > 24 h
after clock-time anchoring).

## 1. Design

Per night the pipeline computes SOL, sleep period, TIB, TST, SE and the sleep
midpoint. Per participant it produces four conclusions, which are the "sinks":

| sink | rule |
|---|---|
| C1 short sleep | mean TST < 420 min |
| C2 low efficiency | mean SE < 85 % |
| C3 irregular | circular sd of sleep midpoint > 60 min |
| C4 data quality | every night passes the package's order rules |

Two corruptions, both taken from real `error_type` values in the correction file:

* **visible** — ±12 h on one time field, chosen so the order rules break
  (`order_error`, 76 % of the 75 corrections).
* **silent** — self-reported WASO set to 0 (`sleep_awake_equal_error`). Order stays
  valid, so nothing in the QC rules can see it.

Review policies see only observable signals (the package's order/SOL/WASO rules),
never the truth.

## 2. Does one bad night move a conclusion?

| corruption | C1 short | C2 efficiency | C3 irregular | C4 quality | QC flags it |
|---|---|---|---|---|---|
| visible (±12 h) | 0.2 % | **25.3 %** | 0.6 % | 89.1 %* | **99.8 %** |
| silent (WASO→0) | 0.2 % | 0.5 % | 0.0 % | 0.0 % | 2.9 % |

\* C4 flips by construction: the corruption is defined as breaking the order rules,
so the quality flag must go false. It is a check that the mechanism works, not a
finding. Read the C4 column as "the pipeline notices", not as "a conclusion broke".

Aggregate movement from one corrupted night out of ~12:

| corruption | mean TST | mean SE | midpoint sd |
|---|---|---|---|
| visible | 1.5 min (p90 0.0) | **4.3 pts** (p90 5.4) | 1.0 min (p90 0.0) |
| silent | 0.8 min (p90 2.3) | 0.15 pts (p90 0.4) | 0.0 min |

So: **random single-night corruption is mostly diluted.** Averaging over 12 nights
absorbs it, and the current QC rules catch 99.8 % of the visible ones anyway. The
one conclusion that does move is mean SE, and only by ~4 points.

## 3. Review policies at participant level (sink errors, lower is better)

Budget = number of nights you may open, out of ~12.

| corruption | budget | none | random | QC-rule | extreme-value | oracle |
|---|---|---|---|---|---|---|
| visible | 1 | 0.582 | 0.524 | **0.014** | 0.472 | 0.000 |
| visible | 2 | 0.582 | 0.471 | **0.002** | 0.379 | 0.000 |
| visible | 3 | 0.582 | 0.428 | **0.001** | 0.295 | 0.000 |
| silent | 1 | 0.008 | 0.006 | 0.008 | 0.004 | 0.000 |

Two things follow.

1. **A one-line rule beats every smarter alternative.** Ranking nights by the
   existing order/SOL/WASO flags gets 0.014 at budget 1, i.e. it finds the bad
   night almost always. Something adaptive has to beat *that*, not the random
   baseline — and the gap between QC-rule and oracle is 0.014.
2. **"Extreme value" is the trap.** Ranking by distance from the participant's
   median TST (a natural anomaly heuristic) is barely better than random (0.472
   vs 0.524) and 30× worse than the QC rule. An outlier night is usually a real
   short night, not an error.

The silent case is below everywhere: all policies sit at 0.004–0.008, i.e. the
error does not matter at aggregate level, so no scheduler can show a gain.

## 4. What actually breaks a participant conclusion: scale, not scheduling

If the defect is systematic (one session, one import, one device, one AM/PM
convention applied to a whole file) then a fraction of the nights is wrong at once:

| share of nights corrupted | C1 short | C2 efficiency | C3 irregular | any conclusion |
|---|---|---|---|---|
| 10 % | 0.3 % | 14.1 % | 0.4 % | **49.2 %** |
| 25 % | 0.3 % | 41.5 % | 1.2 % | **80.7 %** |
| 50 % | 0.5 % | 68.2 % | 1.6 % | **94.0 %** |

This is the real risk profile: a single bad night is noise, a systematic bias is
decisive. Review scheduling that picks one night out of twelve is therefore
solving the wrong problem. What matters is detecting that *a block* is wrong and
which block.

## 5. Side finding: the default cuts do not discriminate in this cohort

Share of the 196 participants for whom each conclusion is already true, and how
close the rest sit to the cut:

| conclusion | already true | median margin | p90 single-night shift | within one bad night of flipping |
|---|---|---|---|---|
| C1 short sleep (< 420 min) | **82.7 %** | −42.6 min | 0.0 | 0.0 % |
| C2 low efficiency (< 85 %) | **79.1 %** | −4.8 pts | 5.4 pts | **13.8 %** |
| C3 irregular (sd > 60 min) | **80.6 %** | −25.4 min | 0.0 | 0.0 % |

Four out of five participants already meet three of the four "problem" cuts. With
cuts that nearly everyone crosses, a conclusion cannot separate anyone, and its
sensitivity to a single corrupt night is not the binding issue. The thresholds in
`inst/config_default.yaml` are the long-standing defaults; for this cohort they
are miscalibrated. **The binding problem is the cut, not the review schedule.**

## 6. What this means for the RL project

1. **Within-record:** no scheduling problem (previous report).
2. **Across-record, single night:** no scheduling problem either — the average
   absorbs it and the existing QC rule already finds it (0.014 vs oracle 0.000).
3. **Across-record, systematic bias:** a real problem (25 % bad nights → 81 % of
   participants misclassified), but it is not a per-node review-ordering problem.
   It is a *block detection* problem: which participant-session is wrong, and is
   the whole block wrong.
4. **Population level:** the default classification cuts are the bottleneck
   (≈80 % prevalence on three of four conclusions).

So the "review scheduling on a dependency graph under a budget" formulation is
best supported where the graph is *not* a within-night DAG and the unit of review
is *not* a single node. The defensible version for this lab is: **given a
participant's nights and a fixed review budget, choose which contiguous block of
nights to open** — the block carries a shared cause, so opening one night inside
it is nearly useless, and the QC flags are already near-optimal for single nights.

That is a genuinely different MDP from the one in the current simulator, and it is
the one worth training on. It should be stated as a *proposed next experiment*,
not as a result.

## 7. Caveats

* Corruptions are synthetic in *placement* but real in *type*. Real errors are not
  uniformly random across nights; that is exactly why §4 exists.
* The visible corruption is deliberately order-breaking, and the QC-rule policy
  uses the same order rules, so §3's visible column is close to circular. It
  establishes an upper bound on what a flag-based policy can do, not a fair fight.
* 178 nights dropped; the four clock fields are self-reported and anchored into a
  ±12 h window around the previous field, which is a modelling choice.
* Circular sd uses the mean-resultant-length estimator.
* C4 is definitional and excluded from the "conclusion" reading.
* One cohort, one pipeline version; thresholds are the package defaults.
* No human labels at participant level — the truth is "the aggregate computed from
  the (presumed correct) nights", not a clinician's judgement.

## 8. 한 줄 요약 (KO)

실제 2,652박·237명 패널로 재생하면, 하룻밤 오류는 12박 평균에 희석되고(결론
전환 25% 이하), 기존 QC 규칙이 그 하룻밤을 99.8% 잡아낸다. 반면 **체계적 편향**
(25% 박 오염)은 참가자 81%의 결론을 뒤집는다. 따라서 검토 스케줄링은 "노드 하나"가
아니라 "연속된 박 블록"을 여는 문제로 재정의해야 하며, 인구 수준에서는 기본
분류 컷(3/4 결론에서 80%가 이미 해당)이 진짜 병목이다.
