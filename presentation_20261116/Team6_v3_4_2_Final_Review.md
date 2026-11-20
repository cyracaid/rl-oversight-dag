# Team 6｜v3_4_2 英文讲稿最终核对与修订稿

课程提案专用｜冻结版内容｜2026-11-16

## 1. 核对范围与结论

依据：6조_제안발표_v3_4_2.pptx 的13页文字与发表者备注、Team6_Script_v3_4_2_EN.txt，以及冻结的 boundary-full-v1 实验记录。

整体研究主线与附录数字一致。本文只修正事实范围、技术定义和英文表达，不加入之后的新实验。原 PPT 和原英文 TXT 均未覆盖。文献对比的建议属于谨慎限定措辞，本次未重新逐篇核验原论文。

原英文主讲约995词，按130词/分钟约7分40秒，尚未包含切页和停顿。因此下文提供按原11页顺序压缩的英文口述稿，附录两页仅供问答，不朗读。请用最终英文稿计时排练；页数不等于发表时长。

## 2. 逐页修订清单

第1–2页：姓名、团队、题目和目录可保留。

第3页｜避免必然传播：原文说错误最终一定使结论错误，过强。用“can propagate”及“may affect the final conclusion”，表示传播取决于依赖和传播机制。

第4页｜固定预算，不是固定200条：不同顺序选出的前200条记录未必相同。“the same 200 records”改为“the same budget of 200 reviews”。13%和84%是对队列中68条已确认错误的覆盖率，不是准确率。准确值为13.2%与83.8%，口述可取整。将“actual errors”改为“human-confirmed errors”。韩语“시각 순서 규칙에 걸린 기록”本身正确，是指被规则标记，不是符合规则。

第4页｜限制类型聚集结论：76%描述75条人工修正记录中的57条，不代表所有潜在错误的类型比例。68条队列错误和75条修正记录属于不同集合，不能互换。

第5页｜保持限定：保留“within the scope of our survey”；不要说首次、唯一或不存在先例。

第6页｜依赖关系表述：将“Oversight treats items as independent”改为“does not explicitly model error propagation through a dependency graph of this kind”。未显式建模不等于证明对象独立。FALCON与WS-option的对比也应限定为本研究这种错误传播与隐藏错误人工审查任务。

第7页｜目标是审查收益：不能说必须先选错误概率最高的节点。应结合错误概率与下游影响，按估计审查收益选择。图中两次查出全部隐藏错误只是示例，不是保证。研究目标用“aim to learn”，不预先保证学到最优顺序。

第8页｜部分可观测性：真实错误隐藏，原始任务是部分可观测的。用近似belief表示，按MDP方法求解；不要声称若干节点边缘概率就保证严格Markov充分性。belief应随审查反馈更新，不只是由初始置信度产生。

第8页｜修复条件：只有审查发现错误时，才清除该节点自身的基础错误并重算下游。审查可能漏检，来自未修复上游的错误仍可能存在。建议同步修改PPT的Transition表格。

第8页｜序贯不等于必须RL：最后一句改为“a sequence of decisions rather than a single ranking”。有序贯结构并不证明必须用学习，也不保证学习优于greedy。

第9页｜计划与完成分开：REINFORCE、PPO、DQN是冻结提案的比较设计；附录报告已完成的REINFORCE与模仿学习预实验。不要暗示附录已覆盖全部算法。真实管道结构评估也不得称为真实系统部署验证。保留同图、同隐藏错误及共同随机数的配对设计。

第10页｜负结果边界：学习策略输给规则，不足以证明规则已经足够或最优。“why the rules are enough”改为“why rules perform better under the tested conditions and what limits learning”。PPT的“학습 ≥ 규칙”易与错误越低越好的指标混淆，建议用文字“Learning performs better”与“Rules perform better”。

第11页：结束语可保留。

第12页｜保留冻结数字：2-step greedy 1.020；belief greedy 1.100；confidence threshold 1.440；REINFORCE/static 1.517；REINFORCE/observed 1.709；BC 1.201；BC+fine-tuning 1.525。均为预算16次审查后的平均残余终端错误。

第12页｜七条件结论：明确指从头训练的REINFORCE与BC+微调。BC在一个条件下均值略优，但未证明优势；不能说所有学习方法在七条件中均值全部更差。五个训练种子适用于学习策略，规则不是五个独立训练模型。

第12页｜执行来源：将“produced/generated with an AI agent”改为“obtained by executing the experiment code”。AI参与执行不代表数值由AI编造。独立复现与预留确认集评估是两件尚未完成的事。

第13页｜终端节点可有多个：将“the most downstream node”改为“a terminal, or sink, node representing a final output or conclusion”。belief严格说是隐藏错误状态的概率表示；节点错误概率是其摘要。REINFORCE使用采样轨迹的回报估计策略梯度，不是只凭一个标签更新。

## 3. 英文口述稿｜按原11页顺序，约5分钟排练版

以下只朗读英文段落。实际时长依语速、切页和停顿而定。

### Slide 1 — Cover

Hello, I’m Kwanghee Han, presenting for Team 6. Our topic is “Review Scheduling on Dependency Graphs under a Limited Budget”: deciding what to review first when human review time is limited.

### Slide 2 — Contents

I’ll cover the background, related work, objectives, methodology, and expected results.

### Slide 3 — Error Propagation

Research pipelines connect data collection, preprocessing, analysis, and conclusions. A wrongly recorded input can affect derived values and downstream conclusions. This motivates reviewing not only suspicious records, but also records whose correction could protect downstream outputs.

### Slide 4 — Review Order Matters

In a team member’s sleep research data, an automated audit flagged 1,048 records, including 68 human-confirmed errors. With a budget of 200 reviews, file order finds about 13 percent of those confirmed errors. Prioritizing records flagged by a time-order rule finds about 84 percent. Separately, 57 of 75 manually corrected records involved time-order errors. These are different sets. The example shows that review order matters under a fixed budget.

### Slide 5 — Related Work

We connect three research areas: deferring decisions to humans, selecting reviews under a budget, and downstream error propagation. Within our survey, we did not find work directly combining all three. [Click] Their overlap motivates our formulation.

### Slide 6 — Our Position

FALCON studies budgeted deferral. Oversight studies limited review capacity. Neither explicitly addresses the dependency-graph error propagation considered here. WS-option studies budgeted graph-node selection, rather than our hidden-error human-review task. We combine these concerns by selecting reviews while estimating hidden errors on a dependency graph.

### Slide 7 — Objectives

We aim to learn a review sequence that reduces final errors within a fixed budget, and identify when learning helps over rules. With only two reviews among eight nodes, we must consider both error probability and downstream impact. Each review outcome informs the next choice. The figure illustrates finding both hidden errors; this is an example, not a guarantee.

### Slide 8 — Decision Formulation

Errors are hidden, so we use an approximate belief representation to approach this partially observable problem as an MDP. Inputs include node type, confidence, downstream impact, review history, estimated error probabilities, and remaining budget. An action selects an unreviewed node. If an error is detected, that node’s own base error is corrected and downstream states are recomputed; inherited errors may remain. The terminal reward is minus the remaining sink-error count. This creates a sequence of decisions rather than a single ranking.

### Slide 9 — Comparison Design

We pair policies on the same graphs, hidden errors, and review randomness. Baselines use confidence, downstream impact, or belief greedy’s estimated immediate benefit. The planned learning comparison includes REINFORCE, PPO, and DQN with GNN node scoring. We use roughly 80-node synthetic graphs and a 16-review budget. We also examine model mismatch and plan complementary evaluation on the sleep-pipeline structure. The appendix reports completed preliminary experiments, rather than every planned comparison.

### Slide 10 — Expected Contribution

If learning performs better, we will identify the conditions. Otherwise, we will analyze why rules perform better in the tested setting and what limits learning. Our deliverables are a reproducible simulator, comparisons, and evidence for allocating review effort. Initial results favor strong rules; they do not establish that rules are always sufficient.

### Slide 11 — Closing

Thank you. We welcome your questions.

## 4. 英文附录｜问答参考，不朗读

### Slide 12 — Preliminary Results

These are frozen boundary-full-v1 development results: 200 graphs, a review budget of 16, and five training seeds for each learned policy. The metric is the mean number of residual sink errors; lower is better.

2-step greedy: 1.020. Belief greedy: 1.100. Confidence threshold: 1.440. REINFORCE with static features: 1.517. REINFORCE with observed-state features: 1.709. Behavior cloning, or BC: 1.201. BC plus fine-tuning: 1.525.

BC learns to imitate belief greedy’s actions. Across all seven evaluated conditions, REINFORCE trained from scratch and BC plus fine-tuning had higher mean error than belief greedy. BC had a slightly lower mean in one condition, but the comparison did not establish an advantage.

The values were obtained by executing the experiment code. Independent reproduction and evaluation on the reserved confirmation set remain pending. These results do not establish that all reinforcement-learning methods are inferior.

### Slide 13 — Data and Terms

Data: 13,990 sleep-diary rows from 237 participants. The audit queue contains 1,048 flagged records, including 68 human-confirmed errors, or approximately 6.5 percent. Separately, 75 records were manually corrected, including 57 time-order corrections, or 76 percent. The queue errors and correction records are different sets. Raw participant data remain private; only aggregates are used here.

Belief: a probability representation of hidden error states, summarized here by estimated per-node error probabilities.

Belief greedy: a rule selecting the node with the largest estimated immediate reduction in sink errors under the current belief, with a fallback when all estimated gains are zero.

Conclusion node: a terminal, or sink, node representing a final output or conclusion. A graph may contain several such nodes.

REINFORCE: a policy-gradient method that uses sampled trajectory returns to estimate the policy gradient.

## 5. 提交前核对

保持原13页结构及冻结实验数字。优先同步第4、8、9、10页和附录的关键措辞；仅改口述稿而不改幻灯片，仍可能出现表达不一致。

确认发表时长与允许语言。本文按现有需求准备英文讲稿，不从PPT的韩语文字推断口头语言要求。主讲排练只覆盖第1–11页，附录用于问答。

本文件是核对与修订建议，不代表原PPT已修改，也不代表已完成LearnUS上传。不要把讲稿审阅文档当作课程要求的PDF幻灯片提交。

依据记录：PROPOSAL_COURSE_CN.md 中真实队列 recall@k 与修正记录汇总；experiments/BOUNDARY_FULL_V1_INTERPRETATION.md 中 matched 数值、七条件结果与验证限制。仅使用既有聚合信息，未访问参与者级原始记录。
