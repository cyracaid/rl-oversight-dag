# The RL plan, in detail

> Course-facing only. Scope: STA3145, deadline 12/05. No external partner, no
> restricted data, every number from one script.
> Companion: `IMPLEMENTATION_SPEC.md` (constants), `TRACKS.md` (why this is separate
> from SciForge).

---

## 0. The one experiment that decides the paper: G0

**Question.** Is the RL gap a *state-representation* problem or a *credit-assignment* problem?

**Design.** Same information, two optimizers. Give the policy the belief posterior
as node features — marginal error probability, entropy, reviewed mask — so it sees
exactly what belief greedy sees. Everything else unchanged (GNN scorer, REINFORCE,
5 seeds, 20k episodes, 200 held-out graphs, paired bootstrap).

| G0 result | Reading | Course claim |
|---|---|---|
| RL ≥ belief greedy (CI excludes 0) | the loss was representation | **Option 1** — RL is the method |
| RL < belief greedy | the loss is credit assignment | **Option 2** — the analysis is the result |

Run this before anything else. It costs ~30 minutes of compute and it sets the
structure of the entire deliverable.

> **Correction (2026-11-09, before anyone spends the 30 minutes).** This exact
> experiment has already been run. The "observed state" variant in
> `experiments/rl_gnn_multiseed.py` already feeds `P(base error)`, `P(error)`,
> `reviewed`, `flagged` and the budget fraction, refreshed after every review.
> Held-out (n=200, paired): **1.56 vs 1.56** static, **−0.00 ± 0.08**; both lose to
> belief greedy by **+0.42 ± 0.15**. The posterior is not the missing piece.
>
> What is still untested is narrower, and it is the actual G0:
> **(a) the one-step value** `gain(i)` that `belief.py:best_action` argmaxes — the
> policy sees the belief, not the value it should compare against;
> **(b)** credit assignment under a terminal-only reward over 16 steps;
> **(c)** the regime where the greedy's model is wrong — that is the only place
> learning has an information advantage over a planner.
>
> Pre-registered gate criteria: `PROPOSAL_COURSE.md` §8.

---

## 1. MDP, stated once

| Element | Definition |
|---|---|
| State | per node: type, confidence, downstream count, reviewed mask; plus budget left and the graph adjacency. **Belief variant adds:** posterior marginal, posterior entropy |
| Action | pick an unreviewed node, or stop |
| Transition | review → observation (`flagged` w.p. `p_catch` if the node is wrong) → fix only if the error originated there; recompute descendants |
| Reward | terminal only: −(# wrong sinks). Variants: potential-based shaping, n-step |
| Horizon | budget B (80-node: 16), γ < 1 |
| Objective | minimize sink errors at fixed budget |

The belief variant is the only change needed for G0: the simulator already models
`p_catch` and the particle filter already exists (`experiments/belief.py`).

---

## 2. Method table (what gets compared)

| Class | Policy | Role |
|---|---|---|
| Baselines | no review / random / confidence threshold / structural greedy | traditional |
| Model-based | **belief greedy** (deployable) | the one to beat |
| Model-free | REINFORCE (MLP), PPO (MLP), DQN | preliminary / control |
| Graph | GNN + REINFORCE (static state), GNN + REINFORCE (observed state) | upgrade path |
| Constrained | CMDP + PPO-Lagrangian (naive) | negative result |
| **New** | **GNN + REINFORCE, belief-conditioned** | G0 |
| Ceiling | oracle greedy (reads truth) | upper bound |

---

## 3. Experiment matrix

| Axis | Levels | Cost |
|---|---|---|
| Environment | 80-node synthetic (main), N=500 modular/BA/ER (heuristics only), N=21 real pipeline | cheap |
| Seeds | 5 training seeds × 20k episodes | ~6 min each on 8 cores |
| Evaluation | 200 held-out graphs (seeds 1000–1199), paired by graph | free |
| State ablation | static / observed / **belief** | 3 × training |
| Reward ablation | terminal only / potential shaping / n-step (3, 5) | 4 × training |
| Budget | 8, 16, 32 | eval only |

**Reporting rule.** Every comparison is a *paired* difference over the same
held-out graphs, with a bootstrap CI. A point estimate without a CI does not go in
the paper — the 5-seed table already fooled us once (best seed 1.00 vs mean 1.54).

---

## 4. If RL loses: the diagnostics that make Option 2 publishable

"RL lost" is not a result until the mechanism is named and tested. Four probes,
cheap ones first:

1. **Credit assignment.** Correlate per-step advantage estimates with the action's
   realized contribution. Near-zero correlation ⇒ the policy cannot tell which
   review mattered.
2. **Return variance.** Terminal-only reward on a 16-step horizon: measure the
   variance of returns across rollouts at fixed policy. High variance + sparse
   signal is the classic failure mode.
3. **Interventions.** Potential-based shaping, n-step returns, larger batches,
   longer training (100k). If none close the gap, the failure is structural, not
   a tuning issue.
4. **Information control.** G0 already equalized the state; if RL with the belief
   state still loses, the information explanation is ruled out.

The write-up becomes: *"policy gradient fails here because X, and here are three
tests that would have falsified X."*

---

## 5. Timeline to 12/05

| Week | Work | Gate |
|---|---|---|
| 11/10–11/16 | G0 run; freeze environment and numbers | **G0 decided**, env frozen |
| 11/17–11/23 | Diagnostics (if Option 2) or seed tightening (Option 1); one transfer set | every table from one script |
| 11/24–11/30 | Paper draft, figures, ceiling section | draft complete |
| 12/01–12/05 | Slides, ≥2 rehearsals, final numbers | talk delivered |

---

## 6. Definition of done

- **Option 1:** belief-conditioned RL beats belief greedy on 200 held-out graphs,
  paired CI excluding 0, 5 seeds, and the gain survives the state ablation
  (i.e., it is not just the belief features doing the work).
- **Option 2:** a named mechanism, at least one intervention that moves RL toward
  parity or provably cannot, and the information control (G0) reported.

Either way: every number reproducible from a single command, and no table edited
by hand.

---

## Appendix A — public datasets worth testing (survey, 2026-11-09)

Criteria: (a) queue of items, (b) binary "needs action" label, (c) type/flag
partition, (d) dependency edges, (e) cost proxy, (f) open licence.

| Dataset | Unit | (a) | (b) | (c) | (d) | (e) | Licence | Fit |
|---|---|---|---|---|---|---|---|---|
| **SYNERGY** (ASReview collective) | record | ✅ | ✅ | partial | ✗ | ✗ | open | **best for the screening task**: fully labelled, many fields, standard benchmark harness |
| **GO annotations** (IEA vs EXP/IDA) | gene–term | ✅ | ✅ | ✅ | ✅ (GO is a DAG) | ✗ | CC BY 4.0 | **best for the DAG story**; also the real "auto vs curator" case |
| **KAIST sleep diary** (Figshare 28509740) | row | ✅ | needs labels | ✅ | ✗ | ✗ | CC BY | tests whether the row/field structure transfers |
| **Manchester diary** (Figshare 23786238) | row | ✅ | needs labels | ✅ | ✗ | ✗ | open | second sleep cohort |
| GitHub code review (HuggingFace `ronantakizawa/github-codereview`) | PR/hunk | ✅ | ✗ (no correctness) | ✅ | partial | ✗ | check | good for "AI review" framing, weak as a benchmark |
| FEVER | claim | ✅ | ✅ | ✗ | partial | ✗ | CC BY-SA | fact-checking flavour, not review scheduling |
| Bug triage (Bugzilla/JIRA exports) | issue | ✅ | priority only | ✅ | ✗ | ✗ | varies | priority learning, not error review |

**Recommendation.** Take **SYNERGY** for the transfer test (labelled, standard,
cheap to load) and **GO** for the DAG version. Together they cover "same task,
different domain" and "same task, real graph" — the two claims a reviewer will
ask about. Skip the rest unless one of these fails to load.

*Licences and downloads were checked only at the level of the source pages; verify
before use and record the version/date.*
