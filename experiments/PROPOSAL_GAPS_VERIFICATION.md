# Implementation verification

2026-11-12. No full experiment or API generation was run.

- New scientific invariant tests: 5/5 passed.
- Existing boundary tests: 8/8 passed.
- Existing simulator semantics tests: 5/5 passed.
- End-to-end smoke: all 24 training cells completed, 2 episodes per cell,
  one training seed; three graphs per evaluation condition, six conditions.
- Checked every one of 24 checkpoint hashes and all saved array dimensions.
- Smoke invocation is the quick verification command in `PROPOSAL_GAPS_RUN.md`.
- Smoke output stayed in `runs/proposal-gaps-smoke-v1` in the isolated worktree;
  checkpoints are debugging artifacts, not scientific performance evidence.

Implementation differs intentionally from legacy ablation: nonzero adjacency,
explicit torch seeds, paired environment replay and saved raw graph outcomes.
No old results or user-modified files were overwritten.
