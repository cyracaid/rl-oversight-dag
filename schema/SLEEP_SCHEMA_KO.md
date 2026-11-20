# 수면 데이터 — 39개 헤더와 권장 자료형

[한국어 인계 안내](TEAM_HANDOFF_KO.md) · [헤더만 받기](sleep_headers.csv) · [원본 집계 JSON](sleep_schema.json)

열 이름은 코드 호환성을 위해 번역하지 않습니다. 아래 순서는 CSV 헤더와 같습니다.
자료형은 권장 파싱 방식이며 원본 시스템의 검증된 타입 선언이 아닙니다.
`nullable`은 결측 허용을 뜻합니다. 실제 데이터 행은 포함하지 않습니다.

| # | 원본 열 이름 | 한국어 설명 | 권장 타입·단위 |
|---:|---|---|---|
| 1 | `pid` | 참여자 식별자 | 불투명 문자열, 특징에서 제외 |
| 2 | `day_num` | 연구 내 일차 | nullable 정수, 1부터 시작 |
| 3 | `row_id` | 행 식별자 | 불투명 문자열, 특징에서 제외 |
| 4 | `bedtime_selfreport_ts` | 자기보고 취침 시각 | nullable datetime |
| 5 | `sleeponset_selfreport_ts` | 자기보고 입면 시각 | nullable datetime |
| 6 | `awakening_selfreport_ts` | 자기보고 최종 각성 시각 | nullable datetime |
| 7 | `getup_selfreport_ts` | 자기보고 기상 시각 | nullable datetime |
| 8 | `tst_minutes` | 총 수면 시간 TST | nullable 실수, 분 |
| 9 | `sol_computed_minutes` | 계산된 입면 잠복기 SOL | nullable 실수, 분 |
| 10 | `se_percent` | 수면 효율 SE | nullable 실수, 0–100% |
| 11 | `tib_minutes` | 침대에 머문 시간 TIB | nullable 실수, 분 |
| 12 | `sleepperiod_minutes` | 입면부터 최종 각성까지의 기간 | nullable 실수, 분 |
| 13 | `waso_computed_minutes` | 계산된 입면 후 각성 시간 WASO | nullable 실수, 분; 계산 정의 확인 필요 |
| 14 | `waso_avg_bout_selfreport_minutes` | 자기보고 각성 1회당 평균 시간 | nullable 실수, 분 |
| 15 | `sol_selfreport_minutes` | 자기보고 입면 잠복기 | nullable 실수, 분 |
| 16 | `waso_selfreport_minutes` | 자기보고 입면 후 각성 시간 | nullable 실수, 분 |
| 17 | `num_waso_bouts_selfreport` | 자기보고 각성 횟수 | nullable 수치, 정수 여부 확인 |
| 18 | `nap_selfreport_totalminutes` | 자기보고 낮잠 총시간 | nullable 실수, 분 |
| 19 | `exercise_light_minutes` | 가벼운 운동 시간 | nullable 실수, 분 |
| 20 | `exercise_moderate_minutes` | 중강도 운동 시간 | nullable 실수, 분 |
| 21 | `exercise_vigorous_minutes` | 고강도 운동 시간 | nullable 실수, 분 |
| 22 | `exercise_strength_minutes` | 근력 운동 시간 | nullable 실수, 분 |
| 23 | `has_correction` | 수정 상태 | nullable 범주 문자열, 정답 관련 |
| 24 | `is_error` | 오류 표시 | nullable 불리언, 정답 관련 |
| 25 | `error_type` | 오류 유형 | nullable 문자열, 원본 확인 필요; 현재 전부 결측 |
| 26 | `is_unusual` | 비정상·특이 기록 표시 | nullable 불리언, 정답 관련 |
| 27 | `unusual_type` | 특이 기록 유형 | nullable 범주 문자열, 정답 관련 |
| 28 | `record_status` | 기록 상태 | nullable 범주 문자열, 정답 관련 |
| 29 | `flag_severity` | 플래그 심각도 | nullable 범주 문자열, 정답 관련 |
| 30 | `human_review` | 사람 검토 상태 | nullable 범주 문자열, 정답 관련 |
| 31 | `caffeine_num` | 카페인 섭취 횟수·수량 | nullable 수치; 세부 정의 확인 필요 |
| 32 | `alcohol_num` | 알코올 섭취 횟수·수량 | nullable 수치; 세부 정의 확인 필요 |
| 33 | `nicotine_doses` | 니코틴 사용량·횟수 | nullable 수치; 세부 정의 확인 필요 |
| 34 | `cannabis_doses` | 대마 사용량·횟수 | nullable 수치; 세부 정의 확인 필요 |
| 35 | `StartDate` | 일지 기록 날짜 | nullable 날짜/문자열, 실제 형식 확인 필요 |
| 36 | `sol_selfreport_raw` | 입면 잠복기 원문 값 | nullable 문자열, 숫자로 즉시 변환 금지 |
| 37 | `sol_selfreport_ambiguous` | 입면 잠복기 해석 모호성 표시 | nullable 불리언, 의사결정 시점 이용 가능성 확인 |
| 38 | `waso_selfreport_raw` | 입면 후 각성 시간 원문 값 | nullable 문자열, 숫자로 즉시 변환 금지 |
| 39 | `waso_selfreport_ambiguous` | 각성 시간 해석 모호성 표시 | nullable 불리언, 의사결정 시점 이용 가능성 확인 |

빈 CSV 셀은 결측입니다. `True`/`False`를 명시적으로 파싱합니다.
시각은 현지 시각이며 시간대 정보가 없습니다. 범주 목록, 결측률 및 범위는
[영문 집계표](SLEEP_SCHEMA.md)와 JSON에 있습니다. 반올림된 비율보다 JSON의
정확한 값이 우선합니다. 필드명의 설명은 인터페이스 안내이며 임상 정의를 대체하지 않습니다.
