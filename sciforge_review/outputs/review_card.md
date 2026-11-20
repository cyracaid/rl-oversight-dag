# Review Card — Phase 0

> Synthetic demo harness over the N=21 sleep-pipeline DAG. **Not** the
> paper's simulator, and **not** a claim about the real queue; the real
> queue anchors are quoted separately below from `triage_bench`.

## What this measures

- **Cost-aware review**: a row review reads 4 fields; a witness-pair review
  reads 2. At 62 s per row review, the same minutes buy twice the coverage.
- **Paired episodes**: every policy sees the same seed, base errors, and
  edge coins. Metrics are averaged over 30 seeds.
- **Read-only**: policies rank nodes; nothing is written or sealed.

## Synthetic N=21 result

| policy | mode | budget (min) | reviews | sink errors | recall | errors/hour |
|---|---|---:|---:|---:|---:|---:|
| no review | — | — | 0.0 | 2.43 | 0.000 | 0.0 |
| queue order | row | 4 | 3.0 | 2.37 | 0.218 | 20.6 |
| queue order | row | 8 | 7.0 | 2.23 | 0.329 | 13.3 |
| queue order | row | 16 | 15.0 | 1.87 | 0.578 | 11.2 |
| type prior | row | 4 | 3.0 | 2.37 | 0.218 | 20.6 |
| type prior | row | 8 | 7.0 | 2.10 | 0.480 | 18.8 |
| type prior | row | 16 | 15.0 | 0.83 | 0.845 | 16.4 |
| belief greedy | row | 4 | 3.0 | 2.37 | 0.218 | 20.6 |
| belief greedy | row | 8 | 7.0 | 2.10 | 0.480 | 18.8 |
| belief greedy | row | 16 | 15.0 | 0.77 | 0.833 | 16.1 |
| queue order | witness | 4 | 7.0 | 2.23 | 0.329 | 26.5 |
| queue order | witness | 8 | 15.0 | 1.87 | 0.578 | 22.5 |
| queue order | witness | 16 | 21.0 | 0.43 | 0.909 | 25.4 |
| type prior | witness | 4 | 7.0 | 2.10 | 0.480 | 37.6 |
| type prior | witness | 8 | 15.0 | 0.83 | 0.845 | 32.8 |
| type prior | witness | 16 | 21.0 | 0.50 | 0.909 | 25.4 |
| belief greedy | witness | 4 | 7.0 | 2.10 | 0.480 | 37.6 |
| belief greedy | witness | 8 | 15.0 | 0.77 | 0.833 | 32.3 |
| belief greedy | witness | 16 | 21.0 | 0.50 | 0.909 | 25.4 |

## Real-queue anchors (not recomputed here)

From `triage_bench/README.md`, `CEILING.md`, and
`AUDIT_CHAIN_DESIGN.md` (generated 2026-11-09, not yet rerun by a teammate):

| fact | value |
|---|---|
| review queue | 1,048 flags, 68 human-confirmed errors (6.5% precision) |
| best type rule | M1-bearing first reaches **83.8%** of errors in **140 reviews (13%)** |
| pipeline's own order | worse than random at k=400 (23.5% vs 39.7%) |
| information ceiling | 17 broad corrections were never flagged (7 narrow); no ranking can reach them |
| cost | median **62 s** per row review; witness-pair review halves reading cost |
| cost model | 60/120/240 min: whole row 8.8/25.0/63.2% vs witness pair **25.0/63.2/83.8%** |

## What this implies for SciForge

1. **Measure first.** The receipt schema is the unit of account: who reviewed
   which version/field, when they opened and submitted, and what they decided.
2. **Direct, do not decide.** `belief_greedy` is a read-only ranking; the
   human still seals. Learned policies are offline comparisons, not the product.
3. **Expose the gap.** Coverage (unflagged rows) and `insufficient` evidence
   are first-class outputs; ranking cannot fix what was never flagged.

## Shape A / B / C in one core

| shape | shared primitive | Phase 0 status |
|---|---|---|
| A review control plane | `EvidenceGraph` + `ReviewReceipt` + policy | graph + policies + receipt reuse |
| B claim audit | `Claim` + `Span` + `sufficiency_check` | interface + checklist |
| C instrument adapter | `InstrumentCapability` + `InstrumentRun` | simulated adapter |

## Next

- Wire the receipt writer into the demo (the `triage_bench/audit/receipts.py`
  hash chain is already tested).
- Port the receipt contract and the read-only policy interface into a
  SciForge worktree; keep the local prototype as the reference implementation.
- Replace the synthetic DAG with a SciForge evidence-graph export when the
  P0/P1 fields from `triage_bench/SCIFORGE_ASK.md` are available.
