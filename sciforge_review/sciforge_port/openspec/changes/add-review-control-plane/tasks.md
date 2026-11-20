# Tasks

## 0. Gates

- [ ] 0.1 Team confirmation that review receipts belong to the evidence chain,
      and who owns the contract.
- [ ] 0.2 Agreement with the line-review front-end on receipt fields; comment
      bodies stay in the front-end.
- [ ] 0.3 Decide whether P1 is a new package or an extension of an existing
      domain; no evidence-dag writes either way.
- [ ] 0.4 A real export (nodes, edges, corrections, receipts) or an explicit
      mock with the same schema.

## 1. P1 — receipt schema and commit

- [ ] 1.1 Define `review.receipt.v1` (strict schema, closed verdict/reason
      vocabularies) with negative tests for content fields.
- [ ] 1.2 Implement `review.receipt.commit` through the artifact-versions
      commit path; idempotent by `eventId`.
- [ ] 1.3 Hash-chain verification (`prev`/`digest`) and tamper tests.
- [ ] 1.4 Reject receipts without `openedAt`/`submittedAt` when duration is
      requested; degrade to review counts, not minutes.

## 2. P2 — read-only suggestions

- [ ] 2.1 `review.suggest` over a bounded evidence slice with a minute budget.
- [ ] 2.2 Rule-based policies only: type prior and belief greedy; reasons from
      a closed vocabulary.
- [ ] 2.3 Fail closed with `coverage_unknown` when the slice is unavailable.
- [ ] 2.4 Tests that the capability performs no write and no seal.

## 3. P3 — coverage

- [ ] 3.1 `review.coverage`: unreviewed, no-receipt, unreachable corrections.
- [ ] 3.2 Report reachable and unreachable recall separately.
- [ ] 3.3 Fixture with corrections that were never flagged.

## 4. P4 — claim audit

- [ ] 4.1 `Span` + mechanical verbatim check before any verdict.
- [ ] 4.2 `insufficient` with reasons (control, n, effect size, statistics).
- [ ] 4.3 Bind audit results to `knowledge-net` records; no new evidence node.

## 5. P5 — instrument adapter (separate change)

- [ ] 5.1 Read-only adapter schema (capabilities, inputs, outputs, failure
      codes) and a simulated adapter.
- [ ] 5.2 A run record that can be cited as evidence; no device control.

## 6. Evaluation and integration

- [ ] 6.1 Paired harness: queue order / random / type prior / belief greedy,
      `recall@minutes`, coverage, worst-of-n.
- [ ] 6.2 N=21 pipeline DAG and the 1,048-item queue as fixtures; all numbers
      produced by a script.
- [ ] 6.3 `npm run capability:generate`, `domain-packages:check`, locales,
      generated docs.
- [ ] 6.4 Native desktop and Windows/Linux checks; no claim from a worker
      test alone.

## 7. Port from the prototype

- [ ] 7.1 Port `sciforge_review/graph.py`, `policies.py`, `simulate.py`, `receipts.py`,
      `store.py`, `loop.py`, `metrics.py` into the package's read model and tests.
- [ ] 7.2 Keep the prototype as the reference implementation; no duplicated
      schema.
- [ ] 7.3 Record the negative result (belief greedy beats learned policies)
      in the package README, not only in a slide.
