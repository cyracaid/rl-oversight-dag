# Pre-registration — the prohibited loop (drift-v1)

Status: **frozen 2026-11-25, before the confirmatory block.** Confirmatory block **5730–5829** (100 graph
seeds per family); block 5600–5699 was pre-registered here by mistake and ran as a replication (§2b). Code: `role3 improvement/run_drift_check.py` + `dag_role3/drift.py`. Output:
`role3 improvement/outputs/drift-v1/`.

## 1. Question

`AUDIT_POLICY.md` v1 forbids one inference: reading a `partial` sink as evidence that its *unreviewed*
sources are clean. `ENTROPY_LIMITS.md` §8 says the prohibition follows from separation, so it should be
load-bearing rather than stylistic. This experiment tests that by building the loop and measuring it.

Two arms, same policy (`marginal`), same graph, same episode, same budget, same tie-breaking:

| arm | what the machine believes |
|---|---|
| `open` | the shipped layer. The receipt describes the review log; nothing feeds back. |
| `closed` | the prohibited mapping. Every unreviewed source still feeding a `partial` sink has its belief multiplied by `1 - p_catch = 0.1`, **compounding once per decision** while it stays on that frontier. |

The multiplier is the marginal likelihood of a miss under the reviewer's hit rate, not a tuned constant.
Compounding (rather than a single nudge) is what "error accumulation" means: a source that stays
unreviewed is progressively written off.

Nothing else differs. Actions are compared per episode (`identical_actions`), so an inert loop is reported
as inert rather than described as a small effect.

## 2. Pilot, disclosed

A 30-seed pilot ran on block **5700–5729** (now spent) to check that the arms separate at all. It changed
the predictions, so it is recorded here rather than omitted:

| family | errors open → closed | inspected open → closed | untouched open → closed |
|---|---|---|---|
| spike | 0.800 → 0.967 | 61 → 25 | 213 → 331 |
| modular | 8.733 → 8.700 | 948 → 400 | 2269 → 2895 |
| real | 0.567 → 0.767 | 1 → 0 | 26 → 37 |
| ticket | 0.167 → 0.433 | 18 → 0 | 22 → 39 |

The loop is live (actions differ on 6 / 15 / 3 / 1 of 30 episodes per family), and its signature is not the
one `ENTROPY_LIMITS.md` §7 guessed. That section predicted `false_inspection` rising with depth. What
happens instead: the machine withdraws. Declared `inspected` collapses, everything becomes
`partial`/`untouched`, and the declared share climbs toward 1.0 — the receipt degenerates toward the
`silent` arm, from the inside.

§7 of that file is amended in the same commit as this pre-registration, i.e. still before the confirmatory
block. The superseded prediction is kept there as superseded, not deleted.

The pilot's numbers are not quoted as results anywhere. Only direction and mechanism were taken from it;
no threshold, statistic, or family list was changed after it.

## 2b. Block-assignment error, corrected before the confirmatory run

The first draft of this file claimed **5600–5699** as fresh. That was wrong. `PREREGISTER_ORDERED_BENCHMARK.md`
and its v2.1 successor reserved those numbers as **episode** seeds (graphs 5160–5195), and v2.1 used that
block to change `q` and the endpoint. Under this repository's rule — a numeric block is spent once it has
informed a choice — 5600–5699 was already spent before this file was written.

The identical frozen code was nevertheless run once on graph seeds 5600–5699. Nothing had ever generated
graphs at those seeds, so the objects are new, but the block is not, and the run cannot carry the
confirmatory claim. It is kept as **`outputs/drift-v1-blocka/`** and labelled a replication.

**The confirmatory run is block 5730–5829** (the first free block after the pilot), pre-registered here
before it ran. Predictions, thresholds, statistic, family list and code are byte-identical between the two
runs. Because the predictions were frozen before either, the second block is an independent test, not a
second draw at the same target. Two blocks agreeing is reported as the result; if they had disagreed, that
would have been the result.

## 3. Predictions

Threshold `p_catch = 0.9`, budget as in `run_supervisor_check.py`
(spike 16, modular 50, real 8, ticket 8). Paired per graph, 10 000-draw percentile bootstrap, seed
20261124, closed − open. `wins` counts graphs where closed is worse.

| | prediction | rationale, fixed now |
|---|---|---|
| **P1** | `errors(closed) > errors(open)` with the 95 % interval excluding zero on **at least two of {spike, real, ticket}**; `modular` is allowed to be null | the frontier starves only when there are enough unreviewed sources to reorder. `modular` has 3 sources, so the frontier is exhausted in the first decisions and can barely change the order |
| **P2** | the count of sinks declared `inspected` at least **halves** (closed/open ≤ 0.5) on every family | write-offs keep sources unreviewed, so full coverage stops being reached |
| **P3** | `untouched` rises on **all four** families, interval excluding zero | the same mechanism, on the sink side: nothing is covered, so nothing is claimed covered |
| **P4** | uncovered errors (`declared_gap`) rise on **at least three of four** families, interval excluding zero | errors survive in regions the receipt has stopped claiming anything about |
| **P5** | declared share (`declared gap / (declared gap + false inspection)`) is **≥ open on every family, strictly greater on spike and modular** | with false inspection driven toward zero the ratio saturates at 1.0: the receipt says "we did not cover it" about everything, which is the `silent` arm arriving by a different route |

P5 is the load-bearing one. A delivery that withdraws is not safer than one that overclaims — the deletion
test exists because both leave a reader unable to say what was covered. If the loop produces withdrawal,
then the prohibition is protecting the *informational* value of the receipt, not merely its honesty.

## 4. Frozen verdict

```
load-bearing : P1 (>=2 of 3 non-modular) and P3 (all four)
weak         : P3 only
inert        : actions identical on every episode, or P3 fails
```

`load-bearing` is computed from the interval-exclusion test, not from point estimates. A family where the
interval touches zero counts as not holding for that family. No threshold is adjusted after the block.

## 5. What this cannot show

- It is not evidence about any external pipeline. The environment is synthetic and the loop is built by
  this repository.
- It does not show that feedback is always harmful. It shows that *this* feedback — a guarantee read as
  evidence about the object it describes — degrades both the errors and the receipt, which is what
  separation predicts.
- The depth table is descriptive. No prediction is registered for depth, because the pilot showed the
  mechanism acts on coverage rather than on per-depth confidence, and inventing a depth law after seeing
  that would be exactly the retro-fitting this file exists to prevent.
- 100 seeds per family. Absolute means do not travel to other blocks; only the paired deltas do.

## 6. Seed ledger

| block | use |
|---|---|
| 5400–5599 | supervisor-v1 (spent) |
| 5600–5699 | spent by ordered v2 / v2.1 (episode seeds); reused here as `outputs/drift-v1-blocka/`, replication only |
| 5700–5729 | pilot for this experiment (spent, disclosed above) |
| 5730–5829 | **this experiment**, confirmatory |
| ≥ 5830 | free |
