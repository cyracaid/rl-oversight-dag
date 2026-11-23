# Standard-library belief v2: results and verdict

2026-11-21. Run by the user; this note only reads the saved output (`runs/belief-stdlib-v2/`). No rerun, no change to the
pre-registered gate (`BELIEF_STDLIB_V2_PREREG.md`).

## Integrity

Source SHA256 of `compare_belief_stdlib_v2.py`, `compare_belief_stdlib.py`, `belief_stdlib.py`, `belief.py` and
`spike_active_selection.py` in the saved provenance match the current files; run commit `0e86481`. 1,000 new graphs (seeds 5000-5999;
the reserved confirmation seeds 2000-2199 were not used), 1,024 particles, budget 16, three policy runs per graph. Synthetic data only.
v2 was designed after seeing v1 (stated in the protocol): the sd, the differing share and the 0.05 allowance came from v1's development
graphs, so only this unseen-seed result is new evidence.

## Verdict against the pre-registered gate: **passed**

| part | result |
|---|---|
| **E1** 95% CI of (stdlib − numpy) inside ±0.10 | **Met**: mean −0.012, CI [−0.046, +0.022] |
| **E2** differing share, port vs original, at most reseed + 0.05 | **Met**: port 0.143, reseed 0.147 |
| **L** rank every node, 80 nodes / 10 layers within 0.5 s | **Met**: median 0.000 s |
| **L** rank every node, 500 nodes / 20 layers within 5 s | **Met**: median 0.007 s (numpy 0.007 s) |
| **L** one observation, 500 nodes / 20 layers within 0.5 s | **Met**: median 0.028 s (numpy 0.002 s) |

Mean residual sink errors: numpy 1.079, numpy reseeded 1.073, stdlib 1.067; one degenerate observation each.

## What this shows

1. **The port changes outcomes no more than a reseed does.** The graphs whose outcome differs from the original are 14.3% for the port and
   14.7% for the original with a different particle seed, and the mean differences are −0.012 and −0.006 with overlapping intervals and
   the same paired sd (0.548 and 0.571). The interval is narrow enough to resolve the ±0.10 margin (half-width about 0.034), which v1's
   was not.
2. **Ranking is cheap and scales with depth like the original.** Ranking every node takes 0.007 s at 500 nodes and 20 layers (68 mean
   descendants per node) for both implementations. The port's per-observation cost is about 14 times the numpy original's (28 ms against
   2 ms at 500 nodes), dominated by resampling the particle bitsets, and is far inside the limit.

## Limits

- The deepest tested graphs have 20 layers and about 68 descendants per node on average. Real evidence graphs may be larger or denser; the
  result shows adequate headroom (the ranking limit is 5 s against 0.007 s) but not behaviour on graphs orders of magnitude larger.
- Both implementations were exercised on the synthetic generator only, with the model's assumptions (known edge probabilities and priors).
- A pass does not show that the ranking helps on real evidence graphs; earlier experiments established it only on synthetic development
  graphs, and real node priors and edge probabilities are not calibrated.

## Decision

Dependency decision 0.2 of the OpenSpec change `add-belief-review-ranking` can be taken as **option A: the standard-library port**, and
numpy is not added to the evidence-dag runtime. Integration into the review pipeline (task 2.x) still depends on the open design questions
(selection score source, node-level base error definition) and is not implied by this result.
