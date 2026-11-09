# Comparison Report: HealthBench vs Our Review-Scheduling Project

> Purpose: a side-by-side comparison for the talk and the proposal. What they did, what we do, what we adopt, what we do not.
> Date: 2026-11-09

---

## 1. One-line each

| | HealthBench (OpenAI, 2025-05) | Ours (STA3145 RL course) |
|---|---|---|
| One-liner | A benchmark for whether LLMs handle real health conversations, scored on 48k physician-written rubric criteria | An RL policy for *which item in a research evidence chain a human should review first*, under a budget, so fewer errors reach the conclusion |

---

## 2. Dimension-by-dimension

| Dimension | HealthBench | Ours | Who is ahead |
|---|---|---|---|
| **Task** | Score LLM replies to health conversations | Schedule human review of dependent AI outputs on a DAG | Different problems; both are "AI + finite human judgment" |
| **Domain** | Clinical medicine (26 specialties, 60 countries) | Sleep-research data pipeline + SciForge evidence chain (health-adjacent) | They are broader; we are deeper in one lab's real data |
| **What is judged** | A model reply, against a weighted rubric | Whether to review a node, judged by whether errors reach sinks | They judge *quality of text*; we judge *allocation of attention* |
| **Who writes the standard** | 262 physicians, 49 languages | Our own annotators; 27 consensus / 48 single-annotator "Agree" | They have a community; we have a lab |
| **Scale** | 5,000 conversations, 48,562 criteria | 13,990 sleep-log rows, 75 corrections; synthetic graph ≈80 nodes | They win on scale of human judgment; we win on a sequential RL problem they do not have |
| **Grader** | GPT-4.1 scores each criterion | Simulator: a review *fixes* the node with p_catch = 0.9 | They grade open-ended text; we grade a discrete scheduling action |
| **Error structure** | Weighted rubric criteria (include/avoid) | Binary node error + DAG propagation + delayed sink penalty | They have richer per-reply rubrics; we have richer *error dynamics* |
| **Reliability** | worst-of-n (one unsafe reply cancels many good ones) | worst-of-5 seeds: GNN 1.90, noise 5.20, oracle 0.80 | We adopted their lens; a noisy signal hurts our tail more than our mean |
| **Consensus** | Consensus split: 3,671 cases, multi-physician, near-zero grader error | 27 Consensus Reached / 48 Agree; not yet split in evaluation | They did the split; we have the labels and have not used them yet |
| **Non-saturation** | HealthBench Hard (1,000 cases frontier models fail) | Even oracle conf leaves 0.72 (p_catch = 0.9); best seed 1.00, worst 1.90 | Both have headroom; ours is also *unstable across seeds* |
| **Human vs AI comparison** | Physicians could not beat o3 / GPT-4.1 on 2025-04 models | Our oracle (perfect conf) reaches 0.72 — the remaining gap is reviewer miss rate, not the policy | Different questions; both locate where the human still adds value |
| **Meta-evaluation** | Model grader agrees with physicians at the rate physicians agree with each other | Ablation: destroying conf (3.78) vs oracle (0.72) — the signal, not the policy, is the bottleneck | Same move, different object |
| **Open release** | Code + data on GitHub (simple-evals) | Code + synthetic experiments on GitHub; real data never committed | Same move, smaller scale |
| **RL / sequential decision** | None (static benchmark) | Bandit → MDP reframe; policy gradient; GNN scorer; CMDP in progress | **This is our unique contribution** |
| **Dependency graph / delayed error** | Not modelled (conversations are one-shot scoring) | Core of our problem: errors propagate, penalty is delayed to the conclusion | **This is our unique contribution** |
| **Budget / fatigue** | Not in the benchmark (they cite FALCON as prior art) | Core of our problem (fixed or soft review budget) | **Ours** |

---

## 3. What we adopt (already in the repo)

1. **Three principles** — meaningful / trustworthy / non-saturated — as the design principles of our SciForge review benchmark.
2. **Worst-of-n** reported next to the mean, because one unreviewed error can invalidate a conclusion.
3. **Consensus / Hard as a planned split** — 27 consensus vs 48 agree, not yet evaluated separately.
4. **Meta-evaluation framing** — our ablation *is* a meta-evaluation of the confidence signal.

## 4. What we do not copy

1. Community-scale physician crowdsourcing (we have 75 rows, not 5,000 conversations).
2. LLM-as-grader for open-ended text (our review is a discrete fix in a simulator).
3. The medical-dialogue task itself (our task is review *scheduling*, not medical QA).

## 5. The comparison in one paragraph (for the talk)

HealthBench asked: *is this LLM reply good enough, by physician standards, on a real health conversation?* We ask: *given a chain of dependent AI outputs and a human who can check only a few, which check should happen first so that the final conclusion is least contaminated?* HealthBench taught us to evaluate with meaningful, trustworthy, non-saturated rubrics and to report worst-of-n reliability. We apply those lessons to a problem they do not solve: the **scheduling** of finite human attention over a **dependency graph**, where errors propagate and the penalty arrives only at the conclusion. Their grading signal (rubrics + a model grader) is exactly the kind of confidence signal our ablation says is the bottleneck — **improving the signal buys more than improving the policy**.

---

## 6. Side-by-side numbers (what we can say today)

| Metric | HealthBench | Ours |
|---|---|---|
| Human experts | 262 physicians | our lab annotators (27 consensus + 48 agree) |
| Items | 5,000 conversations | 75 corrections on 13,990 rows |
| Criteria / labels | 48,562 weighted criteria | binary node error + type (76% order_error) |
| Best system | o3, +28% over prior OpenAI models | GNN+REINFORCE mean 1.54 ± 0.46 (best seed 1.00) |
| Worst-of-n | reported as a curve | GNN 1.90 / noise 5.20 / oracle 0.80 |
| Ceiling | HealthBench Hard still unsolved | oracle conf 0.72 (p_catch = 0.9) |
| RL scheduling | not part of the benchmark | the entire project |

---

## 7. What "better than HealthBench" would even mean

It would not mean beating o3 on medical QA. It would mean:

- Showing a **sequential, budgeted, graph-structured** review problem they left open;
- Applying their **evaluation philosophy** (meaningful, trustworthy, non-saturated, worst-of-n) to that problem;
- Delivering an **honest negative-and-positive package**: bandit fails, MDP reframe helps, the confidence signal is the ceiling, and here is a decision guide for when to use which rule.

That is the A+ version of this assignment. It is not "we beat HealthBench." It is "we used HealthBench's evaluation philosophy on a problem HealthBench does not touch."
