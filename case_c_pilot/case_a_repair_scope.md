# A：反转修复结论能推广多远？

开发版本 0.1，2026-11-12。公开聚合证据已读取；未运行 R、未接触个体数据。

## 原主张与分析对象

开发用待审主张：“两个 swap 子类在评测中达到 100%，因此所有时间反转都能正确修复。”
这是为开发构造的推断主张，不冒充仓库作者逐字说过的话。
分析对象是固定版本的合成注入评测，不是参与者真实意图或全体研究人群。

## 初始证据

同一结果表中，`swap:上床-入睡` 为 106 条，`swap:醒来-起床` 为 25 条，
两类 `corrected_pct` 均为 100，`wrong_repairs` 均为 0。
初始包在正式执行时必须包括其本来可见的表名与评测说明；若原角色本就能读整表，
不得截表制造虚假的主动取证优势。截取子表只能标记为受控材料条件。

## 已完成的公开核验

固定 commit：`ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9`。
本端通过 GitHub CLI 内容 API 读取以下文件，保存 blob 标识如下：

| 来源 | Git blob SHA |
|---|---|
| `validation/reverse_order/README.md` | `7778f4e41f11af79bf68930d87a8c207436f39d5` |
| `validation/reverse_order/results/real_mix_outcome.csv` | `2891d54bf7ea4fdae67acf08f88c3fc1c6bf1abc` |
| `validation/reverse_order/results/real_mix_run_info.csv` | `8eda01f2a737406075e62529b842315b0789327e` |
| `validation/reverse_order/results/real_mix_clean_rows.csv` | `5ef2744ce1b88eeeb8631cde138cc2304ff693bb` |

原始列名保留，不改写成另一套指标：

| class | n_injected | corrected_pct | wrong_repairs |
|---|---:|---:|---:|
| awake_before_bed | 17 | 0 | 17 |
| night_block_12h | 40 | 5 | 38 |
| single_field_12h:上床 | 40 | 17.5 | 33 |
| single_field_12h:入睡 | 102 | 100 | 0 |
| single_field_12h:起床 | 17 | 100 | 0 |
| single_field_12h:醒来 | 3 | 0 | 3 |
| swap:上床-入睡 | 106 | 100 | 0 |
| swap:醒来-起床 | 25 | 100 | 0 |
| ALL | 350 | 74 | 91 |

各类 n 合计 350，wrong_repairs 合计 91；350 × 0.74 = 259，259 + 91 = 350。
这些是表内算术一致性核验，不是重新运行评测。
本表 `flagged_only_pct` 全为 0；不能把“可能人工兜底”当作这 91 条已有成功修复证据。

运行信息：sleepcleanr 1.7.2，seed 20260817，500 participants × 14 days，rate 0.05。
`real_mix_run_info.csv` 中 `n_clean=7000` 对应此运行的总生成行数；
`real_mix_clean_rows.csv` 的 `n_clean=6650` 对应未注入行，`altered=0, flagged=0`。
7000−350=6650；字段同名但口径不同，引用时必须指明文件与分母。
README 说明固定结果包版本 1.7.2，而当时源码树已经是 1.8.0 development；
commit 固定表的来源，不代表表是用该源码树重跑得到的。

## 开发参考判断

- “本次混合注入全部正确修复”：contradicted，91 条 wrong_repairs 构成直接反例。
- “两种 swap 在本次注入设置中均为 100%”：supported，限于所列样本和版本。
- “真实人群所有反转有 74% 可修复”：unresolved；注入类别比例与成功率不能直接当总体性能。
- “未注入行在这次运行中未被标记或修改”：supported，限于 6650 条。
- “74% 是最新开发版本的性能”：unresolved；当前读取的是 1.7.2 的已保存结果。

参考判断为本端开发评审，尚无独立评判者；不能据此报告测试集准确率。

## 手工行动轨迹与停止

1. 查完整 outcome 表：发现成功率按类别显著不同，取得反例。
2. 查 README：核对合成注入、固定混合比例及适用样本限制。
3. 查 run info：确认版本与实验参数，避免把保存结果写成最新源码重跑。
4. 查 clean-row 表：核对未注入行分母和误改情况。

对“本次混合评测全部正确修复”可停止于 contradicted；无需回访或运行真实数据。
对其他版本及真实人群的泛化保持 unresolved。没有计时的人工成本记 unknown，
不根据文件数量虚构分钟数，也不声称该行动顺序最优。

## 来源入口

[README](https://github.com/cyracaid/sleepdiary-cleaner/blob/ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9/validation/reverse_order/README.md) ·
[Outcome](https://github.com/cyracaid/sleepdiary-cleaner/blob/ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9/validation/reverse_order/results/real_mix_outcome.csv) ·
[Run info](https://github.com/cyracaid/sleepdiary-cleaner/blob/ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9/validation/reverse_order/results/real_mix_run_info.csv) ·
[Clean rows](https://github.com/cyracaid/sleepdiary-cleaner/blob/ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9/validation/reverse_order/results/real_mix_clean_rows.csv)
