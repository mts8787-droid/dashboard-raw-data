# BigQuery Schema 계약

본 문서는 **`dashboard-raw-data` (writer) ↔ `my-geo-newsletter` (reader)** 두 레포 사이의 단일 결합 지점이다. 코드는 공유하지 않고, 이 스키마와 컨벤션만 양쪽이 따른다.

---

## 데이터셋

- **프로젝트**: 환경변수 `GCP_PROJECT_ID` (예: `lg-geo-prod`)
- **데이터셋**: 환경변수 `BQ_DATASET` (기본: `semrush_data`)
- **위치**: `US` (loader가 dataset 자동 생성 시 기본값)

---

## 테이블

### `ai_visibility` — AI 검색 가시성 (모델별·일별)

`SEMrush Enterprise Element API → ai_visibility` 응답을 `model`, `date`, 시스템 컬럼만 추가해 그대로 적재.

**시스템 컬럼** (writer가 항상 추가)

| 컬럼 | 타입 | 의미 |
|---|---|---|
| `_loaded_at` | `TIMESTAMP` | 적재 시점 (UTC ISO8601) |
| `_source` | `STRING` | 원천 식별자, 항상 `"semrush_enterprise"` |
| `model` | `STRING` | AI 모델 (`search-gpt`·`perplexity`·`gpt-5`·`gemini-2.5-flash`·`copilot`·`claude`·`meta-ai`) |
| `date` | `STRING` (YYYY-MM-DD) | 데이터 일자 |

**SEMrush 응답 컬럼** (autodetect, 변경 가능)

SEMrush API 응답 스키마는 SEMrush 측에서 변경될 수 있다. 컬럼 이름·타입은 BigQuery `autodetect`로 자동 감지된다. 현재 시점 주요 컬럼은 SEMrush UI의 "Generate API Request"로 확인하거나 `bq show --schema {project}.{dataset}.ai_visibility`로 조회.

**파티션·클러스터링 (권장 — 미적용 시 reader는 풀 스캔)**

```sql
-- (수동 적용 권장, 비용 절감)
CREATE OR REPLACE TABLE `{project}.semrush_data.ai_visibility`
PARTITION BY DATE(date)
CLUSTER BY model, _source AS
SELECT * FROM `{project}.semrush_data.ai_visibility`;
```

---

## Reader 측 사용 패턴

`my-geo-newsletter`의 브릿지 API(`routes/bridge.js`)는 BigQuery 결과를 기존 `sync-data` JSON 형식으로 변환해 편집 페이지에 전달한다.

**예시 쿼리**

```sql
-- 최근 7일, LG 브랜드, 모델별 일평균 가시성
SELECT
  model,
  date,
  AVG(visibility) AS visibility_avg
FROM `{project}.semrush_data.ai_visibility`
WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) AND CURRENT_DATE()
  AND _source = 'semrush_enterprise'
GROUP BY model, date
ORDER BY date DESC, model;
```

**Reader 가드라인**
- `_source = 'semrush_enterprise'` 필터 권장 — 향후 다른 소스 추가 대비
- `_loaded_at`으로 신선도 판정 (24시간 초과 시 stale 배지)
- `WHERE date BETWEEN ...` 필터 필수 — 파티션 미적용 시 비용 폭주 방지

---

## 추가 예정 테이블 (writer 측 계획)

| 테이블 | 출처 | 예정 시점 |
|---|---|---|
| `tracker_intake` | 사이트맵 크롤러 (§4.4) | Phase 1 |
| `dim_prompt` | 프롬프트 마스터 (§4.2) | Phase 2 |
| `dim_prompt_history` | 프롬프트 수정 이력 | Phase 2 |
| `audit_logs` | 감사 로그 (게시·프롬프트·설정 변경) | Phase 2 |
| `logs.insight_runs` | AI 인사이트 호출 메타 (token·비용·지연) | Phase 2 (현재 JSONL → BQ 이관) |

각 테이블 추가 시 본 문서에 컬럼 정의 + 신선도·파티션 가이드 추가.

---

## 스키마 변경 절차

| 변경 | 안전성 | 절차 |
|---|---|---|
| **컬럼 추가** | 🟢 안전 | writer만 추가, reader는 무시. 며칠 후 reader 사용 시작 |
| **컬럼 이름 변경** | 🔴 위험 | (1) 새 이름 추가 → 둘 다 씀 → (2) reader 새 이름 사용 → (3) 옛 이름 제거 |
| **타입 변경** | 🔴 위험 | 새 컬럼 추가 후 마이그레이션. 직접 변경 금지 |
| **컬럼 삭제** | 🟠 주의 | reader 코드에서 참조 제거 후 N개월 대기 → 삭제 |
| **테이블 삭제** | 🟠 주의 | reader 사용 종료 확인 후 dataset에서 archive 처리 |

본 문서 변경 시:
1. 변경 사유·날짜를 git commit message에 명시
2. `my-geo-newsletter` 측에 영향 있으면 PR 코멘트로 cross-link

---

## 환경변수 (writer)

| 변수 | 필수 | 기본 | 설명 |
|---|:---:|---|---|
| `SEMRUSH_API_KEY` | ✅ | — | SEMrush Enterprise API Key |
| `SEMRUSH_WORKSPACE_ID` | ✅ | — | Enterprise Workspace ID |
| `SEMRUSH_PROJECT_ID` | — | (없음) | Enterprise Project ID (선택) |
| `SEMRUSH_DATABASE` | — | `us` | DB locale |
| `TARGET_DOMAIN` | — | `example.com` | 대상 도메인 |
| `GCP_PROJECT_ID` | ✅ | — | BigQuery 프로젝트 |
| `BQ_DATASET` | — | `semrush_data` | 데이터셋 이름 |
| `GOOGLE_APPLICATION_CREDENTIAL_JSON` | ✅ | — | 서비스 계정 키 JSON 문자열 (Cloud Run Job은 `--service-account` 플래그로 대체 가능) |

---

*v1.0 · 2026-05-02 — 초기 계약 문서 (ai_visibility 단일 테이블)*
