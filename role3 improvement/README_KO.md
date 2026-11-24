# DAG 검토 환경과 강화학습 실험 — 3차 개정

3번 역할에 필요한 그래프 생성, 오류 전파, 사람 검토·수정, 학습 인터페이스, 정책 비교를 구현한 파이썬 프로젝트입니다. 이번 개정의 상세 내용과 실측 실행 결과는 변경내역.md에 있습니다.

## 실행

Python 3.10 이상에서 ZIP을 풀고 이 폴더로 이동합니다.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_demo.py --family real --policy marginal --particles 1024 --out outputs/v3/particle_demo
python reproduce.py
```

마지막 명령은 세 시드의 학습, 5개 그래프 유형의 평가, 신념 추정법 비교, 구버전 가중치 재평가, 데모, 테스트를 모두 실행합니다. CPU 사양에 따라 수 분 이상 걸립니다. 이번 결과는 outputs/v3에 있으며, outputs 바로 아래의 기존 파일은 이전 개정의 기록입니다.

동봉 가중치만 평가하는 예시는 아래와 같습니다.

```bash
python run_benchmark.py --families spike --seeds 100 --checkpoints outputs/v3/train_1/gnn_spike_observed.pt outputs/v3/train_1/dqn_spike.pt --out outputs/recheck
```

## 검토와 오류의 의미

각 노드는 작업 단계입니다. 노드 자체에서 발생한 원천 오류와 부모 단계에서 넘어온 오류를 합쳐 현재 오류 상태를 계산합니다. 간선별 전파 성공 여부는 한 에피소드 동안 고정합니다.

A의 원천 오류가 B와 C에 전달된 경우, B의 오류를 발견하면 B 자체의 원천 오류만 제거합니다. 따라서 A가 원인인 오류는 남을 수 있습니다. A를 고치면 같은 간선 전파 결과를 사용해 B와 C를 다시 계산합니다. 각 노드는 최대 한 번 검토하며, 오류가 있는 노드를 발견할 확률은 기본 0.9입니다.

| 그래프 | 노드 수 | 검토 예산 | 최종 결론 |
|---|---:|---:|---|
| Spike | 80 | 16 | 마지막 층 20개 |
| Modular / BA / ER | 500 | 50 | 자식이 없는 노드 |
| 수면 분석 구조 | 21 | 8 | 명시한 결론 4개 |
| 가상 티켓 처리 구조 (2026-11-24 추가, 합성) | 21 | 8 | 명시한 결론 4개 |

티켓 구조는 실제 티켓 자료가 아니라 고정 위상과 가정한 사전확률만 사용합니다. 같은 검토 예산 8에서 규칙 정책끼리 비교한 결과가 `outputs/ticket-v1/ticket.md`에 있고, 2026-11-24에 같은 예산으로 학습 기준선도 추가 훈련해 `outputs/v3-learned/`에 비교를 넣었습니다(GNN +0.037, DQN +0.200, 규칙 우세).

수면 구조의 결론에는 다른 결론으로 연결되는 중간 결론도 포함됩니다. 평가자는 지정한 네 노드의 오류를 합산합니다. 수면 구조는 모든 에피소드에서 같고 원천 오류·전파·검토 난수가 달라집니다.

## 팀원 연결 API

```python
from dag_role3 import generate_graph, OversightEnv
from dag_role3.policies import choose

graph = generate_graph('spike', seed=101)
env = OversightEnv.from_seed(graph, seed=201, budget=16)
obs = env.reset()
while not env.done:
    action = choose(obs, 'marginal')
    obs, reward, done, info = env.step(action)
print(env.final_audit())
```

reset은 같은 에피소드를 재생합니다. 새 에피소드는 새로운 seed로 from_seed를 호출합니다. 관측 배열은 내부 상태의 사본이며, 에피소드 표본과 DAG 구조는 외부 변경으로부터 보호합니다.

| 관측 | 내용 |
|---|---|
| features | N행, K+7열의 공개 특징 |
| mask | 현재 검토 가능한 노드. 종료 시 모두 False |
| edge_index | 2×E, 부모·자식 인덱스 |
| edge_probability | 대응 간선의 공개 전파 확률 |
| topological_order | 부모부터 계산하는 순서 |
| sink_ids | 평가할 결론 인덱스 |
| budget_left | 남은 검토 횟수 |

features의 0~K−1열은 유형 one-hot, 이후 7열은 신뢰도, 정규화된 결론 도달 수, 원천 오류 추정확률, 전파 포함 오류 추정확률, 검토 여부, 발견 여부, 잔여 예산 비율입니다. K는 유형 수로 Spike 5, 대형 그래프 10, 수면 구조 6입니다.

step은 종료 단계에만 잔여 결론 오류의 음수를 보상으로 반환합니다. 중간 info는 검토한 노드와 발견 여부만 전달합니다. final_audit는 완료 후 평가자가 호출하며 실제 오류 수와 검토 기록을 반환합니다. snapshot과 내부 변수는 평가자용 특권 정보입니다. 학습 정책에는 observation만 전달합니다.

## 정책과 신념 추정

none은 무검토, random은 무작위, confidence는 낮은 신뢰도순, hub는 자식 수가 많은 순, structural은 낮은 신뢰도와 결론 도달 수를 결합합니다. type_prior는 신뢰도를 쓰지 않고 유형별 원천 오류율만으로 정렬합니다. oracle은 숨은 원천 오류 상태를 읽어 marginal과 같은 식으로 정렬하는 평가 전용 참조값이며 배포 정책이 아닙니다.

marginal은 원천 오류 추정확률에 평균장 전파식의 결론 오류 민감도를 곱합니다. 계산할 때 원천 오류 확률로부터 전파 확률을 다시 계산하여 순방향 계산과 미분의 기준을 일치시킵니다. 공유 조상이 있는 경로의 상관관계를 생략하는 근사이며, 원천 오류 확률을 0으로 바꾸는 유한 개입의 정확한 효과와 차이가 날 수 있습니다.

기본 particles=0은 평균장 근사입니다. from_seed에 particles=1024, belief_seed=17을 지정하면 입자 필터가 켜집니다. 원천 오류와 고정 간선 동전을 표본 추출하고, 발견·미발견 결과로 가중치를 갱신합니다. 발견 시 해당 원천 오류를 제거하며 유효 표본 수가 절반 미만이면 재표집합니다.

## 기준선 확장 (2026-11-24)

type_prior와 oracle을 추가하고 같은 시험 구간(그래프 시드 90000–90099, 유형별 100개)에서 다시 평가해 `outputs/v3-baselines/`에 저장했습니다. `outputs/v3/`는 동결 상태 그대로 둡니다. spike에서 marginal 0.66, oracle 0.52, confidence 1.03, type_prior 3.76입니다. type_prior가 크게 뒤지는 것은 공개 신뢰도가 실제 정보를 담고 있다는 뜻입니다. 500노드 세 유형에서는 marginal과 oracle의 차이가 5–7개로 커집니다. 평균장 근사가 남긴 여지가 학습 정책을 더 훈련해서 얻을 수 있는 것보다 크다는 뜻이며, oracle은 숨은 값을 읽으므로 배포할 수 없습니다. 전체 과제 정의·기준선 행렬·판정 규칙은 저장소 루트의 `BENCHMARK_SPEC.md`에 있습니다.

관측을 설명하는 입자가 사라지면 초기 사전분포에서 다시 표본을 만들고 모든 과거 관측·수정을 순서대로 반영합니다. 최대 8개 표본 묶음으로 복구를 시도합니다. 실패하면 남은 회차를 평균장으로 진행합니다. particle_recoveries와 particle_fallback을 최종 감사 기록에 남깁니다. 유한 입자의 표본 다양성 감소와 근사 오차는 여전히 있습니다.

## 학습과 평가

GNN은 같은 훈련 사례에서 현재 모델의 결정적 선택이 얻은 보상을 기준으로 REINFORCE를 학습합니다. 기준 보상 계산에는 기울기를 전달하지 않습니다. DQN은 온라인망의 선택을 목표망으로 평가하며 할인율은 1입니다.

DQN의 학습용 보상은 r + Φ(next) − Φ(current)입니다. Φ는 공개 관측에 담긴 결론 오류 추정확률 합계의 음수이고, 종료 상태에서는 0입니다. 한 에피소드의 보상 합은 원래 보상 합에서 시작 상태의 Φ를 뺀 값이므로 같은 시작 상태에서 최적화 목표를 보존합니다. 평가 CSV에는 실제 잔여 오류를 기록합니다.

| 구분 | 그래프 시드 | 에피소드 시드 | 용도 |
|---|---|---|---|
| 훈련 | 훈련시드×1,000,000 + 회차 | GNN은 그래프시드+40,000, DQN은 +10,000 | 가중치 갱신 |
| 검증 | 60,000~60,029 | 그래프시드+300,000 | 최적 학습 회차 선택 |
| 시험 | 90,000~90,099 | 그래프시드+20,000 | 최종 정책 비교 |

배포 실험은 GNN 1,000회, DQN 300회를 훈련 시드 1·2·3에서 각각 수행했습니다. 100회마다 검증하고 마지막 회차도 검증합니다. 초기 모델도 후보에 포함하며 동률이면 먼저 기록된 모델을 유지합니다. 최종 시험 결과로 모델을 선택하지 않습니다. 시험 API는 시드 구간을 90,000 이상 100,000 미만으로 제한합니다. eval-seeds 인수는 검증 사례 수입니다.

벤치마크는 정책마다 같은 그래프·오류·전파·검토 난수를 공유합니다. 각 사례의 검토 순서, 오류 개수·비율, 실행 시간을 저장합니다. 요약표의 gain_vs_confidence는 신뢰도순 오류에서 해당 정책의 오류를 뺀 값입니다. 양수가 개선이며 paired_lo/hi는 사례 단위 2,000회 백분위 부트스트랩 95% 구간입니다. 표준편차, 95백분위 오류, 무오류 비율, 승·무·패도 기록합니다. 실행 시간은 시스템 부하에 영향을 받습니다.

세 훈련 시드가 같은 시험 사례를 공유합니다. 사례를 300개로 부풀리지 않고 시드별 결과를 제시합니다. 각 구간은 해당 모델에 조건부이며 훈련 시드 불확실성이나 다중비교 보정은 포함하지 않습니다.

## 결과 파일

| 경로 | 용도 |
|---|---|
| outputs/v3/benchmark_role3.csv | 사례별 정책 결과와 선택 순서 |
| outputs/v3/benchmark_summary.csv | 평균·산포·대응 구간 |
| outputs/v3/benchmark_summary.png | 정책 비교 그래프 |
| outputs/v3/train_1~3 | 모델, 학습 기록, 검증 기록 |
| outputs/v3/belief_episodes.csv | 입자 필터와 평균장 비교 원자료 |
| outputs/v3/previous_checkpoints | 구버전 가중치를 새 시험 사례에서 평가한 결과 |
| outputs/v3/manifest.json | 실행 설정과 소스·가중치 SHA-256 |
| outputs/v3/tests.txt | 자동 테스트 결과 |
| outputs/v3-baselines/ | 8개 규칙 + oracle 참조값, 6개 유형 재평가 |
| outputs/v3-learned/ | 학습 기준선 6개 유형 평가와 `learned_vs_marginal.md` |
| outputs/learned/ | 유형·시드별 학습 가중치와 훈련 로그 |

모든 오류와 신뢰도는 가상 생성했습니다. 공개 전파 확률, 오류 사전확률, 신뢰도 생성분포를 알고 있다는 모형 가정이 있습니다. 실제 LLM 시스템의 오류 탐지 성능을 입증하려면 별도의 데이터 검증이 필요합니다.

## 학습 기준선 6개 유형 확장 (2026-11-24)

기존에는 spike에서만 학습 정책을 비교했습니다. 같은 예산(GNN 1,000회, DQN 300회, 훈련 시드 3개, 검증 30개)으로 나머지 5개 유형도 훈련해 표의 비대칭을 없앴습니다. 결과는 `outputs/v3-learned/`에 있습니다. `run_learned_baselines.py`가 훈련·평가·보고를 한 번에 수행하고, `report_learned_baselines.py`가 marginal 대비 짝지은 구간을 계산합니다.

marginal 대비 차이(학습 − 규칙, 음수면 학습이 우세)는 전 유형에서 양수입니다. spike +0.403, real +0.080, ticket +0.037(구간이 0을 포함하는 동점), modular +6.257, er +8.947, ba +16.970입니다. 36개 (유형, 학습기, 시드) 조합 중 34개의 95% 구간이 0을 배제하며, 나머지 2개는 ticket의 GNN 시드로 승리가 아닌 동점입니다.

차이는 그래프가 커질수록 커집니다. 500노드에서 관측 한 건당 노드가 더 많은데도 격차가 벌어지므로 데이터 부족으로 설명되지 않습니다. 관측에 평균장 전파량이 없어 학습기가 다중 홉 도달도를 보상만으로 다시 배워야 하기 때문이며, 이는 oracle이 보여주는 규칙의 여지와 같은 양입니다. 따라서 "규칙이 학습보다 우세하다"는 결론은 이제 spike가 아니라 6개 유형 전체에서 측정된 결과입니다.

원본 프로젝트에서 전달된 참고 링크는 아래와 같습니다. 이번 개정은 첨부 코드와 변경내역을 기준으로 수행했습니다.

- https://cyracaid.github.io/rl-oversight-dag/READING.html
- https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html
- https://github.com/cyracaid/rl-oversight-dag
