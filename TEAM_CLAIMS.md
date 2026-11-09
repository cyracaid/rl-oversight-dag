---
title: "Team Claims: Paper Track & SciForge Track"
layout: default
---

# Team Claims: Paper Track & SciForge Track

> 5 people · two tracks · 2026-11-09
> Positioning (agreed): **AI-for-Science — human review scheduling on research evidence chains.**
> First real instance: sleep EMA (Maia ten Brink, Stanford Psychophysiology Lab, 1 year).
> Second instance: SciForge evidence DAG (Zhangyang Gao, AI4Science, Shanghai AI Lab).
> The proposal is **for SciForge**. The course deliverable is a **standalone paper / talk**.

---

## 0. Two tracks, one method

| | Track P — Paper | Track C — SciForge chain |
|---|---|---|
| What | Standalone RL paper / talk for STA3145 | Embed the suggester as a read-only review layer in SciForge |
| Deadline | Course final (~12/05) | After the paper, or in parallel if the chain owner agrees |
| Audience | Professor + classmates | 郑心 (chain owner) + Zhangyang Gao + lab users |
| Data | Synthetic DAGs + sleep 75/13,990 + real pipeline N=21 | Same, plus a de-identified SciForge DAG export |
| Risk | GNN variance; RL may not beat greedy at N=500 | Integration cost; SciForge may not have a confidence field |

**Recommended sequence:** Track P first (it is already running). Track C starts after W2, in parallel, using the same numbers. Do not integrate into SciForge code before the paper figures are frozen.

---

## 1. Five claims (each person picks one row)

### Person 1 — 组长 / 叙事
**Track P (claim):** narrative, proposal, HealthBench/BioBasics section, figures into slides.
**Track C (claim):** none. 동채하 (Person 5) owns the 郑心 / DAG-export ask.
**Do not:** train models. **Do not:** become the SciForge integrator.

**Done when:**
- Paper: 12-page-equivalent narrative with figures, three-language sync.
- Chain: a de-identified DAG export (nodes, edges, types) or a written mock if none exists; one meeting note from 郑心.

---

### Person 2 — Policy gradient / confidence signal
**Track P (claim):** a learned policy that beats deployable belief greedy (currently GNN − belief greedy = +0.42 ± 0.15 on held-out graphs; try a deeper GNN, per-step credit, or a misspecified belief model where belief greedy should degrade); PPO-Lagrangian / dual-critic CMDP (naive 2.15 is the thing to fix); confidence-signal upgrade (Gap D — the ablation said this is the lever).
**Track C (claim):** none before W3. After the paper, port the scorer as a read-only endpoint.
**Do not:** touch SciForge integration; do not tune DQN into a win.

**Done when:**
- Paper: a learned policy whose paired held-out gap to belief greedy is below zero, or a written reason it is not; either dual-critic beats naive 2.15, or a written reason it still fails.
- Signal: a better conf (calibration / small predictor) that closes part of the oracle−normal gap (0.72 vs 1.38).

---

### Person 3 — Environment + GNN + scale
**Track P (claim):** freeze `spike_active_selection.py` + `graph_scale.py` + `real_pipeline_graph.py`; N=500 three-family table (already run); GNN on a 200-node subsample if Person 2 has time.
**Track C (claim):** the same environment code, wrapped so SciForge DAG export can be dropped in (Gap A consumer).
**Do not:** invent a new graph family during the paper weeks.

**Done when:**
- Paper: N=500 table reproduced; N=21 real pipeline table reproduced.
- Chain: `load_sciforge_dag(path)` works on Person 5's export.

---

### Person 4 — Baselines, controls, optional third data
**Track P (claim):** threshold / greedy / hub / no-review / random on every family; shuffle + flatten controls; consensus/hard split **only if** Person 5 hands over the 27/48 labels.
**Track C (claim):** none, unless Gap A fails — then Gap C (third real dataset).
**Do not:** download CIFAR-10H or BurstGPT.

**Done when:**
- Paper: shuffle/flatten controls reproduced; a one-row "consensus vs agree" table if Gap B is done.
- Optional: a third real set only if Person 5's SciForge export fails.

---

### Person 5 — 동채하 — narrative, 郑心 liaison, GO search, literature, writing, presenting (English)
**Track P (claim):** HealthBench + BioBasicsBench sections (already drafted); sleep 75 / 13,990 motivation; Korean outline `presentation_outline_ko.md`; presenting (English OK).
**Track C (claim):** SciForge liaison — ask 郑心 for the DAG export and receipt fields; write the SciForge-side one-pager from `EVIDENCE_CHAIN_DESIGN_CN.md`.
**Do not:** become the RL theory person. The method is Persons 2–3.

**Done when:**
- Paper: related-work section, motivation slide, Korean outline rehearsed once.
- Chain: a one-page SciForge ask (what the suggester needs from the DAG).

---

## 2. Section 8 verification, split to owners

| Item | Owner |
|---|---|
| All simulation numbers, curves, shuffle/flatten | Person 3 (env) + Person 4 (controls) |
| Real-data 76% / 13,990 / 237 (already recomputed 11-09) | Person 5 |
| Simulator design / why no-review 5.62 vs 5.90 | Person 3 |
| "No direct precedent" — search again | Person 5 |
| Full texts of cited papers | Person 5 |
| GNN vs belief greedy; belief greedy under misspecification | Person 2 |
| GNN+PPO convergence | Person 2 |
| Dual-critic CMDP | Person 2 |
| SciForge confidence field / graph size | Person 5 |
| Consensus/hard split (27/48) | Person 5 + Person 4 |
| BestReject = our threshold (claim dropped) | Person 5, if they read the full paper |
| Stale numbers in slides / PDFs (old 1.54, "95%") | Person 1 (PM) |

---

## 3. Dependency graph (who waits for whom)

```
Person 3 (env + graphs)  ──►  Person 2 (RL)  ──►  Person 4 (controls)
        │                                              │
        ▼                                              ▼
Person 5 (SciForge ask + write)  ──►  郑心 / Zhangyang Gao
        │                                              │
        └─────────────► Person 1 (PM + timeline) ◄────┘
```

Critical path: **Person 3's frozen environment** → everyone else. If the environment moves, all numbers move.

---

## 4. What "part of the evidence chain" vs "standalone paper" actually means

### Standalone paper (Track P) — the course deliverable
Title shape: *Learning When a Human Should Review AI Output on a Research Evidence Chain.*

Sections: problem (two facts) → bandit negative → graph MDP reframe → GNN + REINFORCE → ablation (conf is the bottleneck) → scale (greedy nearly clears) → real pipeline (threshold 0.50) → controls → related (L2D, HealthBench, BioBasics) → limits.

This is a complete, honest RL-course paper. It does not need SciForge code. It uses sleep data as the first real instance.

### Part of the evidence chain (Track C) — the AI4Science landing
After (or beside) the paper, the same suggester becomes a **read-only node-ranking service** in SciForge:

```
POST /suggest/review-order
  in:  evidence DAG slice, budget, conf field name
  out: ranked node ids + reasons (downstream, likelihood, type)
  never: a receipt, a stamp, a write
```

This is a feature of SciForge, not a separate product. Zhangyang Gao decides if it enters the client. 郑心 decides if "followed-suggestion" is a receipt field.

### Our recommendation
**Do both, in this order.**
1. Freeze Track P by ~12/03 as the course paper/talk.
2. Track C starts W3 in parallel as a design + mock export, not as a production integration.
3. After the course, Track C can become a SciForge PR (read-only suggester) if Maia and Gao want it.

Trying to land in SciForge *before* the paper is how this becomes an unfinished engineering project. Trying to stay "just a paper" forever is how it never becomes AI4Science. Sequence, do not merge.

---

## 5. Data division (final)

| Data | Already have? | Who touches it |
|---|---|---|
| Sleep EMA 13,990 / 237 | yes (Maia, 1 year) | Person 5 (counts), Person 3 (N=21 DAG) |
| 75 corrections (76% order_error; 27/48 consensus) | yes | Person 5 (motivation + Gap B), Person 4 (split eval) |
| Synthetic 80 / 500 / modular / BA / ER | yes (code) | Person 3 |
| Real pipeline N=21 | yes (hand-encoded) | Person 3 |
| SciForge DAG export | **no — Gap A** | Person 5 asks; Person 3 consumes |
| Conf-signal upgrade | **no — Gap D** | Person 2 (not a dataset) |
| CIFAR-10H / BurstGPT / wet-lab images | **do not search** | — |

---

## 6. Claim protocol (this week)

Each person sends a one-line message in the group chat:

> I claim **[row]** on **[Track P / Track C / both]**. My first deliverable is **[thing]** by **[date]**.

If a row is unwanted, swap with another member. Do not leave two people on the same row. Do not leave a row empty.

Default (if nobody swaps): the table in §1.

---

## 7. The one thing each person should be able to say at the meeting

| Person | The sentence |
|---|---|
| 1 | "I keep the timeline and the proposal. 동채하 owns the evidence-chain design and the 郑心 ask." |
| 2 | "Policy gradient with a GNN scorer is the main method. The ablation says the confidence signal, not the scheduler, is the remaining error. I will either fix the signal or report that we did not." |
| 3 | "I own the environment. If the graph moves, every number moves. I will freeze it and reproduce the tables." |
| 4 | "I own the baselines and the controls. If shuffle and flatten kill the advantage, the advantage is real. If they do not, we say so." |
| 5 동채하 | "I own the narrative, the 郑心 ask, the GO search, the real-data motivation, and I present in English. HealthBench and BioBasicsBench sit next to our results." |
