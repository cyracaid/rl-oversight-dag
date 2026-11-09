---
title: "依赖图审阅调度 — 实现规格书（中文）"
layout: default
---

# 依赖图审阅调度 — 实现规格书（中文）

<p><b>语言：</b> <a href="https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC.html">中文（网页版）</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_EN.html">English</a> · <a href="https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html">한국어</a></p>

> STA3145 RL 小组项目 · 实现设计（不是实测结果）· 2026-11-09
> 对应英文版：`IMPLEMENTATION_SPEC.md` · 叙事文档：`PROJECT_CN.md`
> 风格说明：本文档确定**搭建时需要的选择和假设**。下面的速度、内存、episode 数、奖励是起始值；除非某节标注「已跑」，否则不是测量结论。

---

## 1. 研究目标与模型范围

AI（分类器、LLM 标注器、日记清洗管道）产出一条相互依赖的条目链。人只能审少数几项。错误不随机：按类型聚集，没审的错误污染建在它之上的一切，危害到结论才出现。

**我们训练的**：一个策略，决定*下一个审哪个节点*（或停止），在预算内。

**我们不训练的**：底层分类器、LLM、视觉模型、splsleep 的 R 包。它们是冻结的环境。

**核心区分**：结果报告为**模拟性能**——(a) 合成 DAG、(b) 从 splsleep SCHEMA 编码的真实管道 DAG、(c) 75 条人工纠错的动机数字。不声称生产 LLM 服务器或临床部署。

**研究问题**

- **RQ1** 学到的策略（REINFORCE / PPO / GNN 打分器）在 mean sink 错误上能不能打赢最好的*固定*规则（按类型校准阈值、结构贪心）和可部署的**信念贪心**（粒子滤波信念上的自适应贪心）？
- **RQ2** 优势是否依赖图族（模块化 / 无标度 / 稀疏 / 真实管道）、预算、置信度信号质量？
- **RQ3** RL 没赢的时候，能不能定位剩余误差（策略 vs 预测器 vs 审阅者漏检率）？

**已跑（AI agent，未独立复现）**：80 节点重构（bandit 负结果；200 张留出图上信念贪心 1.14 打赢 GNN 1.56，配对差 +0.42 ± 0.15）；消融（noise 3.78 / normal 1.38 / oracle 0.72）；N=500 启发式（信念贪心 vs oracle 贪心）；真实管道阈值 2.12 → 0.50。本规格书是组员复现和扩展这些数字的操作手册。

---

## 2. 环境规格（冻结的选择）

### 2.1 三种图族 + 一个真实管道

| 图族 | N | 典型边数 | 生成器 | 用途 |
|---|---|---|---|---|
| `spike`（主 RL） | 80 | 约每节点 2 父，4 层 | 分层 DAG，5 类型 | GNN / REINFORCE / PPO / DQN |
| `modular` | 500 | ~750 | 10 簇 × 50；簇内高，簇间仅经 3 个接口节点 | 规模基线 |
| `ba` | 500 | ~1491，最大度 ~64 | Barabási–Albert `m=3`，低→高索引定向 | 无标度 / hub |
| `er` | 500 | ~1850，最大度 ~14 | Erdős–Rényi `p=0.015`，低→高定向 | 稀疏对照 |
| `real` | 21 | 4 个 sink | 手工编码 splsleep SCHEMA | 应用 |

**DAG 定向规则（BA / ER）**：无向边 `{u,v}` 若 `u<v` 变 `u→v`，否则 `v→u`。去自环。Kahn 算法必须恰好返回 N 个节点，否则丢弃该种子。

**模块化接口**：只有簇 *c* 的最后 3 个节点可能指入簇 *c+1* 的前 5 个节点，概率 0.5。

### 2.2 类型和基础错误率

**80 节点主实验（K=5）**。`P_TYPE = [0.01, 0.03, 0.08, 0.15, 0.25]`（致命→温和；早期 80 节点跑过 `[0.02,0.05,0.12,0.22,0.35]`——表格要注明用的哪套）。

**500 节点（K=10）**。Zipf `p_t ∝ t^{-1.2}`，映射到 `0.02 + 0.38 * 归一化权重`。致命类型 ≈ 0.17，最温和 ≈ 0.03。

**真实管道（K=6）**。速率对齐 75 条纠错：

```
order_error             0.35   # 人类纠错的 76%
awake_getup_diff_error  0.15
bed_sleep_diff_error    0.12
sleep_awake_equal_error 0.10
sleep_awake_24h_error   0.08
metric_spike            0.05
```

### 2.3 传播（因果干预形式）

每条边 `(u,v)` 每个 episode 抽一次 `w_uv ~ U(0.5, 1.5)`（烘进 `coins`），然后

```
P(X_v = 0 | X_u = 0) = 1 - exp(-λ * w_uv)
λ = 0.8   (500 节点)     λ = 0.9   (真实管道)
```

审节点 `v` 只清除 **v 自身（源头）的错误**；从仍然错误的上游继承来的错误，要等上游被修好才消失。抓到错误（`P_catch = 0.9`）时重算后代。这**不是** `do(X_v = 1)` 干预 —— 见 `experiments/SEMANTICS_AUDIT.md`。

**信息泄露铁律**：策略永远看不到 `X_v`、`base[]`、未来的 coins。它只看到 `type`、`confidence`、`sink_reach`、`reviewed`、`budget`。真实错误只用于 (i) 决定审阅是否修好该节点 和 (ii) 计算终局奖励。

### 2.4 置信度信号（预测器）

```
logit = (−1.5 若 X_v=0 否则 +1.5) − 0.4·(P_TYPE[type] − 0.15) + N(0, 1.2)
conf = sigmoid(logit)
```

消融把 conf 换成 `conf ~ U(0,1)`（噪声）或 `conf = −1.5 若 X_v=0 否则 +1.5`（oracle）。**除了这三种条件，永远不要把真实 `X_v` 喂给策略。**

### 2.5 真实管道 DAG（N=21）

```
层 0（叶子）：time_bed, time_sleep, time_awake, time_getup,
              sol_self, waso_self, waso_count, nap
层 1：          bed_sleep_diff ← {time_bed, time_sleep}
              sleep_awake_diff ← {time_sleep, time_awake}
              awake_getup_diff ← {time_awake, time_getup}
              SOL_calc ← {bed_sleep_diff, sol_self}
              WASO_calc ← {waso_self, waso_count}
层 2：          TST ← {sleep_awake_diff, WASO_calc}
              TIB ← {time_bed, time_getup}
              SE ← {TST, TIB}
              TST_TIB_ratio ← {TST, TIB}
层 3（sink）：  SOL_validity ← {SOL_calc, bed_sleep_diff}
              WASO_validity ← {WASO_calc, nap}
              SE_conclusion ← {SE, TST_TIB_ratio}
              record_quality ← {SOL_validity, SE_conclusion, WASO_validity}
```

预算 8/21（38%），λ = 0.9。这个 DAG 是领域知识，不是拟合的。

---

## 3. 数据

| 来源 | 是什么 | 用途 | 永远不用于 |
|---|---|---|---|
| `deidentified_intervalvars_forCD_111325.rds` | 13,990 行 / 237 人 | 只用动机计数（N, 237） | 永不提交、永不整份交给 agent |
| `manual_error_correction_updated.csv` | 75 条纠错；`order_error` 57/75 = 76%；27 Consensus / 48 Agree | 类型率、共识/困难拆分（计划中） | 永不提交；文档只引汇总数字 |
| 合成 DAG | 代码生成 | 所有 RL 和规模实验 | — |

**75 条的预处理**：数 `error_type` 和 `agreement_cd_mtb`；不丢行；无标签的 8 行单独报告。**泄露**：不要在 75 条上拟合策略；它们定类型率和真实管道 DAG。

**合成数据的 train / val / test**：种子 1–5 训练，种子 1–16 评估（所有策略用同一批评估种子）。i.i.d. 图不用时间切分。真实轨迹扩展时按 `pid` 60/20/20，同一参与者不跨集。

---

## 4. MDP 定义（精确）

### 4.1 Episode

一个 episode = 一张图 + 一次错误抽样 + 一次置信度抽样 + 一条审阅轨迹。

```
for t in 1..T:
    观察 s_t
    a_t = π(s_t)            # 节点索引，或 STOP（仅 CMDP）
    if a_t == STOP: break
    budget -= 1
    if err[a_t] and rng() < P_CATCH:
        base[a_t] = False
        err = 重算下游(base)
r_T = -sink_errors(err)
```

固定预算主方法：`T = budget`（80 节点主方法 R=16；500 节点 R=50）。停止动作只在 CMDP naive 变体。

### 4.2 状态（GNN 打分器，80 节点主方法）

每节点特征，每审一次重算（`rl_gnn_multiseed.py`，变体 `observed`，`F[i] ∈ R^{K+7}`）：

```
F[i, 0:K]   = one-hot(type_i)
F[i, K]     = conf_i
F[i, K+1]   = log1p(sink_reach_i) / log1p(N)
F[i, K+2]   = 信念 P(i 处有源头错误)       # 粒子滤波，belief.py
F[i, K+3]   = 信念 P(i 是错的)             # 含传播来的错误
F[i, K+4]   = reviewed_i
F[i, K+5]   = flagged_i                    # 审查者在 i 看到错误
F[i, K+6]   = 剩余预算 / R
```

变体 `static` 只保留前 K+2 列、每局算一次（原方法）。真实错误状态永远不是特征。

GNN 层（1 层消息传递，子→父）：

```
agg = A @ F                # A = 子节点行归一化邻接
h   = tanh(F @ W_self + agg @ W_neigh)      # H = 32
s   = (h @ w + b).squeeze()                 # 每节点分数
```

未审节点上 masked softmax。**主方法没有 stop 动作**（N=80 固定预算 R=16；N=500 R=50）。stop 只在 CMDP naive 变体。

### 4.3 动作

固定预算主方法：贪心评估选分数最高的未审节点；训练时从 softmax 采样。等价于从剩余 N 个节点选一个。

CMDP naive（不要进主表）：N 个节点动作 + 1 个 STOP。

### 4.4 奖励

```
r_T = − sink_errors          # 结束时仍错误的 sink 节点数
```

无逐步奖励。REINFORCE MC 直接用终局，γ 只影响消融的 TD 变体（γ=0.97）。

CMDP naive（负结果，留作消融）：

```
G = r_T − λ_u · max(0, c − d_u) − λ_l · max(0, d_l − c)
d_u = 16, d_l = 8   (80 节点)
λ 更新：λ ← clip(λ + α_λ · violation, 0, 2.0),  α_λ = 8e-4
```

### 4.5 信息增益替代（还没跑）

```
R = α · ΔH_v − β · Cost(v)
ΔH_v = H(结论) − H(结论 | 审 v)
```

实现成蒙特卡洛代理：`ΔH_v ≈ (审前 sink 错误 − 审后) / n_MC`。只在主终局奖励太稀疏时用；不要在已跑数字上额外加这个再换种子协议。

---

## 5. 训练配置（我们实际用的数）

### 5.1 GNN + REINFORCE（主方法）

| 项 | 值 | 来源 |
|---|---|---|
| 优化器 | Adam | `rl_cmdp_gnn.py` / 80 节点隔离跑 |
| 学习率 | 0.003 | 同 |
| Hidden | 32 | 同 |
| Episodes | 20000 | 训练量敏感（12000 局那次更差） |
| 温度 | `max(0.3, 2.0 · 0.9993^ep)` | 同 |
| Baseline | EMA `0.95·旧 + 0.05·r` | 同 |
| 预算 | 16 | 80 的 20% |
| P_catch | 0.9 | 同 |
| 训练种子 | 1, 2, 3, 4, 5（`torch.manual_seed(seed)`） | 多种子脚本 |
| 评估种子 | 旧 1..20（`CFG["seeds"]`）；留出 1000..1199，配对 | 同 |
| 信念粒子数 | 1024（太少会在几次标出后塌缩） | `belief.py` |

**多种子结果（已跑，`final_table.md`）**：留出集均值——阈值 1.41 ± 0.25，结构贪心 1.45 ± 0.22，**信念贪心 1.14 ± 0.20**，GNN 静态 1.56 ± 0.29，GNN 带观测 1.56 ± 0.15。配对：GNN 带观测 − 信念贪心 = +0.42 ± 0.15；带观测 − 静态 = −0.00 ± 0.08。旧种子 1–20：GNN 静态 1.51 ± 0.41，带观测 1.68 ± 0.56。

### 5.2 GNN + PPO（不进主表）

lr 0.001，clip 0.2，epochs 2–3，8k–20k episodes——**未收敛（~5.60）**。重试方向：(i) 价值归一化 (ii) advantage 白化 (iii) 更小 lr。未收敛的 PPO 不要放 Slide 8。

### 5.3 CMDP naive（负结果，留作消融）

PPO-Lagrangian + STOP + coverage ∈ [8, 16]。lr 0.003，α_λ 8e-4，λ clip 2.0，20k episodes。结果 **2.15**（`torch.manual_seed(1)`；更早未播种的一次是 4.85）。诊断：整条轨迹一个终局回报没法给 STOP 决策记功。下一版要么做 **奖励 critic + 成本 critic 分离**（FALCON 式）+ 双 GAE，要么别做。不要说「RL 失败」，说「我们的 naive CMDP 失败」。

### 5.4 DQN（对照）

MLP Q 网络吃 (ctx, features)，replay 20k，target 200 步更新，γ=0.98，ε 1.0→0.05。80 节点主动选择上 **5.05**。留作值函数对照。**不要把它调赢**——退化本身是教学点。

### 5.5 MLP REINFORCE / PPO（80 节点初版）

Hidden 32，lr 0.003 / 0.001，12k–20k episodes，tabular 变体 conf_bins = 8。结果 1.60 / 1.35。是从 bandit 负结果到 GNN 升级的桥。

---

## 6. 对比策略（每个图族都跑）

| 策略 | 规则 | 目的 |
|---|---|---|
| 不审 | 永不审 | 下限 |
| 随机 | 均匀 R 个节点 | 没有规则的注意力 |
| 置信度阈值 | 审 conf 最低的 R 个 | 静态，看不到图 |
| Hub | 审出度 / 孩子数最高的 R 个 | 拓扑先验，看不到 conf |
| 结构贪心 | 按 (1 − conf) × (1 + sink 可达数) 排序取前 R | 静态、手工 |
| **信念贪心** | 每步选粒子信念下期望 sink 错误下降最大的节点，审完用结果更新信念 | **要打赢的可部署基线**（自适应贪心） |
| Oracle conf | GNN，特征里放真实 `X_v` | 信号天花板 |
| GNN + REINFORCE | 学到的打分器，固定预算，静态或带观测 state | 主学习方法 |
| Oracle 贪心 | 与信念贪心同样的选法，但用真实 `X_v` | 不现实的天花板 |

**公平比较铁律**

1. 同一评估种子、同一图种子、同一 coins、同一条 catch 随机流（配对）。
2. 同一预算 R。
3. 同一 P_catch。
4. 任何读真实 `X_v` 的东西都标 oracle，和可部署策略**分开**。
5. 有策略用验证集调阈值，所有策略给同样调参预算。

**已跑 N=500 均值（5 种子，预算 50，λ=0.8）：**

| 图族 | 不审 | 随机 | 阈值 | hub | **信念贪心** | oracle 贪心 |
|---|---|---|---|---|---|---|
| modular | 24.0 | 22.6 | 9.2 | 21.0 | **8.4** | 2.0 |
| BA | 80.6 | 78.2 | 37.6 | 29.2 | **12.8** | 3.6 |
| ER | 42.6 | 42.0 | 21.4 | 34.0 | **19.2** | 7.8 |

真实管道（8 种子，预算 8，λ=0.9）：不审 2.12，随机 1.88，hub 1.75，**阈值 0.50**。

---

## 7. 指标和成功判据

| 指标 | 怎么算 | 为什么 |
|---|---|---|
| Mean sink 错误 | 主指标 | 就是目标 |
| Worst-of-n | 训练种子在共享评估集上的 max | 一个漏审错误能作废结论（HealthBench） |
| 95% CI | GNN 用训练种子的 t；基线和配对差用留出图的 t | 见 `final_table.md` |
| P99 sink 错误 | n_sinks 够大时（500 节点） | 尾部 |
| 消融差距 | normal − noise；normal − oracle | 信号有没有被用；预测器是不是天花板 |
| 图族差距 | 信念贪心 − 阈值 在 BA vs ER | 拓扑会不会改变最优规则 |
| 审阅者漏检 | 1 − P_catch = 0.1 残余 | 非饱和 |

**除非（学到的 − 信念贪心）的配对 CI 整个低于 0，否则不要声称赢**。当前诚实句子：*200 张留出图上，可部署的信念贪心打赢我们的 GNN（+0.42 ± 0.15）；把审查结果喂给 GNN 没帮助；消融说剩余误差在置信度信号，不在调度器。*

**必出图（对标 LLM 规格书的四张图）：**

1. 方法对比柱状图（所有图族 / 所有策略）—— `results_bar.png`、`scale500.png`
2. 消融柱状图（noise / normal / oracle）—— `ablation_conf.png`
3. 学习曲线 —— `learning_curves.png`（真实训练日志，由 `rl_final.py` 画）
4. 真实管道柱状图 —— `real_pipeline.png`
5. （有时间）GNN 选点热力图：层 × 类型

---

## 8. 对照（破坏结构，看优势死不死）

| 对照 | 破坏什么 | 预期 |
|---|---|---|
| 打乱 `base[]` | 类型聚集 | 学习优势消失 |
| 清空 `parents[]` | 传播 | 优势消失，问题变独立 bandit |
| noise conf | 预测器 | RL 比静态阈值差（已跑：3.78 > 2.30） |
| oracle conf | 预测器天花板 | 与 normal 拉开大差距（已跑：0.72 vs 1.38） |
| 压平 + 打乱一起 | 两个事实 | RL ≈ 随机 |

每个对照用*同一个*训练好的策略和*同一批*评估种子。除非标「对照下重训」，否则不要在对照上重训。

---

## 9. 四周计划（实现，不是叙事）

| 周 | 搭什么 | 完成长什么样 |
|---|---|---|
| 1 | 冻结 `spike_active_selection.py` + `graph_scale.py` + `real_pipeline_graph.py`；复现：bandit 负结果（阈值 2.81 > Q 3.38）、GNN 多种子 CI、N=500 表、真实管道表 | `experiments/` 里的数字和本规格书的表在种子噪声内一致 |
| 2 | 双 critic CMDP（FALCON 式）**或** GNN+REINFORCE 上 N=500 的子采样（比如 200 节点）——选一个，不要两个都做砸 | 要么「CMDP 打赢 naive 2.15」要么「GNN 上 200 节点」 |
| 3 | 75 条的共识/困难拆分（27/48）；各自消融；N=500 对照 | 两行表：共识 vs 单人 |
| 4 | 用 `presentation_outline.md` 加四/五张图做幻灯片；排练 ≥2 次 | talk |

### 9.1 谁负责什么（五个人）

| 人 | 主责 | 背景那块 | 数据 |
|---|---|---|---|
| 1 | 组长 + 时间线 + L2D 经典（Mozannar / FALCON / SLTD） | 提案 | — |
| 2 | 策略梯度（REINFORCE → PPO-Lagrangian）+ 置信度信号升级 | PG / PPO / CMDP / 消融 | 洞 D（conf，不是数据集） |
| 3 | 环境 + GNN + DQN + 规模（N=500） | GNN 选节点 / 三图族 | 合成（已有） |
| 4 | 基线 + 打乱/压平对照 + HealthBench / BioBasicsBench | 那两个基准 | 洞 C 只在洞 A 失败时 |
| 5 동채하 | 叙事 + 郑心联络 + 写作 + 英文发表 | Data Cascades / 错误传播 / 综合 | 睡眠 75 / 13,990；洞 B |

**代码布局（基本已成立）：**

```
experiments/
  belief.py                   # 置信度模型 + 粒子滤波信念
  spike_active_selection.py   # 80 节点环境 + 阈值 / 结构贪心 / 信念贪心
  graph_scale.py              # N=500 modular/BA/ER
  real_pipeline_graph.py      # N=21 SCHEMA DAG
  rl_active_selection.py      # 主动选择 REINFORCE（早期）
  rl_methods_compare.py       # REINFORCE/PPO/DQN MLP
  rl_cmdp_gnn.py              # GNN + CMDP naive
  rl_gnn_multiseed.py         # 5 种子 GNN
  rl_ablation.py              # noise/normal/oracle
  rl_final.py                 # 冻结数字出图
  plot_*.py                   # 图
  verify_clustering.py        # 真实数据计数（文件缺失则跳过）
```

不加新方法就不加新文件和新种子协议。

---

## 10. 预期困难和诚实应对

| 困难 | 应对 |
|---|---|
| GNN 打不赢信念贪心 | N=80 上已经是这样。报告它。主张是*可部署的信念贪心是标杆*；打赢它（比如信念模型设错时）是开放的 RL 问题。不要硬凹赢。 |
| 有人引用旧的「贪心降 95%」 | 那是 oracle 贪心（读真实错误）。可部署数字：BA 80.6 → 12.8（降 84%）。 |
| 双 critic CMDP 还是失败 | 报告 naive 2.15（未播种时 4.85）和原因（只有终局信用）。引 FALCON 当没做完的配方。 |
| 真实管道太小（N=21）喂不动 GNN | 没关系。它是应用价值表，不是 RL 表。阈值 0.50 就是结果。 |
| 共识/困难只有 27 行共识 | 当动机数据的拆分报告，不当有功效的实验。 |
| 审阅者漏检 10% 意味着永远到不了 0 | 非饱和。直说。下一杠杆是 P_catch / 审阅质量，不是调度器。 |
| 组员复现不出 `final_table.md` | 重跑 `rl_gnn_multiseed.py`、`rl_methods_compare.py`、`rl_cmdp_gnn.py`，再跑 `rl_final.py`；数字动了就更新每个文档。**永远不许手改表格。** |

**每次出表前的信息泄露清单：**

- [ ] 策略特征不含 `base`、`err`、`coins`、未来完成时间
- [ ] Oracle / 读真值的贪心在每张表和图里视觉分开
- [ ] 验证阈值（如有）只在 train/val 种子上调
- [ ] 75 行 CSV 不在 repo、没整份贴进 prompt
- [ ] Worst-of-n 和 mean 用同一批评估 episode

---

## 11. 评估哲学（HealthBench + BioBasicsBench，落地）

- **Meaningful**：真实睡眠管道和结构化 DAG 上的 sink 错误，不是玩具分类器 accuracy。
- **Trustworthy**：75 条人审（27 共识 / 48 同意）；机器永不盖 SciForge 收据章。
- **Non-saturated**：oracle conf 0.72 ≠ 0；BioBasicsBench 最强 66.7%——都有空间。
- **偏学分 rubric**（SciForge 收据，模拟器还没用）：哪个下游指标、严重度、确定性。
- **错误检测是一等技能**，对标 BioBasicsBench。
- **「证据尚不支持该结论」**是建议器允许的动作，不只是「审 17 号节点」。

---

## 12. 什么叫「比 LLM 调度规格书做得好」

那份 LLM 规格（BurstGPT + Llama KV + PPO 权重）是更紧的**系统**沙盒。我们的是更紧的**证据链**沙盒。我们不在 token/s 或 KV GiB 上打赢它。如果我们执行这份规格，我们赢在：

1. **有诊断的负结果**（bandit 输是因为图被压平）；
2. **定位剩余误差的消融**——在预测器，不在策略；
3. **规模 + 拓扑**（BA hub、模块化簇、真实 SCHEMA DAG）；
4. **诚实的留出集比较**（信念贪心打赢 GNN，配对，200 张没见过的图）；
5. **决策指南**（置信度噪声 → 别用 RL；大无标度 → 信念贪心；我们的真实管道 → 阈值）；
6. **三语项目文档**，组员真的能读。

这才是 A+ 版本。不是「我们在 BurstGPT 上打赢 PPO」，是「用同样的实现纪律，做一个那份规格没碰的问题，并且不藏失败。」
