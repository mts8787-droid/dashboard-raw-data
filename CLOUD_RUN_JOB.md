# Cloud Run Job 배포 절차


> **이미 완료된 셋업**은 `docs/prd-data-connection.html` 참고. 이 문서는 **PRD 끝난 다음 4단계**만 다룬다.

---

## 0. 현재 상태 (2026-05 기준)

PIC가 PRD 단계로 이미 완료한 것:

| 항목 | 값 |
|---|---|
| GCP 프로젝트 | `pj-my-geo` |
| BigQuery API · 데이터셋 | ✅ 활성, `semrush_data` |
| 서비스 계정 (writer) | `my-geo-dashboard@pj-my-geo.iam.gserviceaccount.com` |
| IAM 역할 | `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` |
| 서비스 계정 키 (JSON) | ✅ 다운로드 완료, Render 환경변수에 등록 |
| dashboard-raw-data 앱 | ✅ Render web service `semrush-admin-portal`로 작동 중 (Streamlit) |

**남은 일은 4개**: ① Cloud Run Job 전환 → ② 매일 자동 트리거 → ③ reader 권한 → ④ my-geo-newsletter 연결.

---

## 단계 A — Cloud Run Job으로 전환 (PIC, 1시간)

지금 Streamlit 앱이 web service(상시 가동)로 떠 있는데, 적재 작업은 매일 새벽 한 번이면 되니까 **Cloud Run Job**(필요할 때만 실행되고 끝남)으로 분리. 비용도 줄고 안정적.

### A-1. Artifact Registry에 컨테이너 저장소 만들기 (5분)

GCP 콘솔 → **Artifact Registry** → "저장소 만들기"

| 항목 | 값 |
|---|---|
| 이름 | `geo-jobs` |
| 형식 | Docker |
| 위치 유형 | 리전 |
| 리전 | `asia-northeast3` (서울) |

→ "만들기"

### A-2. 컨테이너 빌드 (10분)

GCP 콘솔 → **Cloud Build** → **트리거** → "트리거 만들기"

| 항목 | 값 |
|---|---|
| 이름 | `semrush-loader-build` |
| 이벤트 | "수동 호출" (또는 GitHub push 연동도 가능) |
| 소스 | GitHub: `mts8787-droid/dashboard-raw-data`, 브랜치 `main` |
| 구성 | Dockerfile (저장소에 이미 있음) |
| Dockerfile 위치 | `/Dockerfile` |
| 이미지 이름 | `asia-northeast3-docker.pkg.dev/pj-my-geo/geo-jobs/semrush-loader:latest` |

→ "만들기" → 만든 트리거 우측 **"실행"** → 5~10분 후 빌드 완료. Artifact Registry에 이미지 등록 확인.

### A-3. Cloud Run Job 생성 (10분)

GCP 콘솔 → **Cloud Run** → **작업** 탭 → "작업 만들기"

| 항목 | 값 |
|---|---|
| 컨테이너 이미지 URL | `asia-northeast3-docker.pkg.dev/pj-my-geo/geo-jobs/semrush-loader:latest` |
| 작업 이름 | `semrush-loader` |
| 리전 | `asia-northeast3` |
| 작업 유형 | 작업 (Job) |
| 최대 재시도 | 1 |
| 작업 시간 제한 | 30분 |
| 서비스 계정 | `my-geo-dashboard@pj-my-geo.iam.gserviceaccount.com` |

**컨테이너 → 변수 및 보안 비밀** 탭:
- Render에 등록된 환경변수 그대로 입력:
  - `SEMRUSH_API_KEY` (Secret Manager에 저장 권장)
  - `SEMRUSH_WORKSPACE_ID`
  - `GCP_PROJECT_ID` = `pj-my-geo`
  - `BQ_DATASET` = `semrush_data`
  - `SEMRUSH_DATABASE` = `us`
  - `TARGET_DOMAIN` = (원래 값)
  - `GOOGLE_APPLICATION_CREDENTIAL_JSON` (Secret Manager 권장)

> 💡 **Secret Manager 사용법**: GCP 콘솔 → Secret Manager → "보안 비밀 만들기" → 이름 (예: `semrush-api-key`) + 값 입력 → 저장. Cloud Run Job에서 "보안 비밀 참조"로 연결.

**컨테이너 → 인수**:
- 인수 추가: `--days`
- 인수 추가: `1`

→ "만들기" → 생성됨.

### A-4. 첫 실행으로 정상 동작 확인 (5분)

만든 작업 클릭 → 우측 상단 **"실행"** → 5~10분 대기.

성공 확인:
1. **Cloud Run** → `semrush-loader` → 실행 기록 → 가장 최근 실행 → "성공" 표시 + 종료 코드 0
2. **BigQuery** → `pj-my-geo.semrush_data.L0_Raw_visibility` → "미리보기" → 행 추가됨

> 실패 시 §트러블슈팅 표 참고.

---

## 단계 B — 매일 자동 트리거 (PIC, 10분)

GCP 콘솔 → **Cloud Scheduler** → "작업 만들기"

| 항목 | 값 |
|---|---|
| 이름 | `semrush-loader-daily` |
| 리전 | `asia-northeast3` |
| 빈도 | `0 4 * * *` (매일 새벽 4시) |
| 시간대 | `Asia/Seoul` |
| 대상 유형 | HTTP |
| URL | `https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/pj-my-geo/jobs/semrush-loader:run` |
| HTTP 메서드 | POST |
| 인증 헤더 | "OAuth 토큰 추가" |
| 서비스 계정 | `my-geo-dashboard@pj-my-geo.iam.gserviceaccount.com` |

→ "만들기" → 생성됨. 다음 날 새벽 4시에 자동 실행.

> 💡 만들고 나면 작업 목록에서 "지금 강제 실행" 버튼으로 즉시 테스트 가능.

---

## 단계 C — reader 서비스 계정 추가 (PIC, 15분)

`my-geo-newsletter`(이 시스템)는 BigQuery에서 데이터를 **읽기만** 하면 되므로, 별도의 read-only 서비스 계정을 만들면 안전. (writer 키를 그대로 쓰면 실수로 데이터 덮어쓸 위험)

### C-1. 서비스 계정 생성 (5분, PRD 단계 2 패턴 그대로)

GCP 콘솔 → **IAM 및 관리자** → **서비스 계정** → "서비스 계정 만들기"

| 항목 | 값 |
|---|---|
| 이름 | `geo-newsletter-reader` |
| 설명 | "my-geo-newsletter용 BigQuery 읽기 전용" |

생성 후 **권한 부여** 섹션에서 두 역할:
- `BigQuery 데이터 뷰어` (`roles/bigquery.dataViewer`)
- `BigQuery 작업 사용자` (`roles/bigquery.jobUser`)

### C-2. JSON 키 다운로드 (5분, PRD 단계 2-2 패턴 그대로)

만든 서비스 계정 클릭 → **키** 탭 → "키 추가" → "새 키 만들기" → JSON → 다운로드.

> ⚠️ 이 키 파일이 reader 권한의 비밀번호. 절대 GitHub에 올리지 말 것.

---

## 단계 D — my-geo-newsletter에 reader 키 연결 (PIC, 5분)

[Render 대시보드](https://dashboard.render.com) → `geo-newsletter` 서비스 → **Environment** 탭 → 다음 환경변수 추가:

```
GCP_PROJECT_ID = pj-my-geo
BQ_DATASET = semrush_data
GOOGLE_APPLICATION_CREDENTIALS_JSON = (단계 C-2에서 다운로드한 JSON 파일 내용을 통째로 복사 붙여넣기)
```

> **주의**: 변수 이름은 `GOOGLE_APPLICATION_CREDENTIALS_JSON` (끝에 `S`+`_JSON`). dashboard-raw-data의 `GOOGLE_APPLICATION_CREDENTIAL_JSON` (S 없음, Render의 옛 표기)와 다름.

저장 → Render가 자동 재배포 (1~2분).

확인:
- 어드민 로그인 → 브라우저 주소창에 `https://<your-app>.onrender.com/api/bridge/health` 직접 입력
- `{"ok":true,"configured":true,"projectId":"pj-my-geo","dataset":"semrush_data"}` 표시되면 성공

추가 확인:
- `/api/bridge/freshness` → `lastLoadedAt`에 가장 최근 적재 시각이 보이고 `stale: false`

---

## 운영 (자동, PIC 작업 0)

이후:
- 매일 새벽 4시 Cloud Scheduler가 자동 실행
- 실패 시 콘솔 → **Monitoring → Alerting**에서 알림 룰 설정 가능 (PIC 이메일로)
- 어드민 신선도 배지에 "데이터 최신화: N시간 전" 자동 표시 (Phase 2 후속 작업에서 편집 화면에 추가됨)

---

## 트러블슈팅

| 증상 | 원인 후보 | 처리 |
|---|---|---|
| 컨테이너 빌드 실패 | Dockerfile에 누락된 파일 | `dashboard-raw-data` 레포의 Dockerfile 최신 확인 |
| Cloud Run Job 실행 실패 (`PERMISSION_DENIED`) | 서비스 계정 권한 부족 | IAM에서 writer 서비스 계정의 `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` 부여 확인 |
| `SEMRUSH_API_KEY가 설정되지 않았습니다` | 환경변수·Secret 미바인딩 | Cloud Run Job → "변수 및 보안 비밀" 탭 점검 |
| 적재 행 수 0 | SEMrush 응답 비어있음 | dashboard-raw-data 앱(Streamlit)에서 직접 조회해 데이터 있는지 확인 |
| Scheduler 실행되지만 Job 안 돔 | OAuth 토큰 권한 부족 | Scheduler 작업 → 서비스 계정에 `roles/run.invoker` 부여 |
| `/api/bridge/health`가 503 | Render 환경변수 미설정 | 단계 D 재확인 |
| `/api/bridge/health`가 500 | reader 키 형식 오류 | JSON 통째로 한 줄로 복붙 (줄바꿈 포함된 JSON 문자열 그대로) |
| `/api/bridge/freshness`가 stale: true | 최근 적재 실패 또는 24h 이상 경과 | Cloud Scheduler 실행 이력·Cloud Run Job 로그 확인 |

---

## 용어집

| 단어 | 한 줄 설명 | 비유 |
|---|---|---|
| **Cloud Run Job** | 한 번 실행되고 끝나는 작업. 서버처럼 계속 떠있지 않음 | 새벽에만 켜지는 공장 |
| **Cloud Run Service** | 사용자 요청을 받기 위해 항상 떠있는 웹 서버 | 24시 편의점 |
| **Cloud Scheduler** | 정해진 시각에 작업을 자동 실행 | 알람시계 |
| **BigQuery** | 거대 데이터를 빠르게 분석하는 GCP 데이터 창고 | 회사 자료실 |
| **데이터셋(Dataset)** | BigQuery 안의 폴더. 여러 테이블을 묶음 | 자료실 캐비닛 |
| **테이블(Table)** | 데이터셋 안의 표 데이터 | 캐비닛 안 폴더 1개 |
| **Service Account** | 사람이 아닌 프로그램의 계정. 특정 권한만 부여 | 청소 로봇용 출입증 |
| **IAM** | 누가 무엇을 할 수 있는지 권한 관리 | 회사 출입증 시스템 |
| **Secret Manager** | API 키·비밀번호 안전 저장소 | 비밀번호 금고 |
| **Artifact Registry** | 컨테이너(앱 패키지) 저장 창고 | 앱스토어의 GCP 버전 |
| **컨테이너(Container)** | 앱과 실행 환경을 통째로 묶은 패키지 | 도시락 |
| **백필(Backfill)** | 과거 데이터를 한꺼번에 채워 넣음 | 이사 첫날 짐 한꺼번에 옮기기 |
| **writer / reader** | 쓰는 쪽 / 읽는 쪽 | dashboard-raw-data가 writer, my-geo-newsletter가 reader |

---

*v2.0 · 2026-05-05 — PRD 후속 단계만 다루도록 재작성. 실제 프로젝트(`pj-my-geo`) + 서비스 계정 반영. PIC 단독 콘솔 클릭으로 4단계 완료 가능.*
