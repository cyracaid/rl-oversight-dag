# Proposal 完成度审计

审计日期：2026-11-12。依据当前工作区的 `PROPOSAL_COURSE.md`、`RL_PLAN.md`、源码及保存结果。
只读核验，没有重新训练或运行全量评估，没有访问私有参与者记录。
“完成”表示该实验/实现存在证据，不表示方法获胜，也不表示独立确认或真实部署完成。

状态限定为：**已完成并有证据 / 已实现但未验证 / 计划或设计 / 未完成**。
旧实验的运行证据强度低于带逐图数组、checkpoint 和 provenance 的 boundary-full-v1。

| # | 用户列项 | 状态 | 证据及限定 |
|---|---|---|---|
| 1 | DAG 环境建模 | 已完成并有证据 | `experiments/spike_active_selection.py`、`dependency_review_sim.py`；合成图及错误传播已用于保存实验。`real_pipeline_graph.py` 是手工编码的 N=21 管道结构上的模拟。 |
| 2 | MDP / sequential review | 已完成并有证据 | `spike_active_selection.py:review_step`、`rl_gnn_multiseed.py:run_episode`；逐步选未审节点、观察、修复源头错误、更新 belief、终局 sink-error 奖励。隐藏真实状态时严格说属于部分可观测过程；用 belief/观测构造策略状态。主方法固定预算，STOP 仅在 CMDP 变体。 |
| 3 | Q-learning、REINFORCE、GNN 等 | 已完成并有证据 | Q-learning：`dependency_review_sim.py`、`experiments/results.md`；MLP REINFORCE/PPO/DQN：`rl_methods_compare.py`、`methods_compare.json`；GNN：`rl_gnn_multiseed.py`、`gnn_results.json`、full-v1 checkpoints。Q-learning 属于旧 bandit 版本，不能混成当前序贯 GNN。实现并运行不等于赢过 baseline；CMDP/PPO 的后续升级未完成。 |
| 4 | Belief particle filter | 已完成并有证据 | `experiments/belief.py`、`test_semantics.py`、`test_boundary.py`，并用于 full-v1。粒子近似有退化事件，不是精确后验。 |
| 5 | Belief greedy baseline | 已完成并有证据 | `belief.py:gain/best_action`，full-v1 matched 平均 1.100；只看允许的 belief、结构及观测。期望收益在粒子近似下计算，proposal 的“exact expected”措辞过强。 |
| 6 | 200 held-out graphs | 已完成并有证据（含独立确认） | `gnn_results.json`、`final_table.md`，full-v1 三份逐图结果均为 seeds 1000–1199；学习策略有 5 个训练种子。它们已反复用于开发，不能再当独立确认集。独立确认已于 2026-11-24 在未使用的 seeds 2000–2199 上运行：`role2_규리/results/confirm-v1/`，marginal 0.885 vs GNN 1.262，GNN−marginal +0.377 [+0.255, +0.510]；同集信号门控 −1.420 [−1.695, −1.150]。原始均值与开发集不可直接比较，仅配对差值可迁移；门控只在易分的均匀噪声上验证。10× 算力对照（10,000 episodes）已跑：GNN−marginal 收窄到 +0.262 [+0.165, +0.365]，held-out validation 平台停在 0.94–0.96（规则 0.885），排序不变，见 `role2_규리/results/confirm-10x/`。补充：门控的均匀噪声结论已在 200 张新图（seeds 3000–3199）上扩成局部性×幅度×覆盖率边界测量，见 `role2_규리/results/corruption-v1/`：全图 −1 平移保持排序、trust 仅比 oracle 差 +0.06，门控却判 195/200 为 noise、回退先验后多出 +1.82 [+1.63, +2.03] 个错误；反之在真实错误节点上加 +3 掩盖错误时判 0/200、trust 多 +3.21 [+2.94, +3.48] 个错误。该实验为探索性边界测量，不是预注册确认检验。 |
| 7 | Confidence ablation | 已完成并有证据（旧消融，有限） | `rl_ablation.py`、`ablation_log.txt`：3 seeds ×12k，normal/noise/oracle=1.38/3.78/0.72，评估 legacy 图，不是 200 图 full-v1 消融。源码训练和评估均传入零邻接 `A0`，不能称已完成真实消息传递 GNN 的配对消融；未设置 torch 训练种子。日志最后 oracle-normal 的算术/标注也有错误，不能引用其机制归因。 |
| 8 | RL 加 belief features | 已完成并有证据 | `rl_gnn_multiseed.py:features` 明确加入 P(base error)、P(error)、reviewed、flagged、budget。旧表 static/observed 均约1.56；full-v1 为1.517/1.709。未加入 entropy；不同运行不混为同一表。不能从失败唯一归因 credit assignment。 |
| 9 | Gain features + GNN | 计划或设计 | `RL_PLAN.md` 提出 gain(i) 输入；当前 features 只有 K+2/K+7，未拼接 gain。`belief.gain()` 与 two-step 使用 gain 不是 gain-conditioned GNN。BC 模仿 greedy 也不能替代这项实验。 |
| 10 | Actor-critic / n-step credit assignment | 计划或设计 | `RL_PLAN.md` 计划 n=3/5、AC；当前主训练是终局 REINFORCE + EMA baseline。无对应多种子实验产物。已有 PPO/DQN/CMDP 不能替代所承诺的 AC/n-step 对照；双 critic CMDP 未完成。 |
| 11 | Model misspecification | 已完成并有证据 | full-v1 `misspec/results.json`：propagation odds ×0.5/2、confidence logit ±0.5，另有 matched 和两个 reviewer shift 条件，共7条件。真实环境在前5条件固定，扰动的是假设模型；不是 λ×0.5/2 原始计划的完全同款实现。RL 未显示胜出。 |
| 12 | Non-stationary error rates | 计划或设计 | 未发现跨 episode/审查步改变真实类型错误率的实现与结果。固定 calibration/propagation 扰动或 catch shift 不构成时间漂移实验。 |
| 13 | Reviewer miss rate 30% | 已完成并有证据 | `rl_boundary.py:SCENARIOS` 和 full-v1 `catch0.7_known/unknown`；真实 catch=0.7，模型假设0.7或0.9。greedy=2.350/2.345；5训练种子×200图结果已保存。 |
| 14 | 与 2-step greedy 比较 | 已完成并有证据 | `rl_boundary.py:two_step_action`、`planning/results.json`：matched greedy1.100、2-step1.020，Δ−0.080，95% CI[−0.160,−0.010]。近似粒子两步回溯、开发集；不是独立确认或精确 POMDP 求解。 |
| 15 | SciForge 真实系统集成 | 未完成 | `sciforge_review/README.md` 明确本地只读原型和 openspec 草案；没有主系统真实 DAG 接入、在线审阅端到端收据和部署验收证据。N=21 模拟、1,048 flags/68 positives 聚合分析、A/C 案例设计均不构成生产集成。 |
| 16 | 队友独立复现实验 | 未完成（尚无证据） | 当前没有第二位执行者的干净环境重跑记录、版本绑定及结果对照。用户完成 full-v1 是真实执行证据，但不能据此推定“队友已独立复现旧表”；应另记独立复现协议和产物。 |

## 总结与后续

按用户实际列出的16项计：**11项有执行/实现证据（其中 confidence ablation 仅旧版有限证据），3项停留在计划，2项未完成**。
没有单独一项仅达到“已实现但未验证”：本次发现的缺口多为对应实现尚未落地。
若要求“真实消息传递 GNN 的规范 confidence ablation”，该项也尚未完成。

应保留的结论：当前 RL 没赢 belief greedy；BC→FT 在 full-v1 五个种子均退步；两步规划只有开发集小幅收益。
未证实的机制：credit assignment 是唯一瓶颈、同样边际 belief 意味着相同决策信息、oracle 消融能识别真实系统瓶颈。

优先补齐：

1. 修订旧文档中“gain/n-step 已落地”“credit assignment 已确证”等超出证据的表述，保留旧结果原文件。
2. 若继续课程 RL 扩展，另建 gain-conditioned GNN 与 AC/n-step 设计和运行产物；不把 BC/FT 改名充数。
3. 非平稳性须先定义真实错误率随时间如何变化，再运行；静态模型误设结果不能替代。
4. 独立确认和队友复现分开记录：独立确认已于 2026-11-24 在 seeds 2000–2199 上完成（见第 6 行），两步收益仍只有开发集证据；队友从干净环境重跑仍无证据。
5. SciForge 主系统集成是独立工程工作流，需真实接口/端到端验收；API开发诊断亦仍无成功生成证据。

本审计不自动启动训练、部署、提交或推送，也不修改用户已有源码与结果。
