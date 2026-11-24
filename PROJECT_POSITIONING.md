# Project positioning: structure vs signal

Status: 2026-11-24. This note decides what the project is allowed to claim and
what it must stop claiming. It does not replace `BENCHMARK_SPEC.md` (frozen
numbers) or `experiments/results.md` (evidence). It is the argument that connects
them.

---

## 1. What we set out to do, and what the data said

Original claim: *when AI outputs depend on each other and a human can review only
some of them, learn which node to review next, so the final conclusion is less
often wrong.*

The method works as a method. It does not work as a product. Those are different
sentences and the evidence separates them cleanly:

| Level | Evidence | Verdict |
|---|---|---|
| **A benchmark exists and is solvable** | `BENCHMARK_SPEC.md`, 6 families, 5 baseline layers | yes |
| **Graph-aware rules beat flat heuristics when the graph is large** | scale-free 80.6 → 12.8 (belief greedy), modular 24.0 → 8.4 | yes |
| **RL beats the best simple rule** | 200 held-out graphs: belief greedy 1.14 vs GNN+REINFORCE 1.56; no learned seed beats `marginal` on any family | **no** |
| **A better reward improves the trained model** | credit assignment: 4.549 → 2.926 errors, 5/5 seeds | yes (training only) |
| **The improvement survives deployment** | same study, two-step rule still ahead by 0.180 [0.021, 0.377] | **no** |
| **It helps on the lab's real pipeline** | N = 21, budget 8: threshold 2.12 → 0.50, but hub = random, and one seed ends at 3 | weak |
| **It helps on the lab's real records** | 75 corrections, 2,652 nights: single-night review is diluted; QC flags already at 99.8 % on visible errors | **no** |

So the project's contribution is not "RL saves review budget". It is:

> **Review scheduling decomposes into *which node to open* (structure) and *what a
> node's error is worth* (signal). On synthetic graphs the structure side is where
> the headroom is; on real records the structure side has almost no headroom,
> because the signal — and the data capture — is the bottleneck.**

That sentence is supported by four independent lines of evidence below, and it is
a *stronger* paper claim than the original one, because it explains why the
original one failed.

---

## 2. The decomposition

A review policy needs two things and they are usually conflated:

* **structure**: given that nodes are connected, which node's correction propagates
  furthest? This is the graph problem.
* **signal**: how likely is this node wrong, and how much does being wrong there
  cost? This is the measurement problem.

Our own ablations and the real-data replays put almost all of the variance on the
signal side:

| Observation | Numbers | Source |
|---|---|---|
| Destroy the confidence signal | 1.38 → 3.78 errors (worse than a static threshold) | §7 ablation |
| Perfect the confidence signal | 1.38 → 0.72, approaching oracle | §7 ablation |
| Graph structure on the real DAG | hub = random (both 1.88); only the *calibrated threshold* separates | §8d |
| Cross-night consistency vs action unit | night-vs-block matters only when budget < run length; the score decides | §12d |
| Visible real errors | one existing QC rule = 0.00 sink errors at budget 4, oracle 0.00 | §12d |
| Learned cross-night score | logistic model on 11 observable features, held-out participants: matches the hand-crafted score on silent defects | §12f |

Two independent experiments, on different data, reach the same sentence: **the
score is the bottleneck, not the scheduler.** That is the paper.

---

## 3. The sleep data as a negative example, not a failure

The lab's data is not a place where the method wins. It is the place where the
method's *premise* fails, and saying so precisely is the contribution.

Three levels, each refuting a different assumption:

1. **Within a record** (`results.md` §12a): the real pipeline DAG has 14 nodes
   after reduction, and 1–2 root-cause reviews clear a record. The graph is
   smaller than the benchmark's, so ordering has less to exploit.
2. **Across records** (`results.md` §12b): one corrupted night is diluted by the
   record's other nights, and visible errors are already caught at 99.8 %. The
   reviewable population is nearly empty.
3. **Across a run of nights** (`results.md` §12d): even when a defect is shared by
   a contiguous block, the unit (night vs block) is secondary to having a
   cross-night score.

And the capture checks (`CAPTURE_CHECKS_INTERPRETATION.md`) close the loop: 39.3 %
of nights report WASO = 0, 3.6 % of records report it every night, and 10.2 % of
records contain an AM/PM error that a deterministic rule repairs. Three of the
four defect classes are fixed *before* review, and one of them cannot be fixed by
review at all.

**This is the honest external-validity result**: not "the method underperforms",
but "in this domain the problem the method solves does not exist at a scale worth
solving, and the defects that do exist live upstream".

---

## 4. Claim ladder (what may be written where)

| Claim | Where it may appear | Evidence file |
|---|---|---|
| Budgeted review scheduling on a DAG is a well-defined benchmark with a solvable structure side | method / benchmark section | `BENCHMARK_SPEC.md` |
| Graph-aware rules beat flat heuristics at N = 500, and the gap to oracle is the mean-field approximation, not the learner | results | `outputs/v3-baselines/`, §8b |
| A learned policy does not beat the best simple rule on held-out graphs | limitation, stated plainly | `learned_vs_marginal.md` |
| Improving the reward improves training but not deployment | results + limitation (both true at once) | §13 |
| In the sleep pipeline the structure side has no headroom; the signal and the capture do | discussion / external validity | §12a–f, capture checks |
| "RL reduces human review by X %" | **nowhere** | retired (legacy seeds 1–20) |

Rule of thumb for every future sentence: if it needs a number from the legacy
column, it is not allowed; if it needs a number from a pilot run, it must be
labelled *pilot* and *simulated*.

---

## 5. How this becomes a paper

Three contributions, in the order a reviewer will accept them:

1. **A benchmark that separates structure from signal.** Six graph families, five
   baseline layers, frozen splits, paired intervals. The point of the benchmark is
   that it can *show a method failing*, which most review-scheduling benchmarks
   cannot.
2. **A negative structural result with a mechanism.** Learned schedulers do not
   beat a belief-greedy rule; the headroom is in the mean-field approximation and
   in the confidence signal, quantified by ablation (1.38 vs 3.78 vs 0.72).
3. **An external-validity study that locates the boundary.** On real sleep
   records, the reviewable population is ~0 because the defects are conventions
   and missing fields. This is what tells a reader when *not* to use the method,
   and it is measured on 2,652 nights and 75 human corrections rather than
   asserted.

The failure mode to avoid: presenting 1 and 2 as if 3 did not happen. A reviewer
who finds the real-data section will trust the paper more, not less, if the paper
says it first.

---

## 6. Reviewer questions and the prepared answers

| Question | Answer | Where |
|---|---|---|
| "Does RL beat your baselines?" | No, and we say so. Belief greedy wins on held-out graphs. | §13, `learned_vs_marginal.md` |
| "Then why RL at all?" | Because the reward formulation is what exposed the bottleneck; the learned model is the instrument, the finding is the signal. Also: per-review credit assignment improves training 4.5 → 2.9 with 5/5 seeds. | §13 |
| "Is the benchmark just a simulator?" | Yes, and its real-data counterpart is reported as a negative result rather than omitted. | §12a–f |
| "Are the real-data numbers statistically powered?" | Where they are not, we say so: the correction-clustering test has 13 usable nights and no power, so it neither supports nor refutes the block hypothesis. | `BLOCK_REVIEW_NOTE.md` §4 |
| "Why is the QC baseline so strong?" | Because it is the lab's actual rule. We found and fixed a bug where our implementation of it silently ranked by midpoint instead of flags; the regression test is in the repo. | `BLOCK_REVIEW_NOTE.md` §5 |
| "What would you do with more data?" | Fix capture first: 24-hour time entry, an intake question about awakenings, and coverage printed next to every mean. Those are cheaper than any scheduler and they remove three of four defect classes. | `CAPTURE_CHECKS_INTERPRETATION.md` |

---

## 7. What to do next, ranked

| # | Action | Cost | Why |
|---|---|---|---|
| 1 | Ship the capture fixes (24 h input, WASO intake question, coverage column) | small | Removes 3 of 4 defect classes; measurable immediately (10.2 % AM/PM, 39.3 % zero-WASO nights) |
| 2 | Write the paper as benchmark + negative result + boundary study | medium | The evidence is already in the repo; this is assembly, not new experiments |
| 3 | Replace the hand-crafted cross-night score with a learned one in the DAG benchmark | medium | §12f shows it is learnable; this would turn "signal > structure" into a design recommendation |
| 4 | More RL tuning | **not now** | §7 and §12d both say the remaining error is upstream of the policy |

Item 4 is the one to resist. Every result in this repo that improved the scheduler
without improving the signal moved the number by less than the seed spread.
