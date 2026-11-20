# 调研证据与发现

## 已确认
- GitHub sleepdiary-cleaner 文件树已读取，存在字段 schema、人工纠错、盲审、typing task、真实数据 specification curve、合成错误目录与 multiverse 脚本。
- 文件存在仅证明实现材料存在，尚未证明运行完成或结果有效。
- 先前 AI4S 汇总中的 4%、79.4%、57.9%、30.4/100 分母和任务不同，待原始来源核验，不作为统一可信度标尺。

## 待阅读
- README、SCHEMA、CLINICAL_WORKFLOW、ARCHITECTURE、validation README、blind audit、synthetic error catalog、downstream analysis plan。

## 本轮已读与重要发现
- README、SCHEMA、ARCHITECTURE、CLINICAL_WORKFLOW、validation README、blind audit README/ANNOTATOR_GUIDE、typing task、下游分析计划、真实 spec curve 脚本已读；固定 commit ef1d5e4cabeba19aa1794b21dd915c8e5cbd9cd9。
- 盲审实际数据尚未开展。SOL 冲突标注示例与“冲突不是已证错误”原则存在张力，需讨论。
- 真实阈值扫描脚本报告所有维度未过筛选阈值；不能预设结论会翻转。
- sleep–affect 下游关联仍是待定 outcome/模型/数据访问的计划。
- BioBasicsBench 官方发布、Kosmos v1、Co-Scientist 扩展 v1、SciIntegrity-Bench v2、FIRE-Bench v1、ActiveClean 官方项目已读。57.9% 是 synthesis 陈述准确率，非通用综合准确率。
- 主稿 SCIFORGE_TRUST_BENCHMARK_DEBATE.md 包含证据分层、竞争定位、任务与指标、六个 debate 点。不是已批准实现设计。
