# 프로젝트 요약 · 토론용 (한영 대조)
# Project Summary · Discussion Draft (KO / EN)

> 조원 토론용. 한국어 기준, 영어 대조. 마지막에 논의할 질문 6개.
> For group discussion. Korean primary, English paired. 6 open questions at the end.

---

## 0. 한 줄 요약 / One-liner

- KO: 제한된 주의 예산 하에서, 인간이 어떤 AI 출력을 검토해야 하는지를 강화학습으로 학습해, 최종 결론에 도달하는 오류를 줄인다.
- EN: We use reinforcement learning to learn which AI outputs a human should review under a limited attention budget, so that fewer errors reach the final conclusion.

---

## 1. 포지셔닝 (솔직한 버전) / Positioning (honest)

- KO: 이것은 밴딧(bandit) 문제가 아니라, 희소한 지연 보상(sparse delayed reward)을 갖는 순차 결정 MDP이다.
- EN: This is not a bandit problem; it is a sequential-decision MDP with sparse delayed reward.

- KO: learning-to-defer와의 차이: 오류가 유형별로 군집되고 의존성 그래프를 따라 전파되므로, 우리는 어떤 노드를 검토할지를 능동적으로 선택한다.
- EN: Difference from learning-to-defer: errors cluster by type and propagate along a dependency graph, so we actively choose which node to review.

---

## 2. 내러티브 (발표의 뼈대) / Narrative arc

- KO: ① 동기: 오류가 유형별로 군집된다 (실제 데이터: order_error = 76%, p=0.0000).
- EN: ① Motivation: errors cluster by type (real data: order_error = 76%, p=0.0000).

- KO: ② 첫 버전은 솔직하게 실패: 밴딧 + 테이블 Q-러닝으로 하니, 보정된 임계값(2.81)이 Q-러닝(3.38)을 이긴다.
- EN: ② First version fails honestly: as bandit + tabular Q-learning, calibrated threshold (2.81) beats Q-learning (3.38).

- KO: ③ 진단: 의존성 그래프를 평평하게 만들면 RL이 학습할 비자명한 구조가 없다.
- EN: ③ Diagnosis: flattening the graph leaves RL nothing non-trivial to learn.

- KO: ④ 재구성 + 승리: 그래프에서 노드를 능동적으로 선택; REINFORCE(1.40)가 구조적 그리디(1.80)와 임계값(2.30)을 이긴다.
- EN: ④ Reframe + win: actively select nodes; REINFORCE (1.40) beats structural greedy (1.80) and threshold (2.30).

- KO: 장점: "실패 → 진단 → 재구성 → 승리"의 인과 사슬이 진짜 이해를 보여준다.
- EN: Selling point: the "fail → diagnose → reframe → win" chain proves real understanding.

---

## 3. 결과 요약 / Results

### 3.1 실제 데이터 (동기 슬라이드) / Real data (motivation)

- KO: 수기 정정 75행; error_type이 매우 집중됨 (한 유형 = 76%).
- EN: 75 manually-corrected rows; error_type highly concentrated (one type = 76%).

### 3.2 첫 버전: 밴딧 (부정적 결과) / First version: bandit (negative)

| 전략 Strategy | 결론 오류 sink errors |
|---|---|
| 무검토 No review | 5.62 |
| 무작위 16 Random 16 | 4.19 |
| 보정 임계값 Calibrated threshold | 2.81 |
| 테이블 Q-러닝 Tabular Q-learning | 3.38 |
| 전체검토(상한) Review-all (upper) | 0.56 |

- KO: 보정 임계값이 모든 구간화 선택에서 Q-러닝을 이긴다.
- EN: The calibrated threshold beats Q-learning across all binning choices.

### 3.3 재구성: 구조적 가치 (spike) / Reframe: structural value

| 전략 Strategy | 결론 오류 sink errors |
|---|---|
| 무검토 No review | 5.90 |
| 신뢰도 임계값 Confidence threshold | 2.30 |
| 구조적 그리디 Structural greedy | 1.80 |
| 그리디 오라클(상한) Greedy oracle (upper) | 0.00 |

- KO: 그래프 구조가 독립적 가치를 갖는다 (그래프를 쓰는 그리디가 임계값보다 22% 우수).
- EN: Graph structure has independent value (graph-aware greedy beats threshold by 22%).

### 3.4 진짜 RL: 방법 비교 (주요 결과) / Real RL: method comparison (main)

| 방법 Method | 결론 오류 sink errors |
|---|---|
| 무검토 No review | 5.90 |
| 신뢰도 임계값 Confidence threshold | 2.30 |
| 구조적 그리디 Structural greedy | 1.80 |
| REINFORCE (정책 경사 policy gradient) | **1.40** ✅ |
| PPO (정책 경사 policy gradient) | **1.60** ✅ |
| DQN (가치 기반 value-based) | 5.10 (퇴화 degenerate) |
| 오라클(상한) Oracle (upper) | 0.00 |

- KO: 정책 경사 계열이 임계값보다 39%/30%, 구조적 그리디보다 22%/11% 더 낮은 오류.
- EN: Policy-gradient methods beat threshold by 39%/30% and structural greedy by 22%/11%.

- KO: DQN은 ≈무작위로 퇴화 — 보상이 종료 시점에만 있고 모든 행동이 공유해서, 가치 함수가 단계별 공로를 못 얻는다. "희소 지연 보상에서는 정책 경사 > 가치 기반"이라는 교훈점.
- EN: DQN degenerates to ≈random: terminal-only, action-shared reward denies value methods per-step credit — a teaching point that policy gradient beats value-based under sparse delayed reward.

---

## 4. MDP 5-튜플 / MDP five-tuple

- KO: 상태 S: 그래프 지식 (노드별 type / 신뢰도 / 하류 sink 영향 / 검토 여부) + 잔여 예산.
- EN: State S: graph knowledge (per-node type / confidence / downstream sink influence / reviewed?) + remaining budget.

- KO: 행동 A: 다음에 검토할 노드 선택 (＋ 종료).
- EN: Action A: choose the next node to review (＋ stop).

- KO: 전이 P: 검토가 노드를 고치면 하류를 재계산 (전파 차단).
- EN: Transition P: review fixes the node → recompute downstream (stops propagation).

- KO: 보상 R: 희소한 종료 보상 = −(결론 오류 수).
- EN: Reward R: sparse terminal reward = −(sink errors).

- KO: 할인 γ: <1, 상류 노드를 일찍 검토하도록 유도.
- EN: Discount γ: <1, encouraging early upstream review.

---

## 5. 방법 / Methods

- KO: 보정된 유형별 임계값 → 정적 규칙 베이스라인.
- EN: Calibrated per-type threshold → static-rule baseline.

- KO: 구조적 그리디 → 손으로 만든 휴리스틱 베이스라인.
- EN: Structural greedy → hand-crafted heuristic baseline.

- KO: 밴딧 + 테이블 Q-러닝 → 첫 버전 (부정적 결과).
- EN: Bandit + tabular Q-learning → first version (negative result).

- KO: REINFORCE (정책 경사 + MLP + 베이스라인) → 주 방법.
- EN: REINFORCE (policy gradient + MLP + baseline) → main method.

- KO: PPO (클리핑 목적 + 중요도 샘플링) → 주 방법.
- EN: PPO (clipped objective + importance sampling) → main method.

- KO: DQN (가치 기반) → 대조 (희소 보상 하에서 퇴화).
- EN: DQN (value-based) → control (degenerates under sparse reward).

---

## 6. 대조 실험 (자기 충족 방지) / Controls (anti-self-fulfilling)

- KO: 오류 섞기 (유형 군집 파괴) → 학습 우위가 사라진다.
- EN: Shuffle errors (break clustering) → learning advantage disappears.

- KO: 그래프 평평화 (전파 파괴) → 학습 우위가 사라진다.
- EN: Flatten graph (break propagation) → learning advantage disappears.

- KO: 의미: 우위는 구조에서 나오며, 조작된 시뮬레이터에서 나오는 것이 아니다.
- EN: Meaning: the advantage comes from the structure, not a rigged simulator.

---

## 7. 역할 분담 (5명) / Roles (5 people)

| # | KO | EN |
|---|---|---|
| 1 | 조장 + 내러티브 통합 | PM + narrative integration |
| 2 | RL 정책 경사: REINFORCE→PPO | RL policy-gradient: REINFORCE→PPO |
| 3 | RL 가치 기반 + 환경: DQN | RL value-based + environment: DQN |
| 4 | 베이스라인 + 대조 실험 | Baselines + controls |
| 5 | 데이터 동기 + 문헌 + 발표 | Data motivation + literature + slides |

- KO: 페어: 2·3은 환경 인터페이스 공유; 4의 대조 실험이 표현을 결정; 1이 매주 동기화.
- EN: Pairs: 2 & 3 share the env interface; 4's controls determine wording; 1 syncs weekly.

- KO: 발표 언어 미정 — 영어 발표 허용 시 동채하가 발표 가능; 한국어 고정이면 동채하는 백엔드(문헌/시뮬레이션/데이터) 담당.
- EN: Presentation language TBD — if English is allowed, 동채하 can present; if Korean-only, 동채하 does backend (literature / simulation / data).

---

## 8. 일정 (4주) / Timeline (4 weeks)

| 주 Week | KO | EN |
|---|---|---|
| W1 | 환경 + 베이스라인 고정; REINFORCE 1.40 재현 | Freeze env + baselines; reproduce REINFORCE 1.40 |
| W2 | PPO + DQN 구동; 방법 비교표 | PPO + DQN running; method table |
| W3 | 대조 실험 + 학습 곡선 + 부정적 결과 절 | Controls + learning curves + negative-result section |
| W4 | 슬라이드 + 리허설 2회 이상 | Slides + ≥2 rehearsals |

---

## 9. 리스크 / Risks

- KO: PPO/DQN이 더 좋지 않음 → 이미 그렇다 (PPO 1.60은 REINFORCE보다 약간 뒤, DQN은 퇴화); 대조로 제시.
- EN: PPO/DQN not better → already the case (PPO 1.60 slightly behind REINFORCE; DQN degenerates); present as comparison.

- KO: "임계값을 그냥 쓰면 안 되나요?" → 임계값은 그래프를 못 봄; 그리디가 그래프 가치를 증명; RL이 22% 추가.
- EN: "Why not just threshold?" → threshold cannot see the graph; greedy proves graph value; RL adds 22%.

- KO: "시뮬레이터가 조작됐나요?" → 두 대조 실험이 답한다.
- EN: "Rigged simulator?" → two control experiments answer.

- KO: 실제 데이터 75행뿐 → 동기 슬라이드 한 장으로 격하.
- EN: Real data only 75 rows → downgrade to one motivation slide.

---

## 10. 논의할 질문 (조원이 정할 것) / Open questions

1. KO: DQN의 "퇴화"를 "방법 선택" 교훈점으로 발표에 공식적으로 넣을까? / EN: Formally frame DQN's degeneracy as a "method choice" teaching point?

2. KO: 실제 데이터를 동기 한 장으로 둘까, 완전 합성으로 갈까? / EN: One motivation slide for real data, or go fully synthetic?

3. KO: 5개 역할이 괜찮은가? 누가 RL, 누가 베이스라인? / EN: Are the 5 roles OK? Who does RL, who does baselines?

4. KO: 4주 일정이 마감에 맞는가? / EN: Does the 4-week timeline fit the deadline?

5. KO: 발표 언어 — 영어 허용되면 동채하가 발표 가능, 한국어 고정이면 다른 조원이 발표. 교수님께 확인 필요. / EN: Presentation language — if English is allowed, 동채하 can present; if Korean-only, another member presents. Needs confirmation with the professor.

6. KO: 현재 제목이 괜찮은가? / EN: Is the current title acceptable?

---

## 11. 파일 목록 / Files

- KO: `提案_角色分工与企划.md` (제안서 + 역할 + 일정) / EN: proposal + roles + timeline
- KO: `pre_叙事与大纲.md` (발표 개요) / EN: presentation outline
- KO: `延迟惩罚审查调度_文献调研/` (문헌 3건, 참고) / EN: 3 literature docs (reference)
- KO: `模拟器与实证/` (스크립트 5 + 결과 + 그림 2) / EN: 5 scripts + results + 2 figures
