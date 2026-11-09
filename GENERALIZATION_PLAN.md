# Generalization plan — team work packages


> Status: **not done, not verified.** The belief-conditioned GNN + REINFORCE result
> is a single run and needs reproducing before anyone cites it. This document is the
> assignment sheet, not a report.

---

## 0. What we believe, and what we still have to check

| Claim | Evidence today | Status |
|---|---|---|
| Belief-conditioned GNN + REINFORCE performs best | **no artifact in `experiments/` as of 2026-11-09**: the committed GNN runs are static and observed (observed already carries the belief posterior) and both lose to belief greedy, 1.56 vs 1.14 | **unsupported — WP1 must produce the run before anyone cites it** |
| Belief greedy beats static/observed GNN on held-out graphs | 200 graphs, paired CI (+0.42 ± 0.15) | verified in-repo, needs rerun by a second person |
| Type partition explains most of the real queue's recall | 1,048 flags, 68 labels | verified in-repo, single lab |

Nothing below assumes the first row is true.

---

## 1. What "generalize" means here (three rungs, in order)

| Rung | Data | Question it answers | Why this rung |
|---|---|---|---|
| **G1** | second sleep cohort (KAIST 1,372/49, CC BY; Manchester) | does the row/field structure transfer across cohorts? | same schema, different people — cheapest real test |
| **G2** | GO annotations (IEA vs experimental, GO is a DAG) | does the method transfer to a different biological unit? | real DAG, real "auto vs curator" split |
| **G3** | clinical (only if a licensed set is found) | does it transfer to a regulated domain? | highest cost, do last |

**Operational definition:** generalization = *the same table, produced by the same
script, with the same metrics, on a new dataset.* If the columns change, it is not
a transfer result.

The table that must repeat:

| dataset | unit | type ceiling | within-type gain | cost gain |
|---|---|---|---|---|
| sleep A | row/field | 84% | none | 2× |
| sleep B (G1) | row | ? | ? | ? |
| GO (G2) | gene–term | ? | ? | ? |

**The claim generalizes only if the ordering repeats** — type ≫ within-type,
cost ≫ recall. A different ordering is a finding, not a failure: it tells us where
the method earns its keep.

---

## 2. Work packages

### WP1 — Verify the belief result, and test its assumption · **Person 2**
- **Input:** `experiments/rl_gnn_multiseed.py`, `experiments/belief.py`.
- **Arm A (verification).** belief-conditioned vs static vs observed vs belief greedy,
  5 training seeds, 200 held-out graphs, paired bootstrap, per-seed numbers published.
- **Arm B (misspecification).** Belief greedy is *model-based*: it assumes the
  propagation probability and the confidence calibration are right. Perturb exactly
  that — λ scaled by 0.5 and 2.0, and the confidence posterior shifted — then rerun
  the same four policies on the same held-out graphs. This is the one condition in
  which a learned policy can legitimately win, so it decides whether the paper's
  claim is "belief wins" or "belief wins *when the model is right*".
- **Acceptance:** two tables with CIs. Arm A decides Option 1 / Option 2; Arm B says
  how much the winner depends on a correct model.
- **Why both, now:** they share the training pipeline; the second arm costs one extra
  sweep, not a new project. Testing only Arm A leaves the obvious reviewer question
  ("what if your model is wrong?") unanswered.
- **If Arm A fails:** that is Option 2 material — hand the diagnostics (below) to WP4.

### WP2 — Freeze the environment and build the G1 adapter · **Person 3**
- **Do:** freeze the synthetic generator (no changes after this point); write
  `adapt_sleep_b.py` producing the same item/type/label schema from KAIST.
- **Acceptance:** `python3 -m experiments.transfer --dataset kaist` runs end to end;
  row counts and missing-data handling reported.
- **Do not:** invent a new graph family, change the reward.

### WP3 — Model survey + two implementations · **Person 4**
Survey at least five alternatives to "learned policy vs belief greedy", rate them,
then implement the two cheapest:

| Candidate | One-line rationale | Effort |
|---|---|---|
| VOI / adaptive-submodular greedy | the principled model-based competitor | low (have it) |
| Monte-Carlo tree search / rollout planning | same model, lookahead instead of myopia | medium |
| Behaviour cloning from belief greedy | tests whether the *policy class* or the *optimizer* is the issue | low |
| Offline RL (CQL/IQL) on logged reviews | matches the real deployment constraint | medium |
| Transformer policy over the DAG | is the GNN the limitation? | high |

- **Acceptance:** a one-page comparison table (fit / effort / risk) + two working
  baselines with the same evaluation harness.

### WP4 — Diagnostics for the negative result · **Person 4 with Person 2**
Only if WP1 fails:
1. per-step advantage vs realized contribution correlation;
2. return variance at fixed policy;
3. interventions: potential shaping, n-step (3, 5), batch size, 100k episodes;
4. information control already covered by WP1.
- **Acceptance:** each probe has a number and a one-line reading.

### WP5 — Dataset survey and licensing · **Person 5**
- **Do:** for each candidate, record: unit, label source, type field, dependency
  edges, cost proxy, licence, download size, access steps. Verify by opening the
  actual files, not the abstract.
- **Priority:** KAIST → GO → (Manchester) → clinical only if licensed.
- **Acceptance:** a table where every row has a verified licence and a working load
  command; no dataset enters the repo.

### WP0 — Protocol and deadline · **Person 1**
- Owns the table columns, the metric definitions, and the paired-CI rule.
- Rejects any table without a CI or without a script path.

---

## 3. Rules that apply to every package

1. **One table, one script.** If a number cannot be regenerated by a command, it
   does not exist.
2. **Paired comparisons only.** Same held-out items, bootstrap CI, ≥5 seeds.
3. **Report the interval, not the winner.** Differences below ~10 pp on the real
   queue are inside the noise.
4. **No dataset in the repo.** Code and aggregate numbers only.
5. **Status labels.** Every claim in a doc is `verified` / `unverified` / `retracted`.

---

## 4. Dependencies: the honest version

The packages are **not independent**. Only two are (WP5 and the reading half of
WP3). Everything else sits on one chain, and pretending otherwise is how five
people produce five incompatible tables.

### 4.1 The real dependency graph

```
WP0 protocol + harness ──► everything (but it is 2 days, not a blocker)
        │
WP2 freeze env ──► WP1 verify ──► decision ──► WP4 diagnostics (only if Option 2)
        │                              │
        │                              └──► paper tables
        ├──► WP3 implement (survey can start day 1)
        └──► WP5 adapter schema ◄──► WP5 dataset survey (survey is independent)
```

| Package | Blocked by | Blocks |
|---|---|---|
| WP0 protocol | — | all |
| WP2 freeze | WP0 (metric definitions) | WP1, WP3 impl, WP4, G1/G2 |
| WP1 verify | WP2 | the Option 1/2 decision, WP4 |
| WP4 diagnostics | WP1 + decision | — |
| WP3 survey | — | — |
| WP3 impl | WP2 + WP0 | — |
| WP5 survey | — | — |
| WP5 adapter | WP2's item schema | G1 |
| G2 (GO) | WP5 adapter + WP2 | — |

**Critical path:** WP0 → WP2 → WP1 → decision → (WP4) → paper. WP5 feeds the
transfer rungs but does not block the course deliverable.

### 4.2 The single choke point

**WP2's freeze.** If the simulator changes after verification, every number
invalidates. So the freeze is a tagged commit plus a rule: *any change to the
environment is a new version and re-runs every table.* Nothing else in the plan
matters if this rule is broken.

### 4.3 Contracts that make parallelism safe

Parallelism is bought with interfaces, not independence:

| Contract | Owner | Consumers | Freeze by |
|---|---|---|---|
| `eval.py` — one recall/CI implementation, imported by everyone | WP0 | WP1, WP3, WP4, WP5 | day 2 |
| Item schema for a transfer dataset (unit, type, label, edge, cost) | WP2 + WP5 | WP5 adapter, G1, G2 | day 2 |
| Environment version tag + seed protocol | WP2 | all experiments | day 2 |
| Table template (columns, CI rule, script path) | WP0 | every report | day 2 |

Two people writing evaluation code is the most likely source of divergent
numbers. One file, one owner.

### 4.4 Day-level sequence

| Day | Person 1 | Person 2 | Person 3 | Person 4 | Person 5 |
|---|---|---|---|---|---|
| 1–2 | protocol + `eval.py` | read code, prep belief features on a branch | freeze env, tag | survey models | survey datasets |
| 2 | publish contracts | — | agree item schema with P5 | — | agree item schema with P3 |
| 3–5 | review tables | **WP1 verification** | adapter skeleton | pick 2 models | verify licences/loads |
| 5 | — | **decision gate** | — | — | — |
| 6–8 | paper skeleton | Option 1: tighten seeds / Option 2: hand off | G1 adapter done | WP4 diagnostics | G1 data ready |

### 4.5 What goes wrong if we ignore this

- **Env changes mid-verification** → P2's table contradicts P3's, nobody knows which is right.
- **Two eval scripts** → recall computed on different denominators; the discrepancy surfaces in the last week.
- **Adapter built before the schema is agreed** → P5's dataset needs a field the simulator cannot express, and the env changes after freeze.
- **P4 implements before the env is frozen** → baselines run on an old graph family and are silently incomparable.
