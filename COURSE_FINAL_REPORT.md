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
ourselves, and two later predictions were flatly reversed. That is the deliverable.

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
information available to the scheduler is worth more to a rule that uses it directly.

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

## 5. Failures we are keeping in the document

| failure | what it rules out |
|---|---|
| `verify` (global repair) | "use a better global statistic" — the trigger still fires on harmless shifts |
| node repair under a harmless global shift | a per-node posterior misreads "everything moved" as "many clean nodes moved" (+0.45 / +0.72) |
| two simultaneous δ | one shared δ per graph, and the per-node family, both fall back to trust |
| `p_catch` size prediction | "the advantage grows when reviewers are unreliable" |
| sampled counterfactual value (seeds 4400–4599) | "the oracle gap is mean-field double counting, and a better score closes it": recovery **−0.049 [−0.087, −0.015]** on modular, 30 graphs worse / 15 better / 155 tie |
| block review MDP (real records) | "the review unit is the bottleneck" — it is the score; block actions only pay below the run length |

## 6. What we can and cannot claim

**Can claim**, inside this benchmark, with the frozen numbers:

* the rule wins the scheduling comparison, across three architectures and one 10× compute check;
* a policy can detect that its confidence scores are unusable when the corruption is large and local, and stay
  near trusting when it is not;
* the decision variable moves node → graph, and the graph model tolerates an off-grid δ;
* with 16 reviews, masking corruption at +3 costs **+0.005 [0.000, 0.015]** errors versus plain trust, and a
  full −4 shift returns the policy to the clean oracle.

**Cannot claim**: that RL produces a gain here; that one shared δ covers two simultaneous shifts; that the
learned policy adapts to a lower hit rate (it was not retrained); that the gate generalises to small, partial,
or masking corruption; that any of this transfers to a real queue with 68 labelled errors.

## 7. The real data, stated plainly

75 human corrections out of 13,990 rows (0.54 %) are motivation, not a training set. On our own lab pipeline
(N=21) the threshold rule gives 0.50 residual errors against 2.12 for no review. On the 1,048-flag queue, one
rule reaches 84 % of errors with 13 % of the queue, but that is an information ceiling: 7 of 72 corrections are
never flagged at all. Ranking participants adds +7.3 % [−8.6 %, +10.0 %] — no significant gain. There is no
headroom to learn from, and we say so instead of quoting 84 % as a win.

## 8. Reproduction, and the honest gap

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
| 70000–70099 | calibration only (thresholds fitted here, never reported) |
| 90000–90099 | the reported benchmark table |
| 91000–94199 | assess / feedback / residual / planning |

Fresh: 4600 and above.

## 9. Gates, unchanged by anything above

| gate | now |
|---|---|
| R1 decisive result + 5 seeds + a second person | ✗ mechanism done (five steps, three codebases agreeing, byte-identical reruns); no second person |
| R2 a real queue with enough positives | ✗ 68 labelled errors, 6.5 % precision |
| R3 a second domain | partial: one synthetic family + one lab pipeline |
| R4 a sharp boundary | ◐ one measured (δ grid, single δ, hit rate, mean-field double counting ruled out); greedy-vs-learning still C1–C4 |
| R5 clean artifact | ◐ manifest, per-graph CSV, byte-identical reruns, seeded verdict code; not one command, no data card |

## 10. What we would do next, in order of cost

1. **One person reruns one chain from scratch.** Nothing else raises R1. Everything is scripted; the cost is a
   session, not a redesign.
2. **Widen the shortlist in the value check.** The failure above is a failure *inside* a mean-field top-16; the
   untested variant is scoring outside it. Fresh block 4600+, new preregistration.
3. **A real queue with hundreds of positives.** Without it, every general claim stays a synthetic-graph claim.

## 11. Where each number lives

| claim | file |
|---|---|
| rule vs learned, three architectures | `README.md` table; `role2_규리/results/confirm-v1/`, `role3 improvement/outputs/ppo-v1/` |
| gate / verify / shrink / scope / boundary | `role2_규리/results/{corruption,verify,shrink,scope}-v1/`, `scope-robust-v1/` |
| hit-rate sweep | `PREREGISTER_P_CATCH.md`, `role3 improvement/outputs/p-catch-v1/` |
| sampled value | `PREREGISTER_EXACT_VALUE.md`, `role3 improvement/outputs/value-v1/` |
| block review | `experiments/BLOCK_REVIEW_NOTE.md`, `experiments/results.md` §12d |
| real queue | `triage_bench/CEILING.md` |
| seed rules | `BENCHMARK_SPEC.md` §3 |
| what these numbers may be cited as | `CROSS_IMPLEMENTATION_VALIDATION.md` §4 |
