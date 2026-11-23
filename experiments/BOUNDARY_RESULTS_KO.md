# RL 경계 실험 결과 — 2026-11-12

**현재 구현에서는 RL의 우위를 확인하지 못했다. 2단계 탐색은 작은 개선을 보였다.**
이는 합성 DAG 개발 세트 결과이며 실제 수면 기록이나 독립 확인 실험 결과가 아니다.

[中文详细解释](BOUNDARY_FULL_V1_INTERPRETATION.md) · [사전등록 / Preregistration](BOUNDARY_PREREG.md) · [실행 방법 / Reproduction](BOUNDARY_RUN.md)

## 설정과 주요 결과

노드 80개, 검토 예산 16회, 학습 seed 1–5, seed별 학습 20,000 episodes.
BC는 seed별 800 graphs × 4 epochs. 개발 graph seeds 1000–1199, 총 200개.
주요 지표는 최종 sink에 남은 오류 수이며 **낮을수록 좋다**.

| 정책 | 평균 오류 수 | belief greedy 대비 차이 | 95% bootstrap CI |
|---|---:|---:|---|
| 2-step greedy | **1.020** | −0.080 | [−0.160, −0.010] |
| belief greedy | 1.100 | 0 | — |
| BC | 1.201 | +0.101 | [+0.007, +0.197] |
| confidence threshold | 1.440 | +0.340 | [+0.200, +0.495] |
| REINFORCE/static | 1.517 | +0.417 | [+0.161, +0.766] |
| BC+FT | 1.525 | +0.425 | [+0.240, +0.650] |
| REINFORCE/observed | 1.709 | +0.609 | [+0.404, +0.829] |

- BC+FT − BC = **+0.324**, CI [+0.129, +0.568]. 5개 seed 모두 악화됐다.
- 모델 오지정 및 reviewer catch 감소를 포함한 7개 조건 모두에서 두 REINFORCE 정책과 BC+FT는 belief greedy보다 나빴다.
- BC의 matched 차이 상한 +0.197은 사전 지정 비열등성 한계 +0.10을 넘는다. 표현 능력이 충분하다고 단정할 수 없다.
- 2-step greedy는 평균 0.080개, greedy 잔여 오류의 약 7.3%를 줄였다. 개발 세트 결과이므로 독립 확인이 필요하다.
- 원인은 아직 식별되지 않았다. 현재 FT가 성능을 떨어뜨렸다는 결과만으로 credit assignment, 탐색 또는 optimizer 중 하나를 확정하지 않는다.

## 해석 범위

95% CI는 graph pairing을 유지하고 학습 seed와 graph를 독립 재표집한 10,000회 crossed bootstrap이다.
planner는 graph만 재표집한다. 추가 particle RNG 불확실성은 포함하지 않는다.
독립 확인 graph seeds 2000–2199는 실행하지 않았다. 여러 개발 조건 중 유리한 결과를 확인 실험처럼 제시하지 않는다.
particle이 관찰된 flag를 설명하지 못하는 사건도 기록되어 있으므로 상세 설명의 수치적 제한을 함께 읽어야 한다.

SciForge의 다음 단계는 실제 과학 주장에 대한 증거 확보 pilot이다. 강한 greedy와 고정 체크리스트,
계획 정책을 비교 기준으로 유지하고 RL은 추가 이점이 검증될 때 채택한다.
이 합성 실험은 실제 수면 필드 의미나 과학적 결론의 타당성을 검증하지 않는다.

## 원본과 재현

- [BC 및 FT 결과](../runs/boundary-full-v1/bc/results.md) · [JSON](../runs/boundary-full-v1/bc/results.json)
- [7개 조건 결과](../runs/boundary-full-v1/misspec/results.md) · [JSON](../runs/boundary-full-v1/misspec/results.json)
- [2-step 비교](../runs/boundary-full-v1/planning/results.md) · [JSON](../runs/boundary-full-v1/planning/results.json)
- [전체 합성 실행 산출물](../runs/boundary-full-v1/): 20개 checkpoint, manifest, 학습 곡선, 로그 포함.

JSON은 실행 당시 commit, 작업 트리 상태와 소스 SHA256을 보존한다. 실행 당시 소스에는 미커밋 변경이 있었으므로
당시 commit만 checkout하는 것으로 재현된다고 가정하지 말고 소스 SHA256을 확인해야 한다.
이번 게시본의 `experiments/*.py`는 저장된 소스 SHA256과 일치하며 checkpoint 해시도 모두 일치한다.
로그와 원본 JSON은 수정하지 않았다. 실제 참여자 기록과 API 자격증명은 포함하지 않는다.
