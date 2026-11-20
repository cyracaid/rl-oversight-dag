# 6조 v3_4_2 대본 최종 피드백

한국어 발표자 노트 · 영어 대본 대조 | 2026-11-16

전체 흐름과 기존 실험 수치는 유지해도 됩니다. 아래는 동결된 수업 발표 버전만 검토한 내용이며, 이후 실험을 추가할 필요는 없습니다. 영어 번역에서 의미가 달라진 부분과 한국어 원문에도 있는 기술적 표현을 구분했습니다.

이 문서는 수정 요청서입니다. 원본 PPT와 영어 TXT를 직접 수정한 파일은 아닙니다. 아래 ‘먼저 볼 수정 목록’에서 위치를 확인한 뒤, 대본 수정은 1–2번의 교체 문장을, PPT 수정은 5번의 교체 문장을 사용해 주세요. PPT와 대본의 수정 위치가 다를 수 있으므로 따로 표시했습니다.

## 먼저 볼 수정 목록

필수 — 4쪽: PPT의 요약 두 줄과 영어 대본을 수정합니다. ‘같은 200개 기록’이 아니라 ‘같은 200건의 검토 예산’이며, 68건은 사람이 확인한 오류입니다.

필수 — 7쪽: 영어 대본만 수정합니다. ‘가장 오류 확률이 높은 노드’를 먼저 본다는 문장을 ‘오류 확률과 하류 영향을 함께 고려한다’로 바꿉니다. PPT 그림과 목적 문구는 유지합니다.

필수 — 8쪽: PPT의 Transition 칸과 두 언어 대본을 수정합니다. 오류가 발견된 경우 해당 노드 자체의 오류를 고치는 것이며, 숨은 상태는 근사 belief로 표현합니다.

필수 — 12쪽: 두 언어 대본의 ‘모든 학습 정책’ 문장을 수정합니다. 이 문장은 PPT 표에는 없으므로 표를 고칠 필요는 없습니다. 표의 수치는 그대로 두고, PPT 하단의 결과 출처 문구만 명확하게 바꿉니다.

권장 — 3·6·9·10쪽: PPT와 대본에서 단정적인 표현을 완화합니다. 정확한 PPT 교체 문장은 5번에 있습니다.

유지 — 1·2·5·11쪽, 7쪽 PPT, 12쪽 숫자 표, 13쪽 한국어 PPT는 그대로 사용해도 됩니다. 13쪽은 영어 용어 설명만 간단히 다듬으면 됩니다.

발표 시간 — 5분 제한이면 별도 분량 조정이 필요합니다. 현재 영어 본문은 약 995단어로, 분당 130단어 기준 약 7분 40초입니다.

## 1. 우선 수정할 부분

### 4쪽 | 같은 200개 기록이 아니라 같은 검토 예산

한국어 원문: “같은 200건을 검토해도 파일 순서대로 보면 13%, 시각 순서 규칙에 걸린 기록부터 보면 84%의 오류를 찾습니다.”

영어 원문: “Even when reviewing the same 200 records, going in file order finds 13% of the errors, while starting with records that violate the time-order rule finds 84%.”

이유: 정렬 방식에 따라 먼저 보는 200건은 달라질 수 있습니다. 같은 것은 기록의 집합이 아니라 검토 건수입니다. 13%와 84%의 분모는 대기열에서 사람이 확인한 오류 68건입니다. 한국어의 “규칙에 걸린 기록”은 올바른 표현이며, 그 부분은 바꿀 필요가 없습니다.

한국어 수정안: “같은 200건의 검토 예산으로, 파일 순서대로 보면 사람이 확인한 오류 68건의 약 13%를, 시각 순서 규칙에 걸린 기록부터 보면 약 84%를 찾습니다.”

영어 수정안: “With the same budget of 200 reviews, file order finds about 13% of the 68 human-confirmed errors, while prioritizing records flagged by the time-order rule finds about 84%.”

앞 문장의 “실제 오류는 68건 / 68 were actual errors”도 “사람이 확인한 오류는 68건 / 68 were human-confirmed errors”로 바꾸면 정확합니다. 수치 자체는 유지합니다.

### 7쪽 | 영어 번역에서 선택 기준이 지나치게 좁아짐

한국어 원문: “오류가 있을 것으로 추정되는 곳을 골라 먼저 보고”

영어 원문: “we have to pick the node most likely to contain an error and review it first”

이유: 한국어에는 ‘오류 확률이 가장 높은 노드’라는 최상급 조건이 없습니다. 영어는 이를 추가했습니다. 목표는 결론 오류의 감소이므로 오류 확률과 하류 영향을 함께 고려해야 합니다.

한국어 수정안: “오류 확률과 하류 영향을 함께 고려해 검토 효과가 클 것으로 예상되는 노드를 고르고, 검토 결과에 따라 다음 노드를 정합니다.”

영어 수정안: “We select a node based on its estimated review benefit, considering both error probability and downstream impact, and use the review outcome to choose the next node.”

### 8쪽 | 숨은 상태와 수정 조건 명확화

한국어 원문: “이렇게 검토 결과를 보고 다음을 정하는 과정을 MDP로 정의했습니다.” / “검토한 노드의 오류가 고쳐지고 하류가 다시 계산되는 과정입니다.”

영어 원문: “We formulated this process … as an MDP.” / “the error in the reviewed node is fixed and everything downstream is recomputed.”

이유: 실제 오류는 숨겨져 있어 부분 관측 문제이며, 사용한 belief는 근사 표현입니다. 또한 검토가 항상 오류를 찾아내는 것은 아닙니다. 발견된 경우 해당 노드 자체의 기초 오류를 수정하며, 상류에서 전달된 오류는 남을 수 있습니다. 두 언어 모두 보완하면 좋겠습니다.

한국어 수정안 — 첫 문장: “실제 오류는 직접 관측할 수 없으므로, 근사 belief 표현을 사용해 부분 관측 문제에 MDP 방식으로 접근합니다.”

English — opening: “Errors are hidden, so we use an approximate belief representation to approach this partially observable problem as an MDP.”

한국어 수정안 — Transition: “오류가 발견되면 해당 노드 자체의 기초 오류를 수정하고 하류를 다시 계산합니다. 상류에서 전달된 오류는 남아 있을 수 있습니다.”

English — Transition: “If an error is detected, the node’s own base error is corrected and downstream states are recomputed; inherited errors may remain.”

마지막의 “검토 순서 전체를 학습해야 하는 / we must learn the entire review order”도 “검토 결과에 따라 다음 선택을 정하는 순차 결정 문제 / a sequential decision problem in which each review outcome informs the next choice”로 바꾸는 편이 정확합니다. 순차 결정이라는 사실만으로 RL이 필요하다고 결론 내릴 수는 없습니다. PPT의 Transition 설명도 함께 맞춰 주세요.

### 12쪽 | ‘모든 학습 정책’이라는 범위 수정

한국어 원문: “7개 조건 모두에서 학습 정책이 belief greedy보다 오류가 높았음.”

영어 원문: “Across all 7 conditions … the learned policies had higher error than belief greedy.”

이유: BC까지 포함하면 지나치게 넓은 결론입니다. BC는 한 조건에서 평균이 약간 낮았지만, 비교에서 우위가 확인되지는 않았습니다. 원래부터 학습한 REINFORCE와 BC+미세조정으로 범위를 명시해야 합니다.

한국어 수정안: “7개 조건 모두에서, 처음부터 학습한 REINFORCE와 BC+미세조정 정책은 belief greedy보다 평균 오류가 높았습니다. BC는 한 조건에서 평균이 약간 낮았지만 우위가 확인되지는 않았습니다.”

영어 수정안: “Across all seven conditions, REINFORCE trained from scratch and BC plus fine-tuning had higher mean error than belief greedy. BC had a slightly lower mean in one condition, but the comparison did not establish an advantage.”

1.020, 1.100, 1.517–1.709, 1.201, 1.525는 기존 동결 실험 기록과 일치하므로 바꾸지 않아도 됩니다.

## 2. 권장 수정 — 결론이 과도하게 들리지 않도록

### 3쪽 | 오류 전파의 가능성

한국어 원문: “연구 결론까지 함께 틀어집니다.” / “최종 결론까지 그대로 전달됩니다.”

영어 원문: “the research conclusion ends up wrong as well” / “it is carried all the way to the final conclusion.”

오류가 최종 결론을 반드시 바꾸는 것은 아닙니다. 두 언어에서 가능성 표현으로 바꾸는 것이 좋습니다.

한국어 수정안: “잘못 기록된 입력값은 파생값과 지표에 영향을 주고, 최종 결론까지 오류가 전파될 수 있습니다.”

영어 수정안: “A wrongly recorded input can affect derived values and metrics, and the error may propagate to the final conclusion.”

### 6쪽 | 문헌 비교의 ‘독립’ 단정 완화

한국어 원문: “Oversight는 검토 순서를 정하지만 검토 대상들이 서로 독립입니다.”

영어 원문: “Oversight decides the review order, but treats the items being reviewed as independent of each other.”

‘의존 그래프 오류 전파를 명시적으로 모델링하지 않음’과 ‘대상들이 독립임’은 다른 주장입니다. 이번 검토에서는 원 논문 전체를 다시 확인하지 않았으므로, 아래처럼 범위를 한정하는 표현을 권합니다.

한국어 수정안: “Oversight는 제한된 검토 용량의 배분을 다루지만, 본 연구와 같은 의존 그래프상의 오류 전파는 명시적으로 모델링하지 않습니다.”

영어 수정안: “Oversight addresses limited review capacity, but does not explicitly model error propagation through a dependency graph of this kind.”

### 9쪽 | 계획과 완료된 실험 구분

한국어 원문: “학습 정책은 REINFORCE, PPO, DQN이며”

영어 원문: “The learned policies are REINFORCE, PPO, and DQN”

제안서의 비교 설계로는 유지할 수 있습니다. 다만 세 알고리즘의 실험이 모두 완료된 것으로 들리지 않도록 다음 문장을 권합니다.

한국어 수정안: “학습 정책 비교 대상으로 REINFORCE, PPO, DQN을 계획하고 있습니다. 부록에는 현재 완료된 REINFORCE와 모방학습 사전 실험을 제시했습니다.”

영어 수정안: “Our planned comparison includes REINFORCE, PPO, and DQN. The appendix reports the completed REINFORCE and imitation-learning preliminary experiments.”

수면 연구 파이프라인의 실제 구조를 이용한 평가도 실제 운영 환경에서의 효과 검증과는 구분해 주세요. “실제 구조에서도 확인합니다 / on the actual structure”는 “수면 연구 파이프라인 구조를 활용한 보완 평가도 계획합니다 / We also plan complementary evaluation using the sleep research pipeline structure”로 쓰면 완료 범위에 대한 오해를 줄일 수 있습니다.

### 10쪽 | 규칙이 충분하다고 단정하지 않기

한국어 원문: “왜 규칙으로 충분한지를 설명합니다.”

영어 원문: “we will explain why the rules are enough.”

학습 정책이 이기지 못했다는 결과만으로 규칙이 충분하거나 최적이라고 증명되지는 않습니다.

한국어 수정안: “현재 실험 조건에서 규칙이 더 효과적인 이유와 학습의 한계를 분석합니다.”

영어 수정안: “We will analyze why rules perform better under the tested conditions and what limits learning.”

### 12–13쪽 | 부록 표현 정리

12쪽 원문: “AI 에이전트로 실행한 결과 / These results were produced with an AI agent.”

권장: “실험 코드를 실행해 얻은 결과이며, 독립 재현과 별도 확인 세트 평가는 아직 수행하지 않았습니다.” / “These results were obtained by executing the experiment code. Independent reproduction and evaluation on the reserved confirmation set remain pending.” 코드 실행 결과임을 분명히 하면 됩니다.

13쪽 한국어: “그래프의 하류 끝 노드”는 유지할 수 있습니다. 영어의 “the most downstream node”는 유일한 노드처럼 들립니다.

영어 수정안: “A terminal, or sink, node representing a final output or conclusion. A graph may have several such nodes.”

## 3. 수정 우선순위가 낮은 부분

1–2쪽과 11쪽: 내용상 수정할 문제는 없습니다. 인사, 목차, 마무리는 유지해도 됩니다.

4쪽: 13%와 84%는 13.2%와 83.8%를 반올림한 값으로, 발표에서는 그대로 사용해도 됩니다. 68건과 75건이 다른 집합이라는 13쪽 설명도 맞습니다.

5쪽: “저희가 조사한 범위에서는 / within the scope of our survey”라는 제한이 있어 유지해도 됩니다.

7쪽: 그림에서 숨은 오류를 모두 찾은 ‘경우’라는 설명은 이미 예시로 표현되어 있습니다. 별도로 길게 해명할 필요는 없습니다.

13쪽: belief와 REINFORCE의 기존 정의는 수업 발표용 간단한 설명으로 사용할 수 있습니다. 엄밀한 정의를 길게 추가하는 것보다 필수 수정 항목을 먼저 반영하는 편이 좋습니다.

## 4. 발표 시간 — 5분 제한이면 별도 조정 필요

현재 영어 본문 1–11쪽은 약 995단어입니다. 분당 130단어 기준 약 7분 40초이며, 화면 전환과 멈춤은 포함하지 않은 시간입니다. 5분 제한이라면 문장 수정과 별도로 분량을 줄여야 합니다. 대략 550–600단어를 출발점으로 삼고 실제로 시간을 재며 조정하는 것을 권합니다. 부록 12–13쪽은 읽지 않습니다.

우선 필수 수정 4개 항목과 발표 시간부터 확인하고, 나머지는 가능하면 반영해 주세요. 기존 슬라이드 구성과 동결 실험 수치를 교체할 필요는 없습니다.

## 5. PPT 편집자용 — 화면에서 실제로 바꿀 문장

아래 ‘현재’는 PPT 화면의 문구입니다. 같은 페이지의 발표자 노트와 영어 대본은 앞의 수정안에 맞춰 주세요. 표·도형·그래프를 새로 만들 필요는 없으며, 해당 텍스트 상자나 표의 셀만 바꾸면 됩니다.

### 4쪽 — 필수 | 상단 요약 두 줄

현재 ①: “수면 연구 데이터에서 자동 플래그 1,048건 중 실제 오류는 68건(6.5%), 그마저 한 유형에 몰려 있음”

교체 ①: “자동 플래그 1,048건 중 사람이 확인한 오류는 68건(6.5%)”

현재 ②: “같은 200건을 검토해도 순서에 따라 찾는 오류가 13%에서 84%까지 달라짐”

교체 ②: “동일한 200건의 검토 예산에서도, 확인된 오류의 발견 비율이 순서에 따라 13%에서 84%로 달라짐”

이유: 68건의 오류와 75건의 수정 기록은 다른 집합입니다. 두 집합을 하나처럼 설명하지 않고, 동일한 예산으로 비교했다는 점을 분명히 합니다.

유지: 그래프 값, 13%·84%, 오른쪽 ‘사람이 수정한 기록 75건의 유형’, 출처는 그대로 둡니다. 왼쪽 제목은 가능하면 “검토 순서별 확인된 오류 발견 비율”로 바꿔 주세요.

### 8쪽 — 필수 | 표의 Transition 칸과 보충 문구

현재 Transition: “검토한 노드의 오류를 고치고 하류를 다시 계산”

교체: “오류 발견 시 해당 노드 자체의 기초 오류 수정 및 하류 재계산”

표 아래에 짧게 추가: “※ 숨은 오류는 근사 belief로 표현하며, 상류에서 전달된 오류는 남아 있을 수 있음”

이유: 검토가 항상 오류를 발견하는 것은 아닙니다. 또한 해당 노드를 고쳐도 미수정 상류 오류의 영향은 남을 수 있습니다. State와 Reward의 기존 목록은 유지해도 됩니다.

### 12쪽 — 필수 | 하단 출처 문구, 숫자 표는 유지

현재: “※ AI 에이전트로 생성한 결과이며 팀의 독립 확인 전”

교체: “※ 실험 코드 실행 결과. 팀의 독립 재현 및 별도 확인 세트 평가 전”

이유: AI가 숫자를 생성한 것이 아니라 코드를 실행해 얻은 실험 결과임을 분명히 합니다.

가능하면 상단의 “개발용 그래프 200개 · 시드 5개 기준”도 “개발용 그래프 200개 · 학습 정책별 훈련 시드 5개”로 바꿉니다. 다섯 훈련 시드는 학습 정책에 해당합니다.

중요: ‘7개 조건 모두에서 학습 정책이 더 나쁨’은 발표자 노트와 영어 대본에 있는 문장입니다. PPT 화면의 숫자 표에는 없으므로, 표에 새로 추가하지 말고 대본만 1번의 수정안으로 교체해 주세요. 모든 실험 수치는 그대로 유지합니다.

### 3쪽 — 권장 | 상단 화살표 뒤 문장

현재: “앞에서 생긴 오류 하나가 검토되지 않으면 최종 결론까지 전달됨”

교체: “앞 단계에서 생긴 오류가 검토되지 않으면 최종 결론까지 전파될 수 있음”

이유: 전파 가능성을 설명하는 것이므로, 최종 결론이 반드시 틀린다고 단정하지 않습니다. 파이프라인 그림은 유지합니다.

### 6쪽 — 권장 | 상단 요약과 비교표

현재 상단: “기존 연구는 검토 대상을 서로 독립으로 보거나, 오류 추정 없이 대상을 선택함”

교체: “기존 연구는 예산 내 검토 배분, 그래프 노드 선택, 오류 누적을 각각 다룸”

FALCON의 ‘우리와 다른 점’ 칸 교체: “본 연구와 같은 의존 그래프 오류 전파는 명시적으로 다루지 않음”

Oversight의 ‘우리와 다른 점’ 칸 교체: “본 연구와 같은 의존 그래프 오류 전파는 명시적으로 다루지 않음”

WS-option의 ‘우리와 다른 점’ 칸 교체: “본 연구의 숨은 오류 추정·사람 검토와는 다른 과제”

이유: ‘독립이다’, ‘오류 전파가 없다’처럼 범위가 큰 단정보다, 이번 연구에서 다루는 구체적인 과제와의 차이를 설명하는 편이 안전합니다. 이번 피드백은 원 논문 전체를 재검증한 문헌 감사가 아니라 표현의 범위를 한정하는 제안입니다. 표의 ‘다루는 것’ 칸과 아래 연구 목적 문장은 유지해도 됩니다.

### 9쪽 — 권장 | 알고리즘 목록 위 제목과 하단 주석

REINFORCE·PPO·DQN 목록 위에 추가: “학습 정책 비교 계획”

현재 하단: “※ 학습 정책은 모두 GNN 점수 함수로 노드를 평가”

교체: “※ 계획한 학습 정책은 GNN 기반 노드 평가 사용. 부록은 완료된 사전 실험 결과”

‘수면 파이프라인 구조’는 “수면 파이프라인 구조 (보완 평가 계획)”로 바꿉니다.

이유: 제안한 비교 전체와 이미 완료된 부록 실험을 구분합니다. 알고리즘 이름, 비교 도식, 기존 실험 설정 숫자는 유지합니다.

### 10쪽 — 권장 | 상단 설명과 결과 시나리오 두 상자

현재 상단: “비교 결과는 학습이 유리한 경우와 규칙으로 충분한 경우로 나뉨”

교체: “비교 결과에서 학습과 규칙이 각각 유리한 조건을 분석”

현재 왼쪽: “학습 ≥ 규칙” / “학습이 유리한 조건 정리”

교체 왼쪽: “학습이 더 효과적인 경우” / “학습이 유리한 조건 정리”

현재 오른쪽: “학습 < 규칙” / “규칙으로 충분한 이유 설명”

교체 오른쪽: “규칙이 더 효과적인 경우” / “현재 조건에서 규칙이 더 효과적인 이유와 학습의 한계 분석”

이유: 성능 지표는 오류 수이므로 부등호가 오해를 줄 수 있습니다. 또한 RL이 이기지 못했다는 결과만으로 규칙이 충분하거나 최적이라고 단정할 수 없습니다. 산출물·활용 상자와 초기 구현 주석은 유지해도 됩니다.

### 나머지 페이지 — 화면 수정 불필요

1·2·5·7·11쪽: 현재 PPT 화면을 유지해도 됩니다. 특히 7쪽 문제는 영어 대본에 추가된 ‘most likely’ 표현이므로 PPT 그림을 바꿀 필요가 없습니다.

13쪽: 한국어의 “그래프의 하류 끝 노드”는 그대로 사용해도 됩니다. 영어 대본에서만 “the most downstream node”를 “a terminal, or sink, node”로 바꾸면 됩니다. belief와 REINFORCE 설명을 길게 늘릴 필요도 없습니다.

## 6. 편집 후 마지막 확인

4쪽의 68건은 ‘확인된 오류’, 75건은 별도의 ‘수정 기록’으로 표현했는지 확인합니다.

8쪽 화면과 대본 모두 ‘발견 시 수정’이라고 설명하는지 확인합니다.

9쪽 비교 계획과 12쪽 완료된 사전 실험을 구분했는지 확인합니다.

12쪽 수치 표는 유지하고, 일곱 조건에 대한 대본 문장만 정확히 좁혔는지 확인합니다.

5분 발표라면 부록을 제외한 영어 본문으로 시간을 재어 봅니다. 긴 설명을 모두 발표문에 추가하기보다, 위의 교체 문장으로 바꾸고 반복 설명을 줄이면 됩니다.
