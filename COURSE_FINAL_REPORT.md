---
title: "Course final report: what we can defend, and what we cannot"
layout: default
---

# Course final report: what we can defend, and what we cannot

<p><b>Language:</b> <b>English</b> · <a href="https://cyracaid.github.io/rl-oversight-dag/COURSE_FINAL_REPORT_CN.html">中文</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/COURSE_FINAL_REPORT_KO.html">한국어</a></p>

> STA3145 reinforcement learning · team project · final write-up, 2026-11-24.
> Every number below is paired, seeded, and regenerated from a committed CSV; the
> commands are in the same folders as the results. Nothing here was verified by a
> second person — §8 says what that costs us.

---

## 0. One paragraph

We asked when a learned review policy beats a simple model-based rule on a dependency graph of AI outputs.
It does not: three architectures, five seed blocks, and a 10× compute check all put the rule ahead. What
survived is a different question that the failure exposed — **which signal should the policy trust, and what
should it do when it cannot trust it.** Five pre-registered steps answer that inside this benchmark: a global
gate is wrong in both directions, the decision variable has to move down to the node and then up to the graph,
and the graph model's own boundary is measured rather than assumed. Two of those steps are failures we declared
ourselves, and two later predictions were flatly reversed. Two further pre-registered experiments then remove
the two cheapest explanations for the rule's remaining gap to an oracle — the one-step value estimate and the
belief's probability scale — leaving multi-step depth as the untested cell. That is the deliverable.

## 1. The question we started with

The evidence chain is a DAG: parsing creates variables, variables create metrics, metrics create conclusions.
With a budget of 16 reviews, the scheduling question is "which node next". A one-step posterior greedy
(`belief greedy` / `marginal`) answers it directly, and a learned policy was supposed to beat it when the rule's
model is wrong.

## 2. What we found first: the learner loses

| comparison | rule | learned | verdict |
|---|---|---|---|
| 200 held-out graphs, N=80, budget 16 | belief greedy **1.14** | GNN+REINFORCE 1.56 | rule wins, +0.42 ± 0.15 |
| untouched confirmation block 2000–2199 | `marginal` **0.885** | 1.185 / 1.325 / 1.275 | +0.377 [+0.255, +0.510] |
| 10× training budget | **0.885** | 1.155 / 1.140 / 1.145 | +0.262 [+0.165, +0.365] |
| PPO, fresh block 4200–4399 | **0.875** | 1.225 / 1.335 / 1.340 | `third-loss`, +0.350 … +0.465 |
| six families × 3 seeds (role 3) | `marginal` | GNN, DQN | rule wins 36/36 cells; gap 5–17 errors at N=500 |

Three architectures, same answer: this is not an optimizer problem and not a compute problem. The
information available to the scheduler is worth more to a rule that uses it directly. PPO is the sharpest
version of that sentence: it is neither better nor worse than REINFORCE, it simply loses to the same rule by
the same margin.

## 3. The reframe: which signal can be trusted

If the confidence scores are wrong, the scheduler is being asked the wrong question. The scores are wrong in
two ways that a single binary decision cannot separate — they can shift without changing the order (harmless),
or shift while masking real errors (harmful). We froze five steps, each in a `PREREGISTER_*.md` before its first
seed, each on a graph block no earlier run had used, each judged by code:

| step | fresh graphs | verdict | result vs trusting the scores |
|---|---|---|---|
| global gate | 3000–3199 | boundary measured | harmless −1: fires 195/200, **+1.82** errors; masked +3: 0/200, **+3.21** |
| gate repair (`verify`) | 3200–3399 | **failure** | −0.015 at −1, but 5 of 13 fired cells worse than trusting |
| per-node (`shrink`) | 3400–3599 | success | +0.105 at −1; **−0.370** where errors are masked; +0.45 / +0.72 on a harmless global +2 / +3 |
| per-graph (`scope`) | 3600–3799 | success | +0.005 at +3 (per-node +0.81); 112-cell mean 1.303 → **1.203**; −4 returns to the clean oracle (0.94 vs 3.86) |
| boundary | 3800–3899 | **partial success** | off-grid δ holds (mean \|δ error\| 0.174, 12/12 cells beat per-node); two δ collapse (−0.016; trust 2.15 / per-node 1.89 / per-graph 1.87) |

The claim this supports is narrow and measured: **with 16 reviews, a policy can estimate whether its confidence
scores are usable, and can stay safe when they are not.** The decision variable belongs at the node when the
question is "which node moved", and at the graph when the question is "did everything move".

The graph model's boundary is part of the result, not a footnote. It survives a shift that is not on its own
grid; it does not survive two layers moving by different amounts. In that second case both single-δ families
fall back to plain trust, so what is measured is "unresolved here", not "our method wins".

## 4. A prediction we got backwards

Every run above assumed reviewers catch 90 % of the errors they look at. Re-running at 0.60 / 0.75 / 0.90 / 1.00
(`PREREGISTER_P_CATCH.md`, seeds 4000–4199) kept the direction — the rule beats confidence ordering in all four
cells, +0.255 [+0.150, +0.375] to +0.530 [+0.370, +0.705], every interval excluding zero — and inverted the
pre-registered size prediction: the lead grows as reviewers become **more** reliable. `oracle` follows the same
path (+0.355 → +0.820), so the environment contracts rather than the rule improving. The frozen verdict is
`inverted`, and it is reported as a failed prediction, not rewritten.

## 5. Closing the gap: two explanations tested, both rejected

The rule loses 5–7 errors per graph to `oracle` at N=500. Three mechanical explanations were on the table; two
have now been frozen and measured on fresh blocks.

**The one-step value is not the problem** (`PREREGISTER_EXACT_VALUE.md`, 4400–4599). The mean-field score
double-counts a source error with two open paths, so we re-ranked the mean-field top 16 by a sampled paired
counterfactual gain (256 particles). Result: **`worse`** on modular, recovery −0.049 [−0.087, −0.015]; it
changed the action on 45 of 200 graphs and lost 30 of them. Better scoring *inside* the shortlist costs more
than it recovers.

**The belief's numbers are not the problem either** (`PREREGISTER_BELIEF_DECOMPOSITION.md`, 4800–4999). Hold
the belief's ranking bit-identical and distort only its values with `q = sigmoid(γ · logit(b))`. On modular the
verdict is **`policy-bound`**: the best cell (γ = 1.25) gives +0.016 [−0.055, +0.072], wins 46 graphs, loses 12,
and moves the aggregate by **−1 error out of 978**. γ = 0.5 costs 1.49 errors. On spike the label is
`calibration-partial` but it closes **0 of 49** errors, so it is not a gain at this size.

What remains is the third explanation: the rule cannot see what this review does to later reviews. Two-step
planning was tested on spike (+0.035, not supported) but never on modular, and an exact-DP ceiling on the rule's
own model is pre-registered and **not yet run**. We are not claiming the gap is now explained; we are claiming
the cheap explanations are gone.

## 6. Failures we are keeping in the document

| failure | what it rules out |
|---|---|
| `verify` (global repair) | "use a better global statistic" — the trigger still fires on harmless shifts |
| node repair under a harmless global shift | a per-node posterior misreads "everything moved" as "many clean nodes moved" (+0.45 / +0.72) |
| two simultaneous δ | one shared δ per graph, and the per-node family, both fall back to trust |
| `p_catch` size prediction | "the advantage grows when reviewers are unreliable" |
| sampled counterfactual value (4400–4599) | "the oracle gap is mean-field double counting, and a better score closes it" (recovery −0.049) |
| belief rescaling (4800–4999) | "the gap is a probability-scale error a temperature can fix" (−1 of 978 errors at the optimum) |
| block review MDP (real records) | "the review unit is the bottleneck" — it is the score; block actions only pay below the run length |

## 7. What we can and cannot claim

**Can claim**, inside this benchmark, with the frozen numbers:

* the rule wins the scheduling comparison, across three architectures and one 10× compute check;
* a policy can detect that its confidence scores are unusable when the corruption is large and local, and stay
  near trusting when it is not;
* the decision variable moves node → graph, and the graph model tolerates an off-grid δ;
* with 16 reviews, masking corruption at +3 costs **+0.005 [0.000, 0.015]** errors versus plain trust, and a
  full −4 shift returns the policy to the clean oracle;
* the residual gap to `oracle` is not the one-step value estimate and not the belief's probability scale.

**Cannot claim**: that RL produces a gain here; that one shared δ covers two simultaneous shifts; that the
learned policy adapts to a lower hit rate (it was not retrained); that the gate generalises to small, partial,
or masking corruption; that the gap is fully explained — the multi-step cell is open; that any of this
transfers to a real queue with 68 labelled errors.

## 8. The real data, stated plainly

75 human corrections out of 13,990 rows (0.54 %) are motivation, not a training set. Two checks on the real
records decide what review can even do there:

* **WASO is absent, not small.** 39.3 % of nights report exactly zero awakenings and 7 of 196 records do it on
  every night. On those nights the efficiency conclusion is not reviewable — no ordering rule can detect a
  well-formed night. The fix is at intake, not in the scheduler.
* **The dominant error is a convention.** 20 of 196 records (10.2 %) contain a night repaired by exactly one
  ±12 h shift, matching the `order_error` family (57 of 75 corrections). It is deterministic, so it should be
  auto-repaired rather than reviewed.

On the 1,048-flag queue, one rule reaches 84 % of errors with 13 % of the queue, but that is an information
ceiling: 7 of 72 corrections are never flagged. Ranking participants adds +7.3 % [−8.6 %, +10.0 %] — no
significant gain. There is no headroom for *visible* defects: 76 % of corrections are already solved.

There is headroom for *silent* ones. Replacing the hand-crafted cross-night score with a learned one (11
observable features, logistic fit, split by participant: 118 train / 78 held-out, 20 evaluation seeds) beats the
per-night QC rule on silent defects at budget 2 — WASO 0.039 → **0.014**, a 90-minute silent shift 0.162 →
0.083 — and a single pooled score without family labels keeps the gain on all three families. The honest limits:
the training labels come from the simulator, not from human review, so this is a mechanism result ("the signal
is in observable features"), not a deployment result.

## 9. Reproduction, and the honest gap

Every number was produced by an AI agent from committed scripts. Reruns are byte-identical, every report is
regenerated from its `episodes.csv`, and the reports are hash-pinned in their manifests. **No teammate has rerun
any of it**, which is why the first publication gate stays open regardless of how the numbers look.

Seed ledger — a block is spent once it has chosen a method or a threshold:

| block | used for |
|---|---|
| 1000–1199 | development |
| 2000–2199 | confirmation (role 2) |
| 3000–3199 | corruption boundary |
| 3200–3399 | `verify` |
| 3400–3599 | `shrink` |
| 3600–3799 | `scope` |
| 3800–3899 | boundary (off-grid, two δ) |
| 4000–4199 | `p_catch` |
| 4200–4399 | PPO |
| 4400–4599 | sampled counterfactual value |
| 4600–4799 | **void** — smoke runs only, excluded from every result |
| 4800–4999 | belief-value decomposition |
| 70000–70099 | calibration only (thresholds fitted here, never reported) |
| 90000–90099 | the reported benchmark table |
| 91000–94199 | assess / feedback / residual / planning |

Fresh: 5000 and above; 5200–5399 is reserved by a pre-registered depth-2 planning check.

## 10. Gates, unchanged by anything above

| gate | now |
|---|---|
| R1 decisive result + 5 seeds + a second person | ✗ mechanism done (five steps, three codebases agreeing, byte-identical reruns); no second person |
| R2 a real queue with enough positives | ✗ 68 labelled errors, 6.5 % precision |
| R3 a second domain | partial: one synthetic family + one lab pipeline |
| R4 a sharp boundary | ◐ one measured (δ grid, single δ, hit rate); the one-step-value and belief-scale explanations for the oracle gap are ruled out; greedy-vs-learning still C1–C4 |
| R5 clean artifact | ◐ manifest, per-graph CSV, byte-identical reruns, seeded verdict code; not one command, no data card |

## 11. What we would do next, in order of cost

1. **One person reruns one chain from scratch.** Nothing else raises R1. Everything is scripted; the cost is a
   session, not a redesign.
2. **Close the multi-step cell.** The exact-DP ceiling on the rule's own belief model is pre-registered and
   unrun; depth-2 on N=500 modular is the other half. Both are cheap relative to another architecture.
3. **A real queue with hundreds of positives.** Without it, every general claim stays a synthetic-graph claim.

## 12. Where each number lives

| claim | file |
|---|---|
| rule vs learned, three architectures | `README.md` table; `role2_규리/results/confirm-v1/`, `role3 improvement/outputs/ppo-v1/` |
| gate / verify / shrink / scope / boundary | `role2_규리/results/{corruption,verify,shrink,scope}-v1/`, `scope-robust-v1/` |
| hit-rate sweep | `PREREGISTER_P_CATCH.md`, `role3 improvement/outputs/p-catch-v1/` |
| sampled value | `PREREGISTER_EXACT_VALUE.md`, `role3 improvement/outputs/value-v1/` |
| belief values | `PREREGISTER_BELIEF_DECOMPOSITION.md`, `role3 improvement/outputs/belief-v1/` |
| block review | `experiments/BLOCK_REVIEW_NOTE.md`, `experiments/results.md` §12d |
| learned real-data score | `experiments/LEARNED_WINDOW_SCORER_INTERPRETATION.md` |
| capture-side checks | `experiments/CAPTURE_CHECKS_INTERPRETATION.md` |
| real queue | `triage_bench/CEILING.md` |
| seed rules | `BENCHMARK_SPEC.md` §3 |
| what these numbers may be cited as | `CROSS_IMPLEMENTATION_VALIDATION.md` §4 |
