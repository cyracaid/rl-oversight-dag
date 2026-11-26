# v2 controls — clean-room reimplementation (blind)

Source of truth: `role4_controls/README.md` (v1 rule + "v2 — frozen before outcomes"
+ "v2 confirmation"). Frozen environment imported read-only from
`role3 improvement/dag_role3`. No forbidden file was read: not `run_controls*.py`,
not `reproduce.py`/`diagnostics.py`, not `reviews/role4_independent/**`, not any
`results/v2|v2_confirm` file other than the two summary CSVs (read only at the
comparison stage, after both blocks had been computed and written).

Isolated dir: `/private/var/.../T/opencode/v2_cleanroom`. Nothing was written to the repo.

## Files

| File | What |
|---|---|
| `core.py` | rewire_index / rewire_order, `MapMismatchEnv`, flatten snapshot, episode helpers |
| `runner.py` | per-graph conditions, gates, aggregation, verdicts, summary writer |
| `finalise.py` | re-aggregation from `rows.csv` (used once, for the aggregation conventions only) |
| `gate_report.py` | independent gate verification recomputed from `rows.csv` |
| `invariants.py` | parent-count / type / sink / shared-episode invariants of both rewires |
| `compare.py` | cell-by-cell comparison with the two target summaries |
| `exp_*.py` | discarded probes of alternative `rewire_order` readings |
| `out90000/`, `out7100/` | `rows.csv` (row-level), `summary.csv`, `gate_report.txt` |
| `mismatch_report.txt` | full comparison log |

Run: `python runner.py --start-seed 90000 --jobs 6 --out out90000` (and `--start-seed 7100`).
Runtime: 629 s (90000 block) and 664 s (7100 block) wall, 6 processes, CPU only.

## (a) What I had to interpret or guess

1. **Mismatch environment (`MapMismatchEnv`).** Subclass of the frozen `OversightEnv`:
   hidden state (`_base`, `_effective`, flags, reward, `final_audit`) on the **true** graph
   with the true edge coins; every structure-facing observation field (edge index, edge
   probabilities, topological order, sink ids, `sink_reach` feature, forward
   "public error probability" feature) from the **view**. Source errors, confidences and
   reviewer uniforms are the shared episode. Interpretation choice: the miss-branch
   belief update (`_belief_base[a] = q(1-p_catch)/(1 - p_catch * effective_risk)`) uses the
   **view** forward proxy, because that quantity is an observation-side feature the policy
   plans on; a flag still zeroes the node's local belief (a true event). With view = truth
   this is bit-identical to the frozen env — confirmed by the intact gate.
2. **Sink preservation.** Both rewires rebuild the DAG with `sink_override=graph.sinks`,
   so the sink set is kept exactly even though rewired sinks may have parents. Dropping the
   override was tested and is clearly wrong (BA marginal rewire_order 37.4 vs target 49.06).
3. **Parent tuple order.** Sampled parents are stored sorted. This matters because
   `sample_episode` pairs its random draws with edges in parent-list order; sorting is what
   makes `rewire_index` reproduce `controls.csv` exactly. Both rules sort.
4. **`rewire_order` parent pool.** I draw from the placement-order list (`order`), which is
   the literal reading of "the nodes placed before it". Sorted-pool and unsorted-parent
   variants were probed and are further from the target, but **none reproduces the target
   exactly** (see (c)). The node choice is `rng.choice` over the ascending feasible list.
5. **`within_graph_sd`.** README only says "within-graph (across draws) vs between-graph SD".
   I used `sqrt(mean_g(var_draws(errors_g, ddof=1)))` (pooled within, sample variance) and
   `std(ddof=1)` over graph means for between, 0.0 when there is one draw. The pooled
   ddof=1 form is what reproduces the target's `rewire_index` cells exactly — I identified
   it by testing candidate formulas against those cells, i.e. it is a formatting/aggregation
   convention pinned to the target, not an outcome-dependent choice. Disclosed for honesty.
6. **Summary conventions** (read off the target file's shape at the comparison stage):
   `margin`, `draw_gain_min/max` empty on intact rows; `verdict` empty on all intact rows and
   on `confidence` rows; `draw_gain_min/max` only when `n_draws > 1`; `margin` always present
   on control rows; `rewire_order` rows exist only for modular/BA/ER; numbers written to 4 dp;
   `direction` ignored. Row order is the target's cosmetic order.
7. **Verdict/margin math** exactly as the README: `m = 0.20 * intact mean gain`, order
   `no-intact-advantage` → `survives` → `removed` (CI inside `[-m, +m]`) → `inconclusive`.
   `draw_gain_min/max` = range over the ten draws of the 100-graph mean gain.
   `gain` per graph uses the draw-averaged policy errors; bootstrap is
   `run_benchmark.interval` copied verbatim (seed 411, 20 × 100), resampling graphs.

## (b) Gates

From `out90000/gate_report.txt`, recomputed from the raw rows:

```
intact==benchmark_role3: compared 1500 rows, mismatches 0
flatten==controls.csv: compared 1500 rows, mismatches 0
rewire_index:0==controls.csv[rewire]: compared 1500 rows, mismatches 0
GATES PASS
```

1500 = 5 families × 100 graphs × 3 policies. Compared on **both** `sink_errors` and the full
action string, row by row. `invariants.txt`: 48 checks (family × seed × rule × draw), all
pass — parent counts, types, rates, sink set, acyclicity, and identical
source errors / confidence / reviewer uniforms between view and truth.

## (c) Mismatch report (target summaries, `direction` excluded, numbers at 4 dp)

| Block | cells compared | mismatched | verdict labels | primary labels |
|---|---|---|---|---|
| 90000 (`results/v2/controls_v2_summary.csv`) | 810 | **48** | 54/54 | **11/11** |
| 7100 (`results/v2_confirm/controls_v2_summary.csv`) | 810 | **48** | 54/54 | **11/11** |

Every mismatched cell is in a `rewire_order` row, and only for `structural` and `marginal`
(the three `rewire_order`/`confidence` rows match exactly, since each draw is identical to
intact). 675 of 675 cells outside the `rewire_order` block match in both blocks; 87 of 135
`rewire_order` cells match.

Mismatching keys, 90000 block (mine → target):

| key | mean | gain | CI | within / between |
|---|---|---|---|---|
| modular/rewire_order/marginal | 18.564 → 18.557 | −7.974 → −7.967 | [−8.894,−7.110] → [−8.891,−7.112] | 4.376/7.006 → 4.428/7.344 |
| modular/rewire_order/structural | 26.229 → 26.466 | −15.639 → −15.876 | [−16.810,−14.542] → [−17.056,−14.785] | 4.092/7.770 → 3.998/8.130 |
| ba/rewire_order/marginal | 49.179 → 49.056 | −19.529 → −19.406 | [−25.378,−12.934] → [−25.203,−13.030] | 23.490/34.802 → 23.108/35.283 |
| ba/rewire_order/structural | 67.021 → 65.334 | −37.371 → −35.684 | [−45.342,−29.446] → [−42.705,−28.597] | 17.872/37.925 → 19.582/36.475 |
| er/rewire_order/marginal | 33.627 → 33.380 | −11.877 → −11.630 | [−13.331,−10.387] → [−13.039,−10.215] | 4.728/6.861 → 4.967/6.835 |
| er/rewire_order/structural | 38.337 → 38.212 | −16.587 → −16.462 | [−18.257,−14.937] → [−18.061,−14.851] | 3.696/6.744 → 3.799/6.437 |

7100 block: the same six keys, same columns, all differences ≤ 1.9 errors (e.g.
er/rewire_order/marginal 33.901 vs 33.900; ba/rewire_order/marginal 49.772 vs 47.866).

Reading: my `rewire_order` draws are close to, but not the same as, the audited ones — the
means move by ≪1 SE of the 100-graph mean (between-graph SD ≈ 6–35), so most (graph, draw)
pairs must coincide and a small subset diverges in the RNG detail. With no row-level anchor
for this rule I could not pin the remaining detail down; the alternatives I tested
(sorted parent pool, unsorted parents, derived sinks, rejection order) all fit worse.
Conclusion: unanchored, but it does not change any label — 54/54 and 11/11 label agreement
on both blocks, including all five `worse-than-confidence` cells implied by the README.

## (d) Verbatim overlap with the audited implementation

Not measurable without reading `run_controls_v2.py`, which is forbidden, so skipped as
instructed. (The only intentional verbatim copy is `interval` from
`run_benchmark.py`, which the task and the README both designate as the frozen source.)
