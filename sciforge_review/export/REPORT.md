# sci-export-v1 报告 — 协议已冻结，数据仍是 mock

**读这一页只需记住一件事：这里所有数字都是合成的。** 它们是控制实验，用来证明
「评估器能看见信号、且只在有信号时看见」，不是任何真实证据链的结果。

协议在 [`PROTOCOL.md`](PROTOCOL.md) 冻结（2026-11-24，之前没看过任何真实导出）。

---

## 1. 做了什么

| 件 | 作用 | 状态 |
|---|---|---|
| `load_export.py` | 按 `SCIFORGE_ASK.md §4` 解析导出，校验失败就抛错，不可用项计数而非静默丢弃 | 17 个测试 |
| `bench.py` | 7 条策略 + oracle，顺序接口，真值只在 harness | 已跑 |
| `make_mock.py` → `sciforge_mock_v1.json` | 21 节点阳性对照（错误按声明先验生成） | 确定性，seed 20261124 |
| `controls.py` | null / 类型信号 / 结构信号 三种错误布置 | 400 次/种 |
| `PROTOCOL.md` | 主指标、baseline 理由、统计、样本量、泄漏规则、句子模板 | 冻结 |

## 2. mock 上的表（无证据价值）

`python3 -m sciforge_review.export.bench --boot 500`

节点 21、确认错误 6、K=5。

| policy | recall@K | 95% CI |
|---|---:|---|
| `pipeline_order` | 0.17 | [0.00, 0.50] |
| `random`（200 次） | 0.22 | [0.00, 0.60] |
| `type_prior` | **0.50** | [0.00, 0.83] |
| `reach` | 0.17 | [0.00, 0.50] |
| `type_x_reach` | 0.33 | [0.00, 0.67] |
| `marginal_adaptive`（flat） | 0.17 | [0.00, 0.50] |
| `marginal_adaptive_declared` | **0.50** | [0.00, 0.80] |
| `receipts` | 0.17 | [0.00, 0.50] |
| `oracle` | 0.83 | [0.45, 1.00] |

人类收据没覆盖到的确认错误：**4 / 6**。

这张表只说明一件事：mock 里的信号是类型信号，`type_prior` 抓到了（0.50 vs 0.17），
`oracle` 没到 1.0（K=5 < 6 个错误）。**单张图的区间宽到 0.5，什么都判不了。**

## 3. 控制实验（这次真正有用的部分）

400 次独立错误布置，同一 21 节点结构，K=5，E=6。

| 布置 | `pipeline_order` | `random` | `type_prior` | `reach` | `marginal_adaptive`（flat） | `marginal_adaptive_declared` | `oracle` |
|---|---:|---:|---:|---:|---:|---:|---:|
| **null**（与类型、结构无关） | 0.241 | 0.237 | 0.231 | 0.241 | 0.241 | 0.231 | 0.827 |
| **type_signal** | 0.131 | 0.242 | **0.414** | 0.132 | 0.132 | 0.391 | 0.818 |
| **structure_signal** | 0.487 | 0.240 | **0.000** | **0.622** | **0.622** | 0.163 | 0.828 |

配对差（同一次布置内比较）：

| 比较 | null | type_signal | structure_signal |
|---|---:|---:|---:|
| `type_prior` − `pipeline_order` | −0.010 | **+0.283**（79% 胜） | −0.487（99% 负） |
| `reach` − `pipeline_order` | −0.000 | +0.001 | **+0.135**（69% 胜） |
| `marginal_adaptive` − `type_prior` | +0.010 | −0.283 | **+0.622** |

### 三条结论

1. **评估器是校准的。** null 下三种布置的均值差都在 ±0.01，没有系统性偏向。
   如果哪天 null 里出现 +0.2，先怀疑泄漏，不要先怀疑方法。
2. **`pipeline_order` 不是弱基线。** 在结构信号下它 0.487，random 只有 0.240 —— 依赖顺序本身
   就近似「影响大在前」。任何方法要赢的是它，不是 random。
3. **先验指错方向时，结构优势会被抹掉。** 同一份结构信号：纯结构 0.622，
   `type_x_reach` 0.260，`marginal_adaptive_declared` 0.163。所以主方法用 flat 先验，
   声明先验只做敏感性臂。这不是保守，是因为先验没有任何一条链上的证据支持。

### 附带一条：flat 先验下，自适应会退化成 `reach`

没有裁决反馈时 `marginal_adaptive(flat)` 与 `reach` 数值相同。自适应项只有在真的审到
错误、且该错误有下游权重时才会改变排序。所以「自适应」必须靠昨日发现的错误数来证明，
不能靠表里多一行来证明。

## 4. 样本量（比方法更硬的约束）

`recall@K = hits/E`，`hits ~ Binomial(E, p)`，E = 确认错误数。本表实测配对差 sd ≈ 0.12–0.26（E=6）。

| 确认错误 E | 近似配对 sd | 可测最小 Δ（80% power） |
|---:|---:|---:|
| 6 | ~0.15 | ~0.42 |
| 25 | ~0.07 | ~0.20 |
| 100 | ~0.037 | ~0.10 |

**冻结要求**：定量主张需 ≥2 个项目、合计 ≥100 个确认错误、≥150 个节点。
低于此只能写案例。这一条已经写进 `PROTOCOL.md §6`，拿到数据后不许改。

## 5. 对周三的意义

可以说：

> SciForge 侧的评估协议已经冻结并跑通：装载器、7 条基线、配对区间、三类控制实验（17 个测试）。
> 控制实验显示评估器在校准范围内，且未经验证的先验会抹掉真实结构优势，所以主方法用 flat 先验。
> 真实导出还没有；按协议需要 ≥2 个项目、≥100 个确认错误才谈得上定量结论。

不能说：

- 「在 SciForge 上验证过」——没跑过。
- 「方法优于现有顺序」——没有真实数据。
- 引用本报告的 mock 数字。

## 6. 真实导出到位时只改三处

1. `--export` 指向真实文件（`load_export` 已按 §4 校验，缺字段直接报错）。
2. 先验：要么留 flat，要么用**另一个项目**估；不许在本项目上估。
3. 重采样单位：项目或误差簇，不用节点（`bench.bootstrap` 现在按节点，需换成簇）。

其余（K、主指标、判定句、baseline 集合）已冻结，不改。

## 7. 复现

```bash
cd ~/Documents/강화학습
python3 -m sciforge_review.export.make_mock
python3 -m sciforge_review.export.bench --boot 500 --out sciforge_review/export/outputs/mock_v1.md
python3 -m sciforge_review.export.controls --out sciforge_review/export/outputs/controls.md
python3 -m unittest discover -s sciforge_review/export/tests -t .    # 17 tests
```

产物：`outputs/mock_v1.md` / `mock_v1.json` / `controls.md`；代码与协议同目录。
