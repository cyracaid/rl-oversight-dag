# role 4 구조 대조 — P5 검증 결과와 수정 요청

검토일 2026-11-27 · 대상 `p4/role4-controls` (12 commits) · 병합: `main`에 `--no-ff`로 반영

## 1. 검증 결과

| 검증 | 범위 | 결과 |
|---|---|---|
| `reproduce.py --full --confirm` | v1 3표 + diagnostics + v2 + 확인 블록, 8개 파일 | **바이트 동일 8/8** (v2 825 s, 확인 1074 s) |
| 확인 블록 앵커 | 7100–7199, `intact` 1,500행 (오류 수 + 검토 순서) | **불일치 0** |
| 클린룸 재구현 | v1 전체 4,500행 + 요약 45칸 + 라벨 20개 + worst-of-n 36 + diagnostics | **불일치 0** |
| 병합 | `merge --no-ff`, 저장소 가드 32 + `role3 improvement` 160/27 | 통과 |

클린룸은 `run_controls.py`를 한 번도 보지 않은 세션이 `README`(v1 부분)만으로 다시 쓴 것입니다
(`reviews/role4_independent/`, 578행, 223 s). 즉 **숫자는 문서화된 규칙에서 재현됩니다.** 이건
`reproduce.py`가 보여주지 못하던 부분입니다(그것은 "같은 코드 = 같은 바이트"만 보장).

단, 세 가지는 검증 범위 밖입니다.

1. **환경**: 양쪽 모두 `dag_role3`를 import. 환경 자체의 버그는 못 잡습니다.
2. **구간(CI)**: 클린룸은 `run_benchmark.interval`을 읽지 못하게 했고, 동결 요약표에서 절차를 역산해
   모든 경계를 1e-9 이하로 맞췄습니다. 점추정은 독립, 구간은 보정, 라벨은 구간 부호를 읽습니다.
3. **v2는 클린룸 미검증**: `rewire_order`, 10 draws, 3단 판정, 20 % 마진은 role 4 코드 단독입니다.

## 2. Q1–Q5 답변 (확정)

| 질문 | 답 |
|---|---|
| Q1 재배선 방식 | 동의. 단 이 대조가 재는 것은 "정책이 틀린 지도에 얼마나 민감한가"이며 "그래프가 필수인가"가 아님을 README에 한 줄 명시. |
| Q2 부모 후보 풀 | v1(index 제한) 허용. 단 그 혼입을 본문에 적을 것 — 아래 수정 1. |
| Q3 v2 사전등록·20 % | 수용. v1 라벨 유지 → v2 동결 → 독립 확인 블록 순서가 맞음. 20 %는 "블록별 `intact` 평균 대비, 이 실험의 판정 관례"로 명시. |
| Q4 `inconclusive` | 동결 라벨 유지. 대신 CI 전체가 `−margin` 아래인 셀은 CSV에도 방향을 병기 — 수정 5. |
| Q5 시드 원장 | 확인 완료. 그래프 7100–7199 / episode 27100–27199를 `BENCHMARK_SPEC.md` §3과 세 보고서 원장에 등록했음(커밋 `605e038`). `COURSE_FINAL_REPORT.md` §9의 "Fresh: 5600 and above"는 구버전이므로 인용하지 말 것. |

## 3. PR 전 수정 요청

1. **BA/ER 문장을 관측 범위로 좁혀 주세요.** "who the hubs are"는 ER에서 성립하지 않습니다(ER에는 허브가
   없습니다). 근거: `_orient_graph`는 모든 간선을 낮은 index → 높은 index로 정렬해 방향을 정하므로
   out-degree가 index의 함수입니다. Spearman(index, out-degree)는 원본에서 ER −0.78 / BA −0.74 /
   modular −0.07이고, `rewire_index` 후 −0.78 / −0.84 / −0.73입니다. 즉 `rewire_index`는 "같은 크기의
   틀린 지도"가 아니라 **index→차수 단조 프로파일을 그대로 복사**합니다. 따라서
   - BA/ER의 `survives`는 "**차수 프로파일**이 남았다"이지 "간선이 남았다"가 아닙니다;
   - modular의 −7.19는 "이득 상실"이 아니라 **원래 없던 프로파일이 주입된 결과**입니다;
   - 동결 표에서 `hub`는 BA/ER에서 confidence보다 10.8 / 16.5개 더 나쁘므로 "차수만으로 충분"도 아닙니다.
   정확한 문장: "차수 프로파일 × 공개 confidence의 상호작용". (근거를 `results/controls.md` §2에 각주로)
2. `EXPLAINER_KO.md`의 "한 요인만 바꿨다" → "이 결과는 허브(정확히는 index에 묶인 차수 분포) 정보가
   중요하다는 **해석**과 일치합니다". 그리고 `rewire_order`는 허브 순위와 함께 경로·sink 도달성도 바꾼다는
   점을 한 줄.
3. 재현 명령에 `--full --confirm` 추가(`EXPLAINER_KO.md:6`, `QUESTIONS_FOR_P5.md:4`), 의존성은
   `numpy` + `networkx` 둘 다로.
4. `role4_controls/.gitattributes` 추가: `results/**/*.csv text eol=lf`. (Windows `core.autocrlf=true`에서
   현재 바이트 비교가 실패합니다. 내용은 같고 줄바꿈만 다릅니다.)
5. `*_summary.csv`에 `direction` 열 추가: `inconclusive`이면서 CI 전체가 `−margin` 아래면
   `worse-than-confidence`. 표에만 적지 말고 CSV에 넣어 주세요(집계 스크립트가 읽을 수 있게).
6. `rewire_index`에서 모듈 상수 `rc.REWIRE_SEED_OFFSET`를 임시로 바꾸는 대신 seed를 인자로 넘겨 주세요.
   지금은 프로세스 풀에서 우연히 동작하는 구조입니다.
7. **확인 블록에 동결 앵커가 없다는 사실을 README에 적어 주세요.** `reproduce.py` 로그가 직접
   "no frozen benchmark or v1 rows exist for it"이라고 출력합니다. 우리 쪽에서 앵커를 만들어 두었으니
   (`reviews/role4_controls_recheck.py`, 1,500행 일치), 인용하거나 직접 앵커를 추가하세요.

## 4. 선택 사항 (PR 이후)

- 그래프 5900–5999에 **전파 없는 `confidence × in-degree` 점수 기준선**을 사전등록하면 "차수 프로파일 vs
  간선"을 분리할 수 있습니다. 이것이 BA/ER의 잔여 이득을 가져가면 "차수" 쪽으로 결론이 굳습니다.
  7100은 이미 소진입니다.
- v2(`rewire_order`, 10 draws, 3단 판정)도 클린룸 재구현 대상으로 남겨 두면 좋겠습니다. 현재 유일하게
  단일 구현에만 의존하는 표입니다.

---

## 5. 후기 — `acbd729` 병합, 남은 2건은 `main`에서 처리

`acbd729`("apply P5 review")를 `main`에 병합했습니다(`9379db7`). 문서 범위 조정, `--full --confirm`,
`.gitattributes`, 확인 블록 무앵커 명시까지 반영 확인했습니다. 결과 CSV는 손대지 않았고, 그 판단이 맞습니다.

남은 두 건은 우리가 `main`에서 직접 처리했습니다. 규칙·수치·라벨은 바꾸지 않았습니다.

| 항목 | 처리 | 검증 |
|---|---|---|
| 5. `direction` 열 | `summarise()`가 `direction`을 생성: `inconclusive` + `paired_hi < -margin` → `worse-than-confidence` | 두 블록 재실행: 기존 열 **전부 동일**, 새 열만 추가. 블록마다 5칸, 모두 `marginal`(spike/`rewire_index`, modular/`rewire_index`, modular/`rewire_order`, BA/`rewire_order`, ER/`rewire_order`) |
| 6. seed 인자화 | `run_controls.rewire(..., offset=None)`, `rewire_index()`가 `index_seed(...) - graph_seed`를 인자로 전달. 모듈 상수 대입 제거 | 두 블록 `controls_v2.csv` **바이트 동일** 재생성 |

즉 `reproduce.py`의 바이트 비교는 새 파일 기준으로도 그대로 성립합니다(행 파일은 동일, 요약 파일만 열 1개 추가).

여전히 열려 있는 것 두 가지:

1. **v2는 클린룸 미검증**입니다. `rewire_order`, 10 draws, 3단 판정, 20 % 마진은 여전히 단일 구현입니다.
2. **BA/ER의 잔여 이득**이 "차수 프로파일"인지 "간선"인지는 아직 분리되지 않았습니다. 그래프 5900–5999에
   전파 없는 `confidence × in-degree` 기준선을 사전등록하면 갈립니다(7100은 소진).

---

## 6. 후기 — 남은 두 항목 처리 (2026-11-26, `main`)

### 6.1 v2 클린룸

`run_controls_v2.py`를 읽지 않은 별도 구현을 돌렸습니다(README의 v2 절과 `dag_role3`만 사용, 대조 요약은
양쪽 블록 계산이 끝난 뒤에만 열람). 결과: `reviews/role4_controls_v2_cleanroom.md`, 코드/로그:
`reviews/role4_independent_v2/`.

| 항목 | 90000 | 7100 |
|---|---|---|
| `intact` == 동결 벤치마크 (1500행, 오류+행동) | 0 불일치 | — |
| `flatten` / `rewire_index:0` == v1 `controls.csv` (각 1500행) | 0 불일치 | — |
| `rewire_order` 밖 요약 셀 | 675/675 동일 | 675/675 동일 |
| 판정 라벨 | 54/54 | 54/54 |
| 주 표 셀(11개) | **11/11** | **11/11** |

즉 v2의 **결론**은 사양만으로 재현됩니다. 다만 `rewire_order` 9행 중 6행(`marginal`/`structural`, modular·BA·ER)은
4자리에서 어긋납니다(최대 1.7 오류, 이득의 4.5 %). 원인은 규칙이 아니라 **미지정 세부**입니다: 후보 풀의 순서와
feasible 노드 tie-break를 README가 고정하지 않았습니다. 정렬 풀·비정렬 부모·유도 sink·rejection 순서를 모두
시험했고 전부 더 나빴습니다.

요청: `README.md`에 그 두 줄(풀 순서, tie-break)을 적어 주십시오. 코드는 그대로 두어도 됩니다. 그때까지
`rewire_order` 수치는 4자리로 인용하지 말고 부호와 라벨만 쓰십시오.

### 6.2 차수 프로파일 vs 간선 — 13000–13099 블록, 사전등록

`role4_controls/PREREG_DEGREE_BASELINE.md`(커밋 `ef3a495`)를 **첫 에피소드 전에** 커밋했고, 원장
(`BENCHMARK_SPEC.md` §3)에 블록을 등록한 뒤 실행했습니다. 정책은 전파 없는 `(1 − conf) · (1 + indeg)^a`,
a ∈ {0.5, 1, 2}(주 지표 a=1), 그리고 기존 `hub`·`confidence`·`marginal`.

| 가족 | `marginal` 이득 | deg1 이득 | Δ = marginal − deg1 | 판정 |
|---|---|---|---|---|
| BA | +19.60 | −21.21 | +40.81 [+29.33, +52.59] | `propagation-necessary` |
| ER | +2.96 | −17.80 | +20.76 [+19.05, +22.53] | `propagation-necessary` |

그리드 최강(a=0.5)으로 바꿔도 BA +21.28 [+21.28, +42.42], ER +15.18 [+15.18, +18.59]로 결론이 유지됩니다.
즉 **전파 없는 차수 점수는 신뢰도 순보다 크게 나쁘고**, `marginal`의 이득은 차수 프로파일로 설명되지 않습니다.
`rewire_index`가 부모 수를 보존하므로 deg 정책의 행동은 두 조건에서 동일합니다(`--selftest`에서 단언) — 그 정책은
재배선 불변이고, 따라서 "남은 이득이 차수 때문"이라는 가설은 성립할 수 없습니다.

재현성: 같은 스크립트를 임시 디렉터리로 한 번 더 돌려 `degree_baseline.csv`, `_summary.csv`, `.md` 세 파일이
**바이트 동일**임을 확인했습니다(`--report-only` 경로 포함). 6000행 = 5가족 × 100그래프 × 2조건 × 6정책.

### 6.3 이 블록이 뒤집은 것 하나 — ER

| 블록 | ER 원래 이득 | `rewire_index` 후 | 잔존율 |
|---|---|---|---|
| 90000–90099 | +4.99 | +1.54 [+0.40, +2.86] | 31 % |
| 7100–7199 | +4.19 | +1.33 [+0.35, +2.29] | 32 % |
| 13000–13099 | +2.96 | +0.02 [−1.01, +1.02] | **1 %** |

BA는 73 % / 84 % / 79 %로 세 블록 모두 생존합니다. ER의 `survives`는 가족의 성질이 아니라 블록의 성질입니다.
`EXPLAINER_KO.md`의 "10회면 충분하다" 문장과 헤드라인의 "ER 31 %"에 P5 추가를 달아 두었습니다. 보고서/발표에서
ER 생존을 근거로 쓰지 마십시오. BA만 쓰십시오.
