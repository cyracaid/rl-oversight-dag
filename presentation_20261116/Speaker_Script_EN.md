# Team 6 - English speaker script

Project title: Review Scheduling on Dependency Graphs under a Limited Budget

Main delivery: 7 slides, 290 seconds plus 10 seconds of transitions. Backup slides 8-10 are not spoken unless requested.

## Slide 1 (25 seconds)

We study how to allocate a limited human review budget across a graph of dependent outputs. An upstream error can affect several downstream conclusions, so reviewing the most suspicious item is not always the best choice. Our question is whether reinforcement learning can learn a better sequence of checks than a strong adaptive greedy policy.

## Slide 2 (35 seconds)

Consider a pipeline that parses an input, computes derived metrics, and produces conclusions. A shared upstream mistake can contaminate multiple outputs. A review both reveals information and may repair an error, changing which node is useful to inspect next. The application is evidence review in research workflows. Our current performance experiments use synthetic graphs; they are not a validated deployment in a real research system.

## Slide 3 (45 seconds)

We formulate the environment as partially observable and use a particle belief over hidden errors. The policy observes graph structure, confidence, review history, and remaining budget. Each action selects an unreviewed node. The outcome updates both the graph error state and the belief. After sixteen reviews, the reward is the negative number of erroneous sink nodes. We use an undiscounted finite horizon, with gamma equal to one.

## Slide 4 (45 seconds)

Our baseline is belief greedy: it updates its posterior after each review and chooses the largest estimated immediate reduction in sink errors. The learned methods share a graph neural policy. We compare REINFORCE, a learned critic using full Monte Carlo targets, and three-step or five-step bootstrap targets. We also test whether providing estimated gain as an extra input helps. This connects directly to policy gradients, Monte Carlo learning, temporal-difference bootstrap, and function approximation.

## Slide 5 (55 seconds)

The completed development run trained one hundred and twenty policies, for two point four million episodes in total. In the primary condition, belief greedy leaves 1.020 sink errors on average. The best learned mean is 1.255, for gain plus three-step targets, about twenty-three percent worse. All eight learned candidates have worse performance, with multiplicity-adjusted difference intervals above zero. This is a negative result for the current implementation, not evidence that reinforcement learning can never help.

## Slide 6 (50 seconds)

An exploratory result suggests a narrower follow-up. Under noisy confidence, observed three-step learning has 3.477 errors versus 3.965 for greedy. However, noise changes both confidence and the derived belief, and the particle filter sometimes degenerates. We will first inspect action choices and belief failures, rather than launch another large training run. If the pattern survives those checks, we will freeze a robustness hypothesis and evaluate on fresh graphs and training seeds. That confirmation has not been performed.

## Slide 7 (35 seconds)

Our project contribution is a reproducible evaluation of when learning is worth its complexity in graph review scheduling. The remaining deliverables are an action-level diagnosis, a precise follow-up hypothesis, and an independently checkable evaluation. We will report a negative result if greedy remains best. We will not claim real-system benefit before testing it. The central question is simple: under what information and model conditions does a learned review sequence improve on adaptive greedy? Thank you.

## Slide 8 (backup)

Backup only. All eight primary contrasts use paired graph outcomes and crossed seed/graph resampling. All adjusted intervals lie above zero. All ten secondary adjusted intervals cross zero, so the current analysis does not establish gains from either the input augmentation or the learning-target changes.

## Slide 9 (backup)

Backup only. Belief greedy is adaptive and deployable given its assumed model; oracle information is not deployable. Negative results are informative only within the tested task, methods and information assumptions. A weak DQN result would not prove policy gradients are uniquely appropriate, and we do not make that claim.

## Slide 10 (backup)

Reference and reproducibility slide; not part of the five-minute delivery. This is a prospective development protocol written after training started, not a pre-training registration. No independent confirmation or clean-clone teammate reproduction has been completed.

## Chinese preparation notes

核心问题：有限预算下，怎样安排图上的人工审阅顺序？当前主结果支持 greedy，而不是 RL 优势。不要把任务具有序列结构，说成 RL 必然优于规划。

模型：真实错误隐藏，用粒子 belief 近似；动作是选下一个未审阅节点。16 步后，以残余终端错误的负数作为奖励，gamma=1。

主结果：greedy=1.020；最好学习均值=1.255，仍差约23%。噪声条件仅是下一步研究线索。真实系统部署、独立确认和队友复现均未完成。
