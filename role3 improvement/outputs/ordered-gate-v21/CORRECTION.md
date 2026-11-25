# v2.1 result — H1 holds, H3 contradicts it, and H3 is the one that decides

Pre-registration: `PREREGISTER_ORDERED_BENCHMARK_V21.md`, frozen before the run.
Blocks: graphs 5184–5195, episodes 5640–5699 (60, `q = 1.0`), K = 8, `real`. Spent by that file.

## Numbers, as measured

| policy | sink errors |
|---|---:|
| `marginal` | 0.933 |
| `truth_reader` | 0.583 |
| `symptom_reader` | 1.117 |
| `oracle` | 0.467 |

| # | prediction | result | verdict |
|---|---|---|---|
| H1 | `R ≥ 0.50` | **R = 0.821** [0.630, 0.964] | **holds** |
| H2 | symptom repair is not the source | **+0.183** [+0.050, +0.350] | **holds** |
| H3 | not locally solvable: node AUC ≤ 0.65, order pattern ≥ 0.75 | node **0.800** [0.718, 0.878], relational **0.500** [0.500, 0.500] | **contradicted** |

## Why H3 decides and H1 does not

H1 says the pair information recovers 82 % of the oracle-readable gap. H3 says that information
is reachable from each node's own adjacent comparisons. Both are true at once, and together they
say: **the recovery does not require relational state.** A two-line local rule (first descent
start, last ascent end) recovers the transposed pair 60/60 on this block
(`outputs/ordered-gate-v2/locality.json`). So `truth_reader`'s advantage over `marginal` here is
"a cheap localisation rule beats a heuristic that ignores order", which is a fair result about
this simulator and no evidence at all about the representation question the line was opened for.

The pre-registration's own outcome table had no cell for this: H1 holds, H3 fails. Read the
conservative way, which is the only way available: **no model experiment is licensed.** A pass on
H1 was written to license one; it was written before it was known that the pairing could
co-occur with an H3 failure, and the failure is the stricter statement.

H2 holding is worth recording separately, because it repeats v2's sign on a fresh block:
reviewing the impossible difference (1.117) is *worse* than the rule (0.933), so the defect is
only repairable upstream. Two blocks now agree on that.

## Three things about this run that must be said

1. **The endpoint's denominator is mostly zero.** 15 of 60 episodes had an oracle-readable gap;
   45 were dropped. The power argument in the pre-registration assumed 60 usable episodes and a
   paired-delta sd of 0.687. The actual estimator ran on 15 ratios, so its CI [0.630, 0.964] is
   wider than the design intended and the "about 90 % power" sentence in that file was wrong at
   the time it was written. The point estimate is not in doubt; the precision claim was.
2. **`run.log` is missing.** The command piped to `tee outputs/ordered-gate-v21/run.log` before
   the directory existed, so stdout was lost. The numbers above come from `gate.json` only. To
   show the rerun is not a second measurement, the script was re-executed on the same block and
   its output compared byte-for-byte: `gate.json` sha256 `5822ee7b…` identical both times.
   Determinism check, not a new sample.
3. **H3's relational number is exactly 0.500 with a degenerate CI**, because that feature set
   has one distinct row per episode (`outputs/ordered-gate-v2/CORRECTION.md`). A number pinned
   at 0.500 by construction does not mean "order carries no information"; it means this feature
   set never varied across positions. Reported as a failed prediction, and the feature set is
   dead.

## Consequence

Not a retry of the same mechanism with a different threshold. `PREREGISTER_ORDERED_BENCHMARK.md`
amendment 2 records the withdrawal and what a next mechanism would have to be: `k ≥ 2` disjoint
transpositions, so that localisation is a minimum-removal problem, shipping with a test that the
local rule fails on it.
