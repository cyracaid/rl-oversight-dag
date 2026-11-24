# 票务环境 与 SciForge 集成：怎么做

日期：2026-11-24
用途：把「票务环境不存在」「SciForge 生产集成未完成」两条缺口，拆成可执行步骤、写清代价与边界。
结论先说：**票务环境值得建，半天内可完成；SciForge 生产集成不该在周三前做，但可以先补「真实形状的导出 + 评估」这一层。**

---

## 一、票务环境（hypothetical ticketing pipeline）

### 1. 建还是不建

| 选项 | 代价 | 收益 | 风险 |
|---|---|---|---|
| A. 删掉这句话（原建议） | 0 | 诚实，但提案里承诺的第三个环境消失 | 老师若追问"说好的票务呢"没有答案 |
| B. 建一个固定的 21 节点票务 DAG（推荐） | 2–3 小时 | 原提案成立；多一个**服务运维域**的结构检验，与科研管道不同域 | 合成环境，不能报"实测错误率" |

选 B，且 **已于 2026-11-24 实施**。理由：它和 `real` 一样是**固定拓扑 + 先验错误率**，不引入新的测量主张；而且第六个 family 能回答"图感知规则是不是只在科研 DAG 上有效"。

实施结果（100 图，seeds 90000–90099，budget 8）：

| policy | mean sink errors | vs confidence |
|---|---:|---|
| confidence | 0.32 | — |
| structural | 0.30 | +0.02 [−0.02, +0.08] |
| marginal | **0.29** | **+0.03 [0.00, +0.08]**，98/100 平手 |

结论：**ticket 上规则与 confidence 打平，不构成跨域优势**。这与 `real` 的薄优势一致，与 `spike` 的 0.66 vs 1.03 不同。报告必须分开写。

### 2. 拓扑设计（21 节点，4 层，4 sink）

| 层 | 节点 | 数量 |
|---|---|---:|
| 收集（原始字段） | `ticket_created_at`、`first_response_at`、`resolved_at`、`reporter_id`、`channel`、`priority_raw`、`queue_raw`、`sla_policy_raw`、`assignee_id` | 9 |
| 预处理（派生） | `response_minutes`（首响−创建）、`resolution_minutes`（解决−创建）、`priority_norm`（P1–P4 映射）、`assignee_team`、`sla_target_minutes`（策略×优先级） | 5 |
| 分析（指标） | `response_ratio`、`resolution_ratio`、`breach_minutes`（max(0, 解决−目标)） | 3 |
| 结论（sink） | `ticket_validity`（时间戳顺序）、`priority_consistency`、`sla_compliance`、`assignment_validity` | 4 |

边：每个派生节点 2 个父节点；指标各 2 个父节点；结论各 2–3 个父节点。
`ticket_validity` 有下游（喂 `sla_compliance`），所以沿用 `real` 的做法用 `sink_override` 指定 4 个 sink。

错误类型与先验（**合成先验，不是实测**）：

| 类型 | 例子 | 先验 |
|---|---|---:|
| `order_error` | 解决时间早于创建；跨时区导致首响为负 | 0.35 |
| `duration_error` | 时长算成负值 / 单位分钟秒混用 | 0.15 |
| `mapping_error` | 优先级 "Urgent" 未映射到 P1；队列→团队映射错 | 0.12 |
| `policy_error` | SLA 策略取错版本，目标时长差 2 倍 | 0.10 |
| `ratio_spike` | 比率 > 10 或为 NaN | 0.08 |
| `zero_equal_error` | 创建=解决、首响=创建被当成有效 | 0.05 |

### 3. 代码落点（不动现有结果）

1. `role3 improvement/dag_role3/graphs.py`
   - 加 `TICKET_ROWS`（同 `_REAL_ROWS` 的 4 元组格式）
   - 加 `TICKET_RATES = (0.35, 0.15, 0.12, 0.10, 0.08, 0.05)`
   - 加 `gen_ticket()`，返回 `DAG(..., family="ticket", sink_override=(...))`
   - `generate_graph()` 注册 `ticket`，拒绝非 21 的 `n`
2. `role3 improvement/run_benchmark.py`：`FAMILIES` 加 `"ticket"`
3. `role3 improvement/compare_beliefs.py`：choices 自动跟着 `FAMILIES` 走
4. `role3 improvement/tests/test_environment.py`：加一条 `ticket` 的 DAG 不变量测试（无环、sink 数=4、确定性）

### 4. 跑什么、报什么

```bash
cd "role3 improvement"
python3 run_benchmark.py --families ticket --seeds 100 --start-seed 90000
```

只跑 6 条规则（none/random/confidence/hub/structural/marginal），**不加载 GNN/DQN checkpoint**——那些是按 family 训练的，跨 family 维度不兼容，也不该硬套。

验收标准：
- `benchmark_role3.csv` 出现 `ticket` 行，6 条规则齐全；
- `ticket` 上 marginal < confidence 才能说"图感知规则跨域成立"，否则如实写"只在本域成立"；
- 论文/汇报中写 "hypothetical ticketing pipeline (synthetic, prior rates)"，禁止写"票务实测"。

代价：2–3 小时，全部是新增，不改任何已有数字。

---

## 二、SciForge 生产集成

### 1. 先纠正一个认知：不是从零开始

`~/Documents/sciforge-main-retest` 里已经有：

- `packages/domains/review-control/`：严格的收据 schema、三个 capability（`review.receipt.commit` / `review.suggest` / `review.coverage`）、通过 Artifact Versions 公共 commit port 落盘、幂等键、workspace 隔离。
- `openspec/changes/add-review-control-plane/`：proposal / design / spec / tasks 齐全。
- 我刚跑的测试：**60 passed / 7 todo**（`npm --workspace @sciforge/domain-review-control run test`，908 ms）。

但它是 `composition: "development-only"`，**没有进应用组装**，读路径还是 `never`：
`readonly.test.ts` 里 3 个 todo 正是「读有界图切片 / coverage_unknown / 预算边界」，也就是 RL 排序器真正需要的入口。

7 个 todo 对应 7 个未决契约：

1. `reasonCode` 闭集词表
2. capability audience 审批
3. 收据链归属、canonical bytes、digest 生成与校验
4. 有界图切片的公共读 schema 与读路径（零写）
5. 图不可用时的 `coverage_unknown` 形状（不得返回排序）
6. 预算校验/截断语义
7. 生产 trace 与文档输出入口的隐私检查

### 2. 三级台阶，不要一步跨

| 阶段 | 做什么 | 依赖 | 工时 | 能不能现在做 |
|---|---|---|---:|---|
| **S0 现状审计** | 固化「60 通过 / 7 todo / development-only」为集成就绪报告 | 无 | 已完成 | ✅ |
| **S1 mock 导出 + 评估** | 按 `SCIFORGE_ASK.md §4` 造 21 节点 mock，`load_export.py` 校验，7 条基线 + oracle，配对区间，三类控制实验；协议先冻结 | 无 | 1 天 | ✅ 2026-11-24（`sciforge_review/export/`） |
| **S2 真实导出** | 用 `evidence-dag.audit-query`（`{subject}`）+ `evidence-dag.record.review` 冻结 sequence 窗口分页，导出真实图与收据；按项目哈希脱敏 | SciForge 侧 gate 0.1/0.4、数据owner签字、隐私规则 | 2–3 天（不含等待） | ⛔ 需外部 |
| **S3 生产 capability** | 补 7 个 todo，尤其 4/5/6（读路径、coverage_unknown、预算边界）；接进 composition；跑 `npm run capability:generate`、`domain-packages:check`、locale、桌面验收 | 团队对 1/2/3/7 的决策 + owner 签字 | 5–10 天 | ⛔ 不该solo做 |

### 3. S1 的具体形状（建议本周做这一个）

产物放 `sciforge_review/export/`：

```
export/
  sciforge_mock_v1.json      # 21 节点、~30 边、6 条纠错、12 条收据
  load_export.py             # 只读加载 -> EvidenceGraph + corrections + receipts
  evaluate_export.py         # queue order / confidence / marginal，recall@minutes
  REPORT.md                  # 表 + 一句"这是 mock，不是真实链"
```

映射到现有原语：

- `nodes[].type` → `graph.types`；`is_sink` → `sink_override`
- `edges[].rel` → 只保留 `derived_from` 作为传播边；`supports`/`contradicts` 不参与错误传播，单独统计
- `corrections[]` → 真值，只在离线评估时 join
- `receipts[]` → 人类基线（顺序、耗时），不参与策略输入

验收：
- mock 文件与加载器在干净 clone 上跑通；
- 三个策略同一批图配对；
- 报告首行写明 "mock schema, not a real SciForge export"。

这一步的价值：把"生产集成"从口号变成**接口已验证、只差真实数据**。老师问起来，能拿出 schema、加载器、配对表和一句边界。

### 4. S2/S3 需要谁点头

| 事项 | 谁 | 具体问题 |
|---|---|---|
| 收据是否属于证据链、谁拥有契约 | SciForge 证据链 owner | gate 0.1 |
| 是否能拿到 ≥1 个真实项目的只读导出 | 郑心 / Zhangyang | 节点 ID 能否保留、脱敏级别 |
| 收据链的 canonical bytes 与 digest | 契约 owner | todo 3 |
| 是否允许 review-control 进 production composition | 平台 owner | 现在标 development-only |

没有这三项，S2/S3 做了也不可验收——这正是 `SCIFORGE_INTEGRATION_CONTRACT_MAP.md` 已经写过的结论，不要绕过。

### 5. 周三怎么说

> "SciForge 侧我们停在**只读契约 + staging 包**：60 个契约测试通过，7 个契约待定；读路径还没开。我们不声称生产集成。本周补的是真实 schema 的 mock 导出与配对评估，真实导出需要对方签字。"

这句话比"集成中"或"已完成"都安全。

---

## 三、两件现在就能做完的事（2026-11-24）

### A. 边界相图：把「spike 赢、real/ticket 打平」变成一条曲线

`experiments/BOUNDARY_REPORT.md`。核心是把三个已发布结果换算到同一个轴 ——
**审阅预算占图的比例**：

| family | 预算/图 | Δ caught（marginal − confidence） |
|---|---:|---:|
| spike | 20% | **+6.2 pp** |
| real | 38% | **+1.3 pp** |
| ticket | 38% | **+1.6 pp** |

在真实 21 节点拓扑上把预算从 2 扫到 20：10% → +16.8pp，29% → +3.4pp（区间不含 0），
38% → +1.3pp（区间跨 0），57% 起 ≤0.8pp 且下界触 0，2/3 以上精确为 0。
**增益随覆盖率单调下降，约 1/3 处降到测不出的量级。** 所以 real/ticket 的打平不是「域的特性」，
是预算位置：K=16 在 n=80 上有 +6.2pp，在 n=21 上只有 +0.3pp —— 绝对次数解释不了，覆盖率能。

回归测试 `experiments/test_published_parity.py` 锁住 harness 与已发布表格一致
（real 0.50/0.47、ticket 0.32/0.29）。形状（深度×集中度×规模）是二阶：10% 预算下
全部 40 个单元增益为正，符号不翻。

### B. 测量层：把「不可用」变成可测的断言

`triage_bench/MEASUREMENT_LAYER.md` + `triage_bench/audit/coverage.py`（15 tests）。

现状（75 条纠错）：`resolved_at` **1/75** 且只有日期、`resolved_by` 17/75、
58/75 是 `resolution_unknown_legacy`、从未被 flag 的错误 7/72（窄）· 17/85（宽）。
所以 `recall@minutes` 现在**在数学上不可回答**，能回答的只有「审了几次」。

代码把这条变成断言：未覆盖的错误计为未知（不算正确）、任一收据缺时长则
`recall@minutes = unavailable`（不填 0）、`coverage_fraction` 空集返回 `unavailable`。
补的缺口就三个字段：`opened_at`、`submitted_at`、`field_path`。

---

## 四、建议顺序

1. ✅ **票务 family 已完成**：`graphs.py` / `run_benchmark.py` / 测试 / `outputs/ticket-v1/`（结果见上，27 个测试通过）。
2. ✅ **S1 已完成**：`sciforge_review/export/`（PROTOCOL 冻结 / REPORT / 17 tests）。控制实验结论：评估器校准；`pipeline_order` 非弱基线；未验证先验会抹掉结构优势，主方法改 flat 先验；定量主张需 ≥100 个确认错误。
3. ✅ **A 边界相图 / B 测量层已完成**（见上）。周三讲：一条曲线解释三个族 + 测量层缺口是三个字段。
4. **周三汇报**：讲 ticket 的"打平"结果 + SciForge staging 现状 + 明确 S2/S3 的外部依赖。
5. **之后**：拿真实导出再谈生产；不要在没有 owner 签字时动 composition。

---

## 五、不要做

- 不要给票务环境编"实测错误率"；它只有先验。
- 不要把 `ticket` 和 `real` 的数字合并成"跨域平均"。
- 不要在 SciForge 主仓新建并行收据接口；契约地图已明确"不成立"。
- 不要把 mock 导出写成"真实证据链"。
- 不要把边界曲线说成「图感知审阅普遍有用」——它只在低覆盖率成立；覆盖率过半后测不出可用差异。
- 不要把 `type_prior`（节点类型先验）和「类型规则」（M1–M6 审计规则）混成同一个"type"。
- 不要把 `review.suggest` 做成写回；建议与人类动作必须分离。
