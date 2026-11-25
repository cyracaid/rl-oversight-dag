# Pre-registration — an order-aware benchmark (v2), and whether the dominant real-data failure mode exists in it at all

Frozen 2026-11-25, before any implementation and before any run. Blocks: **graphs
5160–5183, episodes 5600–5639** (12 graphs per family, 40 episodes). Registered in
`BENCHMARK_SPEC.md` §3 before a line of v2 code exists.

This file prices a *benchmark*, not a model. No encoder, no training, no labels-as-input
appears here. If the gate below passes, the model experiment gets its own pre-registration
on its own block; if the gate fails, the line is written down as closed.

## Why this file exists

The contrastive pilot (`PREREGISTER_CONTRASTIVE.md`, `CONTRASTIVE_PILOT_CN.md`) came back
negative, and its correction (`outputs/contrastive-v1/diagnostic.json`) removed the
explanation the first draft of the report used. What survived is narrower and less
comfortable:

- the augmentation erased the only informative column, which is a bug in the design, and
- **the simulator cannot host the question at all**, because the failure mode we actually
  observed in human corrections does not exist in it.

The second half is the one worth paying for once. Either the failure mode can be built —
and then the whole representation line has a testbed it never had — or it cannot be built
in a way any policy could act on, and the line is closed with a reason instead of an
excuse.

## What the real corrections are (facts, no inference)

From `runs/replay-manual-corrections/results.json` (75 rows, 53 replayed, 36 participants):

| fact | value |
|---|---|
| error types | `order_error` 40, `bed_sleep_diff_error` 3, `awake_getup_diff_error` 2, `sleep_awake_equal_error` 1, unlabeled 7 |
| reviewer's top suspicion was on a genuinely wrong node | **53 / 53** |
| sink errors after one root review | **0.0** |
| wrong nodes per record (of 21) | 5.92 on average |
| sink errors before the correction | 1.53 on average |

Three of these constrain the design jointly, and each rules out one convenient story:

1. Top-1 suspicion was never wrong, so the human failure is **not** "ranked the wrong node
   by its own anomaly". A node-level anomaly score is not where they lost.
2. One root review cleared every sink error, so the failure is **not** many independent
   defects. It is one defect with a large downstream fan-out.
3. 40 of 53 are `order_error`, applied to adjacent segments of one night, so the defect is
   a **pair whose recorded order is impossible**, where either member would be plausible
   on its own.

The structure to build is therefore: two adjacent segments, individually plausible, jointly
inconsistent, exactly one of them the culprit, and fixing the wrong one costs the budget
without repairing the derived value.

## Why the cheap mechanism is rejected before implementation

**Candidate A — swap the Bernoulli flags.** Take two adjacent segment nodes and swap their
`source_errors` entry and their `confidence` entry. Cost: about ten lines. Rejected, and the
reason is recorded *here, before any code*, so that it cannot later be presented as a
post-hoc excuse:

> After the swap the wrong flag and its confidence signature move together. The anomaly
> stays co-located with the defect, so a node-level score still finds it, and the expected
> value of the two candidate reviews is symmetric by construction. The mechanism produces
> regret that no policy can avoid and decision headroom of zero — a null by design. A null
> obtained from a mechanism built to be undetectable is not evidence about representation
> learning, and reporting it as one would be the same error the pilot's first draft made.

Candidate A is therefore not run. It is the reason we may not, later, blame the augmentor
for a v2 null.

**Candidate B — the order channel (M2, adopted below).** Make the culprit identifiable
*only* through the pair relation: individually plausible clocks, a violated monotone
constraint between them, and one member consistent with its other neighbour. Then the
decision has value and the value sits in the pair.

## M2 — the order channel

> **Superseded in part by the Amendment at the end of this file.** The amendment was
> written the same day, after the analytic check below and before any sampler code or any
> episode on the reserved block. The original text is kept rather than edited, so the
> defect can be read in the form it was committed.

Scope is deliberately small: **7 of the 21 nodes** in `real` and 5 of 21 in `ticket`.
Everything else keeps v1 semantics, unchanged, bit for bit.

| family | segment nodes (chain) | derived nodes |
|---|---|---|
| `real` | `time_bed` 0, `time_sleep` 1, `time_awake` 2, `time_getup` 3 | `bed_sleep_diff` 8, `sleep_awake_diff` 9, `awake_getup_diff` 10 |
| `ticket` | `ticket_created_at` 0, `first_response_at` 1, `resolved_at` 2 | `response_minutes` 9, `resolution_minutes` 10 |

Per episode:

1. Sample clock values in minutes along the chain, increasing by construction:
   `t_0 ~ U(lo, hi)`, and each `t_{i+1} = t_i + d_i`, `d_i ~ U(lo_d, hi_d)` with the
   constants frozen in the table at the end of this file. Derived node values are the
   adjacent differences, `t_{i+1} - t_i`, so the monotone constraint *is* the semantics:
   a negative difference is an impossible record.
2. With probability `q`, one eligible adjacent pair `(i, i+1)` is **transposed**: the two
   recorded clocks are exchanged, so `t'_i = t_{i+1}` and `t'_{i+1} = t_i`. Both remain
   inside the plausible range for a segment of that type. The pair now violates monotonicity
   and one derived difference is negative.
3. Eligible pairs are those where the culprit is uniquely recoverable: member `i` is
   inconsistent with `t_{i-1}`, member `i+1` is inconsistent with `t_{i+2}`. A pair at
   either end of the chain has only one such neighbour, and the pair where both members are
   equally consistent with their outer neighbours (chain of length 2) is **excluded from the
   eligible set**. The discriminating information must be genuinely pairwise and
   non-degenerate, or the mechanism is Candidate A wearing a clock.
4. Public observation gains exactly three things per segment node and one per adjacent pair:
   the recorded clock, and the monotone residual `t_i - t_{i+1}` for each adjacent pair, plus
   the derived difference (already present as the derived node). Hidden, as always: which
   member of a transposed pair is the culprit.

Transition rule (declared deviation from v1, on the record): reviewing a segment node, if it
is the culprit, catches with `p_catch = 0.9` and re-derives its clock from its *other*
neighbour, which repairs the derived difference. If it is the innocent member, the review
catches nothing, the derived difference stays wrong, and only the belief updates — v1
semantics for a miss. So the pair choice carries value, and the value exists only through
the pair relation.

## Families, labels, guardrails

- v2 is a **new family label**: `real_order`, `ticket_order`. `real` and `ticket` keep their
  v1 meaning, so no committed number is reinterpreted.
- **Bit-identity guard:** with `q = 0` the sampler must return episodes identical to v1 for
  the same seed, asserted by test on `(source_errors, confidence, review_uniforms,
  edge_coins, edge_probs)` tuple equality. Any drift fails the test suite, not a review.
- Nothing under `outputs/` is edited. `PREREGISTER_*` files and frozen result reports stay
  as they are; v2 lands as new files plus a `BENCHMARK_SPEC.md` row.

## Baselines, all on v2, all frozen

| baseline | what it sees | why it is in the table |
|---|---|---|
| `marginal` | node scores only (v1 rule, extended observation) | the incumbent. Within a transposed pair the two members are symmetric under this score, so it is expected to coin-flip the culprit |
| `pair_residual` | node score times the sign of the owning edge's monotone residual | a hand-built **relational** heuristic. This is the number a learned state has to beat to be worth anything |
| `truth_reader` | which member of the transposed pair is the culprit | ceiling for the value of the pair information. Not deployable; it exists to bound the prize |
| `dp_v2` | exact optimum of the mean-field model with the transposition prior marginalised over sites | reported, but **not** treated as a ceiling: the DP does not condition on pair consistency, so its optimum is a lower bound on the value of ordering. `truth_reader` is the ceiling |

## Gate — read before anything else is run

| # | prediction | verdict rule |
|---|---|---|
| G1 | the culprit is identifiable from public features alone: AUC of "which member of the transposed pair" holds ≥ 0.70 on held-out episodes, `real`, both members pooled | `holds` if ≥ 0.70, `contradicted` if < 0.60, otherwise `inconclusive` and the line stops until a bigger block is argued for |
| G2 | the pair carries decision value: `truth_reader − marginal` ≥ **0.15** sink errors per episode at K = 8 on `real` | `holds` if ≥ 0.15, `contradicted` if the 95 % CI upper bound < 0.15, otherwise `inconclusive` |
| G3 | negative control: with clocks only and `confidence_mode="noise"`, G1's AUC falls to ≤ 0.60 | `contradicted` if > 0.60, which **voids** the v2 numbers rather than reporting them |

0.15 is chosen a priori and is not a round number chosen for convenience: v1's entire DP
headroom on `real` at K = 5 is **0.030 sink errors per episode (4.2 %)**, which is below the
resolution of forty episodes. A testbed that cannot leave five times that much room is not a
testbed, and building it would only add a fifth null to a list that already has four. The
threshold is written here so that it cannot be moved after the measurement.

## What each outcome means, decided before the numbers exist

| G1 | G2 | reading | consequence |
|---|---|---|---|
| pass | pass | the testbed exists: an order failure mode that is observable and that a policy can get right or wrong | the representation experiment gets its own pre-registration on a fresh block; `pair_residual` is the baseline to beat |
| pass | fail | order errors are visible but carry no decision value at this budget | the real-data failure is a **labelling** problem, not a policy problem; the representation line closes, and the report says so in one sentence rather than three pages |
| fail | — | the channel is not observable from public inputs | stop. Reported as a negative benchmark-building result, with the AUC and the mechanism named |
| — | G3 fail | the mechanism leaks through a channel we do not control | v2's numbers are **void**, reported as void. Not a result |

## Frozen constants

| constant | value |
|---|---|
| `q` (one transposition per episode) | **0.50** |
| clock start `t_0` | `U(1200, 1560)` minutes |
| segment durations `d_i` | `U(20, 480)` minutes, one draw per gap |
| value noise added to the recorded clock | `N(0, 8)` minutes, clipped to ±30 |
| `p_catch` | 0.90 (unchanged from v1) |
| budgets | `real_order` 8, `ticket_order` 8 |
| episodes | 40 per family, seeds 5600–5639 |
| graphs | 12 per family, seeds 5160–5183 (same convention as `exact_dp.py`) |
| CIs | 2000 bootstrap resamples over episodes |
| sign convention | **policy − comparison**; positive means more sink errors |

`q = 0.5` is a round number picked before measuring, on the reasoning that half the episodes
carrying one transposition keeps the transposition share of errors well above the 4 % of
records the real correction set shows — the real set is *corrected* records only and cannot
speak to how often the failure occurs. Sensitivity at `q ∈ {0.25, 0.75}` may be reported as
a property of the generator. It **may never be used to select `q`**: if `q = 0.5` fails the
gate, the primary verdict is a failure, and a passing `q = 0.75` is reported as a footnote
that does not overturn it.

## Limitations, stated in advance

- 7 of 21 nodes carry the order channel in `real` (5 of 21 in `ticket`); the rest stay
  independent Bernoulli. v2 is a
  probe for one mechanism, not a realistic pipeline.
- One transposition per episode, and only between two members. Real corrections show up to 8
  wrong nodes per record, so v2 understates the combinatorial part of the real problem.
- `truth_reader` is an optimist's bound: it knows the pair, which no deployable policy knows.
  A large `truth_reader − marginal` proves the information is valuable, not that it is
  recoverable by any particular learner.
- v2 says nothing about N = 500, nothing about the `ba` / `er` / `modular` / `spike`
  families, and nothing about tickets beyond the two timestamp triples named above.
- If G2 fails on `real` at K = 8, that is a statement about this budget and this graph. It is
  not a proof that order errors are worthless in general, and the report must not phrase it
  that way.

## Non-negotiables

1. The gate is read before any model is trained on v2. No exceptions, no "quick look".
2. No parameter in the frozen table moves after the gate is read.
3. Every outcome, including the ones that close the line, is written into
   `BENCHMARK_SPEC.md` and the course report.
4. Blocks 5160–5183 and 5600–5639 are spent by this file whether or not v2 ships.

---

# Amendment, 2026-11-25 — M2's eligible-pair rule is degenerate; mechanism revised to M2′

Written after implementing the sampler's specification on paper and before writing sampler
code, before any episode was drawn from 5600–5639, and before any gate number existed. No
result is being reinterpreted; a design defect was found and is being recorded where it can
be read.

## What was found

M2 restricted the transposition to *adjacent* members `(i, i+1)` and justified itself with
the claim that "member `i` is inconsistent with `t_{i-1}` and member `i+1` with `t_{i+2}`".
That claim is false. Transposing two adjacent elements of a monotone sequence changes exactly
one constraint — the one between them — and leaves both members consistent with their outer
neighbours *and* inside the plausible range:

```
true chain   [10, 400, 430, 700]
recorded     [10, 430, 400, 700]      transpose (1,2)
violated     only (430, 400)
outer checks member 1: 10 < 430  ok      member 2: 400 < 700  ok
```

So the culprit is localisable only by asking "is this clock plausible for *this position's
type*" — a per-node feature — or not at all. That is Candidate A's defect one layer up: the
mechanism would either be solvable by a node-level score, or be a coin flip. M2 as frozen
could not have produced the evidence it was written to produce, and a null from it would have
been a null by construction for the second time in the same week.

## M2′, the revised mechanism

A transposition is over two chain positions at distance **≥ 2**, chosen uniformly among
eligible pairs `(i, j)`, `j ≥ i + 2`, restricted to chains of length ≥ 4 (`real` qualifies,
`ticket`'s triple qualifies at distance 2 only, and is reported as the smaller case).

```
true chain   [10, 400, 430, 700]
recorded     [10, 700, 430, 400]      transpose (1,3)
violated     (700, 430) and (430, 400)
```

Every recorded value is still inside the plausible range and still plausible for the position's
type, and **no single node is locally anomalous**: position 1 holds a large value that a large
sleep segment could legitimately hold, position 3 holds a small value a short segment could
hold. What identifies the two misplaced positions is the *rank pattern across the chain* —
the misplaced values are the ones whose removal restores monotonicity with the fewest changes.
That is a comparison between nodes, not a property of one, which is exactly the structure the
pilot failed to reach.

Transition, unchanged in spirit: reviewing a misplaced node re-derives its clock from the
monotone fit of the remaining chain, catching with `p_catch = 0.9` and repairing the derived
differences that involve it. Reviewing an innocent node catches nothing (v1 miss semantics).
Two nodes per transposed episode are misplaced, so the budget trade-off is real.

## Revised gate — strictly stricter, not looser

| # | prediction | verdict rule |
|---|---|---|
| G1a | the signal is **not local**: AUC of "is this node misplaced" from per-node public features only (own clock, own adjacent residuals, own confidence, own belief) ≤ 0.65 | `contradicted` if > 0.65 — the mechanism would be Candidate A again, and the benchmark would prove nothing about relational state |
| G1b | the signal **is** global: AUC of the same question from the chain's rank pattern (positions' ranks, longest-monotone fit residuals) ≥ 0.75 | `contradicted` if < 0.75 — the mechanism would be undetectable, and no policy could win |
| G2 | `truth_reader − marginal` ≥ 0.15 sink errors per episode at K = 8 on `real` | unchanged |
| G3 | negative control with `confidence_mode="noise"`: G1a stays ≤ 0.65 and G1b stays ≥ 0.75 | unchanged in intent; a shift *upward* in G1a voids the numbers |

G1 is now a two-sided test, because the failure has two directions: a mechanism that is
locally solvable proves nothing about relational state, and a mechanism that is unobservable
proves nothing about anything. The original single-sided G1 could not tell them apart.

## What is unchanged

`q = 0.50`, episode seeds 5600–5639, graph seeds 5160–5183, budgets, `p_catch`, the clock and
duration constants, the sign convention, the bit-identity guard, the four-outcome reading
table (with G1 replaced by G1a ∧ G1b), and every non-negotiable. The 0.15 threshold in G2 is
untouched and was not revisited while writing this amendment.

The `ticket` case is kept and reported separately rather than dropped: its chain has length 3,
so the only eligible distance-≥2 pair is `(0, 2)`, and a single pair per episode is a weaker
version of the same mechanism. If `real` and `ticket` disagree, both are reported.

---

# Amendment 2, 2026-11-25 (same day, after v2.1) — the gate's AUCs were unconditional; v2 is withdrawn as a relational testbed

Written after the v2.1 gate was read on its own fresh block, on spent blocks, with no new
sampling. This amendment records that the numbers this file's gate produced do not mean what
this file said they would mean, and withdraws the claim rather than the numbers.

## What was wrong with the gate's definitions

The gate pooled AUC over every node row of every episode, while only half the episodes
contained a transposition. A pooled AUC in that situation answers "is this episode damaged"
as well as "which position is misplaced", and cannot separate them. Splitting the two
(`outputs/ordered-gate-v2/locality.json`):

| feature set | pooled AUC (as read) | within-episode AUC, affected only | clean-vs-transposed AUC |
|---|---:|---:|---:|
| node-level (G1a) | 0.599 | 0.512 | 0.767 |
| order pattern (G1b) | 0.822 | 0.500 | 1.000 |

Neither feature set ranks positions inside an episode. G1b is worse than uninformative: the
feature vector is broadcast, so there is one distinct row per episode and the 0.822 is pure
incidence detection. G1a's 0.599 is the same leak, smaller. **Both `holds` verdicts are void.**

## What was wrong with the mechanism

A single transposition of a monotone chain has its two exchanged positions exactly at the
endpoints of the inverted interval, so first-descent / last-ascent — each node's own two
adjacent residual signs — recovers the pair exactly: 21/21 at `q = 0.5`, 60/60 at `q = 1.0`,
across all three eligible pairs. M2′ is locally solvable. That is the property this file
rejected Candidate A for, and the gate reported the opposite because it was not measuring it.

## What this file now claims, and what it does not

- withdrawn: "the defect is invisible to a single node's own features, and visible in the rank
  pattern". There is no such evidence, and there is direct contrary evidence.
- withdrawn: the same-day Amendment's statement that distance-≥2 "leaves no single node locally
  anomalous". Each single node's *value* is plausible, but the localisation never used the value.
- unchanged: G2's paired number (−0.100) and v2.1's paired numbers, which do not depend on the
  AUC definition. Their interpretation changes from "the relational channel does not pay" to
  "a locally solvable channel does not pay", which says nothing about relational state.
- unchanged: blocks 5160–5183, 5600–5639 and 5184–5195, 5640–5699 are spent. No number here is
  re-derived from them, and no future file may use them to price a new mechanism.

## The rule adopted, which is the actual output of this episode

Any quantity about a defect that affects only some episodes is computed **inside the affected
episodes**, and reported next to its unconditional version rather than instead of it. This is
the third appearance of the same error in this line — G2's endpoint, G1a, G1b — and it is now
written into `BENCHMARK_SPEC.md` §3 as a reading rule.

## What a next mechanism would have to satisfy

`k ≥ 2` disjoint transpositions, so the inverted interval no longer names the culprits and the
answer is a minimum-removal / longest increasing subsequence problem. It must ship with a test
that the descent-ascent rule **fails** on it (accuracy well below 1), and its gate must report
within-affected-episode AUC as the primary number. Neither is written yet; nothing is reserved.

---

# Amendment 3, 2026-11-25 — the condition set by amendment 2 is met by a mechanism that is still solved, so v3 is not built and this line closes

Written before any v3 code, with no block spent and no episode sampled.
`role3 improvement/outputs/ordered-v3-design/DESIGN.md` holds the study; the numbers are in
`mechanisms.json`.

Amendment 2 said a next mechanism must be `k ≥ 2` disjoint transpositions and must ship with a
test that the descent-ascent rule fails. Both are satisfiable, and both were about to be
satisfied:

| mechanism (n = 4, 4000 draws) | descent-ascent | interval ends | rank − index |
|---|---:|---:|---:|
| one transposition (v2) | 1.000 | 0.836 | 1.000 |
| **two disjoint transpositions (planned v3)** | **0.000** | 0.327 | **1.000** |
| rotation of a subarray | 0.601 | 0.601 | 1.000 |
| one element moved by one place | 1.000 | 1.000 | 1.000 |

The rank column is not a rule of thumb. Let the truth be strictly increasing and the record a
permutation of the same values with no ties; then position `p` is misplaced iff
`rank(c_p) ≠ p`, because a value in its own position is by definition the `p`-th smallest and
conversely. Three lines, no search, exact for **every** permutation mechanism, including ones
not yet invented. Measurement noise at the sampler's own settings does not dent it (0.998–1.000).

So the requirement amendment 2 wrote was the wrong requirement, in the same way v2's gate tested
the wrong solver: it forbade one cheap rule where a cheaper one exists. The correct requirement —
"no statistic computed in one pass over the chain recovers the culprit set" — cannot be met by
any permutation mechanism at all, by the claim above.

## What this file now requires, and what it withdraws

- withdrawn: "`k ≥ 2` disjoint transpositions" as the recommended next mechanism, and the test
  criterion attached to it.
- withdrawn: the framing that this line is held open by an unbuilt v3. It is not open.
- adopted: an order defect on a monotone chain is **information, not latent structure** — a
  permutation to be inverted, plus an offset that shows up as two adjacent difference
  inconsistencies. Both are one-pass statistics. A representation-learning question cannot live
  here.
- adopted: the only route that would keep the question alive is corrupting the derived
  differences so that the one-pass statistics stop being sufficient. That is a robust-estimation
  benchmark with a new family, a likelihood model and a different question, and it is *not* "the
  real data's failure mode in this simulator". Nothing is reserved for it.

**No block is spent by this amendment.** Graphs 5196–5199 and 60030–60099 and episodes
5700–59999 remain free. The line is closed with no further measurement, which is the outcome
`PREREGISTER_ORDERED_BENCHMARK.md` was written to make possible: a mechanism can be rejected
before its numbers exist, and that is cheaper than rejecting it after.
