# Correction — the v2 gate's AUCs measured "is this episode damaged", not "which node is wrong"

Written 2026-11-25, after reading the v2.1 gate, on spent blocks. **This file withdraws the v2
gate reading.** It does not reopen the gate, does not re-run a block, and adds no verdict of
its own.

The commit that introduced the v2 numbers is `19ebb3f`, and its message says the order channel
is "relational and real". That sentence is wrong, and it cannot be edited out of history, so it
is contradicted here.

## What was read

| gate | number as read | frozen rule | verdict as read |
|---|---|---|---|
| G1a not local | node-level AUC 0.599 [0.504, 0.703] | ≤ 0.65 | holds |
| G1b global | order-pattern AUC 0.822 [0.745, 0.894] | ≥ 0.75 | holds |
| G3 noise control | 0.587 | ≤ 0.65 | holds, uninformative |
| G2 decision value | −0.100 [−0.250, +0.025] | ≥ 0.15 | contradicted |

Only half the episodes (21/40) contained a transposition. The AUCs were pooled over all node
rows, which mixes two different questions: *is this episode damaged* and *which of these four
chain positions is misplaced*. Splitting them (`diagnose_ordered_locality.py`,
`locality.json`):

| feature set | pooled AUC (what the gate read) | within-episode AUC, affected episodes | clean-vs-transposed AUC |
|---|---:|---:|---:|
| node-level | 0.599 | **0.512** | 0.767 |
| relational | 0.822 | **0.500** | **1.000** |

Neither feature set answers "which node" at all. The relational set is worse than that: its
feature vector is built once per episode and broadcast to all four positions, so it holds
**one distinct row per episode** (measured: 1, chain length 4). Its 0.822 is the model
separating clean episodes from transposed ones with AUC 1.000 and being unable to say anything
within an episode. G1b was therefore never a test of locality — it was a test of incidence
detection, which no prediction in the pre-registration asked about.

G1a's 0.599 is the same contamination, milder: within affected episodes the node-level score
is 0.512, and its 0.767 clean-vs-transposed component is what carried the pooled number.

## The mechanism is also solvable locally, which both readings said it was not

A single transposition of a monotone sequence has a property that is not an artefact of this
sampler: the inverted interval's endpoints *are* the two exchanged positions. So the classic
rule — first descent start, last ascent end, both read from that node's own two adjacent
residual signs — recovers the pair exactly:

| block | q | exact | pairs sampled |
|---|---:|---|---|
| 5600–5639 | 0.50 | **21/21** | (0,2) ×8, (1,3) ×8, (0,3) ×5 |
| 5640–5699 | 1.00 | **60/60** | (0,2) ×23, (0,3) ×26, (1,3) ×11 |

100 % at both `q`, on every distance-≥2 pair, from two adjacent comparisons per node. M2′ did
not clear the bar the pre-registration set for Candidate A; it failed it, and the gate reported
the opposite because the measurement could not see within-episode ranking.

## What survives, what does not

**Withdrawn**
- G1a "holds" and G1b "holds". Both are void. There is no evidence in this repository that the
  v2 mechanism is invisible to single-node features, and direct evidence that it is visible.
- The framing "the real-data order failure can be built, and in the built version it is
  invisible to a single node's own features and visible in the order pattern" — struck.
- Amendment 1's claim that distance-≥2 transposition "leaves no single node locally anomalous".
  It does leave each *single node's value* plausible, but the localisation never needed the
  value: two adjacent sign comparisons per node suffice.

**Not withdrawn**
- The G2 number itself (−0.100, paired over episodes) is unaffected by the AUC definition.
  What changes is its interpretation: the correct sentence is not "the relational channel does
  not pay at K=8", it is "a *locally solvable* mechanism does not pay at K=8 either", which is
  a statement about this mechanism and says nothing about relational state.
- The `ticket` observation that a three-segment chain has one eligible pair stands, but it is
  now uninformative in the other direction: a local rule solves length 3 trivially, so `ticket`
  failing G1a was a side effect of the same broken measurement, not a length argument.
- The v1 bit-identity guard: unaffected, `q = 0` still reproduces v1 exactly.

## The recurring error, named

This is the third time the same mistake has shaped a number in this line, in three different
places: G2's pooled endpoint (diluted by the 19 clean episodes), G1a (diluted the same way), and
G1b (structurally degenerate). All three are *unconditional statistics over a conditional
effect*. The rule adopted from here, in `BENCHMARK_SPEC.md` §3: any quantity about a defect that
affects only some episodes is computed **inside the affected episodes**, and reported next to
its unconditional version, never instead of it.

## What would have to be true for the next mechanism

A defect whose localisation requires the whole chain. With `k ≥ 2` disjoint transpositions the
inverted-interval property no longer holds and the culprit set is a minimum-removal / longest
increasing subsequence problem, which no adjacent-pair rule solves. Any such mechanism must
ship with a test that asserts the local rule above **fails** on it (accuracy well below 1) —
the same way `tests/test_ordered.py` now asserts, for M2′, that it succeeds.
