# 给郑心的一页：审阅调度需要从 SciForge 拿什么

> 用途：SciForge 证据链上的**只读审阅优先级建议器**（Track C）。
> 课程侧（Track P）已有合成图与睡眠管道的结果；这一步是把同一方法放到真实证据链上。
> 状态：草稿，等确认字段与脱敏规则后再发。

---

## 1. 一句话

当一条 AI 辅助的科研证据链只能人工抽查少数节点时，我们想学「先审哪个节点」，
并用**真实审阅记录**验证它比现有顺序好在哪。不需要写权限，不需要改 SciForge 的任何规则。

## 2. 为什么必须是真的

我们已经在 1,048 行的睡眠管道队列上算过：队列精度 6.5%，一条类型规则用 13% 的
审阅量拿到 84% 的错误——**但这就是类型信息的天花板**（见 `triage_bench/CEILING.md`）。
要判断这个天花板是睡眠数据特有，还是证据链的普遍性质，必须有第二条真实的链和真实的审阅过程记录。

## 3. 需要的数据（按优先级）

| 优先 | 对象 | 字段 | 用来做什么 |
|---|---|---|---|
| **P0** | 节点 | `id`、`type`（claim / dataset / run / figure）、`created_at`、`is_sink` | 建图 |
| **P0** | 边 | `src`、`dst`、`rel`（`derived_from` / `supports` / `contradicts`） | 传播方向 |
| **P0** | 纠错 | `node_id`、`error_type`、`severity`、`agreed_by`（人数或共识标记） | ground truth |
| **P1** | 收据 | `node_id`、`reviewer_hash`、`reviewed_at`、`duration_min`、`verdict` | 人类基线 + 人时成本 |
| **P1** | 范围 | ≥2 个不同项目/团队 | 跨链泛化 |
| **P2** | 快照 | 审阅发生时的图版本（而非最终图） | 避免用未来信息评估当时决策 |

**P1 的 `reviewed_at` 和 `verdict` 是整套评估的命门。** 睡眠侧 75 条纠错里
`resolved_at` 只有 1 条有值，所以我们只能算「审了几次」，算不出「审了几分钟」，
也重建不了人类当时的顺序。SciForge 的 receipts 如果有时间戳，这一块就补上了。

## 4. 导出长什么样（最小可用的形状）

```json
{
  "project": "proj_<hash>",
  "snapshot_at": "2026-11-xxT..Z",
  "nodes": [{"id": "n1", "type": "claim", "is_sink": true, "created_at": "..."}],
  "edges": [{"src": "n1", "dst": "n2", "rel": "derived_from"}],
  "corrections": [{"node_id": "n2", "error_type": "stale_dataset", "agreed_by": 2}],
  "receipts": [{"node_id": "n2", "reviewer_hash": "r7", "reviewed_at": "...",
                "duration_min": 12, "verdict": "accepted"}]
}
```

节点 ID 保留内部值即可（我们只需要图结构）；如果连 ID 也不便给，就用稳定哈希，只要边和收据能对上。

## 5. 边界（不改你们的规则）

- **只读**：不写回、不产生收据、不盖章；建议器只输出排序和理由。
- **不进仓库**：导出文件留在本地，仓库里只放代码和聚合数字（如「N 个节点、6.2% 精度」）。
- **不对外**：任何逐节点内容、项目名、客户名不进论文；论文只报聚合量与图统计。
- **可撤回**：任何时候你说停，我们就删本地导出并改用 mock。
- **不做**：不训练于你们的审阅结果做「预测谁对」；只做「先审谁」的排序评估。

## 6. 需要你确认三件事

1. **收据里有 `reviewed_at` / `duration` / `verdict` 吗？** 有 → 我们能报「每抓一个错花多少人时」；没有 → 只能报次数。
2. **能给几个项目？** 1 个只能做案例，≥2 个才能谈跨链泛化（这是 Nature Communications 那条线的硬条件）。
3. **谁签字、脱敏到什么程度？** 你，还是 Zhangyang？节点 ID 能不能保留原值？

## 7. 时间线

| 时间 | 我们做什么 | 需要你 |
|---|---|---|
| 本周 | 发这份清单 + 环境接口（`load_sciforge_dag(path)`）写好 | 确认 §6 三问 |
| 下周 | 拿到最小导出（一个项目、P0+P1），跑 recall@budget 与错误逃逸 | 一次 15 分钟对齐 |
| 再下周 | 出离线评估报告（聚合），决定是否做只读原型 | 看报告 |

## 8. 我们回馈什么

1. **一份离线评估报告**：建议器排序 vs 现有顺序 vs 按置信度，指标是 recall@budget 与每错误人时。
2. **一个只读原型**：`POST /suggest/review-order`，入参是 DAG 切片 + 预算，出参是排好序的节点和理由；不产生任何写操作。
3. **代码与复现包**：环境、基线、评估脚本，Apache-2.0 / MIT，随论文一起放出去。

---

*联系：동채하（cyracaid）· 仓库 `cyracaid/rl-oversight-dag` · 相关文档 `EVIDENCE_CHAIN_DESIGN_CN.md`*
