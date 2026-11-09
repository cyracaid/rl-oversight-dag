---
title: "Reading Guide: Who Should Read What (and What to Skip)"
layout: default
---

# Reading guide — pick your row, read those, skip the rest

> The repo has ~20 documents and only four readers. This page says which is which, and every
> name below is a link to the rendered page. If you read nothing else, read section 0.

---

## 0. The whole project in five lines

1. A conclusion is built from items that depend on each other; one wrong item poisons the rest.
2. A human can only check a few items, so **which one first** matters.
3. A simple adaptive rule ("check what most reduces the expected number of wrong conclusions")
   scores **1.14** wrong conclusions. Our trained RL policy scores **1.56**. Lower is better —
   **the learned policy loses.**
4. We do not hide that. We wrote down, in advance, the test that decides whether the loss is
   fixable (Option A) or a real limit worth explaining (Option B).
5. Everything else in this repo supports those five lines.

---

## 1. Who are you?

| You are… | Read, in this order (all clickable) | Skip | Time |
|---|---|---|---|
| **RL course teammate** (running experiments, building slides) | [PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) → [RL_PLAN](https://cyracaid.github.io/rl-oversight-dag/RL_PLAN.html) → [IMPLEMENTATION_SPEC](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html) → [PROJECT_EN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_EN.html) §5 and §8 | SciForge ask, meeting PDFs, roadmap | ~60 min |
| **RL course professor / grader** | [PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) → [PROJECT_EN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_EN.html) → [COURSE_ALIGNMENT](https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT.html) → [presentation_outline](https://cyracaid.github.io/rl-oversight-dag/presentation_outline.html) | [RL_PLAN](https://cyracaid.github.io/rl-oversight-dag/RL_PLAN.html), [TRACKS](https://cyracaid.github.io/rl-oversight-dag/TRACKS.html), [GENERALIZATION_PLAN](https://cyracaid.github.io/rl-oversight-dag/GENERALIZATION_PLAN.html), [ROADMAP](https://cyracaid.github.io/rl-oversight-dag/ROADMAP.html) | ~30 min |
| **Not in the RL course** (SciForge partner, advisor, curious reader) | [EVIDENCE_CHAIN_DESIGN](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html) → [proposal_sciforge_en](https://cyracaid.github.io/rl-oversight-dag/proposal_sciforge_en.html) | anything with MDP / REINFORCE / policy gradient in the title | ~20 min |
| **Checking whether we over-claim** | [README](https://github.com/cyracaid/rl-oversight-dag#readme) "Honest caveats" → [PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) §12 → [ROADMAP](https://cyracaid.github.io/rl-oversight-dag/ROADMAP.html) §3 | the rest | ~10 min |

If you are the third or fourth row, you never need to open a plan document. They exist for the
people doing the work.

---

## 2. What each document is (one line each)

**Languages.** Every document now exists in English, 한국어 and 中文, and each page carries a
switcher at the top. The one exception is `PLAN.html`, the generated visual work plan
(English-only; it is rebuilt from `tools/build_plan.py`).

| Document | What it is | For |
|---|---|---|
| [PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) | the course proposal: question, MDP, methods, **the sleep-data tables we already ran (§7.2)**, the two gates | everyone |
| [PROJECT_EN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_EN.html) · [KO](https://cyracaid.github.io/rl-oversight-dag/PROJECT_KO.html) · [CN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_CN.html) | the full narrative, same content in three languages | professor, teammates |
| [EVIDENCE_CHAIN_DESIGN](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html) · [中文](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN_CN.html) | the design argument: why a chain, why review scheduling, what the layer looks like | non-RL readers |
| [IMPLEMENTATION_SPEC](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html) · [KO](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html) · [中文网页版](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.html) | the build manual: constants, state/action/reward, file layout | whoever writes code |
| [COURSE_ALIGNMENT](https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT.html) · [中文](https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT_CN.html) | how the project maps onto the syllabus week by week | professor, graders |
| [proposal_sciforge_en](https://cyracaid.github.io/rl-oversight-dag/proposal_sciforge_en.html) | the same idea pitched to SciForge | SciForge partners |
| [triage_bench/](https://github.com/cyracaid/rl-oversight-dag/tree/main/triage_bench) | the real-data analysis: 1,048 flags, 68 errors, the ceiling | anyone asking "does this work on real data" |
| [RL_PLAN](https://cyracaid.github.io/rl-oversight-dag/RL_PLAN.html) · [TRACKS](https://cyracaid.github.io/rl-oversight-dag/TRACKS.html) · [GENERALIZATION_PLAN](https://cyracaid.github.io/rl-oversight-dag/GENERALIZATION_PLAN.html) · [PLAN.html](https://cyracaid.github.io/rl-oversight-dag/PLAN.html) | internal plans, schedules, work packages | teammates only |
| [ROADMAP](https://cyracaid.github.io/rl-oversight-dag/ROADMAP.html) | what would make this publishable, and what we must not claim yet | advisors, future us |
| [TEAM_CLAIMS](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.html) · [presentation_outline](https://cyracaid.github.io/rl-oversight-dag/presentation_outline.html) · [talk.html](https://cyracaid.github.io/rl-oversight-dag/talk.html) · [meeting_proposal](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal.html) | who owns what, slides, illustrated talk, meeting handout | team + audience |

---

## 3. Five words you need (plain)

- **DAG / graph** — items where later items depend on earlier ones.
- **node** — one item: a diary row, a computed value, a claim.
- **budget** — how many items the human is allowed to check.
- **sink / sink errors** — the final conclusion(s); "sink errors" = how many of them end up wrong.
  Lower is better.
- **held-out** — graphs the policy never saw during training, used for the honest score.

Two more, only if you read the proposal: **belief greedy** is the simple adaptive rule (not
learning); **REINFORCE / GNN** is the trained model. The whole proposal is about the gap between
them.

---

## 4. 中文速览（五句）

1. 一串互相依赖的结果，错一个会污染下游，人只能抽查几个，所以"先查哪个"最值钱。
2. 一个简单自适应规则漏 **1.14** 个错；我们训练的模型漏 **1.56** 个——模型输了。
3. 我们不藏这一点，而是**事先写好**判定规则：输了到底是"没调好"（A 路线）还是"这类问题本来就这样"（B 路线）。
4. **不是 RL 课的人**：只看 [EVIDENCE_CHAIN_DESIGN](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html) 和 [proposal_sciforge_en](https://cyracaid.github.io/rl-oversight-dag/proposal_sciforge_en.html)，其余全部可以跳过。
5. **RL 课的同学**：[PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) → [RL_PLAN](https://cyracaid.github.io/rl-oversight-dag/RL_PLAN.html) → [IMPLEMENTATION_SPEC](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html)，其他计划文档是内部用的。
