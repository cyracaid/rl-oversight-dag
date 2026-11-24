# sci-export-v1 — 评估协议（冻结版）

冻结日期：2026-11-24。**在拿到任何真实导出之前冻结**，目的就是让「真实数据到了以后」没有调指标的空间。
改动只能通过 `v2` + 在文末「变更」里写清为什么改；不允许就地改。

---

## 1. 这个 benchmark 回答什么

一句：**在一条 AI 辅助的科研证据链上，把有限的审阅量花在哪些节点，能最快抓到人类复核确认的错误？**

不回答：错误率是多少、模型能不能替代审稿、哪个团队更可靠。

## 2. 任务定义（固定）

| 项 | 定义 |
|---|---|
| 输入 | 一个证据图：`nodes`（id / type / is_sink）、`edges`（`derived_from` / `supports` / `contradicts`）、隐藏的真值 `corrections`、可选 `receipts` |
| 动作 | 输出一个节点排序；每次审阅消耗 1 个节点额度，审过的节点不再出现 |
| 预算 K | `max(3, round(0.25 × N))`，主指标只用这个 K；另报 10% 与 50% 作次要 |
| 反馈 | 只能拿到**已审节点**的裁决（相当于收据里的 `verdict`）；未审节点的真值不可见，由 harness 强制 |
| 传播 | 只用 `derived_from` 边；`supports` / `contradicts` 不参与传播，单独计数 |
| 审阅命中 | 主指标**不**模拟「审了但没看出来」。P(catch)=0.9 只在模拟器里用，不进主指标 |

> 为什么去掉 P(catch)：它是又一个假设，会把「排序好不好」和「人看不看得出」混在一起。
> 真值 join 是离线的，不需要假设审阅者视力。

## 3. 指标（一个主指标，其余都是次要）

**主指标**：`recall@K` = 前 K 个被审节点命中的确认错误数 / 全部确认错误数。

**次要**（全部标为 exploratory，不得单独当作结论）：
- `precision@K`
- `reviews→50%`：抓到一半错误需要审几个节点；抓不到就写 `not reached`，**不填 K 或 0**
- `recall@minutes`：仅当 `receipts` 带 `duration_min` 才计算；缺失写 `unavailable`，**不当 0**
- `errors never reviewed by humans`：人类收据覆盖不到的确认错误数（睡眠侧 17/85 的同类量）

**禁止**：把 `unavailable` 当 0、把 `not reached` 当 K、用不同 K 的 recall 互比、把两个项目平均成「跨链均值」而不报各自的 N。

## 4. Baseline 梯子（每一条都必须存在，理由写死）

| id | 排序依据 | 为什么必须在 |
|---|---|---|
| `pipeline_order` | 节点在导出中的自然顺序（≈ 依赖顺序） | 现状。DAG 上它**不是**弱基线：结构信号实验里它比 random 高 0.25 |
| `random` | 均匀随机，200 次排列取均值 | 校准。睡眠侧只用一次抽样，结果 R@100 反而高于队列顺序，是噪声 |
| `type_prior` | 节点类型 + 固定先验（claim 0.30 / run 0.20 / figure 0.15 / dataset 0.10） | 类型信息的天花板（睡眠侧 84% @ 13% 审阅量） |
| `reach` | 纯结构：可达下游节点数，归一化 | 检验「图结构本身」是否携带信号，与类型无关 |
| `type_x_reach` | 先验 × (1 + 归一化 reach)，结构最多加权 2× | 静态组合，即「没有裁决反馈时的我们」 |
| `marginal_adaptive` | 同上 + 据已审裁决做下游 noisy-OR 更新（λ=0.9） | 方法本体。**主版本用 flat 先验**（不假设类型） |
| `marginal_adaptive_declared` | 同上，用声明先验 | 敏感性臂，不是主方法 |
| `receipts` | 人类实际审阅的时间顺序 | 人类基线。不是竞争者，回答「人本来做得怎么样」 |
| `oracle` | 真值在手 | 天花板，永远不参与「胜负」 |

**为什么 `marginal_adaptive` 主版本用 flat 先验**：控制实验里，先验指错方向时
`type_x_reach` 0.26、`marginal_adaptive_declared` 0.16，而纯结构 0.62 —— 一个未经验证的先验
可以把真实的结构优势抹掉。先验是假设，不是测量；主张不能建在假设上。

**唯一的先验比较**：`marginal_adaptive` vs `type_prior`（单侧，α=0.05）。
其余全部视为探索性，多重比较不做校正，但结论句必须写「exploratory」。

## 5. 统计

- **配对**：所有策略跑同一批图、同一份真值；差值按图配对。
- **重采样单位**：真实数据用**项目**（≥2 个项目）或**误差簇**（错误节点的连通分量）；一个项目内按节点
  重采样是乐观的，只能用于单个项目的案例报告，必须在表下注明。
- **区间**：2000 次 bootstrap，2.5/97.5 百分位。
- **判定**：差值 95% CI 含 0 → 写 `indistinguishable`；不含 0 → 写 `ahead` / `behind`，
  并列方向。禁止用「显著提升」这种没有区间的说法。

## 6. 样本量（先算，不要事后解释）

`recall@K = hits / E`，`hits ~ Binomial(E, p)`。E = 确认错误数。单次 recall 的 sd ≈ √(p(1−p)/E)。
本仓库 21 节点 / E=6 / K=5 上实测的配对差 sd ≈ 0.12–0.26。

| 确认错误 E | 近似配对 sd | 80% power 能测到的最小 Δ（α=0.05 双侧） |
|---:|---:|---:|
| 6（本 mock） | ~0.15 | ~0.42（测不了任何有用差异） |
| 25 | ~0.07 | ~0.20 |
| 50 | ~0.05 | ~0.14 |
| 100 | ~0.037 | ~0.10 |

**冻结的最小数据要求**：

- 任何定量主张：**≥2 个项目，合计 ≥100 个确认错误，≥150 个节点**。
- 1 个项目 / 25–99 个错误：只报案例（`case study`），可以给点估计，不给「优于」结论。
- <25 个错误或 <60 个节点：只报 `not answerable at this sample size`，并把数字列出来当描述统计。

这条比任何方法都重要：21 节点 6 个错误的项目，无论排序多好，都测不出差异。

### 6b. 测量层前提（样本量够 ≠ 指标可算）

上面的样本量假设「确认错误数 E」是已知的。现有审计数据里它不是：

- 75 条纠错中，`resolved_at` 只有 **1/75**（且只有日期，无时刻）；
- `resolved_by` **17/75**；`review_resolution` 有 **58/75** 是 `resolution_unknown_legacy`；
- 审阅时长字段 **0/75**；`duration_*_totalmin_*` 是睡眠时长，不是审阅成本。

所以在这个导出上 `recall@minutes` **不可计算**，能算的只有 `recall@K`（审了几次）。
补上缺口只需三个字段：`opened_at`、`submitted_at`、`field_path`。

落实为断言的是 `triage_bench/audit/coverage.py`（15 tests）：
未覆盖的错误计为**未知**而非正确；任一收据缺时长 → `recall@minutes = unavailable`，
不填 0；`coverage_fraction` 在空集上返回 `unavailable`。

详见 [`triage_bench/MEASUREMENT_LAYER.md`](../../triage_bench/MEASUREMENT_LAYER.md)。

## 7. 泄漏规则（可测的，不靠自觉）

1. `State` 只暴露 `reviewed` 集合与这些节点的 `revealed` 判决；`State.verdict(v)` 对未审节点抛
   `PermissionError`（`test_state_refuses_unreviewed_verdict`）。
2. 真值只在 harness 与离线 join 里出现；策略签名不接收真值（`test_every_policy_is_labelfree_and_deterministic`）。
3. 先验只能来自**别的项目**或声明值；在同一条链上拟合类型率再评估同一链，视为泄漏。
4. `supports` / `contradicts` 不得进入传播。

## 8. 结果 → 能说什么（先写好句子模板）

| 观察 | 允许的句子 | 禁止的句子 |
|---|---|---|
| 差值 CI 含 0 | 「在该项目上，方法顺序与 X 不可区分」 | 「没有差别」 |
| 差值 CI 不含 0，且 ≥2 项目 | 「在 N 个项目的合并样本上，方法比 X 多抓到 Δ 的确认错误（95% CI …）」 | 「证明了图结构普遍有用」 |
| 方法赢但 receipts 覆盖不到多数错误 | 「增益只出现在已被 flags 覆盖的部分」 | 「覆盖率问题已解决」 |
| 只有 1 个项目 | 「案例：本项目上 …」 | 任何「优于」 |
| mock 数字 | 「这是控制实验，用来检查评估器」 | 任何引用为结果 |

## 9. mock 的定位（说清楚，防止自己骗自己）

`sciforge_mock_v1.json` 是**阳性对照**：错误按声明先验生成，所以 `type_prior` 应当明显高于
`pipeline_order`。它通过 = 装载器、策略接口、指标、区间都工作。它**不是**数据，
不能写进任何结果表，不能与睡眠侧或 ticket 侧的数字比较。

## 10. 复现

```bash
cd ~/Documents/강화학습
python3 -m sciforge_review.export.make_mock                        # 重新生成 mock（确定性）
python3 -m sciforge_review.export.bench --boot 500                # mock 上的表
python3 -m sciforge_review.export.controls                        # null / 两类信号控制
python3 -m unittest discover -s sciforge_review/export/tests -t . # 17 个测试
```

## 变更

- v1 2026-11-24：初版冻结。此版本没有看过任何真实导出。
- v1.1 2026-11-24：新增 §6b「测量层前提」。协议本身不改；补记现有审计导出
  `recall@minutes` 不可算，以及把它变成断言的位置。
