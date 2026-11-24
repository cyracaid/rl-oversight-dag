# sciforge_review — Phase 0–1

> 一个**只读**的审阅控制面原型：把「审了谁、花多久、覆盖到哪」变成可计算的量。
> 不是调度器，不训练策略，不盖章，不写 SciForge 主仓。

## 这是什么

三个形态共用一个核：

| 形态 | 共用原语 | 状态（P0–P1） |
|---|---|---|
| **A 审阅控制面** | `EvidenceGraph` + `ReviewReceipt` + 只读排序 | 已跑通；P1 收据可回放 |
| **B claim 审计** | `Claim` + `Span` + `sufficiency_check` | 接口 + 清单 |
| **C 仪器适配** | `InstrumentCapability` + `InstrumentRun` | 模拟 adapter |

核心判断来自实验：调度器不是瓶颈（belief greedy 1.14 赢 GNN 1.56；噪声 3.78 / 正常 1.38 / oracle 0.72）。
缺的是**测量层**——审阅收据、成本、覆盖率、以及「这块根本没被 flag」的显式输出。

## 跑

```bash
# 从仓库根目录
python3 -m sciforge_review.demo
python3 -m unittest discover -s sciforge_review/tests -v
```

`demo` 会写 `outputs/review_card.md` 和 `outputs/review_card.json`。

## 当前结果（合成 N=21，30 seeds，仅作演示）

| policy | mode | budget | reviews | sink errors | recall |
|---|---|---:|---:|---:|---:|
| no review | — | — | 0 | 2.43 | 0.000 |
| queue order | row | 8 min | 7 | 2.23 | 0.329 |
| type prior | row | 8 min | 7 | 2.10 | 0.480 |
| belief greedy* | row | 8 min | 7 | 2.10 | 0.480 |
| queue order | witness | 8 min | 15 | 1.87 | 0.578 |
| type prior | witness | 8 min | 15 | **0.83** | **0.845** |
| belief greedy* | witness | 8 min | 15 | **0.77** | 0.833 |

> `*` Phase 0 的 belief greedy 是「类型先验 × 下游影响 / 成本」的简化排序，不是论文里的粒子滤波版本。
> 这是 demo harness，**不是**论文里的模拟器；真实队列的数字在
> `triage_bench/README.md`、`CEILING.md`、`AUDIT_CHAIN_DESIGN.md`：
> 1,048 flags / 68 errors（6.5%）、M1-first 83.8% @ 140 reviews、17 条从未被 flag、
> 中位 62 秒/行、witness 对把 60/120/240 分钟的 recall 从 8.8/25/63.2% 提到 25/63.2/83.8%。

## Phase 1（收据可回放）

```bash
python3 -m sciforge_review.demo_phase1
```

每次审阅写一条 `review.receipt.v1`（绑定 node + 不可变版本 + 时间戳 + 裁决 + hash 链），
`recall@minutes` 从磁盘回放收据再算，不再从模拟器内存里读。

| policy | mode | 8 min recall | 8 min reviews |
|---|---|---:|---:|
| queue order | row | 0.277 | 7 |
| type prior | row | 0.404 | 7 |
| belief greedy* | row | 0.404 | 7 |
| queue order | witness | 0.499 | 15 |
| type prior | witness | 0.819 | 15 |
| belief greedy* | witness | 0.811 | 15 |

- **360/360** 条收据链校验通过；15 个测试全过。
- 收据只含引用与时间戳，不含正文、参与者信息；`accepted` 不代表真值，真值只在离线 join 时使用。
- 覆盖率示例：合成图 21/21 flagged，unreachable=0；真实队列 17/85 从未被 flag。

## 边界（写死，不靠自觉）

- **只读**：policy 只输出排序；不写 DAG、不产生收据、不盖章。
- **收据只记引用**：`field_path` / 时间戳 / 裁决 / hash 链；不存正文、不存参与者信息。
- **不碰主仓**：本目录是原型；SciForge 侧只放 openspec 草案和契约。
- **合成数据**：N=21 是实验室管道图；真实睡眠数据一行都不进仓库。

## 文件

```
graph.py        N=21 EvidenceGraph（节点/边/sink/下游影响）
policies.py     queue / type prior / belief greedy；字段成本
simulate.py     配对 episode、传播、recall@minutes
claims.py       Span / Claim / sufficiency（B）
adapters.py     InstrumentCapability / InstrumentRun / SimulatedAdapter（C）
demo.py         跑表、写 review card（P0）
receipts.py     ReviewEvent -> Receipt 绑定
store.py        append-only 收据库 + 回放
loop.py         最小审阅会话：排序 -> 写收据 -> 预算停
export/         SciForge 导出装载器 + 冻结协议 + 基线 + 控制实验（17 tests）
metrics.py      从收据算 recall@minutes / coverage
demo_phase1.py  3 policies × 20 seeds，写收据再回放
outputs/        review_card.md / phase1_report.md / json
tests/          15 个测试（收据链、绑定、回放、指标、claims、adapter）
```

## 与 SciForge 的映射

| 原型 | SciForge 落点 |
|---|---|
| `ReviewReceipt` | `artifact-versions` 的 commit 路径，或 `evidence-dag` 的 producer receipt；append-only |
| `EvidenceGraph` | `evidence-dag` 的只读切片（node type / `derived_from` / `supports`） |
| `Claim` / `Span` | `knowledge-net` 的 4 层笔记 + span 校验；`insufficient` 作为一等裁决 |
| `InstrumentRun` | 只读 adapter schema；先接模拟器/公开日志，不接真实设备 |
| `review.suggest` | 新 capability（`read` / `none` / `workspace`），不改现有能力 |

## SciForge 落点（需要你在 Terminal 跑一条）

沙箱只允许写 `~/Documents/강화학습`，`SciForge/.git` 在 workspace 外，所以我不能在这里建 worktree/分支。
草案已经准备好，在：

`sciforge_review/sciforge_port/openspec/changes/add-review-control-plane/`

在 Terminal 跑：

```bash
cd ~/Documents/sciforge-main-retest
git worktree add ../sciforge-review -b feat/review-control-plane main
cp -R ~/Documents/강화학습/sciforge_review/sciforge_port/openspec/changes/add-review-control-plane ~/Documents/sciforge-review/openspec/changes/
cd ~/Documents/sciforge-review
npx -y @fission-ai/openspec validate --strict add-review-control-plane
```

我没有提交、没有推送、没有改 `SciForge` 主仓。草案覆盖 P1 收据、P2 只读建议器、P3 覆盖、
P4 claim 审计；P5 仪器 adapter 单列。

## 导出评估协议（`export/`，2026-11-24）

`sci-export-v1`：在按 `triage_bench/SCIFORGE_ASK.md §4` 形状的导出上做节点级审阅排序评估。
协议在拿到真实数据**之前**冻结，避免事后挑指标。

```bash
python3 -m sciforge_review.export.make_mock
python3 -m sciforge_review.export.bench
python3 -m sciforge_review.export.controls
python3 -m unittest discover -s sciforge_review/export/tests -t .
```

- `PROTOCOL.md` 冻结：主指标 recall@25%、7 条基线 + oracle、配对区间、泄漏规则、样本量下限
  （≥2 项目 / ≥100 确认错误 / ≥150 节点才能谈定量结论）。
- `REPORT.md`：mock 表 + 三类控制实验（null / 类型信号 / 结构信号）。**所有数字为合成。**
- 控制实验的结论：评估器在校准内；`pipeline_order` 不是弱基线；未验证的类型先验会抹掉
  真实结构优势（0.62 → 0.16），所以主方法用 flat 先验。
- 17 个测试：装载器拒绝环/缺字段/坏裁决、策略看不到未审真值、指标与边界。

**未做**：任何真实 SciForge 导出、`review.suggest` 读路径、生产 composition。

## 路线图

| Phase | 内容 | 落点 |
|---|---|---|
| **0（本目录）** | 收据 + 图 + 三种排序 + cost-aware demo | `강화학습/sciforge_review/` |
| 1 ✅ | 收据写入 demo + 回放 + `recall@minutes`（本地 JSONL；artifact-versions 对齐等 worktree） | 本目录 |
| 2 | 只读 `review.suggest` + 最小面板 | SciForge worktree |
| 3 | claim 审计：span 校验 + `insufficient` | knowledge-net 扩展 |
| 4 | 仪器 adapter：schema + 模拟日志 | 独立 change |
| 5 | 真实 DAG 导出接入（P0/P1 字段） | `triage_bench/SCIFORGE_ASK.md`；协议与装载器已在 `export/` 就绪 |

## 状态

Phase 0–1 代码与 15 个测试通过；`review_card.md`、`phase1_report.md` 已生成；
SciForge openspec 草案已就绪，worktree 需在 Terminal 创建。所有数字为 AI 产出，未由第二名
成员复现。收据 schema 沿用 `triage_bench/audit/receipts.py`，链校验与回放已测。
