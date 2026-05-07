# 데이터 스키마 디렉터리

`pj-my-geo.semrush_data` 데이터셋의 8개 테이블 — 컬럼 정의 + 데이터 리니지(흐름).

**원천 명세서**:
- [Ascent DB 데이터 스키마 시트](https://docs.google.com/spreadsheets/d/1zgs-BV4gyhR0uGSCX3Mww8loacpDcWcYV-BVMhbUOno) — 변환 흐름·Prompt ID 규칙
- ERD 다이어그램 (PIC 2026-05-06 공유) — 7개 테이블 컬럼 정의 (실 스키마)

## 파일 구조

```
docs/schema/
├── README.md                                       ← 이 파일
└── pj-my-geo__semrush_data__<table>.json           ← 테이블별 단일 latest (7개)
```

테이블별 1개 JSON에 컬럼 정의 + 리니지(상류·하류·변환 규칙)를 모두 담는다.
시간 역순 변경 이력은 별도로 관리하지 않음 (필요 시 git log로 추적).

## 8개 테이블 현황

| 레이어 | 테이블 | 컬럼 | 역할·주기 |
|---|---|:---:|---|
| **L0 (Raw)** | `L0_Raw_visibility` | 12 | SEMrush API 원천 적재 / weekly |
|  | `L0_Raw_prompt_master` | 14 | 분류체계 마스터 / weekly |
| **L1 (Transform)** | `L1_visibility` | 12 | L0_Raw_visibility ⨝ L0_Raw_prompt_master / weekly |
|  | `L1_citation` | 13 | L0_Raw_visibility ⨝ L0_Raw_prompt_master / monthly |
|  | `L1_report_visibility` | 9 | L1_visibility ⨝ L0_Raw_prompt_master → GROUP BY AVG / weekly |
|  | `L1_report_citation` | 24 | L1_citation ⨝ L0_Raw_prompt_master ⨝ L1_domain_mapping / monthly |
|  | `L1_competitor_brand` | 4 | 경쟁사 브랜드 매핑 / static |
|  | `L1_domain_mapping` | 3 | 도메인 유형 매핑 / static |

## JSON 구조

```json
{
  "dataset": "pj-my-geo.semrush_data",
  "table": "report_visibility",
  "saved_at": "...",
  "columns": [
    { "name": "...", "bq_type": "STRING", "nullable": "Y", "key": "PK",
      "description": "...", "category": "차원(Dimension)",
      "source_file": "...", "source_column": "...", "derivation": "..." }
  ],
  "lineage": {
    "role": "transform",
    "frequency": "weekly",
    "sources": [
      { "system": "SEMrush API", "frequency": "weekly" } |
      { "table": "visibility", "join_on": "prompt_id" }
    ],
    "downstream": ["report_visibility"],
    "transforms": ["GROUP BY ...", "AVG(...) ..."]
  }
}
```

## 갱신 방법

**Streamlit `🧠 스키마 학습`** 페이지에서:
1. 테이블 선택 → BigQuery 실데이터 가져와 자동 분석
2. 컬럼별 description·category 검수
3. 리니지(role/주기/sources/downstream/transforms) 입력
4. 저장 → `<table>.json` 갱신 (시간 스냅샷 X, 단일 latest)

## reader(my-geo-newsletter) 측 사용

`my-geo-newsletter`의 `routes/bridge.js`가 본 디렉터리의 latest JSON을 참고해 매핑 코드를 작성. 컬럼 변경 시 양 레포 동기화 필요. 자세한 절차: 상위 레포 `BIGQUERY_SCHEMA.md` 참고.
