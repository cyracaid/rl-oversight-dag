# role2_규리 로컬 재실행 결과

- 실행: 2026-11-25 13:17, 커밋 `e4f2f5a`, 전체
- 환경: Windows 10, Python 3.11.9, numpy 1.26.4, torch 2.12.0+cpu
- 비교 기준: 같은 그래프·같은 정책끼리 `sink_errors`(남은 결론 오류)를 한 줄씩 대조

| 실험 | 비교한 줄 | 완전히 같은 줄 | 결과 파일 해시 |
|---|---:|---:|---|
| scope_within | 6300 | 6300 (100.0%) | 일치 |

## scope_within (그래프 100개, 평균 남은 결론 오류)

| 셀 | 저장된 결과 | 재실행 | 차이 |
|---|---:|---:|---:|
| clean / scope | 1.180 | 1.180 | +0.000 |
| clean / shrink | 1.230 | 1.230 | +0.000 |
| clean / trust | 1.200 | 1.200 | +0.000 |
| within / scope | 1.669 | 1.669 | +0.000 |
| within / shrink | 1.690 | 1.690 | +0.000 |
| within / trust | 1.718 | 1.718 | +0.000 |

## 실행 기록

- `C:\Users\한광희\AppData\Local\Programs\Python\Python311\python.exe -X utf8 C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\evaluate_scope_within.py --out C:\Users\한광희\Downloads\rl-oversight-dag\role2_규리\runs\review-scope_within-20261125-131648 --workers 4` → exit 0, 53초
