# Pre-registration — can instance-level contrastive learning (no labels) do better?

Frozen 2026-11-25, before any run. Blocks: **train 5024–5119, evaluation 5120–5159**
(96 training and 40 evaluation episodes per family). Committed before the encoder
exists.

Correction made before the first training run, recorded here rather than silently: the
first draft of this file said train 5024–5059 / evaluation 5060–5099, which is only 36
training episodes — fewer than the frozen batch of 64, so the "batch 64" line would have
been decorative. The block was widened to 96 so the frozen batch is a real batch. No
evaluation was computed under the narrower block; the only code that ran before this
edit was a six-episode, two-epoch smoke test of the tensor plumbing.

## Question

Three pre-registered experiments removed every mechanical explanation of the residual
gap to `oracle`: one-step value, probability scale, and horizon. What is left is
"information the confidence channel does not carry" (§11 of the course report). The
obvious next move, and the one this file prices, is the *label-free* one:

> If we never show the model which nodes are wrong, but let it learn an instance-level
> representation of the review state, does that representation (a) recover the error
> structure, and (b) carry anything that the confidence channel lacks?

The design is deliberately the analogue of instance-prototype contrastive learning
(IPCL; Konkle & Alvarez 2020/2022): no category labels, positives are two augmented
views of the same instance, negatives are everything else, and the learned geometry is
then compared with an independently measured geometry (there: brain responses; here:
the latent error structure, and — qualitatively only — human corrections).

**What is unsupervised and what is not.** The encoder is trained with no labels of any
kind. The readout is a linear probe fitted on labelled *training* episodes and evaluated
on held-out episodes — the same split the IPCL paper uses when it probes frozen features.
Any claim in the report must say "label-free representation, supervised readout".

## Instance, view, augmentation

| object | definition |
|---|---|
| instance | one `(episode, node)` pair: a node's review state in one sampled pipeline execution |
| view | the same pair with a random corruption applied to the public features only |
| augmentation | 30 % of non-centre nodes have their confidence/belief/effective columns reset to the type prior; the centre node's confidence/belief columns are reset with probability 0.5; 20 % of edges are dropped |
| positive | the two views of one `(episode, node)` pair |
| negative | every other `(episode, node)` pair in the batch |
| objective | InfoNCE, temperature 0.2 |

No hidden variable ever enters an input. The augmentation is the only place where a
prior about "what may be missing" enters, and it is stated here so a reader can disagree
with it.

## Frozen settings

- families `real`, `ticket` (21 nodes, budget 8) and `spike` (80 nodes, budget 16);
- encoder: 2 message-passing layers (parent and child aggregation, edge-probability
  weighted), hidden 64, embedding 32, L2-normalised;
- InfoNCE: Adam, lr 3e-3, 200 epochs, batch 64, two views per instance;
- supervised twin: identical encoder, BCE on the node's own source error, same schedule;
- probe: logistic regression on frozen embeddings; baseline probe: logistic regression on
  the node's own public features (confidence, logit, type one-hot, sink reach, belief);
- scheduler: rank available nodes by the probe's score, budget as above, `p_catch = 0.9`;
- evaluation: 40 episodes per family on 5120–5159, paired inside an episode;
- CIs: 2000 bootstrap resamples over evaluation episodes;
- sign convention: **policy − comparison**, negative means fewer sink errors.

Hyperparameters are frozen. If the run is reported at all, it is reported with these
settings; no grid is run and nothing is selected on the evaluation block.

## Predictions

| # | prediction | verdict rule |
|---|---|---|
| C1 | the label-free geometry tracks the latent error geometry: Spearman ρ(embedding RDM, truth RDM) ≥ 0.30 on `real` **and** `ticket` | pass if both ≥ 0.30, fail if either < 0.30 |
| C2 | the structure adds nothing beyond the node's own channel: AUC(contrastive probe) − AUC(own-features probe) ≤ +0.02 | fail if the difference exceeds +0.02 with a CI excluding 0 |
| C3 | no scheduling gain: `contrastive − marginal` ≥ −0.05 errors per episode at the point estimate, and its 95 % CI lower bound > −0.05 | contradicted if the CI excludes −0.05 in the improving direction |
| C4 | labels help fit but not the action: AUC(supervised) ≥ AUC(contrastive), and `supervised − marginal` ≥ −0.05 as in C3 | both parts reported separately; the second is the one that matters |
| C5 | (exploratory, no verdict) on the `real` graph the four time nodes (`time_bed`, `time_sleep`, `time_awake`, `time_getup`) sit closer together in the label-free embedding than the median node pair, consistent with 40 of 53 replayed human corrections being order errors | reported as a number with its n, never as confirmation |

## What would change our mind

If C3's CI excludes −0.05 in the improving direction, the repository's "the gap is
information, not the scheduler" claim is wrong for this model class and must be rewritten.
If C2 fails (structure adds > 0.02 AUC) while C3 holds, the representation carries
information that the greedy rule cannot use, which is a different and more interesting
finding, and would justify a deeper planner on top of the learned state.

If C1 fails, the geometry result is reported as a failure of the augmentation, not of the
idea, and the augmentation is named as the suspect.

## Limitations stated in advance

- simulation only; the real 75 corrections enter C5 as a qualitative check;
- graphs here are 21 and 80 nodes; nothing is claimed for N = 500;
- the probe uses labels, so this is not "unsupervised scheduling";
- one architecture, one temperature, one augmentation; the paper this borrows from found
  architecture and normalisation matter more than accuracy, so a single architecture can
  only produce a pilot, not a verdict about contrastive learning in general.
