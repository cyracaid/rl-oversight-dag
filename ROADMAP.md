---
title: "Roadmap: What Would Make This Publishable, and What We Do Next"
layout: default
---

# Roadmap — what would make this publishable, and what we do next

<p><b>Language:</b> <b>English</b> · <a href="https://cyracaid.github.io/rl-oversight-dag/ROADMAP_KO.html">한국어</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/ROADMAP_CN.html">中文</a></p>

> Status note, 2026-11-24. Updated after the trust chain (gate → node → graph → boundary) and the
> `p_catch` sweep. This is **not** the next-week plan (that is
> [`PROPOSAL_COURSE.md`](PROPOSAL_COURSE.html) §8). It exists so we stop implying that a
> course project is a Nature Communications submission.

---

## 0. Where we actually are

| | today |
|---|---|
| scope | course project; talk given 11/23 |
| main evidence | the trust chain, on **synthetic** graphs, every step frozen before its run: a global gate that fails both ways (fires 195/200 on a harmless −1 shift, 0/200 on errors masked at +3); a per-node repair (+0.105 on −1, −0.370 where errors are masked); a per-graph repair (+0.005 at +3 where the node repair loses +0.81; 112-cell mean 1.303 → 1.203); a measured boundary (off-grid δ holds, two simultaneous δ collapse to plain trust). Underneath it, the original negative: learned 1.56 vs belief greedy 1.14, paired +0.42 ± 0.15 |
| real data | 75 corrections = 0.54% of 13,990 rows — motivation, one N=21 application, one 1,048-flag queue analysis. **Not a training set.** |
| reproduction | every number produced by an AI agent; no teammate has rerun it. Reruns are byte-identical and every report is regenerated from `episodes.csv` |
| claim status | "with 16 reviews a policy can estimate whether its confidence scores are usable, and stay safe when they are not" — supported inside this benchmark. The learned *scheduler* still loses to the rule |

That is a complete, honest course deliverable. It is **not** a paper.

---

## 1. What "publishable" would require

| # | gate | why it is required | now |
|---|---|---|---|
| **R1** | a decisive result — positive under misspecification, or a mechanism with a passing falsification test — replicated across 5 seeds **and** by a second person | one negative run is a course result, not evidence | ◐ mechanism half done: five pre-registered steps, 200+100 fresh graphs, a second codebase agreeing; no second person has rerun it |
| **R2** | a real queue with enough positives to train on (hundreds, not 68) | 6.5% precision cannot support a general claim | ✗ |
| **R3** | a second domain or chain (SciForge receipts, GO, SYNERGY) | one synthetic family + one lab pipeline is not generalization | partial |
| **R4** | a sharp boundary: when does a one-step posterior greedy dominate, and when must learning win | the boundary is the contribution; the benchmark is not | ◐ one boundary measured (δ grid, single δ, hit rate); two mechanical explanations for the oracle gap are ruled out (sampled value `worse`, belief rescaling `policy-bound`); the greedy-vs-learning boundary is still C1–C4 |
| **R5** | clean artifact: one command, fixed seeds, data cards, no hand-edited tables | reviewers check this before they read the result | ◐ manifest + per-graph CSV + byte-identical reruns + seeded verdict code; not one command, no data card |

Pre-registration is a strength for grading, but it does not move R1–R5 on its own.

---

## 2. What to do after 11/23, in order

1. **Reproduce, then freeze.** Person 2 and Person 4 rerun the gate matrix from a clean
   clone; tag the commit. Nothing gets cited before this (R1, R5).
2. **Turn the branch into a claim.** If Option B: promote C1–C4 from "claims" to "tested
   statements", with the 2-step greedy control deciding whether the story is *learning* or
   *planning depth*.
3. **Get a trainable real queue.** SciForge receipts if they arrive; otherwise a public
   labelled queue (SYNERGY for screening, GO for the DAG). R2/R3 is where the paper lives or dies.
4. **Write the boundary, not the benchmark.** The interesting sentence is "a one-step
   posterior greedy is near-optimal when the model is correct, and learning wins when it is
   not" — with the misspecification curves to back it.
5. **Venue ladder.** Workshop (NeurIPS D&B / RL4RealLife) → full paper only after R1–R5.
   Nature Communications is a later, different project — not this one.

---

## 3. What we say now, and what we do not

- Say: *"course project; a pre-registered test of whether the learned policy can catch a
  model-based baseline, with both branches specified in advance."*
- Do not say: *"Nature Communications submission"*, *"we show RL fails at review scheduling"*,
  *"our scheduler improves review"*. None of those are supported yet.
