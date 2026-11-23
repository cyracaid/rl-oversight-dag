# Propagation recovery: protocol frozen before the full run

Date: 2026-11-21. Status: harness validated by unit tests and a tiny smoke run only.
**No full-run numbers exist and none are asserted here.** The user executes the full runs.

Purpose: decide whether an estimator of edge propagation probability from an audit chain's own
correction records is allowed to touch real records. This is the precondition in the OpenSpec change
`add-belief-review-ranking` (task 1.4; real-record use is task 4.1). Everything is synthetic.

## Discipline (same as `BOUNDARY_PREREG.md`)

Every claim traces to saved raw results, explicit configuration and source hashes. Tables come from
saved JSON. Never hide a failed replicate, choose the best seed, overwrite a run or rewrite a hypothesis
after seeing results. Negative results remain results. **Agents run only `--smoke` and unit tests.**
Each output directory must be new.

## What is simulated

- Layered graphs as in `spike_active_selection.py` (N=80, 4 layers, 1–2 parents) with **three edge
  families**, defined by the child's layer, and known propagation probabilities:

  | family (child layer) | true p |
  |---:|---:|
  | 1 | 0.30 |
  | 2 | 0.60 |
  | 3 | 0.85 |

- Hidden source errors by node type (`P_TYPE`), observed confidence as in the earlier experiments,
  reviewer catch rate 0.9, budget 16 reviews per graph.
- A **review policy** chooses which nodes get reviewed. The log only contains what a real chain could
  record: per review, whether an error was flagged and whether it was **cleared** after re-derivation
  (cleared = the node's own source error; flagged but not cleared = inherited from a parent); for each
  cleared correction and each child, whether the child changed, the child's in-degree, its family and
  whether the child had already been reviewed.
- Policies: `random` (selection-neutral reference), `confidence` (highest posterior error first),
  `blast` (largest downstream sink reach first; the analogue of the current `select_a2_targets` rule).
  Policies share the same worlds in each replicate.

## Estimators (per family)

| id | definition | known weakness |
|---|---|---|
| E0 | changed children / children of corrected nodes | a child can be wrong for other reasons or already reviewed, so it should under-estimate |
| E1 | E0 restricted to single-parent children, divided by (1 − b̂), b̂ = root flag rate / assumed catch | policy selection can change which children were already cleared |
| E2 | E1 restricted to children not reviewed before the correction | relies on the assumed catch rate and on the in-degree-1 stratum being representative |

Posterior: uniform Beta(1,1) on the change rate, 2,000 draws, 95% equal-tail interval; for E1/E2 the
root flag rate is also a Beta posterior and the result is capped at 1.

## Hypotheses and gate (chosen before any full run)

- **H1.** E0 is biased low in every family under `random`.
- **H2.** E2 recovers the truth under `random`: |bias| ≤ 0.05 and 95% interval coverage ≥ 0.90 in all
  three families.
- **H3.** Under `confidence` and `blast`, E1 may be biased by selection; E2 stays within the H2 tolerances.
- **Gate.** The estimator passes only if E2 meets the H2 tolerances in **all three policies and all three
  families**, with mean usable events (`mean_n`) of at least 100 per family. Otherwise the estimator does
  **not** proceed to real records and the OpenSpec task 4.1 stays blocked. If `mean_n` is below 100,
  increase `--graphs` and rerun in a new directory; do not relax the tolerance.

The tolerances are fixed now. They may be revised only before the first full run, and the revision must
be committed with its reason.

## Commands (run from the repository root)

Primary run:

```bash
python3 -u experiments/rl_propagation_recovery.py --out-dir runs/propagation-recovery-v1
```

Exploratory sensitivity runs (not part of the gate; each in a new directory):

```bash
# assumed catch rate wrong (true 0.9, assumed 0.7)
python3 -u experiments/rl_propagation_recovery.py --assumed-catch 0.7 --out-dir runs/propagation-recovery-v1-catch07
# some true changes are not observed
python3 -u experiments/rl_propagation_recovery.py --obs-miss 0.2 --out-dir runs/propagation-recovery-v1-miss02
# true catch rate lower than assumed (true 0.7, assumed 0.9)
python3 -u experiments/rl_propagation_recovery.py --true-catch 0.7 --out-dir runs/propagation-recovery-v1-truecatch07
```

No time estimate is promised. Tiny harness check: `--smoke` (not evidence).

## Reading the output

1. `missing` and `mean_n` first: an estimator with few events or missing replicates is not evidence.
2. Then bias, RMSE and coverage per policy, estimator and family. Quote failures alongside successes.
3. `event_counts` shows how many corrections were cleared versus flagged-but-inherited per policy.
4. Check `provenance` (git status, source hashes) before quoting any number.

## What a pass means and does not mean

A pass means: in this synthetic world, with every child re-derived and changes observed exactly, a
known catch rate and known family structure, the estimator recovers the generating propagation
probability even when review selection is not random.

It does **not** show the estimator works on a real audit chain, where re-derivation may be partial,
observations noisy, families unknown, selection driven by humans and confounding present. Real records are
never used here, never committed, and are processed locally by the data owner only after the gate passes
and the OpenSpec change is accepted.

## Related

- OpenSpec change `add-belief-review-ranking`: tasks 1.4–1.6 and 4.1; requirement "Propagation estimated
  from audit-chain records".
- `SEMANTICS_AUDIT.md`: a review clears the node's own source error; inherited errors persist. This is why
  the log records cleared versus not cleared.
