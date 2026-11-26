# NOTES — clean-room reimplementation of role4_controls

Blind reimplementation from `SPEC.md` + `TASK.md` only. The frozen environment
(`role3 improvement/dag_role3`) is imported unchanged; nothing under any
`role4_controls/` path was opened, listed, grepped or read, and no search for the
original implementation was performed.

## Command

```bash
cd /private/var/folders/rw/0p5p9d812dbgk7qw_mxpcfz40000gn/T/opencode/indep_role4
/private/var/folders/rw/0p5p9d812dbgk7qw_mxpcfz40000gn/T/opencode/rlvenv/bin/python reimplement.py
```

Runtime: **223 s wall (3 min 43 s)**, one core, no GPU
(`real 223.12 / user 204.07 / sys 0.82`). Outputs: `out/controls.csv`
(4500 rows), `out/controls_summary.csv` (45 rows),
`out/benchmark_worst_of_n.csv` (36 rows), `out/diagnostics.csv` (808 rows).

`ci_calibration.py` is the throw-away calibration harness used for ambiguity 1
below; it reads only the two frozen benchmark CSVs and is not part of the
pipeline.

## Primary result (marginal; gain = errors(confidence) − errors(policy))

| family | condition | mean gain | 95 % CI | removed vs intact | verdict |
|---|---|---|---|---|---|
| spike | intact | +0.37 | [0.20, 0.56] | 0.00 | survives |
| spike | flatten | +0.09 | [0.03, 0.15] | 0.28 | survives |
| spike | rewire | −0.72 | [−1.07, −0.40] | 1.09 | removed |
| modular | intact | +1.81 | [1.10, 2.56] | 0.00 | survives |
| modular | flatten | +0.01 | [−0.10, 0.13] | 1.80 | removed |
| modular | rewire | −7.15 | [−8.17, −6.19] | 8.96 | removed |
| ba | intact | +9.52 | [4.25, 15.99] | 0.00 | survives |
| ba | flatten | −0.58 | [−0.77, −0.38] | 10.10 | removed |
| ba | rewire | +7.09 | [1.70, 13.54] | 2.43 | survives |
| er | intact | +4.99 | [3.52, 6.61] | 0.00 | survives |
| er | flatten | −0.35 | [−0.48, −0.23] | 5.34 | removed |
| er | rewire | +0.84 | [−0.38, 2.15] | 4.15 | removed |

`real` is uninformative as expected (intact +0.03 [0.00, 0.07]).
Hub-breaking: median Spearman(out-degree original vs rewired) = spike 0.40,
modular 0.05, ba 0.63, er 0.62, real 0.32.
`sink_review_share` (spike, flatten, pooled over all reviews): confidence 0.2362,
structural 0.1556, marginal 0.3088.

## Acceptance gate — PASS

3600 frozen rows, of which **1500 are shared** with this recomputation
(5 families × 100 graph seeds × 3 policies `confidence/structural/marginal`).
All 1500 reproduce **integer sink errors and the exact action sequence**.
The gate runs before any file is written; on failure the script exits 2 and the
`out/` directory is untouched (verified by deleting `out/` first).

Additional selftest: `MismatchEnv` with `view == truth` returns the same errors
and the same action sequence as `run_public_policy` / `OversightEnv`
(30 episodes: 2 seeds × 5 families × 3 policies). The controls path therefore
degenerates to the frozen environment when no mismatch is injected.

## Ambiguities and the reading chosen

1. **The bootstrap CI.** The spec says "copied verbatim from
   `run_benchmark.interval` (seed 411, 20 × 100)" but `run_benchmark.py` is not
   in the readable set. "20 × 100" is read as **2000 replicates** (20 blocks of
   100), and the CI as the 2.5/97.5 percentile of the sorted replicate means
   with `numpy` linear interpolation. Because `benchmark_summary.csv` is a
   permitted read and the spec says the CI is copied verbatim, the exact
   convention was identified empirically (harness: `ci_calibration.py`):

   ```python
   rng = np.random.default_rng(411)
   idx = rng.integers(0, n, size=(2000, n))       # one matrix, reused for every cell
   means = np.sort(values[idx].mean(axis=1))
   lo, hi = np.percentile(means, [2.5, 97.5])
   ```

   This reproduces all 30 frozen paired bounds to < 1e-9 (15 cells:
   structural/marginal/hub × 5 families; the summary's other policies are out of
   scope). `interval()` keeps that form. Note the frozen
   bounds have 5-decimal tails (…975, …025) that no 20-replicate scheme can
   produce; 2000 replicates can, which is the empirical confirmation.

2. **"the sink set is kept" on rewire for modular / BA / ER.** Their sinks are
   derived as "nodes with no children", so keeping parent *counts* alone would
   move the sink set (a sink can acquire a child; a non-sink can lose all of
   them). The spec does not ask to constrain child counts, so the rewired `DAG`
   is built with `sink_override = original sinks`. Spike and real already carry
   an explicit `sink_override`, so every family keeps `graph.sinks` exactly;
   this is asserted per graph. Consequence: on the rewired view a "sink" may
   have outgoing edges — which the `DAG` class explicitly allows ("a named
   conclusion can have outgoing edges to another conclusion") and which
   `sink_reach` already accounts for.

3. **Parent-pool ordering, and parent order inside a node.** The spec pins the
   *sets* a node draws from but not their order, and `random.sample` is
   order-sensitive. Pools are built in ascending node-index order; the sampled
   parents are stored sorted ascending (as `gen_spike`/`_orient_graph` do). One
   independent `random.Random(4_040_000 + graph_seed)` is advanced in node-index
   order; a node with zero parents consumes no randomness. This choice is the
   single most likely source of divergence from the original rewire draws.

4. **"the previous layer" for spike.** Read as the generator's contiguous
   partition rule `min(L-1, i*L//n)` with `L = max(graph.layers) + 1 = 4`,
   i.e. 20-node blocks. For the frozen spike graphs this partition is identical
   to "nodes whose longest-path layer is one less"; the generator's rule is used
   literally.

5. **`flatten` mechanics.** Implemented as truth edge coins all `False`, with
   the view = the true graph and the true (unchanged) edge probabilities. So the
   policy's forward model, belief column and miss update are bit-identical to
   `intact`; only the propagation of errors changes (`effective == source`).
   Source errors, confidences and reviewer uniforms are the frozen ones.

6. **`rewire` mechanics.** `sample_episode(rewired, 20000 + seed)` is called and
   asserted to return *identical* `source_errors`, `confidence` and
   `review_uniforms` (true because each node keeps its parent count, so the RNG
   stream is consumed identically). Truth = `(graph, snapshot)`; view =
   `(rewired, rewired_snapshot)`; only `source_errors` and `edge_coins` of the
   truth are used for propagation. `MismatchEnv` is a line-for-line copy of
   `OversightEnv`'s observation/miss-update arithmetic (including the
   `float32` feature matrix, which matters: `marginal` reads the `float32`
   belief column) with the truth hidden state separated.

7. **Verdict applied to every row.** `verdict()` is applied uniformly to all
   45 (family × condition × policy) rows, including `condition=intact` — where
   it degenerates to `survives`/`no-intact-advantage` with
   `gain == intact gain` — and including `real`, which the spec says is reported
   but not used for the verdict. A `cell` column marks
   `primary` (marginal × spike/modular/ba/er) vs `secondary`.

8. **Rounding in the verdict.** Labels use the unrounded CI bounds; the CSVs
   print 4 decimals. No cell sits close enough to 0 for the two to disagree.

9. **`gain_removed_vs_intact` for `condition=intact`** is identically 0.0
   (same arrays), CI [0, 0].

10. **`diagnostics.csv` layout** is long-format
    (`diagnostic, family, graph_seed, condition, policy, value, n`) because the
    two diagnostics have different axes. Per-graph rows carry the seed;
    aggregate rows use `graph_seed = "median"` (hub_rank_corr, median over the
    100 graphs) or `"pooled"` (sink_review_share, pooled over all reviews).
    Hub out-degree = `len(graph.children[i])`. Spearman uses average ranks for
    ties and is *undefined* (`nan`, blank cell) when either degree vector is
    constant; the median then skips those graphs (none were skipped: all five
    families have variable out-degree).

11. **`p95`** in `benchmark_worst_of_n.csv` uses `np.percentile(..., 95)`
    (linear interpolation), which is what the frozen summary's values such as
    `10.05` and `4.049999…` imply. `worst_of_n` is `graphs_with_any_sink_error /
    100` over **all** policies present in `benchmark_role3.csv` (including
    `none`, `random`, `hub`, `dqn_s*`, `gnn_s*`), as the spec asks; `none` rows
    have no actions and are only used for the worst-of-n groupby.

12. **Not reproduced:** `elapsed_seconds` (wall clock, not requested) and the
    non-shared policies. `episode_seed` is written as `20000 + graph_seed`.

## Determinism

No wall-clock, no global RNG, no threading. Every stream comes from a documented
seed: graph generator `seed`, episode `20000 + seed`, rewire
`4_040_000 + seed`, policy RNG `snapshot.seed + 981` (unused by the three
policies here, passed for fidelity), bootstrap 411. Tie-breaking inside the
policies is `numpy.argmax/argmin` (first index wins), which is the frozen
behaviour; the implementation does not add any tie-break of its own.
