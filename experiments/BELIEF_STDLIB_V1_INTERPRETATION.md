# Standard-library belief v1: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/belief-stdlib-v1/`). No rerun, no change to the
pre-registered gate (`BELIEF_STDLIB_PREREG.md`).

## Integrity

Source SHA256 of `compare_belief_stdlib.py`, `belief_stdlib.py`, `belief.py` and `spike_active_selection.py` in the saved
provenance match the current files; run commit `c9e5566`. 200 development graphs (seeds 1000-1199), 1,024 particles, budget 16.
Synthetic data only. The numpy original reproduces the earlier matched belief-greedy result (mean residual 1.100).

## Verdict against the pre-registered gate: **not passed** (equivalence); latency met trivially

| part | result |
|---|---|
| **E1** 95% CI of (stdlib − numpy) inside ±0.10 | **Not met**: mean −0.065, CI [−0.175, +0.045]. The upper end is inside the margin, the lower end is not |
| **L1** rank every node, N = 80 within 0.5 s | Met: median 0.0001 s (numpy 0.0001 s) |
| **L1** rank every node, N = 500 within 5 s | Met: median 0.0006 s (numpy 0.0006 s) |

Mean residual sink errors: numpy 1.100, stdlib 1.035. First chosen action agrees on 0.955 of graphs; degenerate observations
0 (numpy) and 1 (stdlib).

## Why E1 failed: the test could not resolve the margin

- Per-graph outcomes are identical on 171 of 200 graphs; 29 differ. The differences are heavy-tailed (−4 to +5) with a standard
  deviation of 0.79, so a 200-graph interval has a half-width of about 0.11, larger than the 0.10 margin before the mean is
  even considered. Achieving a half-width of 0.05 would need about 950 graphs.
- The protocol itself noted that 200 graphs cannot resolve differences much smaller than the margin; it should have computed
  this power before fixing the gate. As written, E1 could pass only by luck.
- The point estimate favours the standard-library version (−0.065), but the interval includes 0 and +0.045, so this is neither
  evidence of equivalence nor of a difference. The estimate does not indicate that the port is worse.
- Two runs of the **same** implementation with different particle seeds would also differ on some graphs; without that
  noise floor, 14.5% differing graphs cannot be read as an implementation effect or as ordinary particle noise.

## Why L1 is a weak pass

The benchmark graphs are four layers deep (the synthetic generator), so every node has few descendants and ranking every node
takes a fraction of a millisecond for both implementations. Real evidence graphs are likely deeper and denser; the gate shows the
port is not slower than the original on these graphs, not that it is fast on realistic ones. One observation costs 4 to 24 ms
for the port (0.3 to 2 ms for numpy), dominated by resampling, which is fine at this scale.

## What this does and does not show

It shows the port runs on every tested graph, matches exact enumeration (unit tests) and the numpy original's mean outcome within
the resolution of 200 graphs, and is not slower at ranking. It does not establish equivalence at the pre-registered margin, nor
latency on deep or large graphs. All earlier caveats about synthetic graphs and development-set results stand.

## Next

A v2 protocol, written and frozen before running: (a) measure the **noise floor** by also running the numpy original with a
different particle seed and require the implementation difference to be no larger than that; (b) use about 1,000 new graphs (not
the reserved confirmation seeds 2000-2199) so the equivalence interval can resolve the margin; (c) benchmark latency on deeper
graphs (12 and 24 layers) with limits set before the run. v1 results stay as they are.
