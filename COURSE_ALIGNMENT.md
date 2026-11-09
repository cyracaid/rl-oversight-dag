---
title: "Course Alignment & Data Division"
layout: default
---

# Course Alignment & Data Division

<p><b>Language:</b> <b>English</b> · <a href="https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT_CN.html">中文</a></p>

> STA3145 · how this project maps to the Korean classroom · how data search is split across 5 people · 2026-11-09

---

## 1. Does this match the course? Yes.

Desktop `강화학습/` is classic Sutton & Barto. Our project uses those tools on a real problem. Side by side:

| Course week | What the class teaches | What we do with it |
|---|---|---|
| W1–2 Bandit, explore–exploit, regret | Multi-armed / contextual bandit, no state, immediate feedback | **V1 bandit** — honest negative result: threshold 2.81 beats Q-learning 3.38. The bandit *flattens the graph*. This is why we need an MDP. |
| W2 Finite MDP $(S,A,R,p,\gamma)$ | Five-tuple, Bellman, delayed return | **The reframe.** State = graph knowledge + budget. Action = next node. Reward delayed to the conclusion. Sparse, delayed — the thing bandit cannot do. |
| W3 DP (policy eval, value iteration) | Bellman as a linear system; sweep | We can add policy-evaluation / value-iteration as a *small-graph* baseline (N=21 real pipeline is tabular-sized). Not yet run. |
| W4 Monte Carlo | First-visit MC, episode returns | **GNN + REINFORCE uses MC returns** $G_t$. Already the main method. |
| W5 TD, Q-learning | Bootstrap, off-policy | **V1 Q-learning** (negative) and **DQN** (degenerate control). Both are teaching points, not the main method. |
| W6 n-step / bootstrap | n-step MC/TD, eligibility | Optional: n-step REINFORCE if terminal-only credit is too sparse. Not required. |
| W7 VAE / DDPM | Generative models | **Not used.** Different module. Do not force it in. |
| W8 Function approximation, control | Linear / neural value & policy, DQN | **MLP scorer** (preliminary) and **DQN control**. GNN is the upgrade. |
| W9 Policy gradient I | REINFORCE, $\nabla J = E[\nabla \log \pi \cdot A]$ | **Main learned method.** Runs. Held-out 1.56; loses to deployable belief greedy (1.14), paired gap +0.42 ± 0.15. |

**Course-project sentence for the professor:**

> This project is the course syllabus applied to one problem. Week 1–2 is our negative result. Week 2 is our reframe. Week 4 + 9 is our main method. Week 5 + 8 is the control that shows why policy gradient is the right tool. Week 3 is a baseline we can still add on the N=21 real pipeline.

It is **not** a survey of RL. It is **not** a new algorithm. It is the syllabus, used honestly, on a problem where the naive version fails.

---

## 2. AI-for-science: general method, specific first instance

**Do not brand this as "AI for sleep."**
**Do not brand this as a generic AI4Sci survey either.**

Brand it as:

> **AI-for-Science: human review scheduling on research evidence chains.**
> The method is general (any DAG of dependent AI outputs + a review budget).
> The first real instantiation is our sleep-EMA pipeline (Maia ten Brink, Stanford Psychophysiology Lab, one year of data).
> The second instantiation is SciForge's evidence DAG (Zhangyang Gao, AI4Science, Shanghai AI Lab).

| Layer | General (AI4Sci) | First instance (sleep) | Second instance (SciForge) |
|---|---|---|---|
| DAG | any dependent AI outputs | splsleep SCHEMA pipeline (N=21) | SciForge evidence DAG (claims, datasets, runs) |
| Error types | type-clustered mistakes | order_error 76% | TBD — ask 郑心 / export |
| Budget | finite human review | 8–16 reviews | whatever a cycle allows |
| Delayed harm | errors reach a conclusion | sleep metrics / record quality | claims / deliverables |
| Who reviews | a human | lab annotators | SciForge users |

This is how you answer "is it sleep-specific or general AI4Sci":

> **The method is general. The first real data is sleep. The second target is SciForge. We do not claim it works on every science domain — we claim the formulation transfers, and we test it on two instantiations.**

That is more honest and more impressive than "AI for sleep" or "AI for everything."

---

## 3. Data search: how to divide it across 5 people

We already have more data than we need for the course. The remaining work is **not** "go find more datasets." It is **organize what we have, and fill two gaps.**

### What we already have (do not re-search)

| Data | Status | Owner |
|---|---|---|
| Sleep EMA 13,990 rows / 237 people | on Maia's side; we have the RDS + 75 corrections | Maia / 동채하 |
| 75 human corrections (27 consensus / 48 agree) | in `manual_error_correction_updated.csv` | 동채하 |
| Synthetic DAGs (80 / 500, modular / BA / ER) | generated in code | Person 3 |
| Real pipeline DAG (N=21) | hand-encoded from SCHEMA | Person 3 |

### What is missing (search / build only these)

| Gap | Who | How | Effort |
|---|---|---|---|
| **A. SciForge evidence DAG export** (de-identified) | Person 5 + 郑心 + Zhangyang Gao | ask for a small export of a real project's DAG (nodes, edges, types). If none exists, build a mock from SciForge docs. | 2–3 days |
| **B. Consensus / Hard split of the 75** | Person 5 (동채하) | already have labels (27 / 48); evaluate the policy on each split. Do not collect new annotations. | 1 day |
| **C. Optional third real set** | Person 4 — **only if** A fails | literature-labeling errors, another EMA set, or OpenNeuro / OpenML human-annotation data. **Do not download CIFAR-10H** unless the professor asks for an image proxy. | skip unless needed |
| **D. Confidence signal improvement** (the ablation said this is the lever) | Person 2 | better conf: calibration, ensemble, or a small predictor on diary features. This is the X-factor, not a new dataset. | 2–3 days |

### What we do NOT search for

- CIFAR-10H (v1 leftover — dropped)
- BurstGPT (teammate's LLM-scheduling topic, not ours)
- ImageNet / gels / wet-lab images (BioBasicsBench is philosophy, not our data)
- A new sleep cohort
- "General AI4Sci benchmark" (there isn't one for this task)

---

## 4. Five-person division (work + data)

| Person | Primary work | Data they own |
|---|---|---|
| **1** | PM + timeline + L2D classics | proposal + timeline |
| **2** | Policy gradient / GNN / confidence-signal upgrade | confidence ablation (Gap D); no new dataset |
| **3** | Environment + GNN + DQN + scale (N=500) | synthetic generators (already done) |
| **4** | Baselines + controls + optional third dataset | Gap C only if A fails; else controls |
| **5 동채하** | Narrative + 郑心 liaison + literature synthesis + writing + presenting (English) | sleep 75 / 13,990; Gap B; Gap A ask |

**Maia ten Brink** = data source + domain sanity-check on the sleep DAG. Not an RL method advisor.
**Zhangyang Gao** = SciForge landing + whether the formulation fits the platform. The AI method is the course project.

---

## 5. Course-coverage checklist (put this on a slide)

| Course item | Where it appears in our talk |
|---|---|
| Bandit, explore–exploit, regret | Slide 4: V1 negative result |
| MDP five-tuple, Bellman, delayed reward | Slide 6: reframe |
| Policy evaluation / DP | Optional N=21 baseline (if time) |
| Monte Carlo returns | Slide 7: GNN + REINFORCE |
| TD / Q-learning | Slide 4 (Q-learning loses) + Slide 8 (DQN degenerates) |
| Function approximation | Slide 7: MLP → GNN |
| Policy gradient theorem, REINFORCE, baseline | Slide 7 |
| PPO clip + importance sampling | Slide 7 / 8 |
| CMDP + Lagrangian | Slide 7 (in progress) |
| Exploration annealing, multi-seed, paired held-out CI | Slide 8: GNN − belief greedy = +0.42 ± 0.15 |
| Worst-of-n reliability | Slide 8b |
| Adaptive greedy / influence maximization; belief (particle filter) | Slide 8c |
| Information gain | Slide 7 math |

**Do not put VAE / DDPM on a slide.** That week is a different module.

---

## 6. Answer to "sleep-specific or general AI4Sci"

Say this:

> We study **when a human should review AI output on a research evidence chain.** The formulation is general. We instantiate it first on a real sleep-EMA pipeline (one year of data from Maia ten Brink's lab at Stanford), then on SciForge's evidence DAG. We do not claim it works on every science domain. We claim the formulation transfers, and we test it on two instantiations. The course tools — bandit, MDP, Monte Carlo policy gradient, function approximation, DQN as a control — are the same tools this class taught. The negative result (bandit loses) is part of the contribution.

That is the positioning. It is RL-course-true and AI4Sci-true. It is not "sleep project" and it is not "we solve all of science."
