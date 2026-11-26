# Blind reimplementation protocol — v2 (as executed)

This directory holds a **clean-room reimplementation of `role4_controls/run_controls_v2.py`**, written to
test what `role4_controls/reproduce.py` cannot test: that the v2 numbers follow from the *written*
specification, not only from the author's code. The v1 clean room (`../role4_independent/`) covers the
v1 layer; this one covers the amendment — `rewire_order`, the ten draws, the three-level verdict and
the 20 % margin.

## Setup

A fresh agent session was started with an isolated working directory and this read whitelist:

- `role4_controls/README.md` — the specification: the v1 rule, "v2 — frozen before outcomes
  (amendment)", "v2 confirmation on a fresh block";
- `role3 improvement/dag_role3/**` — the frozen environment, imported read-only;
- `role3 improvement/outputs/v3/benchmark_role3.csv`, `role4_controls/results/controls.csv` — the two
  row-level anchors;
- the two target summaries (`results/v2/controls_v2_summary.csv`, `results/v2_confirm/…`) — **only at
  the comparison stage**, after both blocks had been computed and written.

Explicitly forbidden: `run_controls_v2.py`, `run_controls.py`, `reproduce.py`, `diagnostics.py`,
`reviews/role4_independent/**` (so the two clean rooms stay independent of each other), any other file
under `results/v2/` or `results/v2_confirm/`, and any `results/*.md`. Ambiguities had to be resolved
from the specification and recorded in `NOTES.md`.

The environment was **not** reimplemented: both sides import `dag_role3` unchanged. `interval` was
copied from `role3 improvement/run_benchmark.py`, which the specification names as its source.

## Deliverables (as specified)

1. `core.py`, `runner.py` — deterministic; hard gates: `intact` must equal `benchmark_role3.csv` and
   `flatten` / `rewire_index:0` must equal `controls.csv`, **errors and action strings**, or the run
   writes nothing.
2. `out90000/`, `out7100/` — `rows.csv` (row-level), `summary.csv`, `gate_report.txt`.
3. `NOTES.md` — every ambiguity, the reading chosen, and which conventions were pinned to the target
   file's shape.

## Verification

| check | result |
|---|---|
| `intact` vs `benchmark_role3.csv` (1500 rows, errors + actions) | 0 mismatches |
| `flatten` vs `controls.csv` (1500 rows, errors + actions) | 0 mismatches |
| `rewire_index:0` vs `controls.csv[rewire]` (1500 rows, errors + actions) | 0 mismatches |
| rewire invariants (48 family × seed × rule × draw checks) | all pass |
| summary cells outside `rewire_order` (675 per block) | 675 / 675 identical |
| summary cells inside `rewire_order` (135 per block) | 87 / 135 identical; six rows differ by ≤ 1.9 errors |
| verdict labels, both blocks | 54 / 54 |
| primary labels (11 cells), both blocks | 11 / 11 |

The six differing rows are the `marginal` and `structural` cells under `rewire_order` on modular, BA
and ER — i.e. the rule whose random-order detail the specification does not pin down. What that means
for the write-up is in `../role4_controls_v2_cleanroom.md`.

## Running it

`REPO` in `core.py`, `runner.py`, `compare.py` and `gate_report.py` is an absolute path to this
checkout; adjust that one constant elsewhere. Then

```bash
python runner.py --start-seed 90000 --jobs 6 --out out90000
python runner.py --start-seed 7100  --jobs 6 --out out7100
python gate_report.py out90000 && python compare.py
```

The committed `out*/` files are the outputs of the runs recorded in `NOTES.md` (629 s and 664 s, six
processes). `rows.csv` is kept so that the gates can be recomputed without re-running the episodes;
`exp_*.py` are the discarded probes of alternative `rewire_order` readings.
