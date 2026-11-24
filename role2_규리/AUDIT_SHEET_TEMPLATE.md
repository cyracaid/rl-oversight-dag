# 审计清单模板（Gap D 负样本 · 给睡眠实验室）

2026-11-24. 配套：`DATA_REQUEST_GAP_D.md`（为什么需要）、`signal_calibration_real.py`（消费者）。

> 背景更新：`experiments/REAL_CONFIDENCE_RANKING.md` 测出流水线自己的信号是**后果驱动**的
> （原始时间戳 AUC 0.569，定位 hit@1 ≈ 0）。所以这份清单要补的**不只是负样本**，
> 更关键的是**对原始时间戳本身的直接判定**。两条都要，见 §3。

---

## 1. 一行 = 一个被审计过的节点

CSV，UTF-8，无参与者标识。表头固定为：

```
record_id,node,node_type,confidence,is_error,audited_by,review_seconds
```

| 列 | 类型 | 说明 |
|---|---|---|
| `record_id` | string | 伪匿名记录键，同一夜不同行共用同一值 |
| `node` | string | 必须是 `experiments/real_pipeline_graph.py` 里的节点名（N=21） |
| `node_type` | string | `order_error` / `awake_getup_diff_error` / `bed_sleep_diff_error` / `sleep_awake_equal_error` / `sleep_awake_24h_error` / `metric_spike`；人工审计时可留空 |
| `confidence` | float (0,1) | **人工介入之前**流水线给出的分数。没有分数就整条不要导出，不要填常数 |
| `is_error` | 0/1 | 人工判定：1 = 该节点值错误 |
| `audited_by` | string | `human:<initials>`；脚本据此拒收模拟行 |
| `review_seconds` | float | 该节点实际耗时，可选，用于成本曲线 |

---

## 2. 抽样规则（必须写进 manifest）

只导出已确认的错误行 = 没有负样本 = 不是标定。规则：

1. 取 **30 条记录**（有校正的、时间戳完整的优先）。
2. 每条记录审计 **5 个节点**：
   - 全部被标记（flagged）的节点；
   - 再从**未被标记**的节点里随机抽，补到 5 个。
3. 30 × 5 = 150 行，其中负样本（`is_error=0`）预期 ≥ 60 行 —— 足够。

若某条记录被标记节点不足 5 个，就用未标记节点补满；全部节点都标记了，就整条记 1 行说明。

### 最低门槛（低于此不拟合，只描述）

| 项 | 值 |
|---|---|
| 审计行数 | ≥ 200（150 可先跑描述，不发布） |
| 不同记录 | ≥ 30（bootstrap 按记录重采样） |
| 每类样本 | ≥ 20 正、≥ 20 负 |
| 覆盖错误类型 | ≥ 6 类中的 4 类 |
| 每个错误类型 | ≥ 10 负样本（本清单新增：分类别定阈值，避免大类淹没小类） |

---

## 3. 最关键的一条：原始时间戳的直接判定

上面的表默认 `node` 是流水线节点名。实测发现：**流水线对四个原始时间戳（bed / sleep /
awake / getup）没有任何直接测量**，它们的分数是从下游反推的均值，所以排不出「因」。

因此清单**额外要求**这四列（如果实验室能提供）：

| 列 | 类型 | 说明 |
|---|---|---|
| `raw_field` | string | `bed` / `sleep` / `awake` / `getup` |
| `raw_confidence` | float (0,1) | 采集端或第二读者对该时间戳的独立可信度。**不是**流水线输出 |
| `raw_source` | string | `device_qc` / `second_reader` / `actigraphy` / `none` |

没有 `raw_confidence` 也能做记录级标定；有了它，节点级定位才第一次可测。
`raw_source=none` 是重要信息，不要省略。

---

## 4. 交付边界

* 不做：参与者标识、原始 `*.rds`、任何逐行数据进仓库。
* 做：本地 CSV → `signal_calibration_real.py --human-audited` → 只提交
  `results/calibration-v1/calibration.json` + `calibration.md` + `manifest.json`（含 sha256）。
* 聚合口径按 `TRACKS.md`；能否出实验室由 IRB 决定。

---

## 5. 已知的坑

1. **全正样本**：现有 `manual_error_correction_*.csv` 三个文件共 75/64/72 行，全是正样本。照抄它们不会得到负样本。
2. **`manual_error_correction_review.csv` 不是审计日志**，它是 step5 名单，全是被标记者。
3. **`awake` 在导出里是起床时钟时间**，`awake == sleep` 永不成立，`sleep_awake_equal_error` 在该导出中不可检出 —— 这一类只能靠审计直接判。
4. **只有 25 条夜间顺序无效**，而已有 21 条校正，所以「从现有文件里回收负样本」上限约 4 条，已实测为不够。

---

## 6. 一句话版本（可直接转发）

> 请按 §1 的列导出一份节点级审计表，30 条记录 × 每条 5 个节点，被标记的节点全查、未标记的随机补满；
> 如果采集端或第二读者对四个原始时间戳有独立可信度，请一并加上 `raw_field` / `raw_confidence` /
> `raw_source` 三列。不需要任何参与者标识，原始文件不用出门。
