# 데이터 스키마 디렉터리

`pj-my-geo.semrush_data` 데이터셋의 BigQuery 테이블 스키마를 PIC가 학습·검수해 누적 저장한다.

## 파일 구조

```
docs/schema/
├── README.md                                            ← 이 파일
├── lineage.md                                           ← 시간 역순 변경 이력 (CHANGELOG)
├── pj-my-geo__semrush_data__ai_visibility.json          ← 현재 스키마 (latest)
└── lineage/
    ├── pj-my-geo__semrush_data__ai_visibility__2026-05-06-091500.json
    ├── pj-my-geo__semrush_data__ai_visibility__2026-05-15-100000.json
    └── ...                                              ← 시간 역순 누적 스냅샷
```

## 누가·어떻게 갱신하나?

**누가**: PIC (이 레포의 Streamlit 관리자 — `pages/5_schema_learning.py`)

**언제**:
- BigQuery 테이블에 새 컬럼이 생겼을 때
- 컬럼 의미·정의가 명확해졌을 때 (PIC가 처음 보고 의미를 정리한 시점)
- SEMrush API 변경으로 데이터 형태가 바뀌었을 때

**방법**:
1. Streamlit `🧠 스키마 학습` 페이지 열기
2. 테이블 선택 → "가져와서 분석" 클릭
3. 자동 분석 결과 확인 (각 컬럼 dtype·null%·distinct·sample)
4. 컬럼별 **설명** + **분류**(차원/측정값/메타/ID/기타) 입력 또는 수정
5. 변경 메모 적기 (예: "sov 정의 보강")
6. **💾 스키마 저장** 클릭

저장 시 자동으로:
- `<dataset>__<table>.json` (latest) 갱신
- `lineage/<...>__<timestamp>.json` 새 스냅샷 추가
- `lineage.md`에 한 행 추가 (시간 역순)

## 시간 역순 보기

`📜 스키마 리니지` 페이지 또는 `lineage.md` 직접 열기. 각 스냅샷의 직전 버전 대비 diff(추가·삭제·변경 컬럼)도 확인 가능.

## reader(my-geo-newsletter) 측 사용

`my-geo-newsletter` 레포의 `routes/bridge.js`가 본 디렉터리의 latest JSON을 참고해 매핑 코드를 작성한다. 컬럼이 변경되면:
1. 본 디렉터리의 lineage가 갱신됨
2. `BIGQUERY_SCHEMA.md` (이 디렉터리와 별개로, 두 레포 사이 명세 문서)도 동기화 필요
3. reader 코드(브릿지) 갱신 후 reader 레포에 PR

자세한 변경 절차: 상위 레포의 `BIGQUERY_SCHEMA.md` §스키마 변경 절차 참고.

## 컬럼 분류 의미

| 분류 | 예시 | 의미 |
|---|---|---|
| **차원(Dimension)** | `tag`, `model`, `date`, `country` | 데이터를 그룹·필터·축으로 사용 |
| **측정값(Metric)** | `visibility`, `sov`, `mentions`, `prompts` | 수치 — 평균·합·비교 가능 |
| **메타(System)** | `_loaded_at`, `_source` | 시스템이 자동 추가, 사용자 입력 아님 |
| **ID/Key** | `prompt_id`, `request_id` | 식별자 — 조인 키, 측정값으로 다루지 않음 |
| **기타** | — | 위 4개 분류 어디에도 안 맞음 (드물게) |
