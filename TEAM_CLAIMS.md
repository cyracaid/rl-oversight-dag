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

Every row: **goal** → **why** → **this week** → **what to do, in order** → **hard part** → **principles** → **done when** → **don't**.

### Person 1 — PM + co-presenter
**Goal:** the paper and the talk ship on 11/23 with numbers that are still true.

**Why:** nobody else owns the whole picture. If the deck and the numbers are assembled in the last three days, the talk will contain a number that no longer holds — that is the normal failure mode of a five-person project.

**This week:** one-page timeline (who does what, who is blocked) and a slide skeleton.
**What to do, in order:**
1. Put the timeline on one page: milestone, owner, dependency, date. Update it every Monday.
2. Build the deck skeleton — 8–10 slides, one message per slide.
3. Under each slide, write where its number comes from (script + table). No source, no slide.
4. Every week: read the newest tables from Persons 2–4, update the deck, delete stale numbers from slides and PDFs.
5. Keep the benchmark list with Person 5 — one line per candidate: what it measures, why we cite or exclude it.
6. Book two rehearsals with a clock; split the talk (you take the first half, Person 5 the second).
7. Submission checklist: file names, PDF export, who sends it, and the deadline in which time zone.
8. Run the distillation probe (behaviour cloning from belief greedy, then REINFORCE fine-tune) and hand the paired table to Person 2.


**You own:**
- the timeline and the risk list, updated weekly;
- the deck: section order, one message per slide, timing;
- **the benchmark scan** — keep a running list of benchmarks we could compare against (learning-to-defer, annotation quality, AI4Science evaluation), check what each one actually measures, and decide with Person 5 which we cite and which we deliberately exclude. A reviewer will ask "why not X"; have the answer ready.
- **the distillation probe** — belief greedy as the teacher: collect (state, action) pairs, train the policy by cross-entropy, then fine-tune with REINFORCE. This is the "(b)" path: can the policy represent the rule at all? Hand the paired table to Person 2.
- **the talk, first half** — problem, what we built, the result. Person 5 takes the second half. Rehearse together, twice, with a clock;
- the submission: file names, PDF export, who sends it.

**Hard part:** you produce no number yourself — every number belongs to someone else, and a nicer story is always available.

**Principles:** one number, one script, one source; unreproduced results go in limits, not the abstract; never edit a table by hand.

**Done when:** the timeline exists, both presenters have rehearsed twice with timing, and the submission checklist is done.

**Don't:** train models; own the SciForge integration; keep the three languages in sync — that is Person 5's.

### Person 2 — policy and confidence signal
**Goal:** find out whether the learned policy can beat the rule, and say which — with evidence either way.

**Why:** the whole project is this one question. Right now our method loses (1.56 vs 1.14). Without an answer, the paper is just a table where we lose. With an answer, it says either "the gap was a missing feature / credit assignment, and here is the fix" or "the gap is structural, and here is where it starts". Every other section of the paper exists to support that one paragraph.

**This week:** run the gate — add `gain(i)` to the node features, 5 seeds, 200 held-out graphs, paired.

**What to do, in order:**
1. In `rl_gnn_multiseed.py`, add `gain(i)` to the observed-state features. `gain(i)` is the expected drop in reachable sink errors if node *i* is reviewed — the exact quantity the rule argmaxes.
2. Write the bar down first: ≤ 1.14, or non-inferior (paired CI contains 0, point estimate < +0.05).
3. Run 5 seeds × 20k episodes, evaluate on held-out graphs 1000–1199, paired. Put the number in the table before interpreting it.
4. If the bar is met: the gap was representational. Record it and stop.
5. If not: add n-step returns or an actor-critic with `gain(a_t)` as the baseline. One variant, one night.
6. If still ≥ +0.20 behind: stop. Write the paragraph on why, hand the numbers to Person 1. No fourth variant.
7. In parallel: fit a small confidence predictor (or recalibrate), and measure noise / normal / oracle (3.78 / 1.38 / 0.72).
8. Then the misspecification runs: edge probabilities ±50%, type rates drifting, reviewer missing 30%.
9. Hand the table and the paragraph to Person 1 one day before the rehearsal.

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

**Why:** every number in the paper is an output of this code. If the simulator is not frozen and reproducible, nothing else means anything: a reviewer cannot tell a real effect from a changed parameter, and we cannot tell either. The job is to make "the same numbers" a property of the repository, not of one laptop.

**This week:** freeze the three scripts and write the intervention rule into the code comments.

**What to do, in order:**
1. Freeze `spike_active_selection.py`, `graph_scale.py`, `real_pipeline_graph.py`. After this week, any change means a new tag and a full rerun.
2. Write the rule into the comment at `review_step`: a review clears the node's own source error; errors inherited from upstream survive and can re-infect the node. (Already pinned by 5 tests — keep them green.)
3. Run `graph_scale.py` on the three families — modular (clusters), scale-free (hubs), random — 500 nodes, budget 50 → the **N=500 table**.
4. Run `real_pipeline_graph.py` — 21 steps, budget 8, 8 seeds → the **N=21 table** (no review 2.12, threshold 0.50).
5. Write one command that regenerates both tables (a small script or a README block).
6. From a fresh clone, run that command, diff the output against the committed tables, and keep the log.
7. Tag the commit.
8. Hand the tag and the reproduction log to Person 1.

**Hard part:** the environment is the critical path — if it moves, every table moves. The intervention semantics is easy to get wrong: the docs said the opposite in 8 places before the audit.

**Principles:** freeze before the paper weeks; any change gets a new tag and a full rerun; tests before prose; the simulator is the truth, not the paper.

**Done when:** the reproduction log and a tagged commit exist.

**Don't:** add a new graph family during the paper weeks.

### Person 4 — baselines and controls
**Goal:** a comparison fair enough that a reviewer cannot dismiss it.

**Why:** a result is only as strong as its comparison. Weak baselines or missing controls give a reviewer the easiest possible objection — "your advantage is an artifact" — and they would be right. This row exists to remove every explanation except the one we claim.

**This week:** run the five baselines on the held-out graphs with paired CIs.

**What to do, in order:**
1. Fix the baseline list: confidence threshold, structural greedy, hub, no-review, random. Same graphs, same seeds, same budget.
2. Run all five on the 200 held-out graphs, 5 seeds, paired; report mean and 95% CI per policy.
3. Run the two controls:
   - *flatten*: remove the graph, treat every node as independent. If our advantage disappears, it came from the graph — which is the claim.
   - *shuffle*: rewire the edges at random. If the advantage survives, our policy was not using real structure.
4. Report **worst-of-n** next to the mean for every policy — one unreviewed error can invalidate a conclusion.
5. If Person 5 delivers the 27/48 labels: run the best policy on each half, one table, two rows. If it only works on the single-annotator half, say that.
6. Write one line per control: what it rules out.
7. Hand the table and the lines to Person 1.
8. Keep the raw outputs in `experiments/` — no hand-edited tables, ever.

**Hard part:** controls that kill our own result feel like losing; a control that passes proves little, and one that fails is information.

**Principles:** same graphs, same randomness, paired; report worst-of-n; if a control removes the advantage, it goes in the abstract, not the appendix.

**Done when:** the control table and a note on what each control rules out.

**Don't:** download CIFAR-10H or BurstGPT.

### Person 5 — 동채하 — narrative, languages, SciForge, co-presenter
**Goal:** make the problem land for a reader who does not do RL, and keep the SciForge door open without delaying the paper.

**Why:** the method is only half the talk. The other half is why anyone outside this course should care — and that is a different skill. This row also owns the two fragile things: the three languages, and the relationship with the external partner.

**This week:** the motivation slide with the three real numbers.
**What to do, in order:**
1. Motivation slide: the three numbers (75 / 13,990 / 76%), one caveat line, one sentence on why nobody can check everything.
2. HealthBench paragraph: what it asks, what it measures, and the one difference from us (they grade a single reply; we schedule attention over a chain).
3. BioBasicsBench paragraph: real wet-lab evidence; the failure mode is an assumption overriding a control.
4. The SciForge ask: one page — nodes, edges, correction types, receipt fields (`reviewed_at`, `verdict`, `duration`). Log the reply in one line.
5. Keep the three languages in sync: same commit, then run the link check.
6. Second half of the talk: why it matters → related work → what is next. Rehearse twice with Person 1.
7. Hand the final text to Person 1 one day before the rehearsal.


**You own:**
- motivation: 75 corrections / 13,990 rows / 76% one type — plus the caveat that this is the *fix* type, not proof the AI caused it;
- related work: HealthBench and BioBasicsBench, 3–5 sentences each, with the difference from us — Person 1 brings the wider benchmark scan, and you two decide the final list;
- **keeping the three languages in sync** — Person 1 no longer does this; when a number changes, all three pages change in the same commit;
- **the talk, second half** — why it matters, related work, what is next — in English, rehearsed with Person 1;
- the one-page SciForge ask to 郑心 (export fields, receipt fields), and a note of the reply.

**Hard part:** the 75 corrections are easy to over-claim — they record the fix, not who caused it; the SciForge ask runs on someone else's schedule; three languages drift.

**Principles:** no number without its caveat; the partner decides, we ask; never promise an integration date; change all three languages in one commit.

**Done when:** those artefacts exist and the second half is rehearsed.

**Don't:** become the RL theory person.

### Timeline — who does what, when

| When | Person 1 | Person 2 | Person 3 | Person 4 | Person 5 |
|---|---|---|---|---|---|
| Mon 11/09 | timeline + deck skeleton | code `gain(i)`, smoke test | freeze the scripts, keep tests green | baseline list, data check | motivation numbers |
| Tue 11/10 | slide skeleton | run the gate, 5 seeds | reproduce N=500 and N=21 | run the five baselines | HealthBench / BioBasics draft |
| Wed 11/11 | collect the first numbers | read-out, **decide A/B** | publish the tag | first control results | send the SciForge ask |
| Thu 11/12 – Fri 11/13 | slides with real numbers | branch work (misspecification / credit) | reruns, 200-node GNN if there is time | shuffle / flatten, worst-of-n | related work, second half |
| Sat 11/14 | **numbers frozen** | final table + paragraph | reproduction log | control table | three-language sync |
| Sun 11/15 – Mon 11/16 | deck, rehearsal 1 | on call | on call | appendix | slides, rehearsal 1 |
| Tue 11/17 – Sun 11/22 | timing, rehearsals 2–3 | on call | on call | on call | English polish, rehearsals 2–3 |
| Mon 11/23 | first half | — | — | — | second half |

**Rules on the timeline:** the gate on 11/11 decides the branch; numbers freeze on 11/14; after 11/14 nobody starts a new experiment.

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

## 5. Who waits for whom — the prerequisite timeline

| # | Prerequisite (owner) | Due | What it unblocks | Hand-off |
|---|---|---|---|---|
| 1 | Freeze the simulator and the graphs (P3) | 11/10 | P2's gate; P4's baselines | tag + the one-line rule |
| 2 | Gate run with `gain(i)` (P2) | 11/11 | the A/B decision; P1's slides | paired table |
| 3 | **A/B decision** (P1 + P2) | 11/11, 18:00 | P2's branch; P4's final control set | one-page memo |
| 4 | Baselines + shuffle/flatten (P4) | 11/13 | the comparison section and the appendix | control table |
| 5 | Confidence signal (P2) | 11/14 | the limits section; Option A conditions | ablation table |
| 6 | N=500 and N=21 reproduction (P3) | 11/12 | the scale and real-data sections | reproduction log |
| 7 | Motivation numbers (P5) | 11/10 | the motivation slide | three numbers + caveat |
| 8 | Related work (P5) | 11/13 | the second half of the talk | section draft |
| 9 | SciForge ask (P5 → 郑心) | sent 11/11, reply by 11/18 | Track C only — never the paper | one-pager + one-line reply |
| 10 | Three-language sync (P5) | after every change | the submission | same-commit updates |
| 11 | Slides with real numbers (P1) | 11/13 | rehearsal 1 | deck v1 |
| 12 | **Numbers frozen** (everyone) | 11/14 | rehearsals 2–3 | tag + frozen tables |

**Critical path:** 1 → 2 → 3 → 4 → 12 → 11 → 11/23. If any of those slips a day, the talk slips a day.

**What has slack:** the SciForge ask (9) can arrive as late as 11/18 and nothing in the paper moves. Related work (8) can slip to 11/15 without touching a number.

**What must not slip:** the environment freeze (1) and the gate (2). Everything downstream is a function of those two dates.
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
