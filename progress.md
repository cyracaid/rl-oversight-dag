# 进度

- 2026-11-12：用户明确设计目标为 SciForge 实际科研核验能力，以 sleep data 验证后跨领域扩展；要求本地 md 与飞书辩论底稿，并调研最新 benchmark。
- 已读取 sleepdiary-cleaner 远端文件树；未读取个体数据，未运行实验。
- 完成 290 行设计 debate 初稿与定向一手调研；文档基础断言检查和 git diff --check 通过。
- 飞书当前页侧栏按钮点击未产生导航或创建入口；未创建、未覆盖任何飞书文档。后续仍需同步独立设计文档。
- 用户确认主任务为审查已有科研主张并主动取得核验依据；主稿更新 v0.2，补充案例契约、行动流程、语义核验示例、成对对照及 pilot 通过条件。具体睡眠主张尚未确定。
- 用户移交 sleep 仓库 agent 的 A/B/C 候选；选 C 主例、A/B 对照。公开固定 commit 核对目录与反转表，纠正 3 人为 4 人；新增 SCIFORGE_CASE_C_AWAKENING.md 七项规格及移交请求。未访问私有记录或执行实验。
- 新增 SCIFORGE_VERIFICATION_PROTOCOL.md，明确双赛道、行动返回、判定与成本评分、基线及 pilot 冻结条件；修正 Case C 中数值稳健不能支持测量语义的逻辑。私有材料返回、飞书同步及相邻理论综述仍未完成。
- 核验用户完成的 boundary-full-v1 原始数组、5 个种子、源码及 checkpoint 哈希；未重跑。开发集 matched：greedy 1.100、2-step 1.020、BC 1.201、BC+FT 1.525；所有条件均未发现 RL 胜过 greedy。解释写入 experiments/BOUNDARY_FULL_V1_INTERPRETATION.md；独立确认集未运行。项目根目录模块 --help 成功，home 目录导入失败原因已定位，未读取密钥或调用 API。
- RL 归档已经隔离 worktree 推送远端 main，提交 8a6769f；包含韩文摘要、原始合成结果与 checkpoint。收到 Case C 聚合移交：5/6 为词匹配，20/75 为筛选样本宽匹配，目录 12 行与窄匹配 9 行未对齐。新增 SCIFORGE_CASE_C_HANDOFF_20261112.md，定义私有端 20 行备注编码与集合对齐返回契约；未读取修正表，未把移交升级为独立验证。所述源案例文档全文尚未取得。
- 新增 case_c_pilot/ 开发包：韩文摘要、候选初始包、证据与行动可用性账本、实际手工核验轨迹、四策略比较规范。C1/C2/C3 目前均 unresolved；等待材料不等同于证据永久不可得或预算耗尽。未运行模型、未生成虚构比较数值；源文定位搜索未成功，广域搜索超时。
- 用户无需持有字段；继续完成 C-aggregate 开发判断和 A 的公开证据手工核验。通过 gh API 固定 commit 读取 outcome/README/run info/clean rows，记录 blob SHA；核对 259 正确+91 错修=350，澄清 n_clean 7000 与 6650 分母。新增 aggregate_judgment.md 与 case_a_repair_scope.md；没有运行四策略、没有独立评分、没有访问私有记录。
- 用户授权模型诊断后，新增 case_c_pilot/run_diagnostic.py 与执行说明，调用已配置模型执行 A/C×四策略。/models=200，但8次生成全部502；最小64-token生成亦502，脱敏响应为 upstream_error / Upstream access forbidden, please contact administrator。保留全部失败提示与日志，新增 FAILURE_REPORT.md；未取得模型答案，禁止报告策略比较或科学判断准确率。恢复依赖网关生成访问权限。
