# Pre-registration — order benchmark v2.1: the conditional endpoint

Frozen 2026-11-25, before any run. Blocks: **graphs 5184–5195, episodes 5640–5699** (60
episodes, `q = 1.0`), reserved in `BENCHMARK_SPEC.md` before this file was written.

Follows `PREREGISTER_ORDERED_BENCHMARK.md` and `outputs/ordered-gate-v2/`. That gate closed on
G2. This file does not reopen it; it prices **one** change — the endpoint — and nothing else.

## What the closed gate actually showed

On 5600–5639 with `q = 0.5`, half the episodes were affected and the effect was inside them:

| on the 21 transposed episodes | sink errors |
|---|---:|
| `marginal` | 1.048 |
| `truth_reader` | 0.857 |
| `oracle` (hidden source errors) | 0.810 |

The pooled mean over 40 episodes was −0.100 against a frozen threshold of 0.15, and 0.15 turned
out to be about the whole empirical headroom. So the threshold asked for roughly 100 % recovery
of a gap while halving the sample with clean episodes. That is a defect in the endpoint, not in
the mechanism, and it is being fixed here in the open rather than by editing the old file.

**Disclosure.** Block 5600–5639 has already been used and its per-episode numbers are known —
they are the table above. This pre-registration therefore cannot be blind to the effect size,
and does not pretend to be. Three consequences are accepted:

1. the criterion is stated as a *fraction*, so it does not inherit the old block's scale;
2. the new block is fresh (5184–5195 / 5640–5699) and its numbers do not exist yet;
3. the reported result may confirm, but can never be the first sighting of, this effect. A v2.1
   pass licenses a model experiment; it does not establish the effect independently of v2.

## The two changes, and why each is allowed

**Change 1 — endpoint becomes conditional.** The quantity of interest is what the pair
information buys *when a transposition is present*. Averaging over clean episodes answers a
different question ("is your benchmark usually broken?"), and dilutes by design.

**Change 2 — `q = 1.0`.** With a conditional endpoint, `q` no longer enters the estimand; it
only decides how many informative episodes a fixed budget of seeds buys. At `q = 0.5`, forty
episodes yield twenty affected ones, and the paired-delta standard deviation measured on the
spent block is 0.687, which needs about 41 episodes for 80 % power at a 0.5 recovery. Sixty
episodes at `q = 1.0` gives 60, and about 90 % power. Nothing else about the mechanism changes;
v2.1 is the same sampler with the transposition always on, which is a stated limitation as well
as a power decision: **v2.1 says nothing about how often order errors occur.** The real
correction set cannot answer that either, since it contains only records a human chose to
correct.

No other number moves: same clocks, same gaps, same `p_catch`, same budgets, same graph
generator, same mechanism `M2′`, same sign convention.

## Primary endpoint

For each episode `e`, with `marginal`, `truth_reader` and `oracle` sink errors at K = 8:

```
recovery(e) = (marginal(e) - truth_reader(e)) / (marginal(e) - oracle(e))   where the
denominator > 0; episodes with no oracle-readable gap are dropped and counted
R = mean over kept episodes, with a 2000-resample bootstrap CI over episodes
```

`oracle` sees the hidden source-error vector and is evaluation-only. It is the strongest
reference that exists in this repository, so `R` is "how much of everything knowable the pair
information alone recovers", and it is comparable across blocks in a way raw sink errors are
not.

## Predictions

| # | prediction | verdict rule |
|---|---|---|
| H1 | the pair information recovers at least half of the oracle-readable gap: `R ≥ 0.50` | `holds` if `R ≥ 0.50` and the CI lower bound > 0.25; `contradicted` if the CI upper bound < 0.50; `inconclusive` otherwise |
| H2 | the recovery does not come from repairing the symptom: `symptom_reader − marginal ≥ 0` on the same episodes | reported with its CI; `contradicted` if the CI upper bound < 0 |
| H3 | the mechanism is still not locally solvable on the fresh block: node-level AUC ≤ 0.65 and order-pattern AUC ≥ 0.75 | same two-sided rule as v2's G1a / G1b |
| H4 | (descriptive, no verdict) the oracle-readable gap itself: `marginal − oracle`, in sink errors | reported so a reader can see the size of the prize next to `R` |

## What each outcome means, fixed before the numbers

| H1 | consequence |
|---|---|
| holds | the order channel is worth building on: a label-free representation experiment gets its own pre-registration, with `truth_reader`'s recovery as the number to approach and `pair_residual` as the hand-built relational baseline to beat |
| contradicted | the pair information is real but not convertible into better decisions at this budget; the line closes, and the real-data `order_error` observation is recorded as *not reproducible in this environment* rather than as an open problem |
| inconclusive | reported as inconclusive with the CI; no new block is spent on the same question without a stated power argument |

H2 is the one that matters for honesty: if repairing the *symptom* is as good as repairing the
*upstream segments*, then the environment does not need a relational state — the defect is
actionable at one node and the whole line is a detour. v2 measured this at 1.143 vs 1.048 and
the sign was against the symptom; if it flips on a fresh block, the relational framing loses.

## Frozen settings

| constant | value |
|---|---|
| `q` | **1.00** |
| episodes | 60, seeds 5640–5699 |
| graphs | 12, seeds 5184–5195 |
| budgets | K = 8, `real` |
| `p_catch` | 0.90 |
| policies | `marginal`, `truth_reader`, `symptom_reader`, `oracle` |
| CIs | 2000 bootstrap resamples over episodes |
| sign convention | **policy − comparison**; positive means more sink errors |
| AUC split | 5 folds over episodes |

## Limitations, stated in advance

- `real` only. `ticket` failed v2's G1a (0.986) because a three-segment chain has one eligible
  pair, and it is not retested here.
- The endpoint is conditional on a transposition, so a reader may not read `R` as "how much
  this would help in production".
- `truth_reader` is a heuristic ceiling, not an optimal policy: it reviews the misplaced
  segments in chain order and then falls back to `marginal`. `oracle` is greedy on the marginal
  score with hidden truth. Neither is the POMDP optimum, so `R` can exceed 1 or fall below 0
  legitimately, and both cases are reported as measured.
- Still no encoder. This file licenses one; it does not run one.

## Non-negotiables

1. The endpoint is read once, on 5640–5699, and no parameter above moves afterwards.
2. If `H1` is contradicted, the answer is final for this mechanism; a third variant of the same
   mechanism would need a different argument, not a different threshold.
3. Blocks 5184–5195 and 5640–5699 are spent by this file whether or not it passes.
4. `outputs/ordered-gate-v2/` is not edited. v2.1 writes to its own directory.
