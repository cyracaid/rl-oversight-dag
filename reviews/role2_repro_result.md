# role2_규리 로컬 재실행 결과

- 실행: 2026-11-24 16:17, 커밋 `af53a60`, 전체(그래프 200개)
- 환경: Windows 10, Python 3.11.9, numpy 1.26.4, torch 2.12.0+cpu
- 비교 기준: 같은 그래프·같은 정책끼리 `sink_errors`(남은 결론 오류)를 한 줄씩 대조

단위 테스트(test_planning, test_sleep): **통과**

| 실험 | 비교한 줄 | 완전히 같은 줄 | 결과 파일 해시 |
|---|---:|---:|---|
| partial | 3600 | 3600 (100.0%) | 일치 |
| confirm | 4200 | 4200 (100.0%) | 일치 |
| conditions | 4200 | 4200 (100.0%) | 일치 |
| feedback | 4800 | 4800 (100.0%) | 일치 |

## partial (그래프 200개, 평균 남은 결론 오류)

| 셀 | 저장된 결과 | 재실행 | 차이 |
|---|---:|---:|---:|
| 0 / feedback | 1.140 | 1.140 | +0.000 |
| 0 / ignore | 2.820 | 2.820 | +0.000 |
| 0 / trust | 1.065 | 1.065 | +0.000 |
| 1 / feedback | 1.800 | 1.800 | +0.000 |
| 1 / ignore | 2.820 | 2.820 | +0.000 |
| 1 / trust | 1.710 | 1.710 | +0.000 |
| 2 / feedback | 2.280 | 2.280 | +0.000 |
| 2 / ignore | 2.820 | 2.820 | +0.000 |
| 2 / trust | 2.180 | 2.180 | +0.000 |
| 3 / feedback | 2.500 | 2.500 | +0.000 |
| 3 / ignore | 2.820 | 2.820 | +0.000 |
| 3 / trust | 2.675 | 2.675 | +0.000 |
| 4 / feedback | 2.810 | 2.810 | +0.000 |
| 4 / ignore | 2.820 | 2.820 | +0.000 |
| 4 / trust | 3.220 | 3.220 | +0.000 |
| 5 / feedback | 2.995 | 2.995 | +0.000 |
| 5 / ignore | 2.820 | 2.820 | +0.000 |
| 5 / trust | 3.760 | 3.760 | +0.000 |

## confirm (그래프 200개, 평균 남은 결론 오류)

| 셀 | 저장된 결과 | 재실행 | 차이 |
|---|---:|---:|---:|
| matched / adaptive_marginal | 0.885 | 0.885 | +0.000 |
| matched / confidence | 1.275 | 1.275 | +0.000 |
| matched / gnn | 1.262 | 1.262 | +0.000 |
| matched / marginal | 0.885 | 0.885 | +0.000 |
| matched / type_prior | 3.735 | 3.735 | +0.000 |
| noise_known / adaptive_marginal | 2.765 | 2.765 | +0.000 |
| noise_known / confidence | 5.120 | 5.120 | +0.000 |
| noise_known / gnn | 4.032 | 4.032 | +0.000 |
| noise_known / marginal | 2.750 | 2.750 | +0.000 |
| noise_known / type_prior | 3.735 | 3.735 | +0.000 |
| noise_unrecognized / adaptive_marginal | 2.765 | 2.765 | +0.000 |
| noise_unrecognized / confidence | 5.120 | 5.120 | +0.000 |
| noise_unrecognized / gnn | 4.700 | 4.700 | +0.000 |
| noise_unrecognized / marginal | 4.185 | 4.185 | +0.000 |
| noise_unrecognized / type_prior | 3.735 | 3.735 | +0.000 |

## conditions (그래프 200개, 평균 남은 결론 오류)

| 셀 | 저장된 결과 | 재실행 | 차이 |
|---|---:|---:|---:|
| matched / adaptive_marginal | 1.130 | 1.130 | +0.000 |
| matched / confidence | 1.545 | 1.545 | +0.000 |
| matched / gnn | 1.485 | 1.485 | +0.000 |
| matched / marginal | 1.130 | 1.130 | +0.000 |
| matched / type_prior | 4.065 | 4.065 | +0.000 |
| noise_known / adaptive_marginal | 3.150 | 3.150 | +0.000 |
| noise_known / confidence | 5.260 | 5.260 | +0.000 |
| noise_known / gnn | 4.192 | 4.192 | +0.000 |
| noise_known / marginal | 3.150 | 3.150 | +0.000 |
| noise_known / type_prior | 4.065 | 4.065 | +0.000 |
| noise_unrecognized / adaptive_marginal | 3.150 | 3.150 | +0.000 |
| noise_unrecognized / confidence | 5.260 | 5.260 | +0.000 |
| noise_unrecognized / gnn | 4.857 | 4.857 | +0.000 |
| noise_unrecognized / marginal | 4.415 | 4.415 | +0.000 |
| noise_unrecognized / type_prior | 4.065 | 4.065 | +0.000 |

## feedback (그래프 200개, 평균 남은 결론 오류)

| 셀 | 저장된 결과 | 재실행 | 차이 |
|---|---:|---:|---:|
| matched / gnn / feedback | 1.228 | 1.228 | +0.000 |
| matched / gnn / fixed | 1.227 | 1.227 | +0.000 |
| matched / marginal / feedback | 1.005 | 1.005 | +0.000 |
| matched / marginal / fixed | 0.995 | 0.995 | +0.000 |
| shuffled / gnn / feedback | 3.853 | 3.853 | +0.000 |
| shuffled / gnn / fixed | 4.083 | 4.083 | +0.000 |
| shuffled / marginal / feedback | 3.075 | 3.075 | +0.000 |
| shuffled / marginal / fixed | 3.820 | 3.820 | +0.000 |
| uniform / gnn / feedback | 3.928 | 3.928 | +0.000 |
| uniform / gnn / fixed | 3.920 | 3.920 | +0.000 |
| uniform / marginal / feedback | 2.855 | 2.855 | +0.000 |
| uniform / marginal / fixed | 2.835 | 2.835 | +0.000 |

## 실행 기록

- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 -m unittest -v test_planning test_sleep` → exit 0, 3초
- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\evaluate_partial.py --out C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\runs\review-partial-20261124-161345 --graphs 200 --workers 4 --start 95000` → exit 0, 33초
- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\evaluate_conditions.py --out C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\runs\review-confirm-20261124-161345 --graphs 200 --confirm` → exit 0, 45초
- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\evaluate_conditions.py --out C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\runs\review-conditions-20261124-161345 --graphs 200 --start 91000` → exit 0, 63초
- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\evaluate_feedback.py --out C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\runs\review-feedback-20261124-161345 --graphs 200 --start 92000` → exit 0, 102초
