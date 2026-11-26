# Blind reimplementation protocol (as executed)

This directory holds a **clean-room reimplementation** of `role4_controls/run_controls.py`, written to
test a claim `role4_controls/reproduce.py` cannot test: that the committed numbers follow from the
*written* specification, not only from the author's code.

## Setup

A fresh agent session was given a directory containing only:

- `SPEC.md` — a verbatim copy of `role4_controls/README.md` up to the line `## Out of scope`, i.e. the
  v1 protocol: frozen items, the three conditions, the rewire rule, the statistic and verdict table,
  the worst-of-n definition;
- `TASK.md` — the deliverable and the read whitelist reproduced below.

Allowed reads: `SPEC.md`, `role3 improvement/dag_role3/**`, and the two frozen benchmark tables
(`outputs/v3/benchmark_role3.csv`, `benchmark_summary.csv`). Explicitly forbidden: every
`role4_controls/` path in every checkout, worktree and branch, any `git show` of that branch, any
search of the disk for the original implementation, and the internet. Ambiguities had to be resolved
from the spec text and recorded in `NOTES.md`, never by looking at the original code.

The environment was **not** reimplemented — both sides import `dag_role3` unchanged. This tests the
control layer only; it cannot find a bug shared by every user of the environment.

## Deliverables (as specified to the agent)

1. `reimplement.py` — numpy + networkx, deterministic, with a hard gate: `intact` must reproduce the
   frozen rows (errors *and* action sequences) for every shared row, or exit non-zero writing nothing.
2. `out/controls.csv`, `out/controls_summary.csv`, `out/benchmark_worst_of_n.csv`,
   `out/diagnostics.csv`.
3. `NOTES.md` — every ambiguity and the reading chosen.

## Verification

`reviews/role4_controls_recheck.py` re-derives the two anchors and compares the two implementations.
What it found, and what remains unverified, is in `reviews/role4_controls_recheck.md`.
