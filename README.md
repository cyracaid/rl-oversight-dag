# 依赖图审查调度 · Review Scheduling on a Dependency Graph

> 强化学习课小组项目（STA3145）。预算约束下、依赖图上，用 RL 学该审哪个节点，使到结论的错误最少。

---

## 最高原则（5 条，不可商量）

1. **数据红线（最高）**：内部真实数据（13,990 行睡眠记录、75 行纠错）**永远不上 repo、不离开组员本机**。即使 deidentified，也是 IRB 约束的研究数据。谁要数据私下发，不 commit。
2. **诚实优先**：所有 AI 生成的结果（数字、代码、图），在组员独立复现之前，一律标注「未验证」。提案第 8 节就是这条原则的落地。
3. **可复现**：任何组员 clone 仓库后，**不需要你的机器、不需要真实数据**，就能跑通合成实验。绝对路径一律可配置 / 文件缺失时自动跳过。
4. **合成为主，真实为辅**：核心实验用合成依赖图；真实数据只用于动机页一句话。
5. **数字可追溯**：每个数字 → 一个脚本 → 一个种子。**改数字必须改脚本，不许手改表格**。表格由脚本生成（`final_table.md` ← `rl_final.py`）。

---

## 项目结构

```
模拟器与实证/
  spike_active_selection.py    依赖图环境 + 结构贪心/阈值基线（合成，无外部数据）
  dependency_review_sim.py     bandit 第一版（负结果）
  rl_methods_compare.py        REINFORCE / PPO / DQN（MLP 打分器）
  rl_cmdp_gnn.py               CMDP + PPO-Lagrangian + GNN（软预算，naive 版）
  rl_final.py                  出最终表格 + 两张图（纯出图，不训练）
  rl_gnn_multiseed.py          GNN+REINFORCE 多种子复现
  verify_clustering.py         真实数据聚集验证（需真实数据，缺失则自动跳过）
  final_table.md               最终表格（rl_final.py 生成）
  results_bar.png / learning_curves.png   图（rl_final.py 生成）
  gnn_multiseed_result.txt     多种子结果（rl_gnn_multiseed.py 生成）
提案_深化版_EN_KO.md           提案（EN/KO）
汇总_讨论稿_EN_KO.md           组内讨论稿
```

---

## 怎么复现（组员照着跑）

| 想要什么 | 跑哪个 | 依赖真实数据？ |
|---|---|---|
| 结构价值（阈值 vs 贪心） | `python3 spike_active_selection.py` | 否 |
| 三种 RL 对比（MLP） | `python3 rl_methods_compare.py` | 否 |
| GNN 升级版 | `python3 rl_cmdp_gnn.py` | 否 |
| 最终表格 + 图 | `python3 rl_final.py` | 否 |
| GNN 多种子 | `python3 rl_gnn_multiseed.py` | 否 |
| 真实数据聚集验证 | `python3 verify_clustering.py` | **是（缺则跳过）** |

依赖：`python3` + `numpy` + `torch` + `matplotlib`（后三个 `pip install torch numpy matplotlib`）。

---

## 数据说明

- **核心实验全是合成数据**（代码现场生成依赖图），任何人 clone 下来都能跑。
- **真实数据**（睡眠记录）在 `verify_clustering.py` 里，路径指向本机 `~/Documents/splsleep`；文件不存在就打印"缺文件"跳过，不影响合成实验。
- 真实数据**绝不 commit**（见 `.gitignore` 和最高原则第 1 条）。

---

## 诚实备注（务必读）

- GNN+REINFORCE = 1.20 是单次 20000-ep 训练确认的，12000-ep 时是 2.05，训练量敏感 → 发表前需多种子复现（跑 `rl_gnn_multiseed.py`）。
- CMDP 软预算（PPO-Lagrangian + stop 动作）naive 版失败（4.85），需 FALCON 式双 critic —— 这是开放问题。
- 所有数字由 AI 智能体生成，未独立核验；提案第 8 节列了完整待核查清单。
