# Pre-registration — degree-only baseline on a fresh block

**Status: frozen before any outcome on this block was computed.** Written and committed 2026-11-26,
after the v1 and v2 results on 90000–90099 and the v2 confirmation on 7100–7199, and before the first
episode on 13000–13099 was run. Nothing below may change afterwards. The block is spent whatever the
outcome.

## Question

Role 4's `rewire_index` keeps every node's number of parents but redraws *which* lower-index nodes
those parents are. On BA it retains about 73 % of the `marginal` gain over confidence, on ER about 31 %
(7100: 84 % / 32 %). Two readings survive that result and were not separated:

- **H-degree.** After a hub-preserving rewire the gain that remains is a consequence of the
  **in-degree profile** — a graph property that `rewire_index` holds fixed — not of the edges.
- **H-edges.** The gain needs the actual edge set; a policy that only reads confidence and in-degree
  cannot reproduce it.

`hub` (argmax in-degree, confidence ignored) is 10.8 / 16.5 errors *worse* than confidence on BA / ER,
so "degree alone" is already dead. This test asks the remaining, sharper question: does
**confidence × in-degree**, with **no propagation in the score**, recover the `marginal` gain?

## Block

| item | value |
|---|---|
| graphs | `generate_graph(family, seed)`, seeds **13000–13099** |
| episodes | `sample_episode(graph, 20000 + seed)` → **33000–33099** |
| budget | spike 16, real 8, modular / BA / ER 50 (unchanged, from `run_controls.budget_for`) |
| families | all five; the pre-registered claim is read on **ba** and **er** only |

Both ranges were checked against every CSV, `.py` and `.md` in the repo before this file was
committed: no `graph_seed`, no `seed` column and no numeric range string uses them.

## Policies (exact, no tuning)

On every step, over the currently available nodes (`obs["mask"]`), take the argmax of:

| name | score | status |
|---|---|---|
| `deg0.5` | `(1 − conf) · (1 + indeg)^0.5` | grid member |
| `deg1` | `(1 − conf) · (1 + indeg)` | **primary** |
| `deg2` | `(1 − conf) · (1 + indeg)^2` | grid member |
| `hub` | `indeg` | existing baseline (`policies.choose`), reported |
| `confidence` | `−conf` (argmin) | reference |
| `marginal` | frozen `policies.marginal_scores` | the policy under test |

`conf = obs["features"][:, k]` with `k = features.shape[1] − 7` (the `confidence` column used by
`policies.choose`); `indeg = bincount(edge_index[1])`, i.e. the number of parents, which is exactly what
`rewire_index` preserves. No sink-reach, no belief column, no edge probability, no propagation.

The exponent grid is declared here, in advance, for one reason: the grid must contain competitors that
favour degree (0.5) and confidence (2) as well as the neutral product, so that "propagation is
necessary" cannot be earned by picking a weak degree baseline. Every grid member is reported.

## Conditions

- **intact** — `run_public_policy(graph, snapshot, …)`; primary, decides the claim.
- **rewire_index** — the view graph is `run_controls.rewire(graph, seed)` (offset 4 040 000, draw 0),
  errors travel on the true graph (`run_controls.run_view`); secondary. Because the rule preserves each
  node's parent count, `deg*` and `hub` take **identical actions** in both conditions; the secondary
  therefore measures whether the *outcome* of a degree-only policy is itself rewiring-invariant.

## Statistic

Per family, per graph: `gain(policy) = sink_errors(confidence) − sink_errors(policy)`, the same paired
definition as v1/v2. Intervals: `run_controls.interval` verbatim (paired bootstrap, seed 411, 20 × 100),
i.e. 100 graphs as the resampling unit. No other statistic decides anything.

## Decision rule (fixed)

For each family, with `Δ = gain(marginal) − gain(deg1)` paired by graph and `[lo, hi]` its interval:

| label | condition |
|---|---|
| `propagation-necessary` | `lo > 0` — `marginal` beats the neutral degree-only score |
| `degree-suffices` | `hi ≤ 0` — degree-only is at least as good |
| `inconclusive` | otherwise |

**H-edges holds** on a family only if `propagation-necessary` holds there. **H-degree holds** only if
`degree-suffices` holds. Anything else is reported as `inconclusive`, with both intervals.

A second, stricter reading is reported alongside and never replaces the first: recompute the label using
`best = argmax over the grid of gain(deg_a)` at the *family* level (a single grid member per family,
chosen by point estimate) and require `lo > 0` against `best`. If that also holds, `propagation-necessary`
is reported as surviving the strongest degree-only competitor. If it does not, the primary label is
downgraded to `inconclusive` in the write-up even if `deg1` was beaten.

Fixed before the run: **the 73 % / 31 % retention figures are not re-read on this block and no threshold
moves.** A `degree-suffices` or `inconclusive` outcome does not change any label in
`results/v2/` or `results/v2_confirm/`; it only changes the sentence that explains them.

## What is reported

1. `results/degree_baseline/degree_baseline.csv` — one row per (family, seed, condition, policy):
   `sink_errors`, `actions`.
2. `results/degree_baseline/degree_baseline_summary.csv` — per (family, condition, policy):
   mean errors, gain vs confidence, paired interval, wins/ties/losses.
3. `results/degree_baseline/degree_baseline.md` — the three labels per family, the grid table, and the
   retention share `gain(deg1) / gain(marginal)` with its own interval.

## Known limits, declared now

- Degree-only policies are single-implementation, like v2's `rewire_order`. No clean room is claimed for
  them; the code path they exercise (`choose` → `OversightEnv.step`) is the one the frozen benchmark uses.
- `rewire_index` preserves parent counts but not the parent *set*, so it cannot isolate "profile of
  in-degrees across nodes" from "which node is a hub" any further than v2 already did.
- A `propagation-necessary` verdict says the score needs edges. It does not say the edges are used
  *correctly*; that is what the frozen benchmark's DP ceiling and the earlier ablations are for.
