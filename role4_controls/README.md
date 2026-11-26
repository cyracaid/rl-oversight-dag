# role4_controls — structural controls and worst-of-n (Person 4)

Answers `TEAM_REQUESTS_P4_P5.md` → Person 4. The claim under test: **the graph is doing the
work** — `marginal` (and `structural`) beat sort-by-confidence because they use how errors travel,
not because any ordering with a good error prior would do as well.

## Files

| File | What |
|---|---|
| `reproduce.py` | **teammate reproduction**: reruns everything into a temp folder, compares byte-for-byte, prints PASS/FAIL |
| `run_controls.py` / `results/controls*.csv`, `controls.md` | v1 (the request as written) |
| `diagnostics.py` / `results/diagnostics.csv` | post-hoc diagnostics quoted in `controls.md` §3 |
| `run_controls_v2.py` / `results/v2/` | v2 amendment (hub-breaking rewire, 10 draws, 3-level verdict) |
| `results/v2_confirm/` | v2 rerun on fresh block 7100–7199; `confirm.md` — 11/11 primary labels replicated |
| `EXPLAINER_KO.md` | 결과 설명서 (Korean FAQ for the team and the Q&A) |
| `QUESTIONS_FOR_P5.md` | questions for P5 (answered in `role4규리피드백.md`) |
| `role4규리피드백.md` | P5 review of this folder, with answers to Q1–Q5 |
| `PREREG_DEGREE_BASELINE.md` / `run_degree_baseline.py` / `results/degree_baseline/` | degree-only baseline (`confidence × in-degree`, no propagation) on block 13000–13099, pre-registered before the first episode |

```bash
python3 reproduce.py                  # v1 + diagnostics, ~6 min
python3 reproduce.py --full --jobs 4  # + v2, ~20-40 min
python3 reproduce.py --full --confirm --jobs 4  # + fresh-block confirmation, another ~20-40 min
```

## How to run

```bash
pip install numpy networkx          # networkx: the frozen graph generator imports it (BA/ER)
python3 run_controls.py --selftest  # invariants only; prints no control outcome
python3 run_controls.py --out results/
```

No GPU, no torch, no real data. About 3 minutes on one CPU core.
`results/controls.md` is written by hand **from** `results/controls_summary.csv`; every number in it
is a cell of that file.

## What is frozen

| Item | Value |
|---|---|
| Environment | `role3 improvement/dag_role3`, tag `role3-env-v3`, imported, not copied or changed |
| Graphs | `generate_graph(family, seed)`, seeds **90000–90099**, the frozen benchmark's graphs |
| Episodes | `sample_episode(graph, 20000 + seed)`, as in `run_benchmark.py` |
| Budget | spike 16, real 8, modular/BA/ER 50, as in `run_benchmark.py` |
| Policies | `confidence`, `structural`, `marginal` |
| CI | paired bootstrap copied verbatim from `run_benchmark.interval` (seed 411, 20 × 100) |

## Frozen before outcomes

This section, `run_controls.py` and the selftest were committed **before** any flatten or rewire
outcome was computed. The commit that adds results comes after it.

### Conditions (all paired on the same graph and the same episode)

- **intact** — `run_public_policy(graph, snapshot, ...)`, exactly the frozen benchmark call.
  Acceptance: errors *and* action sequences must equal `outputs/v3/benchmark_role3.csv` row by row;
  otherwise the script stops with exit code 2 and writes nothing.
- **flatten** — the same snapshot with every `edge_coins` value set to `False`. Source errors,
  confidences, reviewer draws and the edge probabilities the policy sees are unchanged. Errors stay
  where they start; the policy still plans as if they travel.
- **rewire** — the policy plans on a rewired copy of the graph; errors keep travelling on the true
  graph with the true edge coins. This is the version that tests the claim: if a *wrong* map does as
  well as the right one, the specific structure is not doing the work. (If policy and errors both
  moved to the rewired graph, it would be just another random graph and the control would test
  nothing about our structure.)

  Rewire rule, per graph, `rng = random.Random(4_040_000 + graph_seed)`, nodes in index order:
  - every node keeps its **number of parents**, its **type**, and the **sink set** is kept;
  - spike: new parents drawn without replacement from the **previous layer** (the generator's rule);
  - real: from all nodes in **strictly lower layers**;
  - modular / BA / ER: from **all nodes with a lower index** (the originals are oriented by index;
    "all other nodes", as the request words it, would allow cycles).

  Because each node keeps its parent count, `sample_episode(rewired, same seed)` consumes the random
  stream identically: source errors, confidences and reviewer draws are asserted identical.
  `MapMismatchEnv` recomputes only the hidden error state on the true graph; with view = truth it
  reproduces the frozen environment exactly (selftest).

### Statistic and verdict

`gain = errors(confidence) − errors(policy)` per graph (positive = policy better), mean with paired
95 % CI. `gain_removed_vs_intact = gain(intact) − gain(control)`, paired CI.

Label per (family, control, policy), fixed in `verdict()`:

| Label | Rule | Reading |
|---|---|---|
| `no-intact-advantage` | intact CI lower bound ≤ 0 | nothing to explain; the control is uninformative for this cell |
| `removed` | intact lower > 0 and control lower ≤ 0 | the advantage does not survive the control |
| `survives` | intact lower > 0 and control lower > 0 | the advantage survives — for **rewire this is a problem** and is reported as one, even if it shrank |

Primary cells: `marginal` on spike, modular, BA, ER. `real` is expected to be uninformative
(frozen gain +0.03 [0.00, 0.07]); it is run and reported, not used for the verdict.

## worst-of-n

`results/benchmark_worst_of_n.csv`: for every policy already in `benchmark_summary.csv`, the fraction
of the 100 graphs where the policy leaves **at least one** sink error (`worst_of_n`), the count, the
maximum and the 95th percentile. It is a groupby over `outputs/v3/benchmark_role3.csv`; the frozen
files are not touched. `worst_of_n = 1 − zero_error_rate` of the frozen summary by construction.

## Out of scope

27/48 consensus split — dropped by Person 4 (not waiting for labels). Not attempted, no split invented.

---

## v2 — frozen before outcomes (amendment)

Written and pushed **after reading v1** and **before** any v2 outcome was computed. v1 code, rules and
results above stay as they are and keep their labels. v2 adds three things; the motive for each is a
v1 result, stated here so the amendment is not mistaken for an original plan.

Run: `python3 run_controls_v2.py --selftest`, then `python3 run_controls_v2.py --jobs 4`
→ `results/v2/controls_v2.csv`, `results/v2/controls_v2_summary.csv`, written up in `results/v2/controls_v2.md`.

### 1. A hub-breaking rewire, `rewire_order` (motive: BA survived v1 rewire)

v1's rule draws parents from lower-index nodes. In BA and ER, low index means "old node", so the
rewired map keeps who the hubs are (out-degree rank correlation 0.63 / 0.62, `results/diagnostics.csv`).
`rewire_order` (modular, BA, ER only):

- build a random feasible order — at each step choose uniformly among unplaced nodes whose parent count
  is at most the number already placed;
- each node draws its parents uniformly from the nodes placed before it;
- parent counts, types and the sink set are kept; the graph stays acyclic; source errors, confidences
  and reviewer draws are asserted identical to the intact episode.

Design check run before freezing (structure only, no outcome; printed by `--selftest`): median out-degree
rank correlation, original vs rewired, draw 0 — modular 0.05 → 0.01, BA 0.63 → 0.01, ER 0.62 → 0.01.
spike and real are layered and their v1 rule already draws uniformly within the allowed layers, so they
get no `rewire_order`.

Reading: if the BA advantage survives `rewire_index` but not `rewire_order`, it rests on *who the hubs
are*; if it survives both, a wrong map with no hub information still helps, which is a problem.

### 2. Ten fixed-seed draws per graph (motive: v1 used one draw per graph)

`rewire_index` draw k uses `Random(4_040_000 + 100_000·k + graph_seed)`, so **draw 0 is v1** (asserted
row by row, errors and actions). `rewire_order` draw k uses `Random(5_050_000 + 100_000·k + graph_seed)`.
k = 0…9. Per graph the ten draws are averaged; the paired bootstrap (unchanged, seed 411) resamples graphs.
Also reported: the range of the 100-graph mean gain across the ten draws, and within-graph (across draws)
vs between-graph standard deviation of the policy's errors.

### 3. Three-level verdict with an equivalence margin (motive: "CI includes 0" was labelled `removed`)

Margin `m = 0.20 × intact mean gain` of the same family and policy. In this order:

| Label | Rule |
|---|---|
| `no-intact-advantage` | intact CI lower bound ≤ 0 |
| `survives` | control CI lower bound > 0 (even if the CI also lies inside ±m) |
| `removed` | control CI lies entirely inside [−m, +m] |
| `inconclusive` | anything else |

A control that makes `marginal` clearly *worse* than confidence (CI entirely below −m) is
`inconclusive` under this rule, not `removed`; the write-up says which direction it went.
Applied to flatten, `rewire_index` and `rewire_order`. Primary cells: `marginal` on spike, modular, BA, ER.

### Acceptance (v2)

`intact` must equal the frozen benchmark and `flatten` / `rewire_index:0` must equal v1 `controls.csv`,
errors and actions, row by row; otherwise the script exits 2 and writes nothing.

---

## v2 confirmation on a fresh block — frozen before outcomes

Why: the v2 rules were chosen after reading v1 on 90000–90099, so by the seed ledger in
`COURSE_FINAL_REPORT.md` that block is spent for v2. The same frozen code and rules (`7f58534`) are
rerun once on a block no run has used.

| Item | Value |
|---|---|
| Graph block | **7100–7199** (ledger: spent blocks end at 5829 and resume at 60000; no file in the repo uses 7100–7199) |
| Episodes | `20000 + graph_seed` (27100–27199), budgets and policies unchanged |
| Rules | exactly v2: `rewire_index` and `rewire_order`, 10 draws, three-level verdict, margin 20 % of this block's intact gain |
| Command | `python3 run_controls_v2.py --start-seed 7100 --jobs 4 --out results/v2_confirm/` |

Endpoint, read once: the label of each primary cell (`marginal` on spike, modular, BA, ER under flatten,
`rewire_index`, `rewire_order`; 11 cells) on 7100–7199, compared with its label on 90000–90099.
A cell is **replicated** if the label is the same; otherwise it is reported as **not replicated** with
both intervals. No rule, margin or code changes after this run. The block is spent whatever the outcome.
There is no row-by-row acceptance check on this block (no frozen reference exists for it).

---

## Reading notes after P5 review (no rule, code or result change)

P5's review is in `role4규리피드백.md`. These notes scope the write-ups; the frozen sections above are unchanged.

- **v1 candidate pool.** Parents are drawn from lower-index nodes on modular/BA/ER because "all other nodes", as the
  request words it, can create cycles, which the frozen `DAG()` rejects. `rewire_order` (v2) is an *additional*
  control that draws parents in a random order, not a replacement for v1.
- **Block roles.** 90000–90099 is the **v2 design block** (v2's rules were chosen after reading v1 on it);
  7100–7199 is the **confirmation block**, run after the rules were frozen (`c07aedc`).
- **Margin.** 20 % is this experiment's decision threshold, applied to each block's own intact mean gain.
- **Scope of the rewire reading.** With the index rule, BA keeps about 73 % of its intact gain and ER about 31 %
  (block 7100: 84 % and 32 %), so the two are reported separately. `rewire_order` changes paths and sink reachability
  as well as hub rank; the index-vs-order contrast is *consistent with* hub information mattering, not a test of hub
  rank alone.
- **`inconclusive` cells.** Every one of them has its CI entirely below −margin; the tables mark them
  "worse than confidence" next to the frozen label.
- **`direction` column (applied on `main`, 2026-11-26).** Both `controls_v2_summary.csv` files now carry a
  `direction` column written by `run_controls_v2.py`: `worse-than-confidence` when the frozen label is
  `inconclusive` and `paired_hi < -margin`, empty otherwise. Five cells per block, all `marginal`
  (spike/`rewire_index`, modular/`rewire_index`, modular/`rewire_order`, BA/`rewire_order`,
  ER/`rewire_order`). Every other cell of both files is unchanged.
- **Rewire seed is a parameter now (applied on `main`, 2026-11-26).** `run_controls.rewire()` takes
  `offset=None`; `run_controls_v2.rewire_index()` passes it explicitly instead of assigning the module
  constant `REWIRE_SEED_OFFSET`. Behaviour is unchanged: both `controls_v2.csv` files regenerate
  byte-identically.
- **Line endings.** `.gitattributes` pins result files to LF so the byte-for-byte check passes on Windows with
  `core.autocrlf=true`. A Windows clone made before this commit refreshes its result files once with
  `git rm -r -q --cached role4_controls/results` then `git checkout HEAD -- role4_controls/results`.
- **Degree profile vs edges (block 13000–13099, pre-registered).** `PREREG_DEGREE_BASELINE.md` asks whether
  the gain that survives `rewire_index` is a property of the in-degree profile. A score that never propagates,
  `(1 − conf) · (1 + indeg)^a` for a ∈ {0.5, 1, 2}, leaves **21.2 more** errors than confidence on BA and
  **17.8 more** on ER (intact, `marginal`: 19.6 and 3.0 fewer). Δ = marginal − deg1 = +40.8 [+29.3, +52.6] on BA,
  +20.8 [+19.1, +22.5] on ER; the best grid member is still beaten on both. Verdict: `propagation-necessary` —
  the residual is carried by the edges, not by the degree profile. See `results/degree_baseline/degree_baseline.md`.
- **ER does not replicate.** Retention after `rewire_index` on that third block: BA 79 %, **ER 1 %**
  (+0.02 [−1.01, +1.02]), against 31 % / 32 % on 90000–90099 and 7100–7199. BA survives on all three blocks;
  ER's `survives` label is block-specific and should not be quoted as a family property.
- **v2 is no longer single-implementation (P5 clean room, 2026-11-26).** An implementation written from
  this README alone, without reading `run_controls_v2.py`, reproduces `intact`, `flatten` and
  `rewire_index:0` row by row (1500 rows each, errors and actions), every summary cell outside
  `rewire_order` (675/675 per block), all 54 verdict labels and 11/11 primary labels on both blocks.
  Six of the nine `rewire_order` rows differ by up to 1.7 errors (≤ 4.5 % of the gain) because the
  random-order detail — the order of the candidate pool and the tie-break among feasible nodes — is not
  specified above. Either state that detail here, or report the `rewire_order` cells by sign and label
  only. Report: `reviews/role4_controls_v2_cleanroom.md`.
