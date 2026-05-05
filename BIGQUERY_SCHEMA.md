# BigQuery Schema 계약


> **누가 읽나요?**
> - **PIC** → §1 (한 줄 설명) + §2 (PIC가 알아야 할 것) + §6 (용어집) — 표 정의는 안 외워도 됨
> - **dev** → §3 (테이블 정의) + §4 (변경 절차) + §5 (환경변수)

---

## 1. 한 줄 설명

이 문서는 **두 시스템(`dashboard-raw-data` + `my-geo-newsletter`)이 같은 BigQuery 테이블을 안전하게 공유**하기 위한 약속이다.

```
dashboard-raw-data (writer, 데이터를 씀)
        ↓
   BigQuery 테이블  ← 이 문서가 정의하는 약속
        ↓
my-geo-newsletter (reader, 데이터를 읽음)
```

코드는 공유하지 않는다. 이 문서의 **컬럼 이름·타입 약속**만 양쪽이 따른다.

---

## 2. PIC가 알아야 할 것

### 어떤 데이터가 어디에 쌓이나?

매일 새벽 SEMrush에서 받아오는 데이터는 모두 **GCP의 BigQuery**라는 데이터 창고에 자동 저장됨.

| 항목 | 값 |
|---|---|
| GCP 프로젝트 | `lg-geo-prod` (Phase 2 셋업 시 결정) |
| 데이터셋(Dataset) | `semrush_data` |
| 첫 테이블 | `ai_visibility` (AI 모델별 LG 가시성) |

### "신선도(stale)"가 뭔가요?

데이터가 24시간 이상 갱신 안 됐으면 시스템이 **stale = true**로 표시 → 어드민의 신선도 배지에 ⚠️ 표시. 이 경우:
1. 어드민 → "Cloud Run Job 배포 절차" → §4 트러블슈팅 표 확인
2. 또는 dev에게 알림

### PIC가 직접 BigQuery 화면을 봐야 할 때는?

**거의 없음.** 어드민의 신선도 배지로 충분. 굳이 본다면:
- 데이터 새로 들어왔는지 확인: GCP 콘솔 → BigQuery → `ai_visibility` 테이블 → "미리보기"
- 직접 SQL은 dev 영역

---

## 3. 테이블 정의 (dev용)

### `ai_visibility` — AI 검색 가시성 (모델별·일별)

`SEMrush Enterprise Element API → ai_visibility` 응답을 그대로 적재 + 4개 시스템 컬럼 추가.

**시스템 컬럼** (writer가 항상 추가)

| 컬럼 | 타입 | 의미 |
|---|---|---|
| `_loaded_at` | `TIMESTAMP` | 적재 시점 (UTC ISO8601) |
| `_source` | `STRING` | 원천, 항상 `"semrush_enterprise"` |
| `model` | `STRING` | AI 모델 (`search-gpt`·`perplexity`·`gpt-5`·`gemini-2.5-flash`·`copilot`·`claude`·`meta-ai`) |
| `date` | `STRING` (YYYY-MM-DD) | 데이터 일자 |

**SEMrush 응답 컬럼** (autodetect, 변경 가능)

SEMrush 측에서 컬럼 이름·타입을 변경할 수 있음. BigQuery `autodetect`로 자동 감지. 현재 시점 컬럼은:
```bash
bq show --schema {project}.semrush_data.ai_visibility
```

**파티션·클러스터링 (권장)**

```sql
CREATE OR REPLACE TABLE `{project}.semrush_data.ai_visibility`
PARTITION BY DATE(date)
CLUSTER BY model, _source AS
SELECT * FROM `{project}.semrush_data.ai_visibility`;
```

미적용 시 reader가 풀 스캔 → 비용 증가.

### Reader 사용 패턴

`my-geo-newsletter`의 `routes/bridge.js`(`@google-cloud/bigquery` 사용)가 sync-data JSON 형식으로 변환해 편집 페이지에 전달.

**예시 쿼리**

```sql
-- 최근 7일, LG, 모델별 일평균 가시성
SELECT model, date, AVG(visibility) AS visibility_avg
FROM `{project}.semrush_data.ai_visibility`
WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) AND CURRENT_DATE()
  AND _source = 'semrush_enterprise'
GROUP BY model, date
ORDER BY date DESC, model;
```

**Reader 가드라인**
- `_source = 'semrush_enterprise'` 필터 권장 (향후 다른 소스 대비)
- `_loaded_at`으로 신선도 판정 (24h 초과 = stale)
- `WHERE date BETWEEN ...` 필수 (파티션 미적용 시 비용 폭주 방지)

### 추가 예정 테이블

| 테이블 | 출처 | 시점 |
|---|---|---|
| `tracker_intake` | 사이트맵 크롤러 (§4.4) | Phase 1 |
| `dim_prompt` / `dim_prompt_history` | 프롬프트 마스터 (§4.2) | Phase 2 |
| `audit_logs` | 게시·프롬프트·설정 변경 | Phase 2 |
| `logs.insight_runs` | AI 호출 메타 (현재 JSONL) | Phase 2 |

---

## 4. 스키마 변경 절차 (dev용)

| 변경 | 안전성 | 절차 |
|---|---|---|
| **컬럼 추가** | 🟢 안전 | writer만 추가 → reader는 무시. 며칠 후 reader 사용 시작 |
| **컬럼 이름 변경** | 🔴 위험 | (1) 새 이름 추가 → 둘 다 씀 → (2) reader 새 이름 사용 → (3) 옛 이름 제거 |
| **타입 변경** | 🔴 위험 | 새 컬럼 추가 후 마이그레이션. 직접 변경 금지 |
| **컬럼 삭제** | 🟠 주의 | reader 코드 참조 제거 → N개월 대기 → 삭제 |
| **테이블 삭제** | 🟠 주의 | reader 사용 종료 확인 → archive 처리 |

본 문서 변경 시:
1. 변경 사유·날짜를 git commit message에 명시
2. `my-geo-newsletter` 측에 영향 있으면 PR 코멘트 cross-link

---

## 5. 환경변수 (writer 측)

| 변수 | 필수 | 기본 | 설명 |
|---|:---:|---|---|
| `SEMRUSH_API_KEY` | ✅ | — | SEMrush Enterprise API Key |
| `SEMRUSH_WORKSPACE_ID` | ✅ | — | Enterprise Workspace ID |
| `SEMRUSH_PROJECT_ID` | — | — | Enterprise Project ID (선택) |
| `SEMRUSH_DATABASE` | — | `us` | DB locale |
| `TARGET_DOMAIN` | — | `example.com` | 대상 도메인 |
| `GCP_PROJECT_ID` | ✅ | — | BigQuery 프로젝트 |
| `BQ_DATASET` | — | `semrush_data` | 데이터셋 이름 |
| `GOOGLE_APPLICATION_CREDENTIAL_JSON` | ✅ | — | 서비스 계정 키 JSON 문자열 |

---

## 6. 용어집

| 단어 | 한 줄 설명 | 비유 |
|---|---|---|
| **데이터셋(Dataset)** | BigQuery 안의 폴더 — 여러 테이블 묶음 | 자료실 캐비닛 |
| **테이블(Table)** | 데이터셋 안의 표 데이터 1개 | 캐비닛 안의 폴더 |
| **컬럼(Column)** | 표의 세로 열 (예: `model`, `date`) | 엑셀의 A열, B열 |
| **타입(Type)** | 컬럼이 담는 값의 종류 (`STRING`, `TIMESTAMP` 등) | "이 칸은 숫자만" 같은 규칙 |
| **시스템 컬럼** | writer가 자동으로 추가하는 컬럼 (`_loaded_at` 등) | 사진의 EXIF (찍힌 시각·기기 정보) |
| **autodetect** | BigQuery가 데이터를 보고 컬럼 타입을 자동 추정 | 엑셀 자동 서식 |
| **파티션(Partition)** | 큰 테이블을 날짜·키별로 나눠 저장해 조회 빠르게 | 연도별로 나뉜 자료실 폴더 |
| **클러스터링(Clustering)** | 같은 모델끼리 묶어 저장해 필터 빠르게 | 알파벳순 정렬 |
| **append-only** | 기록은 추가만, 수정·삭제 안 됨 | 출입 기록부 (덮어쓰기 안 함) |
| **writer / reader** | 쓰는 쪽 / 읽는 쪽 | dashboard-raw-data가 writer, my-geo-newsletter가 reader |

---

*v1.1 · 2026-05-05 — PIC용 §1·§2, dev용 §3~5, 용어집 §6로 분리.*
