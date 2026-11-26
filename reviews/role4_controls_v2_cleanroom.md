# role 4 v2 controls — clean-room recheck

- run: 2026-11-26 17:50, commit `f8d73c6` + `acbd729` (v2 code unchanged since `7f58534`)
- clean room: `reviews/role4_independent_v2/` — protocol in `PROTOCOL.md`, ambiguities in `NOTES.md`
- what this adds: the v1 clean room (`reviews/role4_independent/`) covered only the v1 layer. This one
  covers the amendment — `rewire_order`, ten draws, the three-level verdict, the 20 % margin.

## A. Gates

Recomputed from the clean room's own row-level file, with the frozen tables as the only anchor:

| gate | compared | mismatches |
|---|---:|---:|
| `intact` vs `benchmark_role3.csv` (errors + action strings) | 1500 | **0** |
| `flatten` vs `controls.csv` (errors + action strings) | 1500 | **0** |
| `rewire_index:0` vs `controls.csv[rewire]` (errors + action strings) | 1500 | **0** |
| rewire invariants (parent counts, types, sink set, acyclicity, shared episode) | 48 | **0** |

**PASS.** The v2 layer sits on an environment the reimplementation reproduces exactly.

## B. Agreement with the committed tables

| comparison (per block) | 90000–90099 | 7100–7199 |
|---|---:|---:|
| summary cells, `rewire_order` rows excluded | 675 / 675 | 675 / 675 |
| summary cells inside `rewire_order` | 87 / 135 | 87 / 135 |
| verdict labels (54 rows) | 54 / 54 | 54 / 54 |
| primary labels (11 cells) | **11 / 11** | **11 / 11** |

Every float outside `rewire_order` is identical at 4 dp, both blocks, including all ten draws'
`draw_gain_min/max`, the `within/between_graph_sd` columns and the interval bounds.

**PASS on the claim.** The qualitative v2 result — flatten removes the gain, `rewire_index` keeps it on
BA and (on these two blocks) on ER, `rewire_order` reverses it into `inconclusive` *worse than
confidence* — follows from the written specification, not only from the author's code.

## C. What does not reproduce, and why

Six of the nine `rewire_order` rows differ, all of them on `marginal` and `structural` (the
`confidence` rows match exactly, since each draw is intact):

| key (90000 block) | clean room | committed | Δ | Δ as % of the gain |
|---|---:|---:|---:|---:|
| modular / `rewire_order` / marginal | −7.974 | −7.967 | 0.007 | 0.1 % |
| modular / `rewire_order` / structural | −15.639 | −15.876 | 0.237 | 1.5 % |
| ba / `rewire_order` / marginal | −19.529 | −19.406 | 0.123 | 0.6 % |
| ba / `rewire_order` / structural | −37.371 | −35.684 | 1.687 | 4.5 % |
| er / `rewire_order` / marginal | −11.877 | −11.630 | 0.247 | 2.1 % |
| er / `rewire_order` / structural | −16.587 | −16.462 | 0.125 | 0.8 % |

7100 block: the same six keys, all differences ≤ 1.9 errors.

Cause: `rewire_order`'s specification fixes the *rule* (random feasible order, parents drawn from the
nodes placed before) but not the **random-order detail** — the order of the candidate pool that
`Random.choice` indexes, and the tie-break among feasible nodes. The clean room tried the alternative
readings that were available to it (sorted pool, unsorted parent tuple, derived sinks, rejection order)
and every one fits worse, so the exact detail is not recoverable from the text. The residual moves the
means by ≪ 1 SE of the 100-graph mean (between-graph SD ≈ 6–35 errors), so most (graph, draw) pairs
evidently coincide and a small subset diverges.

## D. Consequence for the write-up

1. **The v2 conclusion is independent of that gap.** Every label, including the five
   `worse-than-confidence` cells, agrees on both blocks, and the effects the claim rests on
   (BA −19.4 against intact +9.5; ER −11.6 against +5.0) are one to two orders of magnitude larger
   than a ≤ 4.5 % shift in a mean.
2. **The `rewire_order` digits are one implementation's digits.** Do not quote them to four decimals,
   and do not treat a sub-0.3-error difference between two `rewire_order` cells as a finding. Quote the
   sign and the label.
3. **The fix is documentation, not code.** Ask role 4 to state the exact pool order and tie-break in
   `README.md`, so the numbers become reproducible without reading the source; or leave the code as is
   and carry the caveat above.

## E. What this does not cover

1. **Environment.** Both sides import `dag_role3`; a bug shared by every user of it is invisible here.
2. **Intervals are not independent.** `interval` was copied from `run_benchmark.py`, which the
   specification names as its source. Point estimates are independent; the intervals are calibrated to
   the same procedure, not re-derived.
3. **`within_graph_sd` is a convention pinned to the target.** The specification does not give the
   formula; the clean room identified the pooled ddof=1 form by testing it against the target's
   `rewire_index` cells. Those SD cells are therefore reproduced, not independently derived
   (`NOTES.md`, ambiguity 5).
4. **`rewire_order` has no row-level anchor.** `intact`, `flatten` and `rewire_index:0` are gated
   against frozen files; `rewire_order` is gated only by invariants (parent counts, types, sinks,
   acyclicity, shared episode). A systematic error in that rule that preserves those invariants and
   still lands within 4.5 % of the committed mean would not be caught.
5. **`flatten` and `rewire` have no ground truth.** Both sides agree on what the controls *produce*;
   nothing here says the controls mean what the write-up says they mean.

## How to re-verify

```bash
cd reviews/role4_independent_v2
python gate_report.py out90000        # A, from the committed rows
python compare.py                     # B and C, against both target summaries
python runner.py --start-seed 7100 --jobs 6 --out /tmp/v2chk   # full recompute, ~11 min
```
