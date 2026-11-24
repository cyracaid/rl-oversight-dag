# 测量层：这条链现在能回答什么、不能回答什么

2026-11-24。所有数字从 `~/Documents/splsleep/manual_error_correction_updated.csv`
现算，写入本仓库的只有聚合值（Core Principle 1）。复现命令在文末。

**一句话**：排序器的收益上限已经被测量层卡住，不是被算法卡住。而测量层缺的不是勇气，
是三个字段。

---

## 1. 现状盘点（每个数都带分母）

| 项 | 值 | 分母 | 意味着 |
|---|---:|---:|---|
| 人工纠错行 | 75 | — | 这是唯一的误差真值来源 |
| `resolved_at` 有值 | **1** | 75 | 且只有一个日期 `2026-10-23`，没有时分 |
| `resolved_by` 有值 | 17 | 75 | 与 `corrected == TRUE` 的 17 行是同一批 |
| `review_resolution = corrected` | 17 | 75 | 其余 58 是 `resolution_unknown_legacy` |
| **从未被任何规则 flag** | **7** | 72 | 窄口径：`human_review == corrected` 且无 FLAG |
| 同上，宽口径 | 17 | 85 | 含只有人工纠错标识的行 |
| 审阅耗时字段 | **0** | 75 | 全表没有 `opened_at` / `submitted_at` |

### 两个必须点名的陷阱

1. **`resolution_unknown_legacy` 不等于「已确认为正确」。** 58 行是未知。把它们当正确，
   覆盖率立刻虚高 —— 这正是 `coverage.py` 把 `errors_without_receipt` 单独列出来的原因。
2. **`duration_totalmin_sol_estimate_am` 这类列不是审阅耗时。** 那是睡眠时长（SOL / WASO），
   是研究对象，不是成本。按名字 grep「duration」会直接掉进这个坑。

---

## 2. 协议里哪些指标现在算得出来

冻结协议在 `sciforge_review/export/PROTOCOL.md`，主指标是 `recall@K`。逐一对照：

| 指标 | 状态 | 原因 |
|---|---|---|
| `recall@K`（K = 审阅条数） | **可算** | 只需要「审了哪些 + 哪些是真错」 |
| `precision@K` | **可算** | 同上 |
| `reviews→50%` | **可算**（以条计） | 顺序可用 `review_resolution` 之外的行序近似，须标注为近似 |
| `recall@minutes` | **不可算** | 75 行里 0 行有 `opened_at`/`submitted_at` 对；只有 1 个日期 |
| 人类基线的时间顺序 | **部分** | 有裁决、无时间戳 |
| 单位错误成本 | **不可算** | 同上 |

**所以「每抓一个真错花了人类多少分钟」这句话，现在在数学上不可回答。**
能回答的是「花了多少次审阅」。这不是小事：次数把「一次审阅 20 秒」和「一次审阅 20 分钟」
抹成同一个单位，而这两者的调度含义完全相反。

---

## 3. 代码：把「不可用」变成可测的断言

`triage_bench/audit/coverage.py`（15 个测试，`triage_bench/tests/`）：

```python
from triage_bench.audit.coverage import summarize_export

block = summarize_export(receipt_path, key_map, error_ids)
block["coverage"]["errors_without_receipt"]        # 未覆盖 = 未知，不是正确
block["coverage"]["capabilities"]["recall_at_minutes"]
# {'status': 'unavailable', 'reason': '2/3 receipts have no opened_at/submitted_at pair; duration is not zero'}
```

四条硬规则，全部有测试：

| 规则 | 测试 |
|---|---|
| 未覆盖的错误单独计数，不算正确 | `test_unreviewed_errors_are_unknown_not_correct` |
| 任一收据缺时长 → `recall@minutes` 为 `unavailable`，不填 0 | `test_recall_at_minutes_unavailable_when_any_duration_missing` |
| 空误差集 → `coverage_fraction` 为 `unavailable`，不是 0 也不是 1 | `test_empty_error_set_is_unavailable_not_zero` |
| 删行 / 换序可被发现 | `test_deleted_line_breaks_chain` |

`to_export_receipts()` 把链式收据映射到冻结协议的 `receipts` 数组；放不下的收据进
`receipts_unmapped`，同一节点重审进 `receipts_superseded`，都不静默丢。

---

## 4. 要补的最小缺口：三个字段

`AUDIT_CHAIN_DESIGN.md §4` 已经列过可回填性，这里只说结论：**只需新增两个字段、一个已有字段
补到字段级**。

| 字段 | 现状 | 缺了会怎样 |
|---|---|---|
| `opened_at` | ❌ 无 | 时长不可导出 → `recall@minutes` 永久不可用 |
| `submitted_at` | ⚠️ 近似 `createdAt` | 时长误差 = 一次性提交的批量审阅，成本被平均掉 |
| `field_path` | ❌ 无 | 退化成行级，失去「审的是哪一个字段」的粒度 |

不需要：正文、备注、参与者信息、服务器、链上存证。`prev` 链是本地 sha256，成本接近零。

**成本估算**：前端提交时多传两个 ISO 时间戳 + 一个字段名。三个值，全是已有 UI 状态的直接读数。

---

## 5. 这条为什么比调排序器更值

- 排序器的天花板：类型规则在 19% 审阅量拿到 83.8%，在 38% 拿到 85.3%。
  剩余可争的约 `(100% − 85.3%) × 68 ≈ 10` 个错误，而现有 CI 是 ±10pp。
  **在现有数据上「方法更好」不可检验。**
- 测量层的收益：一旦有 `opened_at`/`submitted_at`，同一个 `recall` 立刻变成
  「每抓一个真错花了 4.2 分钟 vs 11 分钟」，这句话可以直接进决策，且不需要新算法。
- 唯一性：这是 SciForge 真正缺的一块（`review-control/src/contract.ts` 有 verdict，
  没有时长），也是我们相对其他组唯一有先手的地方。

---

## 6. 复现

```bash
cd ~/Documents/강화학습
python3 -m unittest discover -s triage_bench/tests -t .     # 15 tests
python3 triage_bench/run_unflagged.py                       # 从未被 flag 的错误
```

现状盘点的字段计数（只输出聚合值）：

```bash
python3 - <<'PY'
import csv, os
from pathlib import Path
d = Path(os.environ.get("SPLSLEEP_DATA_DIR", Path.home()/"Documents"/"splsleep"))
rows = list(csv.DictReader((d/"manual_error_correction_updated.csv").open()))
nz = lambda v: v not in (None, "", "nan", "None", "NA")
print("rows", len(rows))
for c in ("resolved_at", "resolved_by", "review_resolution", "corrected"):
    print(c, sum(map(nz, (r[c] for r in rows))), "/", len(rows))
PY
```
