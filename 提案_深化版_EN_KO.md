# Topic Proposal (Deepened): Review Scheduling on a Dependency Graph Under a Budget
# 주제 제안서 (심화판): 예산 제약 하의 의존성 그래프 위 검토 스케줄링

> Team project proposal | STA3145 Reinforcement Learning | Deepened version, 2026-11-08
> Each section is written in English first, then in Korean. / 각 절은 영어 → 한국어 순으로 작성.
> This version keeps the six sections of our first proposal (topic, description, RL application, dataset, related work, differentiation and feasibility) and updates them with what our second round of work found. / 첫 제안서의 여섯 절(주제, 설명, RL 적용, 데이터셋, 관련 연구, 차별점과 실현 가능성)을 유지하고, 두 번째 연구 라운드의 결과로 갱신했다.
> **Verification status:** the experiment code and results were produced by an AI agent and have not been independently checked. Items that could not be verified are listed in Section 8 and must be checked by team members later. / **검증 상태:** 실험 코드와 결과는 AI 에이전트가 만들었고 독립적으로 확인되지 않았다. 검증하지 못한 항목은 8절에 정리했으며, 이후 조원들이 확인해야 한다.

**One-line summary / 한 줄 요약:** When an AI's outputs depend on one another and a human can review only a few, we use RL to learn which node to review next, so that fewer errors reach the final conclusion. / AI 출력들이 서로 의존하고 사람은 일부만 검토할 수 있을 때, 다음에 어떤 노드를 검토할지를 RL로 배워 최종 결론에 도달하는 오류를 줄인다.

---

## 0. What Changed From the First Version / 첫 버전에서 무엇이 달라졌나

**EN**
1. **From bandit to MDP.** The first version decided pass-or-review for each item on its own. Our experiments showed that this flattens the structure, and a calibrated threshold (2.81) beat tabular Q-learning (3.38). Now the agent chooses which node of a dependency graph to review next, and a review changes what happens downstream.
2. **From a proxy dataset to our own data plus a synthetic graph.** The first version proposed CIFAR-10H images as a stand-in for human review. We now use our own real error-correction data (75 rows) to motivate the problem, and a synthetic dependency graph for the main experiments.
3. **From a plan to results.** We now have numbers, control experiments, and a failure that we report openly.

**KO**
1. **밴딧에서 MDP로.** 첫 버전은 항목마다 독립적으로 통과/검토를 정했다. 실험 결과 이 방식은 구조를 평평하게 만들었고, 보정된 임계값(2.81)이 테이블 Q-러닝(3.38)을 이겼다. 지금은 에이전트가 의존성 그래프에서 다음에 검토할 노드를 고르며, 검토는 하류에서 일어나는 일을 바꾼다.
2. **대리 데이터셋에서 우리 데이터 + 합성 그래프로.** 첫 버전은 사람 검토의 대용으로 CIFAR-10H 이미지를 제안했다. 지금은 문제의 동기를 보이기 위해 우리의 실제 오류 정정 데이터(75행)를 쓰고, 주요 실험에는 합성 의존성 그래프를 쓴다.
3. **계획에서 결과로.** 이제 수치, 대조 실험, 그리고 숨기지 않고 보고하는 실패가 있다.

---

## 1. Topic
**EN**
Learning which node to review, on a dependency graph, under a limited review budget.

**KO**
제한된 검토 예산 아래에서, 의존성 그래프 위의 어떤 노드를 검토할지 학습한다.

---

## 2. Description
**EN**
AI now does much research work, such as cleaning data and labeling literature. Part of it has no answer key, so only a human can judge whether an item is wrong, and a human cannot check everything. Two facts make *what* to review matter more than *how much*:

- **Errors are not random; they cluster by type.** In our real data, one error type (`order_error`) makes up 76% of the corrections.
- **Unreviewed errors are reused downstream, and the harm shows only at the conclusion.** Items depend on one another, so a wrong item contaminates what is built on it.

We therefore treat the evidence as a dependency graph. With a budget of reviews, the agent picks which node to review. Fixing a node stops its errors from spreading, so an early review of an upstream node can be worth more than several reviews downstream.

**KO**
지금은 AI가 데이터 정제, 문헌 라벨링 같은 연구 작업을 많이 한다. 일부는 정답지가 없어서 항목이 틀렸는지는 사람만 판단할 수 있고, 사람이 전부 확인할 수는 없다. 두 가지 사실 때문에 *얼마나* 검토하느냐보다 *무엇을* 검토하느냐가 더 중요하다.

- **오류는 무작위가 아니라 유형별로 뭉친다.** 우리의 실제 데이터에서는 한 오류 유형(`order_error`)이 정정의 76%를 차지한다.
- **검토되지 않은 오류는 하류에서 재사용되고, 피해는 결론에서야 드러난다.** 항목들이 서로 의존하므로 틀린 항목은 그 위에 쌓인 것을 오염시킨다.

그래서 증거를 의존성 그래프로 본다. 검토 예산이 있을 때 에이전트는 어떤 노드를 검토할지 고른다. 노드를 고치면 그 오류의 전파가 멈추므로, 상류 노드를 일찍 검토하는 것이 하류 노드 여러 개를 검토하는 것보다 가치가 클 수 있다.

---

## 3. How RL Is Applied
**EN**
This is a **sequential-decision MDP with sparse, delayed reward**, not a bandit.

| RL element | Definition |
|---|---|
| State S | Graph knowledge (per node: type, confidence, downstream influence on the conclusion, reviewed or not) + remaining budget |
| Action A | Choose the next node to review (plus "stop") |
| Transition P | Reviewing a node fixes it, then downstream is recomputed (propagation stops) |
| Reward R | Sparse terminal reward = −(sink errors), where sink errors are the errors that reach the conclusion |
| Discount γ | γ < 1, which encourages reviewing upstream nodes early |

Methods compared:

| Method | Role |
|---|---|
| Calibrated per-type threshold | Static-rule baseline |
| Structural greedy (picks by downstream fan-out × error likelihood) | Hand-crafted heuristic baseline |
| Bandit + tabular Q-learning | First version (negative result) |
| REINFORCE / PPO (MLP node scorer) | Preliminary run (results in Section 5) |
| **GNN node scorer + REINFORCE (fixed budget)** | **Main method (mean 1.54 ± 0.46, best seed 1.00)** |
| CMDP + PPO-Lagrangian (soft budget) | In progress (naive version fails, Section 8) |
| DQN (value-based) | Control (degenerates under sparse reward) |

The node scorer is a **graph neural network (GNN)** that encodes each node's (type, confidence, downstream influence) together with its graph neighborhood, following the GNN node-selection recipe of Mattick et al. (arXiv:2310.00112). We train it with policy gradient (REINFORCE / PPO) under a fixed review budget. We are extending this to a **CMDP + PPO-Lagrangian**, where the budget becomes a soft coverage constraint ($d_l \le$ coverage $\le d_u$) following FALCON (arXiv:2604.00904); this extension is still in progress.

**KO**
이 문제는 밴딧이 아니라 **희소하고 지연된 보상을 가진 순차 결정 MDP**이다.

| RL 요소 | 정의 |
|---|---|
| 상태 S | 그래프 지식(노드별: 유형, 신뢰도, 결론에 미치는 하류 영향, 검토 여부) + 남은 예산 |
| 행동 A | 다음에 검토할 노드를 고른다 ("종료" 포함) |
| 전이 P | 노드를 검토하면 고쳐지고, 하류를 다시 계산한다(전파 차단) |
| 보상 R | 희소한 종료 보상 = −(결론 오류 수). 결론 오류(sink errors)는 결론에 도달한 오류를 말한다 |
| 할인 γ | γ < 1: 상류 노드를 일찍 검토하도록 유도 |

비교하는 방법:

| 방법 | 역할 |
|---|---|
| 유형별 보정 임계값 | 정적 규칙 베이스라인 |
| 구조적 그리디 (하류 팬아웃 × 오류 가능성으로 선택) | 손으로 만든 휴리스틱 베이스라인 |
| 밴딧 + 테이블 Q-러닝 | 첫 버전 (부정적 결과) |
| REINFORCE / PPO (MLP 노드 점수 함수) | 예비 실행 (결과는 5절) |
| **GNN 노드 점수 함수 + REINFORCE (고정 예산)** | **주 방법 (평균 1.54 ± 0.46, 최고 시드 1.00)** |
| CMDP + PPO-Lagrangian (소프트 예산) | 진행 중 (naive 버전 실패, 8절) |
| DQN (가치 기반) | 대조군 (희소 보상에서 퇴화) |

노드 점수 함수는 Mattick et al.(arXiv:2310.00112)의 GNN 노드 선택 레시피를 따라, 각 노드의 (유형, 신뢰도, 하류 영향)을 그래프 이웃과 함께 인코딩하는 **그래프 신경망(GNN)**이다. 고정 검토 예산 아래 정책 경사(REINFORCE / PPO)로 학습한다. 이를 FALCON(arXiv:2604.00904)을 따라 예산을 coverage 소프트 제약($d_l \le$ coverage $\le d_u$)으로 두는 **CMDP + PPO-Lagrangian**으로 확장 중이며, 이 확장은 아직 진행 중이다.

---

## 4. Dataset and Controls
**EN**
**Real data, for motivation (internal data, not public).** We use an internal sleep-research dataset stored on our team's computer. The main file, `deidentified_intervalvars_forCD_111325.rds`, holds **13,990 participant-day rows** of daily sleep logs: for each row a participant records when they went to bed, fell asleep, woke, and got up, and an automated pipeline derives sleep metrics (sleep-onset latency, wake after sleep onset, sleep efficiency). A human reviewed flagged rows and corrected **75** of them, recorded in `manual_error_correction_updated.csv`. These 75 corrections are not spread uniformly: **57 of 75 (76%)** are a single error type, `order_error` (for example, a get-up time recorded earlier than the wake time); entropy is 0.612 and the Monte Carlo p-value is < 0.0001 (uniformity rejected). So the error rate is low (75/13,990 ≈ 0.54%) but the errors cluster strongly by type — exactly the setting where a limited review budget must target the right nodes. The real data motivates the problem; the core experiments use the synthetic graph.

**Synthetic dependency graph, for the main experiments.** A simulated graph (about 80 nodes) with errors that cluster by type and propagate downstream to the conclusion. Synthetic data is standard for an RL course and lets us know which nodes are truly wrong and change one factor at a time.

**Controls, to show the advantage is not built into the simulator.**
- Shuffle which items are wrong (breaks the type clustering): the learning advantage disappears.
- Flatten the graph (breaks propagation): the learning advantage disappears.
- Meaning: the advantage comes from the clustering and the propagation, not from a rigged simulator.

**KO**
**동기를 위한 실제 데이터 (내부 데이터, 비공개).** 팀 컴퓨터에 있는 내부 수면 연구 데이터셋을 쓴다. 주 파일인 `deidentified_intervalvars_forCD_111325.rds`는 **13,990행의 일별 수면 기록**을 담는다: 각 행은 참가자가 잠자리에 든 시각, 잠든 시각, 깬 시각, 일어난 시각을 기록하고, 자동 파이프라인이 수면 지표(입면 잠복기, 수면 중 각성, 수면 효율)를 계산한다. 사람이 플래그된 행을 검토해 **75건**을 정정했고, 이는 `manual_error_correction_updated.csv`에 기록되어 있다. 이 75건의 정정은 고르게 퍼져 있지 않다: **75건 중 57건(76%)**이 단일 오류 유형인 `order_error`(예: 기상 시각이 각성 시각보다 빠르게 기록됨)이고, 엔트로피 0.612, Monte Carlo p값 < 0.0001(균일 분포 기각)이다. 즉 오류율은 낮지만(75/13,990 ≈ 0.54%) 오류가 유형별로 강하게 뭉쳐 있다 — 제한된 검토 예산을 올바른 노드에 써야 하는 바로 그 상황이다. 실제 데이터는 문제의 동기를 보이고, 핵심 실험은 합성 그래프를 쓴다.

**주요 실험을 위한 합성 의존성 그래프.** 오류가 유형별로 뭉치고 결론까지 하류로 전파되는 시뮬레이션 그래프(약 80개 노드). 합성 데이터는 RL 수업에서 표준이며, 어떤 노드가 정말 틀렸는지 알 수 있고 요인을 하나씩 바꿀 수 있다.

**우위가 시뮬레이터에 내장된 것이 아님을 보이는 대조 실험.**
- 어떤 항목이 틀렸는지를 섞는다(유형 뭉침을 깨뜨림): 학습의 우위가 사라진다.
- 그래프를 평평하게 만든다(전파를 깨뜨림): 학습의 우위가 사라진다.
- 의미: 우위는 뭉침과 전파에서 나오며, 시뮬레이터를 유리하게 조작해서 나온 것이 아니다.

---

## 5. Results So Far
**EN**
All numbers are **sink errors** (errors reaching the conclusion). **Lower is better.**

**First version (bandit): a negative result we report openly.**

| Strategy | Sink errors |
|---|:---:|
| No review | 5.62 |
| Random 16 | 4.19 |
| **Calibrated threshold** | **2.81** |
| Tabular Q-learning | 3.38 |
| Review-all (upper bound) | 0.56 |

The calibrated threshold beats Q-learning across all binning choices. Diagnosis: reviewing item by item flattens the dependency graph, and with one type at 76%, the best policy collapses into a static rule.

**After reframing as active node selection on the graph:**

| Method | Type | Sink errors |
|---|---|---:|
| No review | traditional | 5.90 |
| Confidence threshold | traditional | 2.30 |
| Structural greedy | traditional (hand-crafted) | 1.80 |
| REINFORCE (MLP scorer) | ours (preliminary) | 1.40 |
| PPO (MLP scorer) | ours (preliminary) | 1.60 |
| **GNN + REINFORCE (fixed budget)** | **ours (upgrade)** | **1.54 ± 0.46** |
| DQN (value-based) | ours (control) | 5.10 (degenerate) |
| Oracle | upper bound | 0.00 |

- The graph itself has value: structural greedy beats the threshold by 22%.
- REINFORCE beats the threshold by 39% and structural greedy by 22%. PPO beats the threshold by 30% and structural greedy by 11%.
- DQN degenerates to roughly random. The reward comes only at the end and is shared by all actions, so a value function gets no per-step credit. Under sparse delayed reward, policy gradient beats value-based methods.

**KO**
모든 수치는 **결론 오류(sink errors)**, 즉 결론에 도달한 오류의 수이다. **낮을수록 좋다.**

**첫 버전(밴딧): 숨기지 않고 보고하는 부정적 결과.**

| 전략 | 결론 오류 |
|---|:---:|
| 무검토 | 5.62 |
| 무작위 16 | 4.19 |
| **보정 임계값** | **2.81** |
| 테이블 Q-러닝 | 3.38 |
| 전체검토 (상한) | 0.56 |

어떤 구간 나누기를 택해도 보정 임계값이 Q-러닝을 이긴다. 진단: 항목별로 검토하면 의존성 그래프가 평평해지고, 한 유형이 76%이므로 최적 정책이 정적 규칙으로 무너진다.

**그래프 위 능동적 노드 선택으로 재구성한 뒤:**

| 방법 | 유형 | 결론 오류 |
|---|---|---:|
| 무검토 | 전통 | 5.90 |
| 신뢰도 임계값 | 전통 | 2.30 |
| 구조적 그리디 | 전통 (손으로 만든) | 1.80 |
| REINFORCE (MLP 점수 함수) | 우리 (예비) | 1.40 |
| PPO (MLP 점수 함수) | 우리 (예비) | 1.60 |
| **GNN + REINFORCE (고정 예산)** | **우리 (업그레이드)** | **1.54 ± 0.46** |
| DQN (가치 기반) | 우리 (대조군) | 5.10 (퇴화) |
| 오라클 (상한) | 상한 | 0.00 |

- 그래프 자체에 가치가 있다: 구조적 그리디는 임계값보다 22% 낮다.
- REINFORCE는 임계값보다 39%, 구조적 그리디보다 22% 낮다. PPO는 임계값보다 30%, 구조적 그리디보다 11% 낮다.
- DQN은 거의 무작위 수준으로 퇴화한다. 보상이 마지막에만 있고 모든 행동이 공유하므로 가치 함수가 단계별 공로를 얻지 못한다. 희소하고 지연된 보상에서는 정책 경사가 가치 기반 방법보다 낫다.

---

## 6. Related Work
**EN**
Titles, authors, and venues were checked on 2026-11-08 against arXiv abstract pages, or against search results for papers not on arXiv. We read abstracts and search summaries, not full papers. There are three strands.

**Learning to defer (when to call a human in)**
- **Mozannar and Sontag. *Consistent Estimators for Learning to Defer to an Expert.* ICML 2020; arXiv:2006.01862.** A classifier and a rejector decide whether the AI or a human predicts.
- **Zhang, Nguyen, Rosewarne, Wells, Carneiro. *Fatigue-Aware Learning to Defer via Constrained Optimisation* (FALCON). arXiv:2604.00904 (2026).** Human performance degrades with workload; a constrained MDP trained with PPO-Lagrangian. Closest to our components, but no dependency-graph propagation.
- **Joshi, Parbhoo, Doshi-Velez. *Learning-to-defer for sequential medical decision-making under uncertainty* (SLTD). arXiv:2109.06312.** Deferral as model-based RL with long-term outcomes.
- **Reid, Sühr, Vernade, Samadi. *Online Decision Deferral under Budget Constraints.* arXiv:2409.20489 (2024).** Online deferral with a budget as a contextual bandit.
- **Saketos, Reveillard, Proutiere, Dalleiger, Xiao. *To Defer or Not to Defer? Online Learning with LLMs and Congested Experts* (KL-PBD). arXiv:2610.15128 (2026).** Deferral with delayed, partially observed feedback and a capacity-limited expert.
- **Turan. *Oversight Has a Capacity: Calibrating Agent Guards to a Subjective, Fatiguing Human.* arXiv:2606.08919 (2026).** Frames "which action to review under finite human attention, with reviewer fatigue" as a resource-allocation problem. Closest to our review-scheduling framing, but it gates flat agent-action trajectories, not a dependency graph.
- **Pesenti, Bogani, Teso, Pugnana. *Too Much of the Same: From Algorithmic to Human Bias in Learning to Defer.* arXiv:2608.28050 (2026).** Deferral can be class-biased; our 76%-single-type clustering connects to this fairness concern.

**Budgeted and delayed-feedback bandits**
- **Badanidiyuru, Kleinberg, Slivkins. *Bandits with Knapsacks.* FOCS 2013; arXiv:1305.2545.**
- **Joulani, György, Szepesvári. *Online Learning under Delayed Feedback.* ICML 2013; arXiv:1306.0686.** Delay increases regret additively in stochastic problems.

**Error cascades and propagation**
- **Sambasivan et al. *"Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI.* CHI 2021.** Data problems compound downstream, often unseen until late.
- **Finkel, Manning, Ng. *Solving the Problem of Cascading Errors: Approximate Bayesian Inference for Linguistic Annotation Pipelines.* EMNLP 2006, pp. 618–626.** Errors in NLP pipelines carry from stage to stage.
- **Xie et al. *From Spark to Fire: Modeling and Mitigating Error Cascades in LLM-Based Multi-Agent Collaboration.* arXiv:2603.04474 (2026).** Multi-agent collaboration as a directed dependency graph.
- **Kou, Wang, Jia, Geng. *Inaccurate Label Distribution Learning with Dependency Noise* (DN-ILDL). arXiv:2405.16474 (2024).** Label noise that depends on instances and labels; type-level error clustering is a known concept.

**Budgeted node selection and graph encoding**
- **Feng, Yu, Xiong, Chen. *Sequential Stochastic Combinatorial Optimization Using Hierarchical RL* (WS-option). arXiv:2502.05537 (2025).** A two-layer MDP — budget allocation on top, node selection below — the same structure as our budget + node selection, in adaptive influence maximization.
- **Mattick, Mutschler. *Reinforcement Learning for Node Selection in Branch-and-Bound.* arXiv:2310.00112.** A GNN encodes the whole tree state and RL selects nodes; the recipe we follow for our GNN node scorer.

**KO**
제목, 저자, 학회는 2026-11-08에 arXiv 초록 페이지로 확인했고, arXiv에 없는 논문은 검색 결과로 확인했다. 전체 논문이 아니라 초록과 검색 요약만 읽었다. 세 갈래가 있다.

**Learning to defer (사람을 언제 부를 것인가)**
- **Mozannar and Sontag. *Consistent Estimators for Learning to Defer to an Expert.* ICML 2020; arXiv:2006.01862.** 분류기와 rejector가 AI가 예측할지 사람이 예측할지를 결정한다.
- **Zhang, Nguyen, Rosewarne, Wells, Carneiro. *Fatigue-Aware Learning to Defer via Constrained Optimisation* (FALCON). arXiv:2604.00904 (2026).** 업무량에 따라 사람의 성능이 떨어지며, PPO-Lagrangian으로 학습하는 제약 MDP. 우리 구성 요소와 가장 가깝지만 의존성 그래프 전파는 없다.
- **Joshi, Parbhoo, Doshi-Velez. *Learning-to-defer for sequential medical decision-making under uncertainty* (SLTD). arXiv:2109.06312.** 장기 결과를 고려하는 모델 기반 RL로서의 deferral.
- **Reid, Sühr, Vernade, Samadi. *Online Decision Deferral under Budget Constraints.* arXiv:2409.20489 (2024).** 예산이 있는 온라인 deferral을 contextual bandit으로 다룬다.
- **Saketos, Reveillard, Proutiere, Dalleiger, Xiao. *To Defer or Not to Defer? Online Learning with LLMs and Congested Experts* (KL-PBD). arXiv:2610.15128 (2026).** 지연되고 부분적으로 관측되는 피드백과 용량이 제한된 전문가가 있는 deferral.
- **Turan. *Oversight Has a Capacity: Calibrating Agent Guards to a Subjective, Fatiguing Human.* arXiv:2606.08919 (2026).** "유한한 인간 주의와 피로 속에서 어떤 행동을 검토할지"를 자원 할당 문제로 본다. 우리의 검토 스케줄링 프레이밍과 가장 가깝지만, 의존성 그래프가 아니라 평평한 에이전트 행동 궤적을 게이팅한다.
- **Pesenti, Bogani, Teso, Pugnana. *Too Much of the Same: From Algorithmic to Human Bias in Learning to Defer.* arXiv:2608.28050 (2026).** deferral은 클래스 편향될 수 있다. 우리의 76% 단일 유형 뭉침은 이 공정성 우려와 연결된다.

**예산 제약 및 지연 피드백 밴딧**
- **Badanidiyuru, Kleinberg, Slivkins. *Bandits with Knapsacks.* FOCS 2013; arXiv:1305.2545.**
- **Joulani, György, Szepesvári. *Online Learning under Delayed Feedback.* ICML 2013; arXiv:1306.0686.** 확률적 문제에서 지연은 regret을 가산적으로 늘린다.

**오류 연쇄와 전파**
- **Sambasivan et al. *"Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI.* CHI 2021.** 데이터 문제는 하류에서 누적되며 종종 뒤늦게야 드러난다.
- **Finkel, Manning, Ng. *Solving the Problem of Cascading Errors: Approximate Bayesian Inference for Linguistic Annotation Pipelines.* EMNLP 2006, pp. 618–626.** NLP 파이프라인의 오류가 단계에서 단계로 넘어간다.
- **Xie et al. *From Spark to Fire: Modeling and Mitigating Error Cascades in LLM-Based Multi-Agent Collaboration.* arXiv:2603.04474 (2026).** 다중 에이전트 협업을 방향성 의존성 그래프로 모델링한다.
- **Kou, Wang, Jia, Geng. *Inaccurate Label Distribution Learning with Dependency Noise* (DN-ILDL). arXiv:2405.16474 (2024).** 인스턴스와 라벨에 의존하는 라벨 노이즈. 유형 수준의 오류 뭉침은 이미 알려진 개념이다.

**예산 제약 노드 선택과 그래프 인코딩**
- **Feng, Yu, Xiong, Chen. *Sequential Stochastic Combinatorial Optimization Using Hierarchical RL* (WS-option). arXiv:2502.05537 (2025).** 상위 레이어는 예산 할당, 하위 레이어는 노드 선택을 하는 2계층 MDP — 적응형 영향 최대화에서 우리의 예산 + 노드 선택과 같은 구조.
- **Mattick, Mutschler. *Reinforcement Learning for Node Selection in Branch-and-Bound.* arXiv:2310.00112.** GNN이 전체 트리 상태를 인코딩하고 RL이 노드를 선택한다. 우리 GNN 노드 점수 함수가 따르는 레시피.

---

## 7. Differentiation and Feasibility
**EN**
**Where we stand.** Each ingredient exists in prior work: fatigue and budget with RL (FALCON), online budgeted deferral (Reid et al.), sequential deferral (SLTD), delayed feedback (KL-PBD), error clustering by type, and error propagation along a dependency graph. The closest prior work is *Oversight Has a Capacity* (which gates flat agent-action trajectories under finite human attention) and *WS-option* (a budget + node-selection two-layer MDP, in influence maximization). Our contribution is the specific combination they do not have: **error propagation on a dependency graph + a human review budget + learning which node to review**, trained as an MDP with sparse delayed reward. Learning to defer mostly decides item by item (a bandit); we choose nodes on a graph.

**What our experiments add.** A negative result that we explain (the bandit version loses to a threshold because the graph is flattened), a reframing that fixes it, a method comparison (policy gradient beats value-based under sparse delayed reward), and controls showing the gain comes from structure.

**Limits, stated plainly.**
- The main experiments are synthetic, on a small graph (about 80 nodes).
- The preliminary results (Section 5) use an MLP node scorer; the GNN scorer of Section 3 is what we build next.
- The real data has only 75 rows, so it motivates the problem and is not the core evidence.
- "No direct precedent" means we did not find one for the exact combination, not that none exists.

**Feasibility.** The simulator, the baselines, REINFORCE, PPO, and DQN already run, and the preliminary results above come from them. Remaining work is building the CMDP + PPO-Lagrangian + GNN method of Section 3, reproducing the numbers cleanly, the controls and learning curves, and the slides. Next: larger graphs and real annotation data.

**KO**
**우리의 위치.** 각 구성 요소는 선행 연구에 이미 있다. 피로도와 예산을 쓰는 RL(FALCON), 예산이 있는 온라인 deferral(Reid et al.), 순차 deferral(SLTD), 지연 피드백(KL-PBD), 유형별 오류 뭉침, 의존성 그래프를 따른 오류 전파. 가장 가까운 선행 연구는 *Oversight Has a Capacity*(유한한 인간 주의 아래 평평한 에이전트 행동 궤적을 게이팅)와 *WS-option*(영향 최대화에서 예산 + 노드 선택 2계층 MDP)이다. 우리의 기여는 이들이 갖지 않은 특정 조합, 즉 **의존성 그래프 위 오류 전파 + 사람 검토 예산 + 어떤 노드를 검토할지 학습**을 희소하고 지연된 보상을 가진 MDP로 훈련하는 것이다. Learning to defer는 대부분 항목별로 결정하지만(밴딧), 우리는 그래프의 노드를 고른다.

**우리 실험이 더하는 것.** 설명 가능한 부정적 결과(그래프가 평평해져서 밴딧 버전이 임계값에 진다), 이를 고친 재구성, 방법 비교(희소하고 지연된 보상에서 정책 경사가 가치 기반을 이긴다), 그리고 이득이 구조에서 나온다는 것을 보이는 대조 실험.

**한계, 솔직하게.**
- 주요 실험은 작은 그래프(약 80개 노드)의 합성 데이터이다.
- 예비 결과(5절)는 MLP 노드 점수 함수를 쓴다. 3절의 GNN 점수 함수가 우리가 다음에 만드는 것이다.
- 실제 데이터는 75행뿐이므로 문제의 동기를 보일 뿐 핵심 증거가 아니다.
- "직접적인 선행 연구 없음"은 정확한 조합을 찾지 못했다는 뜻이지 존재하지 않는다는 뜻이 아니다.

**실현 가능성.** 시뮬레이터, 베이스라인, REINFORCE, PPO, DQN이 이미 돌아가며 위 예비 결과는 거기서 나왔다. 남은 일은 3절의 CMDP + PPO-Lagrangian + GNN 방법 구축, 수치의 깔끔한 재현, 대조 실험과 학습 곡선, 슬라이드이다. 다음: 더 큰 그래프와 실제 라벨링 데이터.

---

## 8. Verification Status
**EN**
The experiment code and results in this document were produced by an AI agent. We are not sure they are correct, so the items below must be checked and deepened by team members later, before anything is presented as established.

**Checked when writing this document**
- Titles, authors, and venues of the cited papers, against arXiv abstract pages or search results (abstracts and search summaries only, not full papers).
- The percentages in Section 5 (39%, 30%, 22%, 11%) against the sink-error numbers listed there.

**Not verified: team members need to check and deepen**
1. **All simulation results** (every sink-error number, the learning curves, and the shuffle-errors and flatten-graph controls). We did not re-run the code or reproduce them. Owners: whoever runs REINFORCE, PPO, DQN, and the controls.
2. **The real data — now verified (2026-11-09).** We opened both files and recomputed. The full dataset is 13,990 rows (`deidentified_intervalvars_forCD_111325.rds`), and 75 rows were manually corrected (`manual_error_correction_updated.csv`). `order_error` is 57 of 75 = 76% — not 85.1%; the earlier "85%" came from 57/67, where 67 is the number of rows with a non-empty `error_type` (8 rows are unlabeled). Entropy 0.612 and p < 0.0001 are unchanged. Use 76% (of 75) as the headline; mention "85% of labeled rows" only if needed.
3. **The simulator design.** We did not inspect how the synthetic graph (about 80 nodes) is built, how errors cluster and propagate, how structural greedy is defined, or which hyperparameters were used. Check that the simulator does not build the advantage in, and that the "no review" baseline differs between experiments (5.62 vs 5.90) for a stated reason.
4. **"No direct precedent" for the combination.** This rests on our literature notes, not on an exhaustive search. Teammates should search again before claiming it in the talk, and phrase it as "we did not find one".
5. **What the papers actually say.** We read abstracts and search summaries only. Anyone citing a paper's findings in the talk should read the relevant part of the full text.
6. **A claim we left out because we could not verify it:** that the BestReject method in the online deferral paper (arXiv:2409.20489) is the same as our calibrated-threshold baseline.
7. **A number that disagrees across our own files:** the presentation outline says RL adds "19%" over the structural greedy in one place, while the results say 22% (1.80 to 1.40). Fix whichever is wrong.
8. **The upgraded method (Section 3): GNN scorer is run, CMDP soft-budget is not.** The GNN scorer with a fixed budget: multi-seed mean 1.54 ± 0.46 (best seed 1.00, single-run 1.20 was luck). Mean does not significantly beat MLP 1.40 or greedy 1.80. The CMDP soft-budget (PPO-Lagrangian + stop action) naive version fails at 4.85 — its stop-action credit assignment is too coarse and needs a FALCON-style reward-critic + cost-critic. GNN+PPO has not converged (~5.60) and is omitted from Section 5.
9. **GNN result is unstable.** Multi-seed mean 1.54 ± 0.46 (per-seed 1.00–1.90); 2.05 at 12k episodes. Report with CI; do not claim a stable win.

**KO**
이 문서의 실험 코드와 결과는 AI 에이전트가 만들었다. 정확한지 확실하지 않으므로, 아래 항목은 무엇이든 확정된 사실로 발표하기 전에 조원들이 확인하고 심화해야 한다.

**이 문서를 쓰면서 확인한 것**
- 인용한 논문의 제목, 저자, 학회를 arXiv 초록 페이지 또는 검색 결과로 확인(전체 논문이 아니라 초록과 검색 요약만).
- 5절의 백분율(39%, 30%, 22%, 11%)을 거기 적힌 결론 오류 수치와 대조.

**검증하지 못한 것: 조원이 확인하고 심화해야 함**
1. **모든 시뮬레이션 결과**(모든 결론 오류 수치, 학습 곡선, 오류 섞기와 그래프 평평화 대조 실험). 코드를 다시 돌리거나 재현하지 않았다. 담당: REINFORCE, PPO, DQN, 대조 실험을 돌리는 조원.
2. **실제 데이터 — 이제 검증됨 (2026-11-09).** 두 파일을 열어 다시 계산했다. 전체 데이터셋은 13,990행(`deidentified_intervalvars_forCD_111325.rds`)이고, 75행이 수동 정정되었다(`manual_error_correction_updated.csv`). `order_error`는 75건 중 57건 = 76%이다 — 85.1%가 아니다. 기존 "85%"는 57/67에서 나왔는데, 67은 `error_type`이 비어 있지 않은 행의 수다(8행은 라벨 없음). 엔트로피 0.612와 p < 0.0001은 그대로다. 헤드라인은 76%(75 중)를 쓰고, 필요할 때만 "라벨 있는 행의 85%"라고 언급한다.
3. **시뮬레이터 설계.** 합성 그래프(약 80개 노드)를 어떻게 만들었는지, 오류가 어떻게 뭉치고 전파되는지, 구조적 그리디가 어떻게 정의되는지, 어떤 하이퍼파라미터를 썼는지 확인하지 않았다. 시뮬레이터가 우위를 내장하지 않았는지, 그리고 실험 사이에 "무검토" 기준이 다른 이유(5.62 대 5.90)가 설명되는지 확인한다.
4. **조합에 "직접적인 선행 연구가 없다"는 주장.** 이는 우리의 문헌 노트에 근거하며 철저한 검색의 결과가 아니다. 발표에서 주장하기 전에 다시 검색하고, "찾지 못했다"로 표현한다.
5. **논문이 실제로 말하는 내용.** 초록과 검색 요약만 읽었다. 발표에서 논문의 발견을 인용하는 사람은 전체 논문의 해당 부분을 읽어야 한다.
6. **확인할 수 없어서 뺀 주장:** 온라인 deferral 논문(arXiv:2409.20489)의 BestReject 방법이 우리의 보정 임계값 베이스라인과 같다는 주장.
7. **우리 파일끼리 맞지 않는 수치:** 발표 개요는 한 곳에서 RL이 구조적 그리디보다 "19%" 더 낫다고 하고, 결과 문서는 22%(1.80에서 1.40)라고 한다. 틀린 쪽을 고친다.
8. **업그레이드 방법(3절): GNN 점수 함수는 실행됨, CMDP 소프트 예산은 아직.** 고정 예산의 GNN 점수 함수: 다중 시드 평균 1.54 ± 0.46 (최고 시드 1.00, 단일 실행 1.20은 운). 평균은 MLP 1.40이나 그리디 1.80을 유의하게 이기지 못한다. CMDP 소프트 예산(PPO-Lagrangian + stop 행동)의 naive 버전은 4.85로 실패한다 — stop 행동의 크레딧 할당이 너무 거칠어 FALCON식 보상 critic + 비용 critic이 필요하다. GNN+PPO는 수렴하지 않아(~5.60) 5절에서 제외했다.
9. **GNN 결과는 불안정하다.** 다중 시드 평균 1.54 ± 0.46 (시드별 1.00–1.90); 12k 에피소드에서 2.05. 신뢰구간과 함께 보고하라; 안정적 승리라고 주장하지 마라.
