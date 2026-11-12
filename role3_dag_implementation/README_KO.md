# 3번 담당: DAG 검토 시뮬레이터 + GNN + DQN

연세대학교 강화학습 팀 프로젝트 `rl-oversight-dag`의 **3번 역할**을 위한 독립 실행형 교육·실험 코드입니다. 기존 공개 저장소의 숫자를 베끼거나 성능을 재현했다고 주장하지 않습니다. 외부 개인 단위 수면 기록은 포함하지 않습니다.

## 1. 내가 맡은 업무

1. **DAG 생성**: spike(80개), modular(500개), BA(500개), ER(500개), 공개 수면 파이프라인 구조(21개).
2. **오류 전파**: 각 노드에서 원천 오류를 뽑고, 인접한 하위 노드로 한 번 결정된 전파 동전을 이용해 오류를 확산합니다.
3. **검토와 수정**: 사람이 선택한 노드를 확인합니다. 오류 발견 확률은 기본 90%입니다. 발견하면 *검토 노드의 원천 오류*만 지운 뒤, DAG 전체를 재계산합니다.
4. **RL 연결**: `reset()`과 `step()`을 제공하고, 학습기가 볼 수 있는 공개 특징만 `observation()`에서 반환합니다.
5. **GNN·DQN 예시**: PyTorch로 독립적인 학습 스크립트를 제공합니다. 학부 실험을 시작하기 위한 코드이며 최적 성능을 보장하지 않습니다.
6. **규모 실험**: 독립적인 그래프 시드마다 여러 정책을 **동일한 오류/전파/검토 난수**에서 비교합니다.

## 2. 설치와 실행

Python 3.10+ 권장. 프로젝트 폴더에서:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_demo.py --family real --policy structural --seed 7
python run_benchmark.py --seeds 10
python train_gnn.py --family spike --episodes 100 --variant observed --seed 1
python train_dqn.py --family spike --episodes 80 --seed 1
```

`outputs/`에 검토 과정 CSV, DAG 이미지, 시뮬레이션 비교 CSV/PNG 및 학습 기록/가중치(`.pt`)가 만들어집니다.

**주의:** 100회/80회 학습은 실행 가능성 검증용입니다. 실제 공개 명세에는 GNN의 학습을 약 20,000 에피소드, 훈련 시드 5개로 제시합니다. 이 코드로 공개 사이트의 `1.14 / 1.56` 결과를 재현한 것으로 간주하면 안 됩니다.

## 3. 핵심 원리 (예시)

```text
A(원천 오류) → B(상위 오류 전파) → C(최종 결론 오류)
```

- B를 먼저 검토해도 B의 오류가 **A에서 물려받은 것**이라면, B의 원천 오류를 제거해도 효과가 없습니다.
- A에서 오류를 발견해 고치면, 같은 전파 동전을 사용해 B/C의 오류 상태를 다시 계산합니다.
- 검토 실패 확률은 10%이며, 성공 여부는 에피소드 시작 때 노드별로 고정된 난수로 결정합니다(정책간 공정 비교).

**중요:** 이 프로젝트에서 `review(v)`는 `do(X_v=정상)`이 아닙니다. `base[v]=False`만 적용한 다음 전파를 다시 계산합니다.

## 4. 파일 설명

| 파일 | 역할 |
|---|---|
| `dag_role3/graphs.py` | DAG 생성 및 위상 정렬, 순환 검증, sink reach |
| `dag_role3/environment.py` | 고정 전파 난수, 검토, 상태, 종료 보상 |
| `dag_role3/models.py` | GNN 노드 스코어러와 DQN Q-네트워크 |
| `dag_role3/policies.py` | 무작위·신뢰도·허브·구조적 그리디 정책 |
| `run_demo.py` | 1개 그래프 검토 과정 시각화 |
| `run_benchmark.py` | spike/modular/BA/ER/real 다중 독립 시드 비교 |
| `train_gnn.py` | GNN + REINFORCE 실행 예제 |
| `train_dqn.py` | DQN replay buffer/target network 실행 예제 |
| `tests/` | 오류 의미론, 난수 재현성, DAG 유효성, 신경망 테스트 |

## 5. 팀원(2번·4번)에게 넘겨줄 API

```python
from dag_role3 import generate_graph, OversightEnv

graph = generate_graph('spike', seed=101)
env = OversightEnv.from_seed(graph, seed=201, budget=16)
obs = env.reset()
while obs['budget_left'] > 0:
    valid_nodes = obs['mask'].nonzero()[0]
    action = int(valid_nodes[0])   # 여기를 학습된 정책의 선택으로 교체
    obs, reward, done, info = env.step(action)
    if done:
        print('terminal reward:', reward)
        print('remaining sink errors:', info['sink_errors'])
```

`obs['features']`: shape `(N, K+7)` (K=오류 유형 개수)

- `0:K`: 노드 유형 one-hot
- `K`: confidence (높을수록 정상일 가능성이 높음)
- `K+1`: 정규화된 sink reach
- `K+2`: **근사** 원천 오류 확률 (신뢰도 기반 베이즈 + 간단한 검토 업데이트)
- `K+3`: **근사** 전파 포함 오류 확률 (독립 근사)
- `K+4`: 검토했는지 0/1
- `K+5`: 검토 중 오류를 발견했는지 0/1
- `K+6`: 남은 예산 비율

`obs['mask']`: 검토 가능 노드 표시; `obs['edge_index']`: `(2, E)` directed edge 배열; `obs['sink_ids']`: 최종 결론 노드 인덱스.

`step()`의 보상은 **마지막 검토에서만** `-남은 sink 오류 개수`, 중간 단계는 `0`입니다. 중간 `info`에는 실제 오류 수를 반환하지 않습니다. 에피소드 후 평가자는 `env.final_audit()`를 이용할 수 있습니다.

## 6. 정확한 범위 및 제한

- 공개 연구 명세의 `belief.py`는 **1,024개 입자의 파티클 필터**입니다. 이번 코드는 팀 합류가 쉽도록 근사 신념을 사용합니다. 따라서 여기의 GNN `observed`는 공개 구현의 파티클 필터 버전과 **동일하지 않으며 수치 비교할 수 없습니다**. 기존 팀원의 `belief.py`를 연결하면 엄격한 비교가 가능합니다.
- 500노드의 원천 오류 유형 분포, 모듈 클러스터 내 동일 유형 편향(65%)은 모형 선택입니다. 이 데이터는 실측 정보가 아닙니다.
- BA/ER 그래프를 낮은 노드 번호에서 높은 번호로 방향을 부여해 DAG로 만듭니다.
- `real`은 **수면 분석 의존성 도식만 가져온 시뮬레이션**입니다. 실제 사람 기록을 불러오지 않습니다.
- 버전 변경 가능성이 있는 공개 명세와의 값 차이가 있을 수 있습니다. 먼저 아래 원문을 확인하세요.

## 7. 출처

- 프로젝트 읽기 안내: https://cyracaid.github.io/rl-oversight-dag/READING.html
- 구현 명세(한국어): https://cyracaid.github.io/rl-oversight-dag/IMPLEMENTATION_SPEC_KO.html
- 오류 수정 의미론: https://github.com/cyracaid/rl-oversight-dag/blob/main/experiments/SEMANTICS_AUDIT.md
- 기존 공개 코드: https://github.com/cyracaid/rl-oversight-dag
