# HealthBench → our review-scheduling project

> Source: OpenAI HealthBench (2025-05), 262 physicians, 60 countries, 5,000 conversations, 48,562 weighted rubric criteria.
> What we take, what we already have, what we add.

---

## HealthBench's three design principles → our benchmark principles

| HealthBench | Ours |
|---|---|
| **Meaningful** — scores reflect real impact, not exam questions | Errors that actually propagate to a conclusion (sink errors), on a real sleep-research pipeline, not a toy classifier |
| **Trustworthy** — scores faithful to expert judgment | 75 human corrections from our own lab; 27 reached consensus, 48 are single-annotator "Agree" |
| **Non-saturated** — room for progress | Even oracle confidence leaves 0.72 sink errors (p_catch = 0.9); HealthBench Hard ≈ our hardest nodes |

---

## Five concrete takeaways

### 1. Worst-of-n reliability (health: one unsafe answer cancels many good ones)
HealthBench reports *worst-of-n*: for n replies to the same case, the lowest score. Reason: a single unsafe answer can cancel many correct ones.

**Ours:** one unreviewed error reaching a conclusion can invalidate it. So report worst-of-n, not just mean.

| | mean | worst-of-5 |
|---|---|---|
| GNN + REINFORCE | 1.54 | **1.90** |
| noise conf (ablation) | 3.78 | **5.20** |
| oracle conf | 0.72 | **0.80** |

The reliability gap (worst − mean) is largest for noisy conf (5.20 − 3.78 = 1.42) and smallest for oracle (0.80 − 0.72 = 0.08). **A noisy signal hurts the tail more than the mean** — same reason HealthBench cares about worst-of-n in medicine.

### 2. Consensus / Hard split
HealthBench Consensus = 3,671 cases with multi-physician consensus (near-zero grader error). HealthBench Hard = 1,000 examples frontier models still fail.

**Ours:** 27/75 corrections are "Consensus Reached"; 48 are "Agree" (single-annotator). order_error: 19 consensus / 38 agree.

Next step (not done): train/evaluate the policy separately on consensus-verified errors vs single-annotator errors. Consensus-verified = our HealthBench Consensus; the residual the policy still misses = our HealthBench Hard.

### 3. Rubric, not binary
HealthBench scores each reply against weighted physician-written criteria (include this fact, avoid jargon), graded by a model.

**Ours:** review is currently binary (fix the error / not). SciForge upgrade: each review produces a **weighted receipt rubric** (which downstream metrics affected, severity, whether the fix is certain). The RL reward can later use the weighted sum, not the count. This is a SciForge receipt-design question for the evidence-chain owner, not something we pre-decide.

### 4. Meta-evaluation = our ablation
HealthBench checks: does the model grader agree with physicians at the rate physicians agree with each other?

**Ours:** the ablation is exactly a meta-evaluation of the confidence signal — how much does grader/signal quality limit the policy. Answer: it is the bottleneck (oracle 0.72 vs normal 1.38 vs noise 3.78).

### 5. Open eval suite
HealthBench released code + data (simple-evals) so the field can measure. Our repo is the same move, smaller scale: simulator + scripts + figures, synthetic-first, real data never committed.

---

## What we do NOT copy

- 5,000 physician-hours and 48k rubrics — we have 75 corrections, not a community benchmark. Do not overclaim.
- LLM-as-grader (GPT-4.1) — our "review" is a human fix in the simulator, not an LLM scoring a conversation. An LLM grader would be a SciForge front-end question (the highlight-and-ask tool), not this course project.
- The health-conversation task itself — our task is review scheduling, not medical dialogue.

---

## One-line for the talk

HealthBench taught the field to evaluate medical AI on *meaningful, trustworthy, non-saturated* rubrics with a worst-of-n reliability lens. We apply the same three principles to a smaller, RL-shaped problem: which item in a research evidence chain should finite human attention review first.
