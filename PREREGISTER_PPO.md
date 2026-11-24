# 预注册：PPO 在 spike 族上的第三个学习基线

冻结时刻：2026-11-24。冻结时**未运行**任何一次 PPO 训练。
执行脚本：`role3 improvement/train_ppo.py`（冻结时尚未写出，只冻结设计）。
报告：`role3 improvement/outputs/ppo-v1/`。

## 为什么要做

仓库里已有两个学习基线：GNN + REINFORCE（自比较基线）与 DQN。
两者都在 6 个族、3 个种子上输给 `marginal`。这会招来一句标准批评：

> 你只试了 REINFORCE 和 DQN，是不是故意选了两个弱算法？

`residual-v1`、`confirm-10x`、`planning-v1` 三个 null 挡不住这句，
因为它们都没换优化器。PPO 是目前最常用的 on-policy 优化器，
换掉它之后，「学不出来」就不再是算法选择的产物。

**本实验的目的是堵这句话，不是刷分。** 预期结果是 PPO 仍然输。
如果它赢了，那是头条，不是需要重跑掉的异常。

## 固定的设置（不允许事后改）

| 项 | 值 |
|---|---|
| 族 | `spike`，n=80，budget=16，sink=最后一层 20 个 |
| 训练回合 | 1000（与 `outputs/v3/train_*/gnn_spike_observed.pt` 相同） |
| 训练种子 | 1, 2, 3 |
| 训练图种子 | `seed*1_000_000 + episode`（与 `train_gnn.py` 相同） |
| 验证 | 图种子 60000–60029，30 个回合，每 100 回合一次，取最好 |
| 评估图种子 | **4200–4399**（200 张，此前未被任何实验使用） |
| 评估 episode 种子 | `20000 + graph_seed`（与 `run_benchmark.py` 相同） |
| 主对照 | `marginal`（不是 `confidence`） |
| 统计 | 配对 bootstrap，10,000 次，seed 20261124 |

超参数在冻结时写死，跑之前不许调：

```
lr 3e-3            Adam
clip 0.2           4 epochs per update
gamma 1.0          无 bootstrap，回合内回报即终端奖励
entropy 0.01       value coef 0.5
8 回合/更新         grad clip 5.0
temperature 1.0    固定，不做退火
hidden 32          与 GNNScorer 相同
```

架构：沿用 `GNNScorer` 作为策略（checkpoint 与 `run_benchmark.load_policy`
兼容），另加一个 2 层 MLP value head，输入端是同一层的节点嵌入的均值池化。
critic 权重单独存，不进 `state_dict`，否则现有加载器会拒绝该 checkpoint。

## 预测（先写死）

**P1.** PPO 的剩余错误数高于 `marginal`，即 Δ = PPO − marginal > 0。

**P2.** PPO 好于 REINFORCE GNN（Δ 相对 `marginal` 的 +0.403 变小），
因为 clip 与 value baseline 降低方差。预测落在 `(0, +0.403)`。

**P3.** 三个训练种子的排序一致，不出现某个种子翻转符号。

**证伪条件（P4）.** 若 Δ 的 95% 区间在负方向排除 0，则 P1 失败，
本仓库「规则优于学习策略」的结论必须改写为「规则优于 REINFORCE 与 DQN，
但 PPO 例外」，并在 `BENCHMARK_SPEC.md` 第 6 节单独成行报告。

## 判定规则

| 结果 | 判定 | 后续动作 |
|---|---|---|
| Δ > 0 且区间排除 0 | `third-loss` | 主结论加强：三种架构均输，非算法选择 |
| 区间含 0 | `tie` | 写「与规则打平」，不计为赢，也不计为输 |
| Δ < 0 且区间排除 0 | `learned-wins` | P4 触发，改 SPEC，作头条 |
| 符号在三 seed 间翻转 | `unstable` | 只报格子，不报排序 |

区间跨 0 一律记「未分离」。`wins/ties/losses` 与均值一起报，因为 `ba` 上
已经出现过均值与胜率讲不同故事的情况。

## 不做的事

- 不用 90000–90099（已花掉的报告块）。
- 不在 4200–4399 上调超参、挑 checkpoint 或换熵系数。
- 不因为 PPO 输得多就换成「PPO + 额外技巧」再跑一次同一块。
- 不把 PPO 的绝对均值与 `outputs/v3/` 并列：图种子块不同，只有配对差值可迁移。
- 不把「PPO 打平」写成「学习策略有希望」：区间含 0 就是没有分离。

## 记录

运行前：本文件提交。运行后结果写入
`role3 improvement/outputs/ppo-v1/`，含逐 episode CSV、汇总 CSV、
`ppo_vs_marginal.md`、`manifest.json`（脚本与 checkpoint 的 SHA-256）。
