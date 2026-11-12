# SciForge read-only integration contract map

Inspected 2026-11-12 at SciForge commit
`97c912687b8af066282e7dbbfc5267d7fc03d25b`, local checkout
`/Users/sloblucyra/Documents/sciforge-main-retest`. Source inspection only;
no runtime acceptance, deployment, or SciForge modifications performed.

| Need | Existing canonical owner / contract | Integration rule |
|---|---|---|
| Evidence audit | `packages/domains/evidence-dag/src/contract.ts`: `evidence-dag.audit-query`, input `{subject}`; output re-exported from domain-sdk research-audit | Use public action contract; do not infer a new HTTP endpoint from action ID. |
| Scientific review | `src/main/scientific-review.ts` within evidence-dag | Existing bounded projection with `recorded-links-only` coverage; retain unknown/bounded states and recorded-link limitations. |
| Attention / changes / history queue | `research-record-contract.ts`: `evidence-dag.record.review` | Existing read effect, scope plus nodeId, mode, sequence window and pagination. Retain revision, throughSequence, origin, historical, limited and page metadata. |
| Per-event provenance | Same contract: `evidence-dag.record.audit` | Existing read effect; inspect source statuses, execution binding and input/output status. An unavailable field stays unavailable. |
| Human changes | Same contract: `evidence-dag.record.edit` | Existing mutation path; outside a read-only adapter. Do not invent verification receipts from history events. |

The record review output already exposes revision, latestSequence, throughSequence,
items, total, nextOffset, pending, blocked, optional page and worker state. Each
review item has ID, sequence, nodeId, title, at, kind, text, sourceIds, historical,
origin and limited. Freeze the returned sequence boundary while paging; preserve
source-aware pagination and report incomplete coverage rather than assuming a full
queue. Exact cursor handling must follow the canonical page contract.

Audit output already separates retained/live source state and matched/changed/
unavailable/not-recorded/not-applicable input/output binding. These fields provide
recorded execution evidence; they do not establish scientific correctness or
measure human review duration.

## Remaining implementation and acceptance

1. Identify the installed host's public action invocation transport and owning
   SDK. The evidence engine service client is not proof that desktop record review
   actions are exposed over the same HTTP service.
2. Build a small consumer using canonical exported schemas and invocation path;
   paginate a stable sequence window and return aggregate review diagnostics.
3. Exercise the consumer against a running SciForge workspace with recorded
   evidence; verify action IDs, source statuses and pagination against actual output.
4. Keep ranking advice separate from persisted human actions. Any later review
   effort measurement requires version/field binding and time instrumentation in
   its canonical owner, with its own acceptance evidence.

No parallel review-receipt interface is justified by current inspection. Fixture
tests would establish compatibility only; real-system acceptance remains pending.
