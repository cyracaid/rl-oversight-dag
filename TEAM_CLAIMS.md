---
title: "Team claims — who owns what"
layout: default
permalink: /TEAM_CLAIMS_EN.html
---

# Team claims — who owns what

<p><b>Language:</b> <a href="https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.html">summary</a> · <b>English</b> · <a href="https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_KO.html">한국어</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_CN.html">中文</a></p>

> 5 people · 2 tracks · talk on **11/23**
> One sentence: we study **where a human should look first** in a chain of dependent AI outputs.
> First real data: sleep diaries (Maia ten Brink, Stanford). Second target: SciForge (Zhangyang Gao, Shanghai AI Lab).

---

## Read this first: the words

| Word | Plain meaning |
|---|---|
| **belief greedy** | the simple rule we have to beat: "review the node whose review is expected to cut the most downstream errors" |
| **learned policy** (GNN + REINFORCE) | our trained model. Right now it is **worse** than the rule: 1.56 vs 1.14 |
| **sink errors** | how many wrong values reach the final conclusion. Lower is better |
| **held-out** | graphs the model never saw while training — the honest score |
| **N=21** | our real lab pipeline (21 steps), not a synthetic graph |
| **shuffle / flatten** | controls that destroy the graph. If our advantage survives them, the graph is doing the work |
| **Gap A / B / C / D** | the four things we do not have: SciForge export (A), consensus labels (B), a third dataset (C), a better confidence signal (D) |
| **N=500, three shapes** | 500-node synthetic graphs: modular (clusters), scale-free (a few hubs), random. Checks whether the method survives scale. |
| **27/48 split** | of the 75 corrections, 27 were agreed by more than one annotator, 48 by one. Results are reported on both halves. |
| **misspecification** | we deliberately give the model wrong assumptions — wrong edge probabilities, drifting type rates, 30% missed errors — and see who survives. |
| **credit assignment** | deciding which of the 16 review actions deserves credit for the final score. Terminal reward makes this hard. |

---

## 0. Two tracks, one method

| | **Track P — course paper** | **Track C — SciForge** |
|---|---|---|
| What | the RL project for STA3145 | the same method as a read-only suggester inside SciForge |
| When | talk **11/23** | after the paper, or design-only in parallel |
| Who reads it | professor + classmates | 郑心 (chain owner) + Zhangyang Gao + lab users |
| Needs | synthetic graphs + sleep data + N=21 pipeline | the same, plus a de-identified SciForge graph export |

**The rule that keeps us sane: Track P never waits for Track C.** If SciForge is slow, the paper still ships.

---

## 1. Who owns what

Every row: **goal** → **this week** → **you own** → **hard part** → **principles** → **done when** → **don't**.

### Person 1 — PM + co-presenter
**Goal:** the paper and the talk ship on 11/23 with numbers that are still true.

**This week:** one-page timeline (who does what, who is blocked) and a slide skeleton.

**You own:**
- the timeline and the risk list, updated weekly;
- the deck: section order, one message per slide, timing;
- **the talk, first half** — problem, what we built, the result. Person 5 takes the second half. Rehearse together, twice, with a clock;
- the submission: file names, PDF export, who sends it.

**Hard part:** you produce no number yourself — every number belongs to someone else, and a nicer story is always available.

**Principles:** one number, one script, one source; unreproduced results go in limits, not the abstract; never edit a table by hand.

**Done when:** the timeline exists, both presenters have rehearsed twice with timing, and the submission checklist is done.

**Don't:** train models; own the SciForge integration; keep the three languages in sync — that is Person 5's.

### Person 2 — policy and confidence signal
**Goal:** find out whether the learned policy can beat the rule, and say which — with evidence either way.

**This week:** run the gate — add `gain(i)` to the node features, 5 seeds, 200 held-out graphs, paired.

**You own:**
- **the gate.** One experiment decides the project. `gain(i)` is the value the rule maximises: how many downstream errors a review of node *i* is expected to cut. The policy currently sees "how likely is this node wrong", not "how much is it worth reviewing".
- **the decision after the gate.** If the gap closes, the gap was a missing feature. If it does not, it is credit assignment. Then try n-step / actor-critic with `gain` as the baseline; if we are still ≥ 0.20 behind, stop and write why. Do not start a fourth variant.
- **the confidence signal.** The number that says how much we trust a node's verdict. The ablation says this is the lever: noise 3.78 / normal 1.38 / oracle 0.72.
- **the misspecification tests.** Break the model on purpose — edge probabilities off by ±50%, type rates drifting over time, reviewer missing 30% of errors. This is where a learned policy could beat a rule that trusts the model.
- **one paragraph** on why the gap exists.

**Hard part:**
- the rule is a planner with the model, not a heuristic;
- the easy explanation is spent: the belief posterior is already in the state and changed nothing (−0.00 ± 0.08);
- reward arrives only at the end, after 16 reviews — that is the credit-assignment problem;
- the signal sets the ceiling (0.72 oracle / 1.38 normal);
- seeds disagree (1.51 ± 0.41), so one run proves nothing.

**Principles:** write the bar down before running; paired held-out with 5 seeds only; a miss is a result, not a failure; never tune on held-out.

**Done when:** a paired table plus that paragraph, and code that reruns from a clean clone.

**Don't:** tune DQN until it looks like a win; touch SciForge code.

### Person 3 — environment and graphs
**Goal:** one frozen simulator that every other number comes from.

**This week:** freeze the three scripts and write the intervention rule into the code comments.

**You own:**
- the three scripts, frozen: `spike_active_selection.py` (the simulator), `graph_scale.py` (large synthetic graphs), `real_pipeline_graph.py` (the real pipeline);
- **the N=500 table.** 500-node synthetic graphs in three shapes — modular (clusters), scale-free (a few hubs), random. It answers: does the method still work when the graph is six times larger than the main setting?
- **the N=21 table.** Our real lab pipeline, 21 steps, budget 8. It answers: what happens on our own data? No review 2.12, threshold 0.50.
- **what "reproduce" means.** Someone else, from a clean clone and one command, gets the same numbers — not "it ran on my laptop".
- the rule "a review clears only the node's own error; errors inherited from upstream survive" (pinned by 5 tests).

**Hard part:** the environment is the critical path — if it moves, every table moves. The intervention semantics is easy to get wrong: the docs said the opposite in 8 places before the audit.

**Principles:** freeze before the paper weeks; any change gets a new tag and a full rerun; tests before prose; the simulator is the truth, not the paper.

**Done when:** the reproduction log and a tagged commit exist.

**Don't:** add a new graph family during the paper weeks.

### Person 4 — baselines and controls
**Goal:** a comparison fair enough that a reviewer cannot dismiss it.

**This week:** run the five baselines on the held-out graphs with paired CIs.

**You own:**
- the five baselines — confidence threshold, structural greedy, hub, no-review, random — on every graph shape, 5 seeds;
- **the controls.**
  - *flatten*: remove the graph and treat every node as independent. If our advantage disappears, it came from the graph — which is the claim.
  - *shuffle*: rewire the edges at random. If the advantage survives, it was not using the real structure.
- **worst-of-n**: the worst seed, not just the average — one unreviewed error can invalidate a conclusion.
- **the 27/48 split.** Of the 75 corrections, 27 were agreed by more than one annotator and 48 by a single one. Evaluate on both halves; if the policy only works on the single-annotator half, say so.

**Hard part:** controls that kill our own result feel like losing; a control that passes proves little, and one that fails is information.

**Principles:** same graphs, same randomness, paired; report worst-of-n; if a control removes the advantage, it goes in the abstract, not the appendix.

**Done when:** the control table and a note on what each control rules out.

**Don't:** download CIFAR-10H or BurstGPT.

### Person 5 — 동채하 — narrative, languages, SciForge, co-presenter
**Goal:** make the problem land for a reader who does not do RL, and keep the SciForge door open without delaying the paper.

**This week:** the motivation slide with the three real numbers.

**You own:**
- motivation: 75 corrections / 13,990 rows / 76% one type — plus the caveat that this is the *fix* type, not proof the AI caused it;
- related work: HealthBench and BioBasicsBench, 3–5 sentences each, with the difference from us;
- **keeping the three languages in sync** — Person 1 no longer does this; when a number changes, all three pages change in the same commit;
- **the talk, second half** — why it matters, related work, what is next — in English, rehearsed with Person 1;
- the one-page SciForge ask to 郑心 (export fields, receipt fields), and a note of the reply.

**Hard part:** the 75 corrections are easy to over-claim — they record the fix, not who caused it; the SciForge ask runs on someone else's schedule; three languages drift.

**Principles:** no number without its caveat; the partner decides, we ask; never promise an integration date; change all three languages in one commit.

**Done when:** those artefacts exist and the second half is rehearsed.

**Don't:** become the RL theory person.
---

## 2. What the paper looks like

One sentence per section:

1. **Problem** — two facts: errors cluster by type, and an unreviewed error is reused downstream.
2. **Bandit fails** — reviewing items one by one ignores the graph (Q-learning 3.38 vs threshold 2.81).
3. **Reframe as a graph MDP** — state, action, terminal reward, budget as the horizon.
4. **Our method** — GNN + REINFORCE; what it sees and what it does not.
5. **Ablation** — the confidence signal, not the scheduler, is the remaining error.
6. **Scale** — at 500 nodes a simple greedy nearly clears the errors.
7. **Real data** — the N=21 lab pipeline: no review 2.12, threshold 0.50.
8. **Controls** — shuffle, flatten, seeds, paired tests.
9. **Related work** — learning-to-defer, HealthBench, BioBasicsBench.
10. **Limits** — what we did not run and what we will not claim.

The paper does **not** need SciForge code. Sleep data is the first real instance, not the product.

---

## 3. The SciForge version, later

The same suggester becomes one read-only endpoint:

```
POST /suggest/review-order
  in:  a slice of the evidence DAG, a budget, the name of the confidence field
  out: ranked node ids with reasons (downstream, likelihood, type)
  never: a receipt, a stamp, a write
```

Zhangyang Gao decides whether it enters the client. 郑心 decides whether "followed the suggestion" becomes a receipt field. We never write into their chain.

**Order matters:** land the paper first. Trying to integrate before the paper is how this becomes an unfinished engineering project.

---

## 4. Verification: who re-runs which number

Nothing counts as verified until the named person reruns it.

| Number or claim | Who |
|---|---|
| every simulation number, the curves, shuffle/flatten | Person 3 + Person 4 |
| real data 76% / 13,990 rows / 237 people (recomputed 11-09) | Person 5 |
| why "no review" is 5.62 in one table and 5.90 in another | Person 3 |
| "no direct precedent" — search again | Person 5 |
| full texts of the cited papers | Person 5 |
| GNN vs belief greedy, and belief greedy when the model is wrong | Person 2 |
| GNN + PPO convergence | Person 2 |
| dual-critic CMDP | Person 2 |
| whether SciForge has a confidence field, and the graph size | Person 5 |
| the 27/48 split | Person 5 + Person 4 |
| the claim that BestReject is just our threshold | Person 5, if they read the full paper |
| stale numbers in slides or PDFs (old 1.54, "95%") | Person 1 |

---

## 5. Who waits for whom

```
Person 3 (environment)  →  Person 2 (policy)  →  Person 4 (controls)
        │
        └── Person 5 (SciForge ask, writing)  →  郑心 / Zhangyang Gao

Person 1 collects the timeline in parallel.
```

**Critical path:** Person 3's frozen environment. If it moves, every number moves.

---

## 6. Data: what exists and what is missing

| Data | Do we have it? | Who touches it |
|---|---|---|
| sleep diaries 13,990 rows / 237 people | yes (Maia, one year) | Person 5 (counts), Person 3 (N=21 graph) |
| 75 corrections (76% `order_error`, 27 consensus / 48 agree) | yes | Person 5 (motivation), Person 4 (split) |
| synthetic graphs 80 / 500 | yes (code) | Person 3 |
| real pipeline N=21 | yes (hand-encoded) | Person 3 |
| SciForge graph export | **no — Gap A** | Person 5 asks, Person 3 consumes |
| better confidence signal | **no — Gap D** | Person 2 (it is a model, not a dataset) |
| CIFAR-10H, BurstGPT, wet-lab images | **do not look for these** | — |

---

## 7. This week: claim your row in one line

Send one line in the group chat:

> I take **[row]** on **[Track P / Track C / both]**. My first deliverable is **[thing]** by **[date]**.

If you do not want your row, swap with someone. Two people must not share a row, and no row may be left empty.

---

## 8. The sentence each person should be able to say

| Person | Say this |
|---|---|
| 1 | "I keep the timeline and the proposal. 동채하 owns the evidence-chain design and the 郑心 ask." |
| 2 | "The learned policy is 1.56, the simple rule is 1.14. The ablation says the signal is the bottleneck. I will either close the gap or report why I could not." |
| 3 | "I own the environment. If the graph moves, every number moves. I freeze it and reproduce the tables." |
| 4 | "I own the baselines and the controls. If shuffle and flatten kill the advantage, the advantage was real. If they do not, we report that." |
| 5 | "I own the narrative, the 郑心 ask, the literature, the real-data motivation, and the English presentation." |
