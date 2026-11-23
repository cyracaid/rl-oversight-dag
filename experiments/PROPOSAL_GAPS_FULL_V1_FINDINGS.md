# Full-v1 development findings

Run: `runs/proposal-gaps-full-v1`. Analysis follows the unchanged `PROPOSAL_GAPS_ANALYSIS_PROTOCOL.md`; no retraining or confirmation data used.

## Artifact gate

`status=completed`; 120 training curves of 20,000 episodes, 120 checkpoints, six evaluation conditions, five training seeds, graph IDs 1000–1199. Frozen analyzer exited successfully after validating arrays, finite integer outcomes, source-manifest presence and all checkpoint hashes. This checks artifact consistency, not independent implementation correctness. `analysis.json` records input and protocol SHA256 digests.

The current redirected log contains a subsequent startup's `FileExistsError` because the output directory already existed. Completed JSON and checkpoints remain available; log alone does not document the original run's completion. The JSON's recorded elapsed seconds must not be equated with observed wall time or used for speed comparisons.

## Primary result: every learned candidate loses to belief greedy

Outcome: residual sink errors after 16 reviews, lower is better. Normal confidence, matched environment. Belief greedy mean = **1.020**. Differences are candidate minus paired greedy; positive is worse. Intervals use 100,000 crossed seed/graph bootstrap draws, seed 20261112, Bonferroni family of eight (99.375% per interval).

| Candidate | Mean | Difference | Adjusted interval |
|---|---:|---:|---|
| observed/reinforce | 1.292 | +0.272 | [0.148, 0.417] |
| observed/ac | 1.391 | +0.371 | [0.211, 0.532] |
| observed/nstep3 | 1.256 | +0.236 | [0.068, 0.432] |
| observed/nstep5 | 1.340 | +0.320 | [0.115, 0.575] |
| gain/reinforce | 1.411 | +0.391 | [0.185, 0.610] |
| gain/ac | 1.427 | +0.407 | [0.215, 0.590] |
| gain/nstep3 | 1.255 | +0.235 | [0.109, 0.373] |
| gain/nstep5 | 1.295 | +0.275 | [0.134, 0.427] |

No development superiority criterion met; all eight adjusted intervals lie above zero. Exploratory selection rule picks gain/nstep3, but its mean is about 23% higher than greedy. Its difference from observed/nstep3 is only −0.001, not evidence that gain inputs help.

All ten secondary adjusted 99.5% intervals cross zero. Neither gain inputs nor critic/n-step modifications demonstrate improvement under this family. This does not prove equivalence or identify the unique learning bottleneck. Five seeds limit uncertainty estimation.

## All conditions: descriptive means

Noise, oracle and drift are exploratory. No headline significance claims from this table.

| Policy | normal matched | normal drift | noise matched | noise drift | oracle matched | oracle drift |
|---|---:|---:|---:|---:|---:|---:|
| belief greedy | 1.020 | 1.555 | 3.965 | 5.320 | 0.705 | 0.965 |
| observed/reinforce | 1.292 | 2.064 | 4.208 | 5.489 | 0.740 | 1.177 |
| observed/ac | 1.391 | 2.154 | 4.031 | 5.314 | 0.730 | 1.204 |
| observed/nstep3 | 1.256 | 1.999 | 3.477 | 4.727 | 0.721 | 1.097 |
| observed/nstep5 | 1.340 | 2.115 | 3.643 | 4.911 | 0.750 | 1.230 |
| gain/reinforce | 1.411 | 2.220 | 3.973 | 5.271 | 0.716 | 1.153 |
| gain/ac | 1.427 | 2.216 | 3.696 | 4.951 | 0.710 | 1.106 |
| gain/nstep3 | 1.255 | 2.024 | 3.485 | 4.746 | 0.710 | 1.046 |
| gain/nstep5 | 1.295 | 2.066 | 3.556 | 4.770 | 0.711 | 1.091 |

Noise/matched observed/nstep3 has mean gap −0.488 (about 12.3% fewer errors than greedy); noise/drift gap −0.593. Noise changes both confidence and derived nominal belief, so this does not isolate a confidence-channel effect. Learned policies also have substantial posterior degeneracy counts under noise, requiring diagnosis before mechanistic claims. Oracle is privileged information; matched means approach but do not beat greedy. Frozen-policy drift performance is not online adaptation.

`analysis.json` preserves every cell's signed gap, seed means, degeneracy counts, and chronological first-50/middle-100/last-50 means. Raw `results.json` preserves all 2.4 million training-episode outcomes. Comparing chronological blocks confounds changing graphs and error rates.

## Interpretation and next decision

The principal result remains negative: the tested learned policies do not improve on belief greedy in the designated normal/matched setting. Training errors generally decline, but training progress does not imply baseline superiority.

Do not launch more full training on the strength of the noise subset. A useful next step is read-only diagnosis of action choices and posterior degeneracy, then a separately specified noise-robustness study if warranted. No independent confirmation (graphs 2000–2199), clean-clone teammate reproduction, or SciForge real-system acceptance has been performed.
