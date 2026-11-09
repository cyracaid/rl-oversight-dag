# Review Scheduling on a Dependency Graph

> STA3145 Reinforcement Learning · Group project. Under a limited review budget, we use RL to learn which node of a dependency graph to review, so that fewer errors reach the final conclusion.
>
> Sleep data: one year of EMA collaboration with Maia ten Brink (Stanford Psychophysiology Lab).
> Application: SciForge, developed by Zhangyang Gao (AI4Science, Shanghai AI Lab).

**Start here — one synthesized design document:**
[Evidence-chain design (EN)](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.md) ·
[证据链设计 (中文)](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN_CN.md)

**Who claims what (5 people, two tracks):**
[Team claims HTML (中文/EN/한국어)](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.html)
(markdown source: [`TEAM_CLAIMS.md`](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.md) ·
[`TEAM_CLAIMS_CN.md`](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_CN.md))

**Meeting one-pager (humanized + math, 中文 / EN / 한국어, click to open):**
[中文 PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_zh.pdf) ·
[English PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_en.pdf) ·
[한국어 PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_ko.pdf) ·
[HTML 三语切换](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal.html) ·
[illustrated talk page](https://cyracaid.github.io/rl-oversight-dag/talk.html)

**Full narrative (pick your language):**
[English](https://cyracaid.github.io/rl-oversight-dag/en/index.html) ·
[한국어](https://cyracaid.github.io/rl-oversight-dag/ko/index.html) ·
[中文](https://cyracaid.github.io/rl-oversight-dag/zh/index.html)

**Implementation spec (build from this):**
[中文网页版 `IMPLEMENTATION_SPEC.html`](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.html) ·
[English `IMPLEMENTATION_SPEC.md`](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.md) ·
[한국어 `IMPLEMENTATION_SPEC_KO.md`](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.md) ·
[中文源码 `IMPLEMENTATION_SPEC_CN.md`](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_CN.md)
(the `.html` page and `IMPLEMENTATION_SPEC_CN.md` are both Chinese — the former is the styled web page, the latter is its plain-markdown source; its on-page language switcher links to the EN/KO spec siblings directly.)

Repo: https://github.com/cyracaid/rl-oversight-dag

---

## What this repo is for (two audiences)

**Yonsei RL course (STA3145)** — the assignment, the talk, the synthetic + 80-node RL experiments:

| File | Language | For |
|---|---|---|
| `PROJECT_EN.md` / `PROJECT_KO.md` / `PROJECT_CN.md` | EN / KO / CN | course narrative |
| `COURSE_ALIGNMENT.md` / `_CN.md` | EN / CN | how this maps to the STA3145 rubric; data-search split across the 5 people |
| `TEAM_CLAIMS.md` / `_CN.md` | EN / CN | markdown source behind `TEAM_CLAIMS.html` |
| `presentation_outline.md` / `presentation_outline_ko.md` | EN / KO | slides |
| `IMPLEMENTATION_SPEC.md` / `_KO.md` / `_CN.md` | EN / KO / CN | build constants |
| `index.html` | EN landing | language cards → EN / KO / CN docs |
| `talk.html` | ZH / EN / KO | humanized illustrated talk page |
| `meeting_proposal.html` | ZH / EN / KO tabs | humanized meeting handout |
| `meeting_proposal_zh.pdf` / `_en.pdf` / `_ko.pdf` | ZH / EN / KO | printable one-pagers |
| `experiments/` | code | every number |

**SciForge (AI4Science, Shanghai AI Lab, developed by Zhangyang Gao)** — the evidence-chain review layer, applied to sleep data from the one-year collaboration with Maia ten Brink (Stanford Psychophysiology Lab):

| File | Language | For |
|---|---|---|
| `proposal_sciforge_en.md` | EN | SciForge-shaped proposal |
| `EVIDENCE_CHAIN_DESIGN.md` / `_CN.md` | EN / CN | architecture, boundaries, landing plan |
| `experiments/real_pipeline_graph.py` | code | N=21 real SCHEMA DAG |
| `experiments/verify_clustering.py` | code | 75-correction clustering (skips if data missing) |

**Local only, never commit:** raw `*.rds` / `*.csv`; anyone else's proposal; long Chinese literature notes (`延迟惩罚审查调度_文献调研/`).

---

## Core Principles (non-negotiable)

1. **Data red line (highest priority).** Internal real data (13,990 sleep-log rows, 75 manual corrections) **never goes on this repo and never leaves a member's own machine**. Even when de-identified, it is IRB-restricted research data. Share it privately if needed; do not commit it.
2. **Honesty first.** Every AI-generated result (numbers, code, figures) is labelled "unverified" until a team member independently reproduces it. Section 8 of the proposal is this principle made concrete.
3. **Reproducible.** Any member, after cloning this repo, can run the synthetic experiments without your machine and without the real data. Hard-coded local paths are either configurable or auto-skipped when the file is missing.
4. **Synthetic first, real data second.** Core experiments use a synthetic dependency graph; the real data is only one motivation slide.
5. **Numbers are traceable.** Every number maps to one script and one seed. **Change a number by changing the script, never by hand-editing a table.** Tables are generated by scripts (`final_table.md` ← `rl_final.py`).

---

## Repository structure

```
PROJECT_EN.md                   Full project document (English)
PROJECT_KO.md                   Full project document (한국어)
PROJECT_CN.md                   Full project document (中文)
COURSE_ALIGNMENT.md / _CN.md    Course-rubric mapping + data-search split (EN / CN)
TEAM_CLAIMS.md / _CN.md         Markdown source for TEAM_CLAIMS.html (EN / CN)
proposal_sciforge_en.md         SciForge / AI4Science proposal (EN)
presentation_outline.md         Presentation outline (EN)

experiments/                    (simulation & experiments)
  belief.py                     Confidence model + particle-filter belief (what a deployable policy may know)
  spike_active_selection.py     Dependency-graph environment + baselines (incl. belief greedy)
  dependency_review_sim.py      First version: bandit (negative result)
  rl_methods_compare.py         REINFORCE / PPO / DQN with an MLP node scorer
  rl_cmdp_gnn.py                CMDP + PPO-Lagrangian + GNN
  rl_final.py                   Final table + figures (no training)
  rl_gnn_multiseed.py           GNN + REINFORCE, static vs observed state, held-out paired eval
  graph_scale.py                N=500 experiments: modular / BA / ER
  real_pipeline_graph.py        Real sleep-pipeline DAG (N=21, from SCHEMA)
  verify_clustering.py          Real-data clustering check (skips if data missing)
  final_table.md                Final table
  results_bar.png, learning_curves.png, ablation_conf.png, scale500.png
```

---

## How to reproduce

| Want | Run | Needs real data? |
|---|---|---|
| Structural value (threshold vs greedy) | `python3 spike_active_selection.py` | No |
| Three RL methods (MLP scorer) | `python3 rl_methods_compare.py` | No |
| GNN upgrade | `python3 rl_cmdp_gnn.py` | No |
| Final table + figures | `python3 rl_final.py` | No |
| GNN static vs observed state vs belief greedy (held-out, paired) | `python3 rl_gnn_multiseed.py` (~6 min, 8 cores) | No |
| N=500 heuristics incl. belief vs oracle greedy | `python3 graph_scale.py && python3 plot_scale.py` | No |
| Real-data clustering | `python3 verify_clustering.py` | **Yes (auto-skips if missing)** |

Dependencies: `python3`, `numpy`, `torch`, `matplotlib` (`pip install numpy torch matplotlib`).

---

## Data note

- **All core experiments are synthetic** — the dependency graph is generated in code, so anyone can clone and run.
- **Real data** (sleep logs) is read only by `verify_clustering.py`, which points to a local path (`~/Documents/splsleep`). If the file is absent it prints "file missing" and skips; this does not affect the synthetic experiments.
- **Never commit the real data** (see `.gitignore` and Core Principle 1).

---

## Honest caveats (please read)

- **Deployable belief greedy beats every learned policy.** On 200 held-out graphs (paired): belief greedy 1.14, GNN static state 1.56, GNN observed state 1.56; GNN − belief greedy = +0.42 ± 0.15. Giving the GNN its review outcomes did not help (−0.00 ± 0.08). See `experiments/gnn_vs_greedy_table.md` (`rl_gnn_multiseed.py`).
- **The old N=500 "greedy" read the true error state** — it was an oracle. It is now reported as "oracle greedy (reads truth)", next to the deployable belief greedy (`belief.py`).
- **CMDP soft-budget (PPO-Lagrangian + stop action), naive version, fails at 4.85** — its stop-action credit assignment is too coarse and needs a FALCON-style reward-critic + cost-critic. This is our open problem.
- **GNN + PPO has not converged (~5.60)** and is omitted from the main table.
- **N=500 results are heuristics, not RL.** Deployable belief greedy: BA 12.8 vs threshold 37.6; on modular/ER it is only slightly better than the threshold.
- **Real-pipeline DAG (N=21): threshold 0.50 vs no-review 2.12** — the application-value result on our actual lab pipeline.
- All numbers were produced by an AI agent and have not been independently verified; Section 12 of `PROJECT_EN.md` lists the full checklist.
