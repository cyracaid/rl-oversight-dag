# Design: review control plane

## 1. Data model

```ts
type ReviewReceipt = {
  schema: 'review.receipt.v1'
  eventId: string
  artifactVersion: string       // immutable version id, never "latest"
  fieldPath?: string            // e.g. 'TIME_AWAKE'; absent = row-level
  actorHash: string             // hashed reviewer id, never a raw account id
  openedAt: string              // ISO 8601
  submittedAt: string
  verdict: 'accepted' | 'corrected' | 'rejected' | 'needs_revision' | 'unresolved' | 'skipped'
  reasonCode?: string           // closed vocabulary, no free text
  prev: string | null           // sha256 of the previous receipt
  digest: string                // sha256 of this receipt
}

type ReviewSuggestion = {
  nodeId: string
  rank: number
  reason: 'type_prior' | 'downstream_impact' | 'low_confidence' | 'unreviewed'
  expectedGain: number          // units documented per policy
  costMinutes: number
}
```

Receipts contain references and timestamps only. The comment body, the artifact
text, the participant id and any free-text rationale stay in the front-end.

## 2. Integration

- **Sealing:** `review.receipt.commit` writes through the same artifact-versions
  commit path used by `knowledge-net.note.commit`; the receipt is a sealed
  version, not a mutable row.
- **Graph:** `review.suggest` reads a bounded `evidence-dag` slice (nodes,
  `derived_from` / `supports` edges, sinks). It never calls a write capability.
- **Claims:** P4 reads `knowledge-net` records and their spans; `insufficient`
  is a verdict on a claim, not a new evidence node.
- **Front-end:** the line-review UI calls `review.receipt.commit` on the human
  decision only; AI replies do not produce receipts.

## 3. Policies

- `type_prior`: order by base error rate per node type, then downstream sink
  influence, then upstream layer. No model, no training.
- `belief_greedy`: rank by posterior source-error probability × downstream
  sink influence / review cost. The posterior is supplied by the caller; in P2
  it is the per-type base rate, not a learned model.
- Learned policies are evaluated offline against these; they are not exposed as
  a capability.

## 4. Evaluation

- `recall@minutes`: sort by policy, spend a fixed minute budget at a documented
  per-field reading time, count human-confirmed errors found.
- `coverage`: fraction of known corrections that were ever flagged; report the
  unreachable remainder separately.
- `worst-of-n`: the lowest score over n runs, because one unreviewed error can
  invalidate a conclusion.
- Baselines: queue order, random, type prior, belief greedy. Paired seeds and
  paired bootstrap intervals; no unpaired "winner" rows.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Receipts are incomplete (no `opened_at`) | fail closed: without timestamps, report reviews, not minutes |
| Timestamps are client-supplied and untrusted | record actor and version; treat duration as self-reported, not audited |
| Double counting | one receipt per submission; `eventId` idempotency |
| Privacy | hash actor and row keys; no content; no export of raw ids |
| Scope creep into a scheduler | capabilities expose ranking only; no policy training in the package |

## 6. Alternatives considered

- **Extend `knowledge-net`:** rejected; reading notes and review receipts have
  different semantics, and knowledge-net is a derived read model.
- **Write receipts into `evidence-dag`:** rejected for P1; the chain is
  append-only and its write surface is owned elsewhere.
- **Standalone JSONL only:** kept for the pilot, rejected for the product;
  it cannot bind a receipt to an immutable artifact version.
