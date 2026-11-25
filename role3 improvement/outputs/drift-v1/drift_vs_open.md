# The prohibited loop — drift, measured

Block 5730–5829, p_catch 0.9, policy `v1:p_catch>=0.90:statuses=4:perspectives=6:constructs=2`, pre-registered in `PREREGISTER_DRIFT.md`.

**Verdict: `load-bearing`.** 100 graphs per family, paired, closed − open, 10000 bootstrap draws (seed 20261124).

`closed` is the mapping `AUDIT_POLICY.md` v1 forbids: an unreviewed source feeding a `partial` sink is read as "the reviewers found nothing here", so its belief is multiplied by `1 − p_catch` once per decision, compounding. Nothing else differs between the arms.

| family | errors open → closed | inspected | untouched | uncovered errors | false-inspected | declared share | actions changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| spike | 0.920 → 1.310 | 151 → 38 | 728 → 1122 | 78 → 131 | 14 → 0 | 0.848 → 1.000 | 82/100 |
| modular | 9.540 → 9.470 | 2338 → 1325 | 8720 → 10239 | 780 → 854 | 174 → 93 | 0.818 → 0.902 | 53/100 |
| real | 0.500 → 0.740 | 7 → 0 | 72 → 124 | 48 → 74 | 2 → 0 | 0.960 → 1.000 | 92/100 |
| ticket | 0.330 → 0.880 | 73 → 0 | 79 → 122 | 26 → 88 | 7 → 0 | 0.788 → 1.000 | 100/100 |

## Paired deltas

| family | metric | closed − open | 95 % interval | wins / losses |
|---|---|---:|---|---|
| spike | errors | +0.390 | [+0.160, +0.660] | 13 / 1 |
| spike | untouched | +3.940 | [+3.260, +4.640] | 75 / 0 |
| spike | declared_gap | +0.530 | [+0.250, +0.850] | 18 / 1 |
| spike | false_inspection | -0.140 | [-0.350, -0.010] | 0 / 5 |
| modular | errors | -0.070 | [-0.130, -0.020] | 0 / 6 |
| modular | untouched | +15.190 | [+8.980, +22.080] | 32 / 0 |
| modular | declared_gap | +0.740 | [+0.260, +1.410] | 16 / 2 |
| modular | false_inspection | -0.810 | [-1.480, -0.330] | 0 / 17 |
| real | errors | +0.240 | [+0.110, +0.390] | 16 / 2 |
| real | untouched | +0.520 | [+0.400, +0.640] | 45 / 0 |
| real | declared_gap | +0.260 | [+0.120, +0.410] | 18 / 2 |
| real | false_inspection | -0.020 | [-0.050, +0.000] | 0 / 2 |
| ticket | errors | +0.550 | [+0.390, +0.720] | 34 / 0 |
| ticket | untouched | +0.430 | [+0.310, +0.550] | 49 / 6 |
| ticket | declared_gap | +0.620 | [+0.450, +0.790] | 40 / 0 |
| ticket | false_inspection | -0.070 | [-0.130, -0.020] | 0 / 6 |

## Predictions

| | prediction | outcome |
|---|---|---|
| P1 | worse on ≥ 2 of sleep families (spike/real/ticket) | holds (3 of 3) |
| P2 | declared `inspected` at least halves everywhere | fails |
| P3 | `untouched` rises on all four | holds |
| P4 | uncovered errors rise on ≥ 3 of 4 | holds (4 of 4) |
| P5 | declared share ≥ open everywhere, strictly up on spike and modular | holds |

P2 is the prediction that failed, and it failed in the direction worth naming: declared `inspected` sinks more than halve on `spike`, `real` and `ticket` — to 38, 0 and 0 — but only fall to 1325 of 2338 on `modular` (0.57×, threshold 0.5×). With 2338 inspected sinks before the loop, a 50 % cut is a different demand than on a 7-sink family. The threshold is not moved; the mechanism still shows, just less than predicted on the large graph.

## What the loop actually does

It does not manufacture confidence. `false_inspected` *falls* on the families where it was non-zero, because almost nothing is declared `inspected` any more: on `real` and `ticket` the count goes to zero, on `spike` it drops from 151 to 38, and on `modular` from 2338 to 1325.

What rises is `untouched`, by +3.9 on spike, +15.2 on modular, +0.5 on real and +0.4 on ticket per graph. Writing off an unreviewed source keeps it unreviewed, so coverage is never reached — the frontier starves.

The receipt therefore degenerates toward the `silent` arm from the inside: a delivery that answers "we did not cover that" about everything is not safer than one that overclaims. The deletion test in `outputs/supervisor-v1/` says the question "how much did we miss" has no answer without the receipt; closing the loop creates a second route to the same dead end, at the cost of +0.55 (ticket), +0.24 (real) and +0.39 (spike) additional surviving errors per graph. This is the argument for the prohibition being structural rather than stylistic.

`modular` is the only family where the loop does not raise errors: it slightly lowers them (-0.070, interval [-0.130, -0.020], 0 of 100 graphs worse). This is not the loop helping. With 3 sources the frontier empties early, so rescaling one belief column redirects an order that is nearly arbitrary to begin with: it changes on 53 of 100 graphs and lands marginally better by chance. What does not depend on chance is the receipt: the same family loses 43 % of its declared coverage (2338 → 1325 inspected sinks) while its declared share climbs.

## Replication on the numerically spent block

The same frozen code first ran on graph seeds 5600–5699. That range had already been spent by the ordered-benchmark experiments (as episode seeds, on different graphs), so it cannot carry the confirmatory claim — see `PREREGISTER_DRIFT.md` §2b. It is reported because it exists.

Verdict there: `load-bearing`. Paired errors, closed − open:

| family | Δ errors | 95 % interval | inspected open → closed |
|---|---:|---|---:|
| spike | +0.360 | [+0.170, +0.590] | 101 → 27 |
| modular | +0.050 | [-0.060, +0.190] | 1184 → 758 |
| real | +0.290 | [+0.160, +0.440] | 12 → 0 |
| ticket | +0.410 | [+0.280, +0.550] | 70 → 1 |

Directions agree on the three sleep families; magnitudes do not, which is exactly why only paired deltas are compared and no mean is carried between blocks. `modular` is again the family where the loop leaves the error count alone — there the interval [-0.060, +0.190] contains zero — while its receipt still withdraws: declared `inspected` sinks fall from 1184 to 758 and its declared share climbs from 0.940 to 0.966. No block changes the mechanism.

## Declared errors by depth (descriptive, not pre-registered)

Depth is the longest path in edges from a source to the sink, so the bins are identical under both arms. No prediction was registered here, because the pilot showed the mechanism acts on coverage rather than on per-depth confidence.

| family | depth | sinks | declared errors open → closed | inspected open → closed |
|---|---:|---:|---:|---:|
| spike | 3–5 | 2000 | 78 → 131 | 151 → 38 |
| modular | 1–2 | 186 | 9 → 10 | 149 → 85 |
| modular | 3–5 | 501 | 47 → 55 | 511 → 349 |
| modular | 6–10 | 613 | 74 → 79 | 514 → 383 |
| modular | 11+ | 331 | 650 → 710 | 1164 → 508 |
| real | 1–2 | 100 | 3 → 3 | 0 → 0 |
| real | 3–5 | 100 | 45 → 71 | 7 → 0 |
| ticket | 1–2 | 100 | 13 → 55 | 73 → 0 |
| ticket | 3–5 | 100 | 13 → 33 | 0 → 0 |

## Bound on this claim

* The loop is built by this repository; nothing here is evidence about an external pipeline.
* 100 seeds per family on each of two blocks (confirmatory 5730–5829; 5600–5699 reported as a replication because the ledger had already spent it). Absolute means do not travel; only the paired deltas do.
* The pilot block 5700–5729 is spent and disclosed; no threshold, statistic or family list was changed after it.
* `false_inspected` falling is not a good outcome: it falls because the receipt stopped claiming coverage, which is the failure this file measures.
* `p_catch` is fixed at 0.9. The multiplier `1 − p_catch` is the miss likelihood, not a tuned constant; a different hit rate would change the magnitude, not the mechanism.
