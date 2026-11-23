# Development analysis protocol

2026-11-12. Written after the user started training at commit 1197e4b.
No full-run output has been inspected for this protocol. This is a prospective
development analysis plan, not a pre-training registration or confirmation study.
Do not change running source files or regenerate their manifests during training.

## Estimand and data gate

Primary outcome: mean residual sink errors after 16 reviews (lower is better).
Primary condition: normal confidence / matched environment, graph IDs1000–1199.
Training seeds1–5. Require complete arrays, five checkpoints per candidate,
source/checkpoint hashes, finite values and completed status before interpretation.
Incomplete runs remain incomplete. Do not replace missing cells with zero or select
successful seeds. Preserve raw artifacts and all requested cells.

## Primary comparisons and multiplicity

There are eight normal/matched learned candidates: observed/gain crossed with
reinforce/ac/nstep3/nstep5. Report every candidate minus the same paired belief
greedy reference. For superiority screening use a Bonferroni simultaneous family:
eight two-sided99.375% crossed-bootstrap intervals, alpha=.05/8 per comparison.
Resample training seeds and graph IDs independently, preserving pairing and the
shared graph reference. Use100,000 draws, bootstrap seed20261112, and no rounding
before decisions. Declare development superiority only if adjusted interval upper
bound is strictly below zero. Also report unadjusted95% intervals descriptively.
The runner's current95% tables alone do not establish multiplicity-adjusted success.
Five training seeds limit uncertainty estimation even with many bootstrap draws.

Secondary mechanistic family: four gain-minus-observed contrasts (one per
optimizer), plus six optimizer contrasts (ac/nstep3/nstep5 minus reinforce,
separately for each input). For these ten comparisons report all differences,
unadjusted95% intervals and Bonferroni99.5% intervals (alpha=.05/10).
Pair training seeds and graphs for candidate-to-candidate contrasts. No
cross-seed flattening. An improvement supports that implementation change; it
does not establish credit assignment as the unique causal bottleneck.

## Secondary analyses

Drift, noise and oracle are exploratory: show every cell, signed paired gaps,
seed means and degeneracy counts; no headline significance claims from these cells.
For drift report first/last50 episode means and remaining100 separately, keeping
chronological graph IDs; comparisons across time confound graph variation and rate.
No conclusion about online adaptation: policies are frozen. Noise changes both
confidence and its derived nominal belief. Oracle is privileged source-error
information, not deployable evidence. These conditions cannot identify the
confidence channel's isolated effect.

## Reporting and follow-up

Show all eight primary candidates even if every one loses. Report full training
curves and seed-level outcomes, not only best checkpoint or seed. Do not infer
wall-clock speed ratios from mixed-condition elapsed time. Training costs and
planner evaluation costs must be measured separately before cost claims.

If selection is needed, choose lowest normal/matched mean among all eight;
exact ties use observed before gain, then reinforce/ac/nstep3/nstep5. Selection
is exploratory regardless of interval result. Before confirmation write a new
protocol freezing candidate, baseline, seed range2000–2199, uncertainty method
and success criterion. Do not run/read confirmation data as part of development.
Independent teammate reproduction is a separate requirement with independent
executor and clean-clone provenance, not another run by the same script author.
