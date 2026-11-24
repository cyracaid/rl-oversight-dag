# `error_type`: the label set, and where each label comes from

> 2026-11-24. Resolves the `TBD — ask 郑心 / export` row in `COURSE_ALIGNMENT.md`.
> Vocabulary read from the SciForge `evidence-dag` domain package. Nothing there
> was modified for this page; every code below is produced by code that already
> runs on real chains.

---

## 0. One page

`SCIFORGE_ASK.md` §4 asks the exporter for `error_type`. We do not have to invent it.
SciForge already emits two closed vocabularies, and both come from production code,
not from the benchmark.

| Vocabulary | Size | Produced by | Answers |
|---|---:|---|---|
| **gap code** | 10 | closure seal (`evidence-dag`, TS) | is this chain structurally complete? |
| **finding type** | 15 | audit run (`audit.py` + `epistemic.py`) | what is wrong with this node? |
| **sleep domain type** | 6 | human corrections (splsleep) | what kind of parsing mistake is this? |

They are **not interchangeable**, and §2 is the reason. That constraint is what keeps
the two-instantiation claim honest instead of convenient.

---

## 1. The vocabularies, verbatim

### 1.1 Gap codes — 10, closure layer

Emitted by the seal as `closure.gapCodes`. A gap code says the chain did not resolve,
not that a node is wrong.

| Code | Set when |
|---|---|
| `missing_delta` | the closure did not reach a delta the policy required |
| `unsupported_edge_family` | an edge family outside `policy.edgeFamilies` touches a reached node |
| `access_restricted` | an access breakpoint blocks resolution |
| `source_unavailable` | a required source cannot be read |
| `lineage_incomplete` | a required lineage link is absent or unknown |
| `independence_unknown` | independence metadata says `not_independently_assessed` |
| `contradiction_unresolved` | contradictory material is present and unresolved |
| `negative_result_missing` | no negative result is recorded where the policy needs one |
| `failed_replication_missing` | a failed replication is expected but absent |
| `shared_ancestry_unknown` | shared ancestry between support paths is unknown |

### 1.2 Finding types — 15, audit layer

Emitted by `run_audit`, each bound to exactly one `target_id`. This is the closest thing
to a per-node `error_type` that the system already produces.

| `finding_type` | Severity | Fires when |
|---|---|---|
| `missing_evidence` | blocker | a conclusion has zero upstream sources |
| `contradiction` | blocker | a `contradicts` edge crosses the review threshold |
| `non_independent_support` | major | several support paths funnel through one source or assumption |
| `single_source_dependency` | major | a conclusion rests on exactly one source |
| `weak_support` | major / minor | aggregate support strength below threshold |
| `load_bearing_dependency` | major / minor | removing the node disconnects ≥ 3 conclusions |
| `conflicted_status` | blocker | node status is `conflicted` (support *and* credible contradiction) |
| `undetermined_claim` | minor | node has not crossed the support threshold |
| `low_credibility_source` | major | a source node is marked low credibility |
| `register_unwarranted` | major | declared truth level exceeds what the method can carry |
| `level_shift_undeclared` | minor | an edge crosses truth levels (`phenomena` / `intersubjective` / `objective`) without declaring it |
| `scope_shift_undeclared` | major | an edge widens scope (`individual` / `cohort` / `population` / `universal`) without declaring it |
| `register_dismissal` | major | objective evidence is used to void phenomenal truth |
| `single_voice_inflation` | major | one testimony at individual scope supports a universal claim |
| `unfalsifiable_universal` | minor | a widened conclusion names no falsifier |

### 1.3 Sleep domain types — 6, value layer

From `manual_error_correction_updated.csv`, as encoded in `experiments/real_pipeline_graph.py`.

| Type | Share of 75 corrections |
|---|---:|
| `order_error` | 76% (57/75) |
| `awake_getup_diff_error` | 5.3% |
| `bed_sleep_diff_error` | 4.0% |
| `sleep_awake_equal_error` | 2.7% |
| `sleep_awake_24h_error` | 1.3% |
| `metric_spike` | residual |

---

## 2. The layers are orthogonal — do not pool labels

`order_error` is a **value-level** defect: a familiar time-order assumption overrode
recorded timestamps. The SciForge codes are **argument- and provenance-level**: they
describe whether a conclusion is grounded, independent, or within its declared scope.

There is no 1:1 map, and the tempting ones are wrong:

| Sleep type | Closest SciForge code | Why it is not the same |
|---|---|---|
| `order_error` | `missing_evidence` | the value exists and is cited; it is simply wrong. No graph audit sees this. |
| `bed_sleep_diff_error` | `weak_support` | a computed value is off; the support structure may be perfectly fine |
| `metric_spike` | `low_credibility_source` | a spike is a statistical artefact, not a credibility judgement |
| `sleep_awake_24h_error` | `contradiction` | a 24h wrap is a units/ARITHMETIC defect, not a conflicting claim |

Consequences, all of which must hold in the paper:

1. **Do not compute one precision across both instantiations.** A model trained to find
   `register_unwarranted` is not being tested on `order_error`.
2. **Per-instance label sets, shared meta-schema.** Every instance carries
   `error_type = {layer, code}` with
   `layer ∈ {value, provenance, evidence, argument, review}`. Within an instantiation
   the codes are closed; across instantiations only `layer` is comparable.
3. **Report the exotic direction explicitly.** SciForge codes include defects that the
   sleep pipeline cannot express (scope widening, testimony inflation). That is an
   argument for generality, but only if stated as a capability difference, not as
   equivalent instances.

This pre-empts the obvious reviewer objection: "you pooled two unrelated label sets".

---

## 3. Injection recipes — the instance generator spec

Each row is a minimal graph mutation that **must** produce that finding, plus the node
it must be reported on. Clean twin = the same graph before the mutation. Ground truth is
the mutation itself, so no human labelling is needed.

| `finding_type` | Minimal trigger | Target |
|---|---|---|
| `missing_evidence` | conclusion with no incoming source edge | the conclusion |
| `contradiction` | add `contradicts` edge above threshold from a credible source | the contested claim |
| `non_independent_support` | two support paths sharing one source or assumption | the claim |
| `single_source_dependency` | exactly one source edge into a conclusion | the conclusion |
| `weak_support` | lower support strength below threshold | the claim |
| `load_bearing_dependency` | make the node the only path to ≥ 3 conclusions | the shared node |
| `conflicted_status` | set status `conflicted` from verifier output | the claim |
| `undetermined_claim` | leave the claim below threshold | the claim |
| `low_credibility_source` | mark a source `credibility: low` | the source |
| `register_unwarranted` | `register: objective` + `method: model_output` (or `testimony` + non-phenomenal) | the claim |
| `level_shift_undeclared` | edge between two nodes with different declared registers, no `shift` attribute | the target node |
| `scope_shift_undeclared` | edge between `individual` and `universal`, no `shift` attribute | the target node |
| `register_dismissal` | `contradicts` edge, objective → phenomena, no `shift` | the phenomenal claim |
| `single_voice_inflation` | `testimony` + `individual` supports `universal` | the universal claim |
| `unfalsifiable_universal` | conclusion at `cohort`/`population`/`universal` with no `falsifier` | the conclusion |

The last six are declared-defect checks: a node that declares **no** register is never
accused, so an instance must set `register` explicitly. That keeps historical chains quiet
and is also why the injection is deterministic.

Gap codes are injected at the policy layer instead (unknown edge family, missing delta,
unreadable source, `independence: not_independently_assessed`), and asserted on
`closure.gapCodes` rather than on a node.

---

## 4. What the export still cannot fill

| Field | Status | Note |
|---|---|---|
| `node_id` | ✓ | claim ids are already first-class (`payload.claims[]`, `targetClaimIds`) |
| `type` | ✓ | `claim` / `conclusion` / `source_assertion` / `artifact` / run and dataset node types |
| `is_sink` | ✓ derived | no outgoing edge, or named in `closure.policy.requiredRecords` |
| `src` / `dst` / `rel` | ✓ | generic edge extraction accepts `from`/`to`/`type` aliases |
| `error_type` | ✓ | §1 above; exported as `{"layer", "code"}`, not a bare string |
| `severity` | ✓ | already on every finding |
| `agreed_by` | ✗ | single `reviewed_by`; no multi-reviewer consensus marker |
| `reviewer_hash` | ✓ | `ReviewPacket.reviewed_by` |
| `reviewed_at` | ✓ | `ReviewPacket.reviewed_at` |
| `duration_min` | ✗ | not recorded. `reviewed_at − computed_at` gives **queue latency**, not review time |
| `verdict` | ✓ | review status (`accepted` / `rejected` / `needs_revision` / `unresolved` / `skipped`) |
| snapshot at review time | ✓✓ | stronger than asked: `expectedHeadDigest` + `barrierWatermark` + `includedDeltaDigests` |

Until `duration_min` exists, the cost axis can only be **reviews spent**, with queue
latency as a secondary. "Minutes per error caught" stays out of the paper.

---

## 5. Instance budget

| Source | Count | Ground truth |
|---|---:|---|
| SciForge finding classes × (clean twin + corrupted) | 15 × 2 = 30 | the mutation |
| SciForge gap codes × (registered / unregistered policy) | 10 × 2 = 20 | the policy |
| Sleep corrections (real) | 75 | human |
| Synthetic DAG episodes (existing) | 80 train / 200 dev | simulator |

So "100–200 instances" is reachable, but **that number is node-level across real chains**,
not 100 newly invented error classes. Class-level, we have 25 SciForge pairs and 6 sleep
types. Saying otherwise would inflate the benchmark.

---

## 6. Metric consequence

Because localization and propagation ground truth is free in the injected pairs, the
primary metrics should be:

- **Root Cause Localization** — is the injected node inside `evidence_refs`, and at what rank
- **Propagation Recall** — are the injected node's descendants flagged `stale` / affected

`recall@budget` stays a **secondary** metric, measured on the real queue. `triage_bench`
already showed that axis is information-limited (6.5% queue precision, 83.8% type-only
ceiling); if the evidence chain lands in the same place, the finding is "auditing is
information-limited there too", which is a statement about the chain, not about the DAG.

---

## 7. Where this sits

- Vocabulary: SciForge `packages/domains/evidence-dag` — `contract.ts` (gap codes),
  `python/evidence_dag/audit.py` and `epistemic.py` (finding types).
- Export shape: `SCIFORGE_ASK.md` §4, with `error_type` = §1 and the gaps in §4 listed
  as `null` rather than omitted.
- Wire contract: `sciforge.review-handoff.v1` —
  `evidenceDagHandoffDocumentSchema` in the same `contract.ts`, JSON Schema at
  `eval-cases/handoff/handoff.v1.schema.json` (generated, freshness-tested), golden
  document at `eval-cases/handoff/handoff.v1.example.json`, producer
  `python -m evidence_dag.handoff [--closure sealed-closure.json]`. Both sides test
  against the golden document, so the shape cannot drift in one repo alone.
- Gap codes: `closure.gap_codes` is authoritative and comes from the seal, with its
  digests. An empty list means the seal ran and found nothing; no seal supplied means
  `closure: null` plus a `not_recorded` reason. The two are not interchangeable.
- Read-only: this page changes no SciForge rule and no sleep data.
