# Full-v1 action and posterior diagnosis

Exploratory, development-only checkpoint replay. No training, simulator changes, or confirmation graphs used.

## Verification

`runs/proposal-gaps-diagnosis-v1/manifest.json` reports completed, replay_verified=true, 13,200 episodes and 211,200 steps. All recorded output SHA256 digests were independently checked after the user's run. The replay script checks each final sink-error count and unsupported-positive-observation count against original full-v1 arrays. All six conditions, both selected policies and all five seeds passed. This establishes replay consistency, not independent reproduction of the simulator.

Selected policies are observed/nstep3 and gain/nstep3, chosen after inspection of development results. Belief greedy has 200 episodes per condition; each learned policy has 1,000. No inferential or causal claims are added to the frozen analysis.

## Every selected cell

Delta is learned minus paired graph greedy; negative is better. Agreement compares the chosen action with greedy on the learned policy's own history. Nominal gain gaps are not true regret.

| Condition | Policy | Mean errors | Delta | Action agreement | Episodes with degeneracy |
|---|---|---:|---:|---:|---:|
| normal/matched | observed/nstep3 | 1.256 | +0.236 | 27.67% | 19/1000 |
| normal/matched | gain/nstep3 | 1.255 | +0.235 | 30.46% | 13/1000 |
| normal/drift | observed/nstep3 | 1.999 | +0.444 | 27.56% | 18/1000 |
| normal/drift | gain/nstep3 | 2.024 | +0.469 | 29.59% | 17/1000 |
| noise/matched | observed/nstep3 | 3.477 | -0.488 | 3.88% | 189/1000 |
| noise/matched | gain/nstep3 | 3.485 | -0.480 | 4.19% | 193/1000 |
| noise/drift | observed/nstep3 | 4.727 | -0.593 | 3.87% | 276/1000 |
| noise/drift | gain/nstep3 | 4.746 | -0.574 | 4.05% | 280/1000 |
| oracle/matched | observed/nstep3 | 0.721 | +0.016 | 25.39% | 0/1000 |
| oracle/matched | gain/nstep3 | 0.710 | +0.005 | 27.51% | 0/1000 |
| oracle/drift | observed/nstep3 | 1.097 | +0.132 | 27.84% | 0/1000 |
| oracle/drift | gain/nstep3 | 1.046 | +0.081 | 30.00% | 0/1000 |

Greedy has zero counted degeneracies in every condition. Drift denotes the original linear odds schedule, not online adaptation. Per-seed and subset results remain in `summary.csv`; no seed was excluded.

## Normal condition: finding errors is not the same as reducing sink errors

Normal/matched step-level averages:

| Metric | Greedy | observed/nstep3 | gain/nstep3 |
|---|---:|---:|---:|
| Review flags | 37.47% | 42.81% | 43.71% |
| Selected node truly has base error | 39.28% | 45.35% | 45.85% |
| Sink reach, including self | 2.463 | 2.217 | 2.035 |
| Realized sink-error reduction per review | 0.3050 | 0.2903 | 0.2903 |
| Mean nominal chosen gain | 0.3210 | 0.3020 | 0.3065 |
| Same-history greedy minus chosen nominal gain | 0 | 0.2224 | 0.2030 |

Learned policies find more errors but deliver less terminal benefit. Their actions reach fewer sinks on average and frequently forgo the highest nominal immediate gain. These descriptive associations are consistent with insufficient prioritization of downstream benefit; they do not isolate its cause or prove that imitating greedy is optimal.

Degeneracy is uncommon and cannot account descriptively for the overall normal-condition loss: excluding each learned policy's own degenerate episodes leaves deltas +0.2426 and +0.2391. Those exclusions are policy-dependent and are not controlled interventions.

## Noise condition: strong type preference and misleading confidence

Noise/matched step-level averages:

| Metric | Greedy | observed/nstep3 | gain/nstep3 |
|---|---:|---:|---:|
| Selected confidence | 0.2079 | 0.4417 | 0.4314 |
| Fraction choosing type index 4 (prior base error 0.25) | 28.2% | 77.4% | 82.9% |
| Selected node truly has base error | 14.03% | 21.59% | 22.27% |
| Belief P(error) at chosen node | 0.7540 | 0.5972 | 0.6058 |
| Actual error at chosen node | 26.12% | 29.11% | 29.67% |
| Nominal chosen gain | 0.4309 | 0.1570 | 0.1686 |
| Realized sink-error reduction per review | 0.1209 | 0.1514 | 0.1509 |

Noise replaces confidence with independent uniform draws, while the posterior still applies the normal confidence model. Greedy selects lower-confidence nodes and its estimated gain greatly exceeds realized benefit. Learned policies strongly favor the highest-rate type and obtain more actual base errors and more terminal benefit despite lower nominal gain. This suggests type-prior selection as a concrete competing explanation for the noise advantage. It does not establish multi-step planning, adaptation, or a causal mechanism. An untrained type-prior-based greedy baseline is needed before attributing this pattern to RL specifically.

Gain estimates versus realized changes are trajectory averages, not a controlled calibration experiment. Selection, histories, finite-sample variation and model misspecification all affect them.

## Counted degeneracy is not necessary for the descriptive noise advantage

| Condition | Policy | Delta with degeneracy | Delta without degeneracy |
|---|---|---:|---:|
| noise/matched | observed/nstep3 | -0.7143 | -0.4353 |
| noise/matched | gain/nstep3 | -0.6736 | -0.4337 |
| noise/drift | observed/nstep3 | -1.0181 | -0.4309 |
| noise/drift | gain/nstep3 | -0.7893 | -0.4903 |

These subsets use the learned policy's own event indicator and the corresponding graph's original greedy outcome. They are observational, with different graphs and policy histories; they cannot estimate an effect of degeneracy. Absence of the counted event does not imply a well-specified or healthy posterior.

`n_degenerate` counts positive review observations with zero supporting error particles. On that event the filter skips resampling, clears the selected node's base-error particles, and refreshes propagated errors. It does not repair unsupported upstream causes. Noise/matched event rates are 240/16000=1.50% and 224/16000=1.40% of reviews; greedy is 0/3200. Noise/drift rates are 399/16000=2.49% and 379/16000=2.37%. Zero events in greedy is not evidence that its posterior is more accurate: its selected-node error probabilities under noise are highly optimistic.

## Next decision

Do not launch another full training run on these results. First specify a small development-only comparison with a type-prior belief-greedy baseline that ignores the noisy confidence channel, plus a simple type-prior ranking. A prior-only particle filter may still have finite-support failures; report them. This tests whether an inexpensive model correction explains the apparent learned advantage. Keep nominal greedy and the frozen learned checkpoints as references. Specify it before executing and do not use reserved confirmation graphs.

Separately, small-graph lookahead/exact-planning comparisons remain useful for measuring available long-horizon benefit. Independent confirmation and teammate clean-clone reproduction are still outstanding.
