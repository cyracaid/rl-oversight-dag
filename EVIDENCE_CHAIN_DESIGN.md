# Designing the Review Layer of an Evidence Chain

> Single synthesized document · STA3145 RL group project · SciForge AI4Science · 2026-11-09
> Languages: this file (English) · `EVIDENCE_CHAIN_DESIGN_CN.md` (中文)
> Repo: https://github.com/cyracaid/rl-oversight-dag
>
> This is the one document. It replaces the scattered proposals as the design view of the evidence chain. Narrative details still live in `PROJECT_EN.md` / `PROJECT_KO.md` / `PROJECT_CN.md`. Build numbers live in `IMPLEMENTATION_SPEC.md`.

---

## 0. What we are designing, in one page

SciForge stores a research evidence chain: claims point to evidence, evidence points to dataset versions and analysis runs, conclusions sit at the top. Humans review some of it. Machines do the rest. Today that review is first-come, first-served, or "whoever shouts loudest." Two facts make that a bad policy:

1. **Errors cluster by type.** In our own sleep-research data (13,990 rows, 237 participants), 76% of human corrections are one type (`order_error`).
2. **Unreviewed errors travel.** A wrong timestamp becomes a wrong SOL, becomes a wrong sleep-efficiency, becomes a wrong conclusion. The harm appears at the top of the chain, not where the mistake was made.

So we design a **review layer** for the evidence chain: an RL suggester that, under a finite human budget, ranks *which node to inspect next* so that fewer errors reach a conclusion. The suggester never stamps anything. Humans do.

This document is the design of that layer — architecture, math, what we have already measured, what is still unverified, and how it lands in SciForge.

---

## 1. Architecture: three layers, one chain

```
┌──────────────────────────────────────────────────────────────┐
│  FRONT END  —  how a review actually happens                 │
│  highlight-and-ask on code / diary row / claim               │
│  produces: review traces, questions, comments (NOT receipts) │
└──────────────────────────┬───────────────────────────────────┘
                           │ traces (who looked at what)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  REVIEW LAYER  —  this project                               │
│  GNN / greedy / threshold suggester                          │
│  input: evidence DAG + confidence + remaining budget         │
│  output: ranked "review these nodes next" (read-only)        │
│  never stamps, never edits a node, never writes a receipt    │
└──────────────────────────┬───────────────────────────────────┘
                           │ human clicks "verdict"
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  BACK END  —  SciForge evidence chain (already designed)     │
│  Evidence DAG + human-review receipts + audit (append-only)  │
│  machine never stamps; comments ≠ receipts                   │
└──────────────────────────────────────────────────────────────┘
```

**Design rule inherited from SciForge, not invented by this project:** the machine does not stamp. The suggester is a **read-only advisor**. A review becomes a receipt only when a human records a verdict.

---

## 2. The evidence chain, formally

A finite DAG \(G = (V, E)\). Each node \(v\) has:

| Field | Type | Source |
|---|---|---|
| `type` | one of K error/skill types | SciForge node kind + our type taxonomy |
| `confidence` | [0,1] | node field if SciForge has one (**unconfirmed**); else a pipeline score |
| `downstream influence` | \|sinks reachable from v\| | computed on the DAG |
| `reviewed` | {0,1} | receipt exists or not |
| true state \(X_v \in \{0,1\}\) | 1 = correct | environment only; **never a policy feature** |

Sinks = conclusion nodes. A **sink error** is a conclusion node with \(X_v = 0\) at the end of an episode.

**Edges that propagate errors:** `derived_from`, `supports`.
**Edges that do not:** `contradicts` (a contradiction is a relation, not an infection).

**Causal propagation** along \((u,v)\), weight \(w_{uv} \sim U(0.5, 1.5)\):

\[
P(X_v = 0 \mid X_u = 0) = 1 - \exp(-\lambda\, w_{uv}), \qquad \lambda = 0.8 \text{ (synthetic)} \;\; 0.9 \text{ (real pipeline)}
\]

**A review is a causal intervention:** force \(X_v = 1\). If the reviewer catches the error (probability `P_catch = 0.9`), descendants are recomputed. Otherwise the error stays.

**Types are heavy-tailed.** Real 75-correction file: 76% `order_error`. Synthetic: Zipf \(p_t \propto t^{-1.2}\) mapped into \([0.02, 0.40]\). Real pipeline: `order_error` 0.35/node, then the other correction types.

---

## 3. The review layer as an MDP

Sparse, delayed reward. Not a bandit (v1 was; it lost).

| | Definition |
|---|---|
| State | graph knowledge: per node (type, confidence, downstream influence, reviewed?) + remaining budget |
| Action | choose the next node to review, or STOP |
| Transition | review = do\(X_v := 1\); recompute downstream |
| Reward | terminal \(r_T = -\#\{\text{sink errors}\}\) |
| γ | < 1 (early upstream review is worth more) |

**Budget as a CMDP** (formal; naive implementation failed — see §7):

\[
\max_\pi \min_{\lambda \ge 0} J(\pi) + \lambda\,(B - C(\pi))
\]

**Information-gain alternative** (not yet run): \(R = \alpha \Delta H_v - \beta\,\mathrm{Cost}(v)\).

**Greedy \((1-1/e)\) baseline:** each step pick the currently erroneous node that most reduces reachable sink errors. On influence-maximization-style submodular objectives this is the theoretical approximation; empirically it is the strongest heuristic we have at N=500.

---

## 4. What the layer must not do (boundaries)

1. No auto-verdict. A suggestion is a ranking.
2. Read-only on the DAG. Append-only on the audit log, and only of *that a suggestion was shown*, if the chain owner allows it.
3. No comment bodies in the feature vector. Receipts store references, not prose.
4. Real raw data (13,990-row RDS, 75-row CSV) never enters git and is never handed whole to an agent. Summary numbers only.

---

## 5. Evidence the layer works (already run; AI agent; unreproduced)

All numbers are sink errors, lower is better. Tables from different settings are **not comparable across the table border**.

### 5.1 Motivation: errors cluster (real 75 corrections)

`order_error` = 57/75 = **76%**, entropy 0.612, p < 0.0001. The old 85.1% was 57/67 (8 unlabeled rows) — fixed 2026-11-09.

### 5.2 V1 bandit: a reported negative result

Threshold 2.81 beats tabular Q-learning 3.38. Diagnosis: per-item review flattens the graph; 76% single type collapses the optimum into a static rule. **This is why the layer must be sequential and graph-aware.**

### 5.3 After the reframe: active node selection (N=80)

| Method | sink errors | Status |
|---|---|---|
| No review | 5.90 | floor |
| Confidence threshold | 2.30 | strong static |
| Structural greedy | 1.80 | strong heuristic |
| REINFORCE (MLP) | 1.40 | preliminary |
| PPO (MLP) | 1.60 | preliminary |
| **GNN + REINFORCE** | **1.54 ± 0.46** (best seed 1.00; single-run 1.20 was luck) | **main method** |
| DQN | 5.10 (degenerate) | control |
| CMDP soft budget (naive) | 4.85 | open problem |
| Oracle | 0.00 | ceiling |

GNN scorer: 1-layer message passing, child→parent aggregation, H=32, following Mattick et al. (arXiv:2310.00112).

### 5.4 Ablation: the confidence signal is the bottleneck

| Condition | mean | Meaning |
|---|---|---|
| noise | 3.78 | destroy the signal → RL worse than a static threshold |
| normal | 1.38 | matches multi-seed mean |
| oracle (true error revealed) | 0.72 | nearly the ceiling |

**Do not keep tuning the policy. Invest in the confidence signal.** The scheduler is already good enough; the predictor sets the ceiling. This is the X-factor of the talk.

Worst-of-5 (HealthBench): GNN 1.90 / noise 5.20 / oracle 0.80. A noisy signal hurts the tail more than the mean.

### 5.5 Scale: N = 500, three graph families

Greedy influence maximization (not RL):

| family | no review | threshold | greedy |
|---|---|---|---|
| modular | 24.0 | 8.6 | **2.0** |
| scale-free (BA) | 80.6 | 29.8 | **3.8** (95% down) |
| sparse (ER) | 42.6 | 16.4 | **8.2** |

Random ≈ no review. Threshold unstable on scale-free (6–76). **Honest scope: greedy, not RL.** Any learned policy must beat this. The 80-node GNN, even at best seed, does not yet.

### 5.6 Real sleep-pipeline DAG (N=21) — the application-value table

Encoded from splsleep SCHEMA: diary leaves → diffs → SOL/WASO/TST/TIB/SE → validity/conclusions.

| policy | sink errors |
|---|---|
| no review | 2.12 |
| **conf threshold** | **0.50** |

On *our actual lab pipeline today*, a calibrated threshold nearly clears conclusion errors. The 500-node result is for when the evidence graph is large. This 21-node result is for our data now.

### 5.7 Controls (advantage is not baked in)

Shuffle errors → advantage gone. Flatten graph → advantage gone. Noise conf → RL worse than a threshold. The advantage comes from clustering + propagation.

---

## 6. Evaluation philosophy (HealthBench + BioBasicsBench, applied to this chain)

Two OpenAI everyday-science benchmarks are the philosophy precedents, not scheduling precedents.

| | HealthBench (2025-05) | BioBasicsBench (2026-11-06) | Ours |
|---|---|---|---|
| Question | Is this health reply good enough by physician rubrics? | Can the agent read raw wet-lab evidence and know when it does not support a conclusion? | Where should finite attention go first on a dependent evidence chain? |
| Human standard | 262 physicians, 48k criteria | Ligo + external PhD, partial-credit rubrics | 75 corrections (27 consensus / 48 agree) |
| Failure mode they showed | — | assumption overrides a control; contradictory observations discounted; miscount | 76% `order_error`: a familiar time-order assumption overrides recorded timestamps |
| What we adopt | meaningful / trustworthy / non-saturated; worst-of-n | partial-credit receipts; error detection as a first-class skill; "evidence cannot support this conclusion" as an action; three-round review | — |
| What we add | — | — | budgeted sequential review over a DAG; delayed conclusion penalty |

**Talk line:** OpenAI's wet-lab agents fail by letting an assumption override a control. Our sleep-pipeline errors fail the same way. The review layer exists because that failure is systematic. Their grading signal is the bottleneck our ablation found — improve the signal, not the policy.

**Do not copy:** 262-physician crowdsourcing; wet-lab images; 18,500 frontier-model evaluations; LLM-as-grader of open-ended text.

---

## 7. Related work, compressed

Each ingredient exists. The combination does not (we did not find it).

| Ingredient | Precedent |
|---|---|
| Learning to defer | Mozannar & Sontag ICML 2020; FALCON arXiv:2604.00904 (closest: fatigue + budget + PPO-Lagrangian, no graph); SLTD arXiv:2109.06312; Reid et al. arXiv:2409.20489; KL-PBD arXiv:2610.15128; Oversight arXiv:2606.08919 (flat actions) |
| Budgeted / delayed bandits | Bandits with Knapsacks FOCS 2013; Delayed Feedback ICML 2013 |
| Error cascades | Data Cascades CHI 2021; Finkel EMNLP 2006; From Spark to Fire arXiv:2603.04474; DN-ILDL arXiv:2405.16474 |
| Budget + node selection | WS-option arXiv:2502.05537 |
| GNN + RL node selection | Mattick arXiv:2310.00112 |
| Everyday-science eval philosophy | HealthBench 2025-05; BioBasicsBench 2026-11-06 |
| Class bias in deferral | Too Much of the Same arXiv:2608.28050 ↔ our 76% single type |

**Closest scheduling precedents we differ from:** Oversight (flat action trajectories) and WS-option (budget + node selection in influence maximization). We differ by **dependency-graph error propagation + sparse delayed reward**.

---

## 8. Verification status (do not present as established)

**Checked:** citations against abstracts; Section 5 percentages against tables; real-data numbers recomputed 2026-11-09 (13,990 / 237 / 75 / 76%).

**Not checked — teammates own these:**

1. Every simulation number, learning curve, shuffle/flatten control.
2. Simulator design (graph build, clustering, greedy, hyperparameters); why no-review differs across tables (5.62 vs 5.90).
3. "No direct precedent" — search again; say "we did not find one."
4. Full texts of cited papers.
5. GNN multi-seed CI needs more seeds (mean 1.54 ± 0.46 already computed; 12k-episode run was 2.05 — training-sensitive).
6. GNN + PPO not converged (~5.60).
7. Dual-critic CMDP not built (naive 4.85).
8. Cross-file 19% vs 22% (1.80 → 1.40 is 22.2%).
9. SciForge: confidence field on nodes; real graph size / edge types.
10. Consensus / Hard split (27 / 48) — labels exist, evaluation not run.
11. BestReject (arXiv:2409.20489) = our calibrated threshold — claim dropped as unverified.

---

## 9. Landing in SciForge (phased; no dates yet)

1. **Offline.** Synthetic DAG + exported de-identified evidence DAG. Suggester vs sort-by-confidence. No app integration, no change to stamping.
2. **Read-only suggestion.** Next to the review interface: "inspect these nodes first" + reasons (downstream influence, error likelihood, type cluster). Human may ignore.
3. **Receipt handshake.** To log "was this review suggestion-followed," the evidence-chain owner (Zhenxing) decides the field. This design does not pre-decide.

**Front-end tool (separate workstream, same chain):** highlight-and-ask on code / diary rows / claims, with an inline branch that keeps context and leaves collaborator notes. That tool produces the *traces* this layer consumes. It is not this course's RL deliverable; it is the采集层 of the same chain.

---

## 10. What "done" looks like for this layer

A teammate can, from this repo, without the real RDS/CSV:

1. Reproduce the four figure families (`results_bar`, `ablation_conf`, `scale500`, `real_pipeline`).
2. Reproduce the bandit negative result (threshold beats Q-learning).
3. Reproduce GNN multi-seed mean 1.54 ± 0.46, or update every table if the CI moves.
4. Point at the three boundaries and say "the machine does not stamp."

A professor can ask "why not just the threshold" and get: the threshold cannot see the graph; greedy proves the graph has value (22% at N=80, 95% on BA at N=500); the GNN mean is comparable today, the ablation says invest in the signal.

A reviewer can ask "is this just FALCON on a graph" and get: FALCON has no error propagation, no delayed sink penalty, no dependency graph; our naive CMDP on this graph *fails*, which is why we did not claim FALCON's recipe as a win.

---

## 11. Decisions this design asks of others

| Who | Decision |
|---|---|
| Maia ten Brink, PhD | bandit → MDP reframe; synthetic main experiment; real data as motivation only; evidence-chain boundaries; sleep-pipeline DAG |
| Zhangyang Gao, PhD | RL method stack (GNN + REINFORCE/PPO; CMDP dual critic); whether a synthetic main experiment is acceptable for an RL course |
| Zhenxing (evidence-chain owner) | may suggester output enter the audit chain; receipt fields; does a node have confidence |
| Teammates | own the Section 8 checks; pick dual-critic CMDP **or** GNN-at-scale, not both badly |
| 동채하 | presenting language: English if allowed, else backend (literature / simulation / data) |

---

## 12. File map (what lives where)

| Path | Role |
|---|---|
| `PROJECT_EN.md` / `PROJECT_KO.md` / `PROJECT_CN.md` | full narrative, three languages |
| `IMPLEMENTATION_SPEC.md` / `IMPLEMENTATION_SPEC_CN.md` | build-level constants, leakage rules, hyperparameters |
| `proposal_sciforge_en.md` | SciForge-shaped proposal |
| `presentation_outline.md` | slide-by-slide |
| `experiments/*.py` | every number's script |
| `experiments/*.png` | figures to embed |
| `延迟惩罚审查调度_文献调研/` (local, not all on repo) | long-form literature notes, HealthBench / BioBasics comparisons |

**Do not commit:** `*.rds`, `*.csv`, the 75-row file, anyone else's proposal.
