# Boundary full v1：开发集结果核验

2026-11-12。只读取用户完成的实验；未重新训练、评估或访问确认集。

## 证据与完整性

- 原始记录：`../runs/boundary-full-v1/{bc,misspec,planning}/results.json`。
- 主指标：预算 16 次审阅后残留的 sink errors，越低越好。N=80。
- 每组学习策略均有训练种子 1–5，每个条件均为 200 张相同图，graph seeds 1000–1199。
- 三份结果记录的 Python 源码 SHA256 与当前 `experiments/*.py` 一致；static/observed 训练 manifest 一致；20 个评估 checkpoint 的 SHA256 全部匹配。
- BC 独立输出与 misspec matched 的 BC/FT 逐图数组完全相同；planning 与 misspec 中所有共有 matched 数组完全相同。
- 区间来自保存结果对应的 10,000 次 crossed bootstrap，保留图配对并重采样训练种子。规划器只有图重采样；未包含额外粒子 RNG 不确定性。
- 这是预注册明确标记的开发集。未读取或运行 graph seeds 2000–2199 的独立确认集。

## Matched

| 策略 | 平均 sink errors | 相对 belief greedy 的差值 | 95% bootstrap CI |
|---|---:|---:|---|
| confidence threshold | 1.440 | +0.340 | [+0.200, +0.495] |
| belief greedy | 1.100 | 0 | — |
| 2-step greedy | 1.020 | −0.080 | [−0.160, −0.010] |
| REINFORCE/static | 1.517 | +0.417 | [+0.161, +0.766] |
| REINFORCE/observed | 1.709 | +0.609 | [+0.404, +0.829] |
| BC | 1.201 | +0.101 | [+0.007, +0.197] |
| BC+FT | 1.525 | +0.425 | [+0.240, +0.650] |

BC+FT − BC = +0.324，95% CI [+0.129, +0.568]。逐训练种子退步为
[+0.110, +0.175, +0.750, +0.295, +0.290]；不是只有一个失败种子。
BC 相对教师的区间上界 +0.197，大于预选非劣界值 +0.10，故未通过 near-parity 判据。
BC 明显优于这次从头训练的 observed RL，但不能据此断言表示能力完全充分。

两步规划平均减少 0.080 个错误，约为一阶 greedy 残留错误的 7.3%；属于开发集上的小幅规划收益。
所有学习策略与两步规划的差值区间均在零以上。现有结果不支持 RL 优势。

## 模型误设与 reviewer shift

| 条件 | belief greedy | static RL | observed RL | BC | BC+FT |
|---|---:|---:|---:|---:|---:|
| prop_odds_x0.5 | 1.160 | 1.517 | 1.714 | 1.216 | 1.540 |
| prop_odds_x2 | 1.080 | 1.517 | 1.712 | 1.188 | 1.490 |
| conf_logit_minus0.5 | 0.990 | 1.517 | 1.612 | 1.167 | 1.398 |
| conf_logit_plus0.5 | 1.250 | 1.517 | 1.866 | 1.196 | 1.687 |
| catch0.7_known | 2.350 | 2.675 | 2.778 | 2.442 | 2.640 |
| catch0.7_unknown | 2.345 | 2.675 | 2.806 | 2.450 | 2.651 |

两个从头 RL 及 BC+FT 在全部条件下均比 greedy 差，开发集逐条件差值区间均在零以上。
BC 在 conf_logit_plus0.5 均值略优，Δ=−0.054，CI [−0.185, +0.067]，不能声称胜出。
该条件上界小于 +0.10，只能记为探索性通过非劣判据，不能挑选为已确认的优势。
FT 在全部 7 条件、每个训练种子上都比相应 BC 差。

static 策略不接收扰动后的 belief 特征，因此前五个固定真实环境条件得分相同符合设计。
模型误设下 greedy 偶有改善，不能推出错误模型更好；有限开发图与粒子近似均可能影响结果。
catch known/unknown 的 2.350/2.345 也不足以说明识别 reviewer 能力没有价值。

## 数值限制与成本

`n_degenerate` 记录观察到 flag、但没有任何粒子能解释该错误的事件；不是一般 ESS 指标。
matched：greedy 0/200 episodes，2-step 3/200，BC 23/1000，BC+FT 22/1000。
conf_logit_plus0.5：greedy 6/200，BC 212/1000；应保留为近似后验的诊断限制。
这些计数不包含规划器所有 hypothetical branch 的完整退化统计，不能声称规划近似已经充分验证。

保存的 matched 整组评估时间：无两步规划约 28.09 秒，含两步规划约 220.32 秒。
这是整个条件的墙钟时间，包含基线和所有模型；不能据此直接声称两步规划的单策略速度比。

## 对研究方向的含义

当前实现与训练配置没有证明 RL 带来优势；也没有证明所有 RL 或更长时域学习都无价值。
受控的 BC→FT 对比支持“本次无 KL 的 REINFORCE 微调损害策略表现”，不能单独识别
credit assignment、探索、学习率、优化或分布漂移中的哪一种机制。
`rl_distill.py` 开头旧说明把该现象直接归因于 credit assignment，解释时应以预注册限制为准。

SciForge 应保留“主动取得核验依据”的研究主线，以强 greedy/固定流程/规划器作为正式竞争基线。
真实睡眠主张的语义核验、证据可得性、判定可靠性和成本尚未被这个合成 DAG 实验检验。
若未来对两步规划做独立确认，应先冻结候选与 matched 条件，再由用户运行独立确认；本次未启动。

## 终端导入问题

`sciforge_review/llm.py` 存在；项目根目录运行 `python3 -m sciforge_review.llm --help` 成功。
日志中的 ModuleNotFoundError 出现在 home 目录，早于进入项目，因此是模块搜索路径问题。
换新密钥后，从项目根目录运行原来的 `--check` 与 `--prompt` 命令即可继续检查网络/API。
本次未读取凭据、未发出 API 请求；不能声称 API 连接已通过。
