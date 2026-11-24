# Repo update, 2026-11-24 — what role 2 established, what to keep, what to run next

<p><b>Language:</b> <b>English</b> · <a href="REPO_UPDATE_20261124_KO.html">한국어</a> · <a href="REPO_UPDATE_20261124_CN.html">中文</a></p>

> One page for the team, written after the boundary experiment and the `p_catch`
> sweep. Every number below is a paired difference inside one run, taken from the
> frozen report of that run. Seeds, manifests and verdict code are in the repo;
> nothing here is hand-edited.

## 1. The chain, in one paragraph

The project started as one negative result — a learned review policy loses to a
deterministic rule (1.56 vs 1.14 on held-out graphs, +0.42 [0.26, 0.51]) and more
compute does not fix it (+0.262 [0.165, 0.365] at 10×). The useful finding came
from asking a different question: not "which policy schedules reviews better" but
**"which signal should be trusted, and what should the policy do when it cannot be
trusted"**. That question was answered in four steps, each frozen before its run:
a global gate that decides whether the confidence scores are corrupted; a per-node
posterior that decides which nodes moved; a per-graph posterior that decides
whether the whole graph moved and by how much; and finally a measurement of where
that last model stops working.

## 2. What we can claim, and what we cannot

**Can claim.** With 16 reviews, a policy can estimate whether its confidence scores
are usable, and can stay safe when they are not: a harmless global +3 shift costs
+0.005 [0.000, 0.015] errors versus trusting the scores, and a masked corruption at
+3 is no worse than trusting (−0.035); a full −4 shift is undone
and the policy returns to the clean oracle (0.94 versus 3.86 for trusting). The
per-graph repair also survives drift that does not sit on its grid: mean δ error
0.174, and all 12 off-grid cells beat the per-node repair.

**And the scheduling null is not our heuristic's fault.** Solve the mean-field belief
model exactly on 24 graphs (seeds 5000–5023, K∈{1..5}) and the best policy in
that model is only 0.030 expected sink errors better than the deployed
rule on real data, CI [0.008, 0.065] as a gain (the tables report policy−comparison, so
they show −0.030 [−0.065, −0.008]); 0.002 on ticket. Planning value is sub-linear in K
(ratio 1.81), so this is not a horizon problem either. Caveat that must travel with the
number: this is the optimum of *our approximation*, not of the POMDP
(`PREREGISTER_DP.md`, `outputs/dp-ceiling-fresh/report.md`; the first run sat on the
model-selection block 60000–60023, and its rerun is in that folder's `AMENDMENT.md`).

**Cannot claim.** Learned policies do not beat the deterministic rule (rule still
wins by 0.377). The repair does not rescue the masking case: it hands back the
per-node repair's −0.36 gain (scope is +0.325 [0.195, 0.470] worse than shrink
there). Two simultaneous drifts are outside the single-δ model: with source and
sink shifted by different amounts, both single-δ families fall back to roughly
plain trust (2.15 / 1.89 / 1.87). The `p_catch` trend did not come out as predicted
(see §3).

## 3. The experiment inventory

| Run | Seeds | Frozen verdict | Keep how |
|---|---|---|---|
| `confidence-v1` + `confirm-v1` + `confirm-10x` | 1000–1199 dev, 2000–2199 confirm | completed | **Main table.** Signal trust is learnable; 10× compute narrows the gap instead of closing it |
| `corruption-v1` (global gate boundary) | 3000–3199 | completed | **Failure evidence only.** Fires 195/200 on a harmless −1 shift (+1.82), 0/200 when errors are masked (+3.21) |
| `verify-v1` (gate repair) | 3200–3399 | **failure** | **Keep as a failure.** 5 of 13 fired cells worse than trusting; the trigger still fires on harmless +3 |
| `shrink-v1` (per-node) | 3400–3599 | success | **Main result.** +0.105 on the rank-preserving −1 shift; −0.370 where errors are masked; boundary +0.72 on a global upward shift |
| `scope-v1` (per-graph) | 3600–3799 | success | **Main result.** +0.005 at +3 (shrink +0.81); 112-cell mean 1.303 → 1.203; pays back +0.325 on masking |
| `scope-robust-v1` (boundary) | 3800–3899 | **partial success** | **Keep, with the failed prediction written out.** Off-grid holds; the declared "shrink wins on two δ" guess is wrong (−0.016) |
| `p_catch` sweep | 4000–4199 | direction holds, **trend inverted** | **Keep, including the inverted part.** +0.255/+0.350/+0.415/+0.530 all exclude zero; the advantage shrinks as the hit rate falls, not grows |
| `planning-v1`, `residual-v1`, `partial-v1`, `feedback-v1`, `credit-v1`, sleep replay | 92000–94199, real | nulls | **One line each** in the "not supported" list |
| `block-review MDP`, `correction clustering` | — | no frozen rules | **Exploratory only.** Pre-register before any number is quoted |
| old confidence ablation (zero-adjacency `A0`) | 1000–1199 | — | **Claim dropped.** Not usable for mechanism attribution |

## 4. Seed ledger — do not rerun a spent block

| Block | Used by |
|---|---|
| 1000–1199 | development comparison |
| 2000–2199 | independent confirmation |
| 3000–3199 | gate boundary |
| 3200–3399 | gate repair |
| 3400–3599 | per-node repair |
| 3600–3799 | per-graph repair |
| 3800–3899 | boundary experiment |
| 4000–4199 | `p_catch` sweep |
| 4200–4399 | PPO baseline (`outputs/ppo-v1/`, `PREREGISTER_PPO.md`) |
| 4400–4599 | sampled counterfactual value (`PREREGISTER_EXACT_VALUE.md`) |
| 4600–4799 | **void** — smoke runs only (4600–4603), excluded from every result |
| 4800–4999 | belief-value decomposition (`PREREGISTER_BELIEF_DECOMPOSITION.md`) |
| 5000–5023 | exact DP ceiling (`outputs/dp-ceiling-fresh/`, `PREREGISTER_DP.md`) |
| 5200–5399 | depth-2 planning (`PREREGISTER_PLANNING_V2.md`) |
| 5400–5599 | coverage receipt (`PREREGISTER_SUPERVISOR.md`) |
| 60000–60029 | model-selection validation (not a result block; 60100–60129 from now on) |
| 70000–70099 | calibration (parameters fitted here only) |
| 91000–91199 / 92000–92199 / 93000–93199 / 94000–94199 | assess / feedback / residual / planning |

Next free block: **5024–5199**, then **5600–59999**, then **60130 and up**. Rerunning a spent
block is a rules violation, not a re-check; the results are already byte-reproducible. (This
line said "4200 and up" until 2026-11-24; four later blocks had gone unrecorded here, so the
ledger listed less than it should have. The earlier "mixed δ at 4200–4299" suggestion was
stale for the same reason.)

## 5. Why the numbers can be trusted mechanically

- Every result directory has `manifest.json` (graph seeds, budget, fitted constants,
  sha256 of episodes and of every source file) plus per-graph `episodes.csv`.
- Reports are regenerated from `episodes.csv`, not typed: two runs give identical
  sha256.
- Verdict arithmetic goes through one comparator; the rules are frozen in a
  `PREREGISTER_*.md` file committed before the first seed of the block runs.
- Budget invariant: every row has `reviews == budget`.

## 6. What to run next (cheapest decisive first)

1. **Mixed δ inside one layer** — the only real hole. The boundary experiment moved
   two disjoint layers by two deltas; it never moved one layer by two different
   deltas. 100 graphs, 20 cells, same cost as the boundary run. Seeds 5000–5099 (the
   earlier 4200–4299 suggestion is spent, and 4400–4999 / 5200–5399 are taken).
2. **`p_catch` × `scope`** — at a 0.60 hit rate, is δ still estimated? This is the
   only meaningful crossing of the two lines.
3. Real `n = 21` pipeline with `scope` — expected negative, optional, not for the
   main table.

Nothing else needs rerunning today.

## 7. Three decisions for 문규리

1. Course deliverable scope: the whole chain, or only "scope success + two
   self-declared failures"?
2. Does the `p_catch` inverted trend go into the main report? (Recommendation: yes —
   hiding it is riskier than reporting it.)
3. How to phrase the two-δ result: as a boundary measurement, or as a limitations
   paragraph?
