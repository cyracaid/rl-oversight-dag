# Change: Add a read-only review control plane

## Why

The evidence chain records conclusions and provenance, but it does not record
**review effort**: who reviewed which immutable version and field, when they
opened and submitted, and what they decided. Without those fields the system
can report "how many reviews" but not "how many minutes per caught error", so
it cannot compare a review order against the queue's default order, and it
cannot tell a detector gap from a ranking miss.

A pilot on a 1,048-item real review queue found three things that shape this
change: a type prior reaches 83.8% of human-confirmed errors in 13% of the
queue; 17 corrections were never flagged at all, so no ranking can reach them;
and a learned scheduler did **not** beat a deployable belief-greedy baseline.
The bottleneck is measurement and coverage, not policy capacity.

## What Changes

- New optional domain package `@sciforge/domain-review-control` (module
  `sciforge.review-control`), built on current `main`, disabled by default.
- Three capabilities:
  - `review.receipt.commit` (`workspace-write`, `none`, `workspace`):
    append a content-free review receipt (`artifact_version`, `field_path`,
    `actor_hash`, `opened_at`, `submitted_at`, `verdict`, `prev`, `digest`);
    sealed through `artifact-versions`; no artifact text, no participant data.
  - `review.suggest` (`read`, `none`, `workspace`): rank a read-only evidence
    slice for a given budget and return reasons; never writes or seals.
  - `review.coverage` (`read`, `none`, `workspace`): report unreviewed,
    unreachable and `insufficient` evidence, so gaps are visible instead of
    being averaged into a recall number.
- Policies are rule-based (type prior, belief greedy). A learned policy is an
  offline comparison only and is not on the product path.
- Claim-level audit (`Span`, `sufficiency_check`, `insufficient`) is a later
  phase that consumes `knowledge-net` notes; it is not part of P1.

## Prerequisites and gates

1. Team confirmation that review receipts belong to the evidence chain, and
   who owns the contract (evidence-chain owner).
2. Agreement with the line-review front-end on the receipt fields; the
   front-end stores comment bodies, the chain stores only references.
3. No write to `evidence-dag`; the graph is read through its existing read
   models.
4. A real export with node/edge/receipt timestamps, or an explicit mock.

## Phasing

- **P1** receipt schema + `review.receipt.commit` + chain verification tests.
  A local JSONL reference implementation (receipts, replay, `recall@minutes`) lives in
  `sciforge_review/` and is the porting source; it does not write the product.
- **P2** `review.suggest` over an evidence slice; rule-based policies only.
- **P3** `review.coverage` (unreviewed / unreachable / insufficient).
- **P4** claim-level `insufficient` audit on `knowledge-net` notes.
- **P5** instrument adapter contract (separate change; read-only, simulated).

## Out of scope

- Reviving Paper Radar or any deep-read plan/verify flow.
- A learned scheduler in the product path; RL stays in offline evaluation.
- Storing comment bodies, free-text notes, raw data, or participant identifiers
  in receipts or the evidence chain.
- Real instrument control; P5 is a read-only contract plus a simulator.

## Impact

- New package, generated installed-domain set, `docs/generated/capabilities.md`,
  locales; no change to existing packages.
- Depends on `artifact-versions` for sealing and on read-only `evidence-dag`
  projections.
- Related: `add-knowledge-net-domain` (claim notes), `add-deep-read-structured-notes`
  (spans), the line-review front-end branch, `triage_bench/SCIFORGE_ASK.md`.
