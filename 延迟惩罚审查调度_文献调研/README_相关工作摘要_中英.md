# 相关工作摘要（中英对照）· Related Work Summary (CN-EN)

> 三篇中文调研文档的精简双语版，供写 related work 段落与 Slide 10 用。
> Bilingual digest of the three Chinese literature docs, for the related-work section and Slide 10.

---

## 1. 我们的定位 / Our positioning

- 中文：我们的贡献是「组合新颖性」：依赖图上的主动节点选择 + 稀疏延迟奖励 + 预算约束，没有任何单一组件是新的。
- EN: Our contribution is combination novelty: active node selection on a dependency graph + sparse delayed reward + budget — no single component is new.

- 中文：三股文献：learning-to-defer（何时把人叫进循环）、预算 bandit（资源约束）、错误级联/传播（依赖图）。
- EN: Three strands: learning-to-defer (when to call humans in), budgeted bandits (resource constraints), error cascades/propagation (dependency graphs).

---

## 2. Learning-to-defer（最直接相关）/ Learning-to-defer (most direct)

| 论文 Paper | 关键点 Key point |
|---|---|
| Mozannar & Sontag, ICML 2020 | 分类器 + rejector 联合决定 AI 或人预测。/ classifier + rejector decide AI vs human. |
| FALCON, arXiv:2604.00904 (2026) | 疲劳 + 预算 + CMDP + PPO。**最接近我们的组件，但无依赖图传播**。/ fatigue + budget + CMDP + PPO; closest components but no graph propagation. |
| SLTD, arXiv:2109.06312 (2021) | 顺序 defer 的 model-based RL；传播的是「不确定性」非「证据条目」。/ model-based RL for sequential deferral; propagates uncertainty, not evidence items. |
| Online Deferral Budget, arXiv:2409.20489 (2024) | 在线 defer + 预算 = 双臂 contextual bandit；**它的 BestReject 就是我们要的「校准阈值」基线**。/ online deferral + budget = two-armed contextual bandit; its BestReject is our calibrated-threshold baseline. |
| KL-PBD, arXiv:2610.15128 (2026) | 延迟 + 选择性反馈 + 队列拥堵。/ delayed + selective feedback + queue congestion. |

- 中文：L2D 是逐条独立 defer（bandit）；我们不同：图上主动选节点 + 稀疏延迟奖励。
- EN: L2D defers per-item independently (bandit); we differ: active node selection + sparse delayed reward.

---

## 3. 预算 bandit / Budgeted bandits

- 中文：Badanidiyuru et al., Bandits with Knapsacks (FOCS 2013)——资源预算下的 bandit 起点。
- EN: Bandits with Knapsacks (FOCS 2013) — starting point for budgeted bandits.
- 中文：延迟反馈 bandit（Joulani et al. ICML 2013）——延迟造成加性 regret 惩罚，是标准结论。
- EN: Delayed-feedback bandits (Joulani et al., ICML 2013) — delay adds an additive regret penalty; standard result.

---

## 4. 错误级联 / 传播 / Error cascades / propagation

- 中文：Data Cascades（Sambasivan et al., CHI 2021）——数据错误「opaque / delayed / invisible」地向下游复合。概念级锚点。
- EN: Data Cascades (CHI 2021) — data errors compound downstream, opaque/delayed/invisible. Conceptual anchor.
- 中文：Finkel et al. 2006——NLP 流水线错误逐级传播，用 Bayesian 网络建模。
- EN: Finkel et al. 2006 — NLP pipeline errors propagate stage-by-stage, modeled as a Bayesian network.
- 中文：From Spark to Fire, arXiv:2603.04474 (2026)——LLM 多智能体协作抽象成**有向依赖图**，错误级联 + 早期风险准则。
- EN: From Spark to Fire (2026) — LLM multi-agent collaboration as a directed dependency graph; error cascades + early risk criterion.
- 中文：label-dependent noise（DN-ILDL, 2024）——「猫狗混淆」式类型级错误聚集，是已知概念。
- EN: label-dependent noise (DN-ILDL, 2024) — type-level error clustering (cat/dog confusion) is a known concept.

---

## 5. 一句话给 related work 段落 / One line for the related-work section

- 中文：先有逐条独立的 learning-to-defer（bandit 族），再有预算/延迟反馈 bandit，再有错误级联传播——但**没有人把「依赖图传播 + 预算 + 学习该审哪个节点」接起来**，这正是我们的立足点。
- EN: Prior work covers per-item learning-to-defer (bandits), budgeted/delayed-feedback bandits, and error cascades — but no one combines dependency-graph propagation + budget + learning which node to review; that is our foothold.
