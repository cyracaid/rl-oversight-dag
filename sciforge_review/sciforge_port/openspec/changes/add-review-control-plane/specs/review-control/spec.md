## ADDED Requirements

### Requirement: Review receipts are append-only, content-free and version-bound

`review.receipt.commit` SHALL seal one receipt per human review submission.
A receipt SHALL reference an immutable artifact version and MAY reference one
field path. It SHALL NOT contain artifact text, comment bodies, participant
identifiers or free-text rationale. A correction SHALL append a new receipt and
SHALL NOT modify an earlier one.

#### Scenario: Human accepts a node
- **WHEN** a reviewer submits an `accepted` verdict on a node at version `v7`
- **THEN** one receipt is sealed with `artifactVersion: v7`, `verdict: accepted`,
  `openedAt`, `submittedAt`, `actorHash`, `prev` and `digest`
- **AND** no artifact text is stored in the receipt

#### Scenario: Verdict changes
- **WHEN** the same reviewer later submits `corrected` for the same node
- **THEN** a second receipt is appended and the first receipt is unchanged

#### Scenario: Content is supplied
- **WHEN** a caller includes a comment body or a raw participant id
- **THEN** the capability rejects the request

### Requirement: Review suggestions are read-only and explainable

`review.suggest` SHALL accept a bounded evidence-graph slice and a minute
budget, and SHALL return a ranked list of nodes with a reason and an estimated
cost. It SHALL NOT write, seal, or mutate the graph.

#### Scenario: Suggest under a budget
- **WHEN** a caller passes a slice with four sinks and a 30-minute budget
- **THEN** the response contains a ranked list, each item carrying a reason
  from a closed vocabulary and a cost in minutes

#### Scenario: Missing graph
- **WHEN** the slice cannot be read
- **THEN** the capability fails closed with `coverage_unknown` and no ranking

### Requirement: Coverage gaps are reported, not averaged away

`review.coverage` SHALL report unreviewed nodes, nodes with no receipt, and
known corrections that were never flagged. The unreachable remainder SHALL be
reported separately from the reachable recall.

#### Scenario: Corrections were never flagged
- **WHEN** known corrections exist for rows that never entered the queue
- **THEN** the report lists them as `unreachable` and excludes them from the
  ranker's recall denominator

### Requirement: Only rule-based policies are on the product path

`review.suggest` SHALL expose only rule-based policies (type prior, belief
greedy). Learned policies SHALL remain offline comparisons and SHALL NOT be
selectable by a runtime caller.

#### Scenario: Caller requests a learned policy
- **WHEN** a caller asks for a learned policy by name
- **THEN** the request is rejected and the available rule-based policies are
  listed

### Requirement: Claim-level insufficiency is explicit

`knowledge-net` claim audit SHALL allow an `insufficient` verdict with reasons
(no control, missing sample size, implausible effect size, incomplete
statistics). A claim whose quote does not match the recorded span SHALL be
rejected before the verdict is computed.

#### Scenario: Implausible effect size
- **WHEN** a result claim reports an effect size of 5.28 with no control and no
  sample size
- **THEN** the audit returns `insufficient` with all fired reasons

#### Scenario: Fabricated span
- **WHEN** the claim quote does not occur at the recorded offsets
- **THEN** the claim is rejected and no verdict is sealed
