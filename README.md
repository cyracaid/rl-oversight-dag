# Review Scheduling on a Dependency Graph

> STA3145 Reinforcement Learning · Group project. Under a limited review budget, we use RL to learn which node of a dependency graph to review, so that fewer errors reach the final conclusion.
>
> Sleep data: one year of EMA collaboration with Maia ten Brink (Stanford Psychophysiology Lab).
> Application: SciForge, developed by Zhangyang Gao (AI4Science, Shanghai AI Lab).

**Status, 2026-11-10 — settled.** The Yonsei course track (STA3145) is final: the classroom content
and the five-person division are decided, and those documents are frozen at tag
`course-freeze-2026-11-10`. **Active work is now building SciForge** — see
[`EVIDENCE_CHAIN_DESIGN.md` §10b](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html)
for the open items; the build brief lives in the team's Feishu wiki.

**New here?** [One-page reading guide](https://cyracaid.github.io/rl-oversight-dag/READING.html) — who should read which document, five plain words, and what to skip. (中文速览在文末。)

**Latest RL results · 2026-11-12:** [한국어 결과 요약](experiments/BOUNDARY_RESULTS_KO.md) · [中文详细解释](experiments/BOUNDARY_FULL_V1_INTERPRETATION.md) · [Preregistration](experiments/BOUNDARY_PREREG.md). Five training seeds, 200 development graphs: belief greedy 1.100, two-step greedy 1.020, BC 1.201, BC+FT 1.525 sink errors (lower is better). Current RL policies do not outperform belief greedy; this now replicates on the untouched confirmation set (seeds 2000–2199): GNN − marginal **+0.377 [+0.255, +0.510]**. [Saved synthetic results and checkpoints](runs/boundary-full-v1/).

**Who does what (visual, EN / 한국어 / 中文):** [PLAN.html](PLAN.html) — dependency graph, 8-day schedule, four interfaces, three gates. Built from one source: `python3 tools/build_plan.py`. Text version: [GENERALIZATION_PLAN.md](GENERALIZATION_PLAN.md).

**Two stages — Stage 1 we decide, Stage 2 is SciForge's system:** [TRACKS.md](TRACKS.md)

**Start here — one synthesized design document:**
[Evidence-chain design (EN)](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html) ·
[证据链设计 (中文)](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN_CN.html)

**Who claims what (5 people, two tracks):**
[Team claims — who owns what (summary + full EN/한국어/中文 pages)](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.html)
(markdown source: [EN](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_EN.html) ·
[中文](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_CN.html))

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

**Implementation spec (build from this) — the same document in three languages:**
[中文](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.html) ·
[English](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html) ·
[한국어](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html)
(each page carries a language bar at the top, so you can switch without coming back here. The Chinese page is the styled web version; its markdown twin `IMPLEMENTATION_SPEC_CN.md` renders at `IMPLEMENTATION_SPEC_CN.html` and is listed in the document index below.)

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
| `triage_bench/` | code | the **real** review queue: recall@k, no simulator |

**SciForge (AI4Science, Shanghai AI Lab, developed by Zhangyang Gao)** — the evidence-chain review layer, applied to sleep data from the one-year collaboration with Maia ten Brink (Stanford Psychophysiology Lab):

| File | Language | For |
|---|---|---|
| `proposal_sciforge_en.md` | EN | SciForge-shaped proposal |
| `EVIDENCE_CHAIN_DESIGN.md` / `_CN.md` | EN / CN | architecture, boundaries, landing plan |
| `experiments/real_pipeline_graph.py` | code | N=21 real SCHEMA DAG |
| `experiments/verify_clustering.py` | code | 75-correction clustering (skips if data missing) |

**Local only, never commit:** raw `*.rds` / `*.csv`; anyone else's proposal; long Chinese literature notes (`延迟惩罚审查调度_文献调研/`).

---

## Headline results (canonical, 2026-11-24)

Two lines supply these numbers and they are the ones to quote: `role3 improvement/` (environment, tag
`role3-env-v3`) and `role2_규리/` (measurements). Raw means are **not** interchangeable between the three
implementations — read `CROSS_IMPLEMENTATION_VALIDATION.md` before putting two of them in one table.

| Question | Simple rule | Learned policy | Verdict | Source |
|---|---|---|---|---|
| Spike, 200 held-out graphs, budget 16 | adaptive marginal **1.130** | GNN 1.410 / 1.590 / 1.455 | rule wins on all 3 training seeds | `role2_규리/results/confidence-v1/` |
| …same, untouched confirmation 2000–2199 | adaptive marginal **0.885** | GNN 1.185 / 1.325 / 1.275 | rule wins; GNN − marginal **+0.377 [+0.255, +0.510]** | `role2_규리/results/confirm-v1/` |
| …same, 10× training budget (10,000 episodes) | adaptive marginal **0.885** | GNN 1.155 / 1.140 / 1.145 | still loses: GNN − marginal **+0.262 [+0.165, +0.365]** | `role2_규리/results/confirm-10x/` |
| Spike, 100 graphs, same env | marginal **0.66** | GNN 0.96 / 1.17 / 1.06 | rule wins; learned CIs contain 0 | `role3 improvement/outputs/v3/` |
| Five graph shapes (spike/modular/BA/ER/real) | marginal **0.66 / 8.78 / 20.13 / 16.76 / 0.47** | — | positive vs sort-by-confidence on every shape; real is thin (+0.03 [0.00, 0.07]) | `role3 improvement/outputs/v3/benchmark_summary.csv` |
| Hypothetical ticketing pipeline (synthetic prior, 21 nodes, budget 8) | marginal **0.29** | — | **ties** confidence 0.32: +0.03 [0.00, +0.08], 98/100 ties — no cross-domain advantage | `role3 improvement/outputs/ticket-v1/` |
| Confidence corrupted (uniform noise, not recognised) | marginal **4.415** | adaptive marginal **3.150** | −1.265 [−1.545, −0.985] | `role2_규리/results/confidence-v1/` |
| …same, untouched confirmation 2000–2199 | marginal **4.185** | adaptive marginal **2.765** | −1.420 [−1.695, −1.150] | `role2_규리/results/confirm-v1/` |
| Corruption boundary: locality × magnitude × coverage (200 fresh graphs) | trust **0.865** (= clean oracle) | global-mean gate **2.745** in the worst cell | fires 195/200 on a rank-preserving −1 shift (+1.82 error) but 0/200 when real errors are masked (+3.21 error) | `role2_규리/results/corruption-v1/` |
| Probe-then-decide repair of that gate (pre-registered, 200 fresh graphs) | trust **0.935** | verify **0.935** (no worse than trusting at −1) | frozen verdict **failure**: 5 of 13 fired cells worse than trust, trigger still fires on harmless +3 shifts | `role2_규리/results/verify-v1/` |
| Per-node mixture posterior instead of a global gate (pre-registered, 200 fresh graphs) | trust **1.050** (= clean oracle) | shrink **1.055** clean, **−0.370** where errors are masked | frozen verdict **success**: all four predictions hold, +0.105 [0.040, 0.175] at −1; boundary — a harmless *global* +2/+3 shift still loses +0.45 / +0.72 | `role2_규리/results/shrink-v1/` |
| Two-step planning / residual GNN | — | — | +0.035 [−0.025, +0.100] / +0.022 [−0.018, +0.072]: **not supported** | `role2_규리/results/planning-v1/`, `role2_규리/results/residual-v1/` |
| Per-node scheduling on real data | — | — | four independent nulls | `CROSS_IMPLEMENTATION_VALIDATION.md` §3 |

The claim these support is **estimating which signal to trust, and staying safe when it cannot be trusted** —
not "the RL policy beats the rules". The learned policy loses to a deterministic two-step rule in the same
study that shows it improved (`role2_규리/results/credit-v1/confirmation/`).

**Confirmed on an untouched set (2026-11-24).** Seeds 2000–2199 were never used for development. Re-running
the confidence study there reproduces both core claims and leaves the paired deltas essentially unchanged:
GNN − marginal +0.355 → **+0.377 [+0.255, +0.510]**; signal gate −1.265 → **−1.420 [−1.695, −1.150]**. The
absolute means move (marginal 1.130 → 0.885) because this set is easier, so raw means are **not** comparable
across sets — only the paired deltas transfer. Caveat: the gate separates the synthetic uniform-noise
corruption almost perfectly (199/200 graphs correctly labelled), so it is evidence for *detectable
mean-shift* corruption, not for subtle or local corruption.

**10× compute control (2026-11-24).** Training the same GNN for 10,000 instead of 1,000 episodes narrows the
gap (GNN − marginal 0.377 → **0.262 [+0.165, +0.365]**) and collapses the seed spread (1.185–1.325 →
1.140–1.155), but the held-out validation objective plateaus at ≈0.94–0.96 while the rule sits at 0.885. So
the 1× numbers modestly overstated the gap; the ordering does not change. Under corrupted confidence the
10× model is unchanged (4.703 vs 4.700), consistent with a learner that cannot detect corruption — which is
exactly what the signal gate is for. Caveat: this is one architecture at 10×, not a scaling study.

**Corruption boundary (2026-11-24, exploratory).** The caveat above — the gate only demonstrates
*detectable mean-shift* corruption — was turned into a measurement. On 200 fresh graphs (seeds 3000–3199,
never used before) only public confidence scores were shifted in logit space,
`sigmoid(logit(c) + shift)`, on a deterministic subset of one locality: all 80 nodes (`uniform`), the 20
source nodes, the 20 sink nodes, or the nodes that actually carry a source error. Detection — the gate
labelling a graph `noise` — needs roughly p·|shift| ≈ 0.75–1 for uniform corruption; a 10 % subset stays
invisible even at shift −4. Two failures matter more than where the boundary sits.

(i) *The gate fires hardest exactly where the damage is smallest.* Shifting every score down by −1
preserves the ranking, so trusting the scores is within +0.06 of the clean oracle, yet the gate labels
195/200 graphs as corrupted and falls back to the type prior, for **+1.82 [+1.63, +2.03]** additional
errors relative to trusting the barely damaged scores. Across the 13 cells where the gate fires on ≥50 %
of graphs, its fallback helps in 3 and hurts in 10.

(ii) *Corruption that masks real errors is never detected.* A positive shift on the truly wrong nodes
leaves the gate at 0/200 even at +3, where trust loses +3.21 [+2.94, +3.48] errors and the gate does
nothing at all. Source and sink pools are both 20 nodes, so detectability is similar (139/200 vs 148/200
at 100 %, −3) while regret is not (source +0.39 vs sink +1.24): one graph-mean decision cannot see *where*
the corruption sits. The `error_nodes` and `oracle` rows use the hidden truth and are upper/lower bounds,
not deployable policies. This sweep is exploratory, not a frozen confirmation test, and it measures a fixed
marginal rule rather than a learned scheduler. Korean report:
`role2_규리/results/corruption-v1/corruption.md`; machine summary `corruption.json`; rerun with
`./run_corruption.sh`.

**Probe-then-decide follow-up (2026-11-24, pre-registered, verdict: failure).** Changing the fallback target
is not enough. A pre-registered policy (`role2_규리/PREREGISTER_VERIFY.md`) spends 4 reviews only when the
scores-as-is and rank-restored hypotheses disagree by more than a calibrated threshold, commits once by the
probed flag likelihood ratio, and never falls back to the type prior. On 200 further fresh graphs
(seeds 3200–3399) it removes the false-alarm cost: on the rank-preserving −1 shift it is
**−0.015 [−0.055, +0.025]** versus trusting, where the gate cost +1.845 [+1.630, +2.075]. It still fails its frozen
test. Of the 13 cells it fires on, 5 end worse than trusting (source layer at 100 %, −4: +0.375; uniform
25 %, −3: +0.140), and the trigger keeps firing on harmless positive shifts (195/200 graphs at uniform +3).
The gain is confined to corruption that is one monotone rescaling of every score (uniform 100 %: −2.52 at −4,
−1.98 at −3) and disappears when only part of the graph is corrupted, because restoring all 80 magnitudes
distorts the untouched nodes. Error masking is untouched: +2.985 [+2.710, +3.260] against the oracle, gate
identical. The `max|ΔP|` trigger measures shift magnitude, not harm — a repair needs per-node trust
estimation, not a better global statistic. Korean report: `role2_규리/results/verify-v1/verify.md`; rerun with
`./run_verify.sh`.

**Per-node shrinkage follow-up (2026-11-24, pre-registered, verdict: success).** The decision variable,
not the statistic, was the bug. A pre-registered policy (`role2_규리/PREREGISTER_SHRINK.md`) leaves the marginal
rule and the budget untouched and only replaces each node's posterior with a two-component mixture — the score
came from the clean distribution, or the same distribution shifted by an unknown delta — fitted by one scalar
π = 0.15 on 70000–70029. On 200 further fresh graphs (seeds 3400–3599) it passes all four frozen predictions:
+0.105 [+0.040, +0.175] versus trusting on the rank-preserving −1 shift (gate: +1.915), clean cost +0.005
[−0.025, +0.040], and **−0.370 [−0.520, −0.235]** where real errors are masked at +3 — the first repair that
beats plain trust there. Its boundary is as sharp as the gate's: a harmless *global* upward shift is read as
"clean nodes were pushed up", the true errors fall from rank 5.6 to 9.4, and the policy loses +0.72
[+0.57, +0.88]. 44 of 112 cells are slightly worse than trusting, of which only those two exceed +0.20.
Node-level posteriors identify *which* node moved, not *whether the whole graph did*, and masking still leaves
+2.72 [+2.45, +3.01] errors above oracle. Korean report: `role2_규리/results/shrink-v1/shrink.md`; rerun with
`./run_shrink.sh`.

---

## Document index (every page, rendered)

**Start here:** the evidence-chain design, then the implementation spec. Everything below is a
rendered page — no link opens raw markdown in the browser. Plans (`RL_PLAN`, `TRACKS`,
`GENERALIZATION_PLAN`) are working documents, not results; `PLAN.html` is their visual summary.

| Document | English | 한국어 | 中文 |
|---|---|---|---|
| Proposal — STA3145 course (phases + pre-registered gate) | [PROPOSAL_COURSE](https://cyracaid.github.io/rl-oversight-dag/PROPOSAL_COURSE.html) | — | — |
| Roadmap — what would make this publishable (and what does not) | [ROADMAP](https://cyracaid.github.io/rl-oversight-dag/ROADMAP.html) | — | — |
| Project narrative | [PROJECT_EN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_EN.html) | [PROJECT_KO](https://cyracaid.github.io/rl-oversight-dag/PROJECT_KO.html) | [PROJECT_CN](https://cyracaid.github.io/rl-oversight-dag/PROJECT_CN.html) |
| Evidence-chain design | [EVIDENCE_CHAIN_DESIGN](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN.html) | — | [EVIDENCE_CHAIN_DESIGN_CN](https://cyracaid.github.io/rl-oversight-dag/EVIDENCE_CHAIN_DESIGN_CN.html) |
| Implementation spec | [IMPLEMENTATION_SPEC_EN](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html) | [IMPLEMENTATION_SPEC_KO](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html) | [网页版](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.html) · [md 渲染](https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_CN.html) |
| Canonical line + reproduction receipts | [CROSS_IMPLEMENTATION_VALIDATION](CROSS_IMPLEMENTATION_VALIDATION.md) | [CROSS_IMPLEMENTATION_VALIDATION_KO](CROSS_IMPLEMENTATION_VALIDATION_KO.md) | — |
| Error card — known failure modes, error budget, what is not comparable | [ERROR_CARD](ERROR_CARD.md) | — | — |
| Open requests to Person 4 / 5 | [TEAM_REQUESTS_P4_P5](TEAM_REQUESTS_P4_P5.md) | — | — |
| Team claims | [TEAM_CLAIMS_EN](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_EN.html) | [TEAM_CLAIMS (三语同页)](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS.html) | [TEAM_CLAIMS_CN](https://cyracaid.github.io/rl-oversight-dag/TEAM_CLAIMS_CN.html) |
| Course alignment | [COURSE_ALIGNMENT](https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT.html) | — | [COURSE_ALIGNMENT_CN](https://cyracaid.github.io/rl-oversight-dag/COURSE_ALIGNMENT_CN.html) |
| SciForge proposal | [proposal_sciforge_en](https://cyracaid.github.io/rl-oversight-dag/proposal_sciforge_en.html) | — | — |
| Slide outline | [presentation_outline](https://cyracaid.github.io/rl-oversight-dag/presentation_outline.html) | [presentation_outline_ko](https://cyracaid.github.io/rl-oversight-dag/presentation_outline_ko.html) | — |
| Meeting one-pager | [HTML (tabs)](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal.html) · [PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_en.pdf) | [PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_ko.pdf) | [PDF](https://cyracaid.github.io/rl-oversight-dag/meeting_proposal_zh.pdf) |
| Experiment plan (gates, diagnostics) | [RL_PLAN](https://cyracaid.github.io/rl-oversight-dag/RL_PLAN.html) | — | — |
| Course vs SciForge split | [TRACKS](https://cyracaid.github.io/rl-oversight-dag/TRACKS.html) | — | — |
| Generalization work packages | [GENERALIZATION_PLAN](https://cyracaid.github.io/rl-oversight-dag/GENERALIZATION_PLAN.html) | — | — |
| Visual work plan (HTML) | [PLAN.html](https://cyracaid.github.io/rl-oversight-dag/PLAN.html) | — | — |
| Illustrated talk | [talk.html](https://cyracaid.github.io/rl-oversight-dag/talk.html) | [talk.html](https://cyracaid.github.io/rl-oversight-dag/talk.html) | [talk.html](https://cyracaid.github.io/rl-oversight-dag/talk.html) |

The same index is on the site landing page: <https://cyracaid.github.io/rl-oversight-dag/#documents>.

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
  rl_final.py                   Final table + figures, read from gnn_results.json /
                                methods_compare.json / cmdp_result.json (no training, no typed numbers)
  rl_gnn_multiseed.py           GNN + REINFORCE, static vs observed state, held-out paired eval
  graph_scale.py                N=500 experiments: modular / BA / ER
  real_pipeline_graph.py        Real sleep-pipeline DAG (N=21, from SCHEMA)
  verify_clustering.py          Real-data clustering check (skips if data missing)
  final_table.md                Final table
  results_bar.png, learning_curves.png, ablation_conf.png, scale500.png
```

**Canonical since 2026-11-24:** `role3 improvement/` (frozen environment, tag `role3-env-v3`) and
`role2_규리/` (canonical measurements). `experiments/` above is the earlier replica; see
`CROSS_IMPLEMENTATION_VALIDATION.md` before quoting any number.

```
CROSS_IMPLEMENTATION_VALIDATION.md   Which line is canonical, what may not be compared, reproduction receipts
role3 improvement/                   Frozen environment (dag_role3, 27 tests, hashed checkpoints, benchmark CSVs)
role2_규리/                          Role 2 measurements: confidence robustness, planning, credit, KAIST nights
```

---

## How to reproduce

| Want | Run | Needs real data? |
|---|---|---|
| Structural value (threshold vs greedy) | `python3 spike_active_selection.py` | No |
| Three RL methods (MLP scorer) | `python3 rl_methods_compare.py` | No |
| GNN upgrade | `python3 rl_cmdp_gnn.py` | No |
| Final table + figures (after the three training scripts) | `python3 rl_final.py` | No |
| GNN static vs observed state vs belief greedy (held-out, paired) | `python3 rl_gnn_multiseed.py` (~6 min, 8 cores) | No |
| N=500 heuristics incl. belief vs oracle greedy | `python3 graph_scale.py && python3 plot_scale.py` | No |
| Real-data clustering | `python3 verify_clustering.py` | **Yes (auto-skips if missing)** |
| Real queue recall@k (Table 1) | `python3 triage_bench/run_bench.py` | **Yes (auto-skips if missing)** |
| M4-only headroom | `python3 triage_bench/run_m4_mining.py` | **Yes (auto-skips if missing)** |
| Canonical benchmark (5 graph families, frozen checkpoints) | `cd "role3 improvement" && python3 run_benchmark.py --checkpoints outputs/v3/train_*/{dqn,gnn}_spike*.pt` | No |
| Canonical Role 2 contrasts (confidence, planning) | `cd role2_규리 && python3 evaluate_conditions.py --out … && python3 evaluate_planning.py --out …` | No |

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
- **CMDP soft-budget (PPO-Lagrangian + stop action), naive version: 2.15 with a fixed seed (4.85 in an earlier unseeded run)** — its stop-action credit assignment is too coarse and needs a FALCON-style reward-critic + cost-critic. This is our open problem.
- **GNN + PPO has not converged (~5.60)** and is omitted from the main table.
- **N=500 results are heuristics, not RL.** Deployable belief greedy: BA 12.8 vs threshold 37.6; on modular/ER it is only slightly better than the threshold.
- **Real-pipeline DAG (N=21): threshold 0.50 vs no-review 2.12** — the application-value result on our actual lab pipeline.
- **Real review queue (1,048 flags, 68 human-confirmed errors, 6.5% precision):** one rule ("M1-bearing first") reaches **84% of errors in 13% of the queue**; the pipeline's own order is *worse than random*. Errors cluster inside participants (variance/mean 2.00 vs null 1.10, p=0.0005), but ranking participants adds **no significant** gain over the row rule (@400 +7.3% [−8.6%, +10.0%]). Inside the 885 M4-only flags a grouped model gets **AUC 0.467** and adaptive belief **P@200 1.5%** vs 1.24% base — no headroom. That makes 84% an **information ceiling**, not a win: 7 of 72 corrections are never flagged at all, so no ranking policy can reach them. See `triage_bench/CEILING.md`.
- All numbers were produced by an AI agent and have not been independently verified, except the 2000–2199 confirmation re-run above, which the repository owner executed end-to-end from the committed scripts; Section 12 of `PROJECT_EN.md` lists the full checklist.
