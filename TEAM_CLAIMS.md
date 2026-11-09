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

## Read this first: seven words

| Word | Plain meaning |
|---|---|
| **belief greedy** | the simple rule we have to beat: "review the node whose review is expected to cut the most downstream errors" |
| **learned policy** (GNN + REINFORCE) | our trained model. Right now it is **worse** than the rule: 1.56 vs 1.14 |
| **sink errors** | how many wrong values reach the final conclusion. Lower is better |
| **held-out** | graphs the model never saw while training — the honest score |
| **N=21** | our real lab pipeline (21 steps), not a synthetic graph |
| **shuffle / flatten** | controls that destroy the graph. If our advantage survives them, the graph is doing the work |
| **Gap A / B / C / D** | the four things we do not have: SciForge export (A), consensus labels (B), a third dataset (C), a better confidence signal (D) |

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

### Person 1 — PM / narrative
**You own:** the timeline, the proposal, the slides, and keeping the three language versions in sync.
**Done when:** the 12-page narrative with figures exists; the slides are rehearsed; no stale numbers are left in any PDF.
**Don't:** train models. Don't become the SciForge integrator.

### Person 2 — policy and confidence signal
**You own:** getting the learned policy to beat the simple rule — or explaining, with evidence, why it does not; plus the confidence-signal upgrade.
**Where we are:** 1.56 vs 1.14 on held-out graphs, gap **+0.42 ± 0.15**. The ablation says the *signal* is the lever: noise 3.78 / normal 1.38 / oracle 0.72.
**Done when:** the gap is below zero on held-out graphs, or there is a written reason it is not; and either a better confidence signal or a written reason it cannot be improved.
**Don't:** tune DQN until it looks good. Don't touch SciForge code.

### Person 3 — environment and graphs
**You own:** the simulator and the graphs (`spike_active_selection.py`, `graph_scale.py`, `real_pipeline_graph.py`). Freeze them.
**Done when:** the N=500 table and the N=21 table reproduce from a clean clone.
**Don't:** introduce a new graph family during the paper weeks.

### Person 4 — baselines and controls
**You own:** threshold / greedy / hub / no-review / random on every graph family; the shuffle and flatten controls; the 27/48 split **only if** Person 5 hands over the labels.
**Done when:** the controls reproduce, and the split table exists — or a line saying it was not run.
**Don't:** download CIFAR-10H or BurstGPT.

### Person 5 — 동채하 — narrative, SciForge liaison, literature, presenting
**You own:** the motivation (75 corrections, 13,990 rows), the related-work section (HealthBench, BioBasicsBench), the 郑心 ask, and presenting in English.
**Done when:** the related-work section and the motivation slide exist; the one-page SciForge ask is written; you have rehearsed once.
**Don't:** become the RL theory person. The method is Persons 2–3.

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
