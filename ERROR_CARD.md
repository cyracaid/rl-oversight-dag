# 错误说明书（Error Card）

范围：本仓库全部可引用数字 —— `experiments/`、`role2_규리/`、`role3 improvement/` 三条线。
日期：2026-11-24
用途：任何对外提交（课程、报告、论文、benchmark）的前置文档。**没有本文件，数字不得单独引用。**

## 0. 摘要（EN）

> The original premise — that per-node review scheduling is where residual error lives — is not supported on real data. Four independent views converge on the same null.
> Across three implementations, a deterministic marginal-value rule beats every learned policy we trained (paired differences 0.18-0.42 sink errors, all CIs excluding 0).
> Two claims do survive: a graph-aware value rule beats static confidence ordering, and trust in a possibly-corrupted confidence signal can be updated from review outcomes.
> One training result is real but does not deploy: per-review credit assignment improves the trained model and still loses to a two-step rule in the field.
> We report the nulls first because the project's value now lies in them, not in "RL wins".

## 1. 我们声称什么（可检验的四条）

| # | 主张 | 状态 | 证据 |
|---|---|---|---|
| A | 图感知的价值规则优于静态置信度排序 | 支持 | role3：marginal 0.66 vs confidence 1.03，五种形状全胜；role2：1.130 vs 1.545 |
| B | 置信信号可能被污染时，选择模型可降低误差 | 支持，**但仅限可检测的全局均值污染** | role2：4.415 → 3.150，−1.265 [−1.545, −0.985]；边界见第 2 节“门控适用范围”行 |
| C | 可从审查结果更新对信号的信任 | 支持 | role2：3.075 vs 3.820，−0.745 [−0.975, −0.520] |
| D | 学习策略优于上述规则 | **不支持（三次独立实现一致否定）** | 见第 2 节 |

## 2. 已知错误

分级：**F = 前提性（动摇项目立意）**、**S = 结构性（限制可比性）**、**I = 推断性（阻止结论）**、**P = 流程性（让错误流出）**。

| 级 | 错误 | 具体表现 | 后果 | 现状 | 证据 |
|---|---|---|---|---|---|
| F | **原前提错误** | 假设残差错误集中在“逐节点审查调度”上 | 四份真实数据视图一致显示几乎无余量可赢：真实 N=21 图阈值 0.50 vs 随机 1.88；单记录 75 条人工更正里两次审查后剩余 ≤0.10（阈值 0.08、结构 0.10，预算 8 时为 0.00–0.01）；跨记录 QC 规则达 0.014 vs oracle 0.000；KAIST 两晚 +0.000014 [−0.0014, +0.0012] | 已接受，贡献改向“估计哪路信号可信 + 不可信时安全行动” | `CROSS_IMPLEMENTATION_VALIDATION.md` §3、`experiments/results.md` §12a–12b |
| S | 三条线不可直接比较 | 不同 sink 定义、不同预算、不同种子、不同生成器 | 只有配对差值可迁移，原始均值不可跨线比较 | 已立法：引用必须标线 | 同上 §1–2 |
| S | 开发集被反复使用 | seeds 1000–1199 已用于开发，不能充当独立确认 | 早期“已确认”表述无效 | 已在未用 seeds 2000–2199 上重跑 | `PROPOSAL_COMPLETION_AUDIT` 第 6 行 |
| I | 门控适用范围被高估 | 200 张新图（seeds 3000–3199）上，门控只在 p·\|shift\| ≈ 0.75–1 附近才检出局部污染。保持排序的全图 −1 平移让 trust 仅比 oracle 差 +0.06，门控却判 195/200 为 noise、回退先验后多出 **+1.82 [+1.63, +2.03]** 个错误；掩盖真实错误的正向平移判 0/200，多 **+3.21 [+2.94, +3.48]** 个错误；13 个高判率格中回退仅 3 格有益、10 格有害 | 不能把 claim B 推广到局部、小幅度或掩盖型污染；需要节点级信任估计而非全局二值判定 | 已量化并写入 README | `role2_규리/results/corruption-v1/` |
| I | 学习策略未胜规则 | 三条线同向：1.14 vs 1.56；1.130 vs 1.410/1.590/1.455；0.66 vs 0.96/1.17/1.06 | 不能声称 RL 有增益 | 已确认集复现：GNN−marginal **+0.377 [+0.255, +0.510]** | 同上 |
| I | 算力不是瓶颈 | 10× 算力（1,000 → 10,000 episodes）后差值仅从 **+0.377 [+0.255, +0.510]** 收窄到 **+0.262 [+0.165, +0.365]**；三个种子的验证误差停在 0.94 / 0.96 / 0.98，规则为 0.885 | 不能以“训练不够”解释失败 | 已排除该解释 | `role2_규리/results/confirm-10x/`、`role3 improvement/outputs/v3_10x/train_*/gnn_observed_validation.csv` |
| I | credit assignment 的部署主张 | 训练端 4.549 → 2.926（−1.623 [−2.136, −1.033]，5/5 种子）；场上 2.945 vs 两步规则 2.765（规则领先 0.180 [0.021, 0.377]） | 训练有效 ≠ 可部署。任一单独引用都错 | 两句话必须同段出现 | `experiments/results.md` §13 |
| I | 消融不是真消息传递 | 旧 confidence ablation 训练与评估都传入零邻接 `A0`；未设 torch 种子；日志末行 oracle−normal 的算术/标注有误 | 不能称“已完成真实 GNN 的配对消融”，也不能据此归因机制 | 保留旧结果，标为有限证据 | `PROPOSAL_COMPLETION_AUDIT` 第 7 行 |
| I | 规划与残差增益不成立 | 两步规划 +0.035 [−0.025, +0.100]；残差 GNN +0.022 [−0.018, +0.072] | 不能写“规划有效”或“GNN 有额外贡献” | 已列为不支持 | `role2_규리/results/planning-v1`、`residual-v1` |
| P | 旧文档过度声称 | “gain/n-step 已落地”“credit assignment 已确证”“exact expected gain” | 与实际实现不符（gain 未拼进特征；主训练是终局 REINFORCE；粒子近似非精确） | 已修订表述，保留原文件 | 审计总结第 1 条 |
| P | 反向过度修正 | 曾把 credit assignment 整体写成“已撤回” | 抹掉了真实的训练效果 | 已改为两句话并存 | §13 |
| P | 独立复现缺失 | 没有第二位执行者的干净环境重跑记录 | 不能声称“队友已复现” | **未完成** | 审计第 16 行 |
| P | 真实系统集成未完成 | SciForge 只有本地只读原型与 openspec 草案 | 不能声称生产集成 | **未完成** | 审计第 15 行 |

## 3. 误差预算

| 环节 | 来源 | 量级 | 方向 |
|---|---|---|---|
| 环境生成 | sink 定义/预算/层数 | 三者不同线不可比 | 未知，禁止跨线比较 |
| 种子 | 训练种子 3–5 个；评估图 200 | CI 宽度约 ±0.1–0.3 sink errors | 已知，已配对报告 |
| 确认集 | 开发集复用 | 早期数字偏乐观 | 已用 2000–2199 校正 |
| 算力 | 1× vs 10× | 差值 +0.377 → +0.262 | 收窄但排序不变 |
| 真实数据 | N=21、75 条更正、公共日记 | 样本极小，效应近零 | 不能外推到其它流程 |
| 队友复现 | 无 | **未知** | **未知** |

## 4. 不可比的情形

1. 把三条线的原始均值并列（1.14 / 1.130 / 0.66 不是同一把尺）。
2. 用开发集（1000–1199）的结果说“独立确认”。
3. 用 1× 算力结果说“再多训练就能赢”（10× 已排除）。
4. 用训练端改进说“模型可部署”（场上已被规则击败）。
5. 用合成图结论说真实睡眠流程有收益（四份真实视图均为零）。
6. 引用不带线标签的表格。

## 5. 什么会推翻我们现在的说法

- 若在未使用种子上出现某个学习种子稳定胜过 marginal（配对 CI 排除 0），则“规则胜学习”需撤回。
- 若 10× 之后继续加算力使验证误差跌破 0.885，则“平台期”判断需撤回。
- 若真实数据上逐节点调度出现可重复增益（例如换一套 N≥100 的真实 DAG），则“无余量”需限定到当前数据。
- 若队友在干净环境复现失败，则所有数字降级为单执行者证据。

## 6. 复现收据（2026-11-24 实跑）

三条线各抽一条主链重跑，比对已发布表格。三处全部一致；重跑输出写在临时目录，未纳入仓库。

| 检查 | 命令 | 结果 |
|---|---|---|
| role3 冻结 checkpoint vs 已发布表 | `run_benchmark.py --families spike --seeds 100 --start-seed 90000 --checkpoints outputs/v3/train_{1,2,3}/{gnn,dqn}_spike*.pt` | confidence **1.0300**、marginal **0.6600**、GNN 0.96 / 1.17 / 1.06、DQN 1.53 / 1.23 / 1.34，与 `변경내역.md` 逐格一致 |
| role2 独立确认集 | `evaluate_conditions.py --confirm --graphs 200` | 4,200 行、21 格一致；matched 下 marginal **0.885**、confidence 1.275、GNN 均值 **1.262**、type_prior 3.735 |
| role2 两步规划 | `evaluate_planning.py --graphs 200` | 12 格一致；shuffled 下 mixture **3.075**、adaptive **3.110**、差值 **+0.035**；`episodes_sha256` 与已发布 `planning-v1` 相同（`f0022485…`） |

未在本次复跑范围内：`sleep-v1`（KAIST 数据不在仓库）、`credit-v1`、`residual-v1`、多种子 CI 重算。

## 7. 引用规则

1. 每个数字必须标线：`experiments/` / `role2_규리/` / `role3 improvement/`。
2. 跨线只引用**配对差值**，不引用原始均值。
3. 训练效果与部署效果必须同段出现，不能只引一句。
4. 零结果写在正结果前面。
5. “未完成”就写未完成，不写“进行中”。

## 8. 状态

| 项 | 状态 |
|---|---|
| 三条主链抽样复跑 | 通过（benchmark / confirm / planning） |
| 全量收据（sleep-v1、credit-v1、residual-v1、多种子 CI） | 未在本次范围 |
| 独立确认集（2000–2199） | 已完成 |
| 10× 算力对照 | 已完成，排序不变 |
| 队友独立复现 | **未完成** |
| SciForge 生产集成 | **未完成** |
| 可声称的最强结论 | 规则胜学习；信号可信度可学习；逐节点调度在真实数据上无余量 |
