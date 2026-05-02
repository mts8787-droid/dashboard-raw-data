# Cloud Run Job 배포 절차

`semrush-loader` Cloud Run Job — 매일 새벽 SEMrush API에서 BigQuery로 데이터 적재.

비개발자가 GCP 콘솔만으로 따라 할 수 있게 단계별로 정리. dev 검토 권장 시점은 ⚠️로 표시.

---

## 0. 사전 요구

- GCP 프로젝트 생성·결제 연결 완료 (예: `lg-geo-prod`)
- BigQuery API·Cloud Run API·Cloud Scheduler API·Artifact Registry API 활성화
- SEMrush Enterprise API Key·Workspace ID 확보

---

## 1. 서비스 계정 생성 ⚠️ (dev 1회 검토 권장)

| 항목 | 설명 |
|---|---|
| 이름 | `semrush-loader-sa` |
| 역할 | `BigQuery Data Editor` (해당 데이터셋 한정) + `BigQuery Job User` |
| 키 | **JSON 키 다운로드 — 컨테이너에 환경변수로 주입할 용도** |

CLI 예시:
```bash
gcloud iam service-accounts create semrush-loader-sa \
  --display-name "SEMrush BigQuery Loader"

# 데이터셋 한정 권한 부여
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member "serviceAccount:semrush-loader-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member "serviceAccount:semrush-loader-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/bigquery.jobUser"
```

> ⚠️ Phase 2 운영 시 키 파일 대신 **Workload Identity Federation**으로 전환 권장 — dev 검토 1일.

---

## 2. Secret Manager에 환경변수 저장

```bash
gcloud secrets create semrush-api-key --data-file=- <<< "your-semrush-api-key"
gcloud secrets create semrush-workspace-id --data-file=- <<< "your-workspace-id"
gcloud secrets create gcp-credential-json --data-file=path/to/sa-key.json
```

---

## 3. 컨테이너 빌드 + Artifact Registry 푸시

```bash
# Artifact Registry 저장소 생성 (1회)
gcloud artifacts repositories create geo-jobs \
  --repository-format=docker \
  --location=asia-northeast3

# 컨테이너 빌드·푸시 (Cloud Build 사용 — 로컬 Docker 불필요)
gcloud builds submit --tag \
  asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/geo-jobs/semrush-loader:latest
```

---

## 4. Cloud Run Job 생성

```bash
gcloud run jobs create semrush-loader \
  --image asia-northeast3-docker.pkg.dev/$GCP_PROJECT_ID/geo-jobs/semrush-loader:latest \
  --region asia-northeast3 \
  --service-account semrush-loader-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --max-retries 1 \
  --task-timeout 30m \
  --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,BQ_DATASET=semrush_data,SEMRUSH_DATABASE=us,TARGET_DOMAIN=lge.com" \
  --set-secrets "SEMRUSH_API_KEY=semrush-api-key:latest,SEMRUSH_WORKSPACE_ID=semrush-workspace-id:latest,GOOGLE_APPLICATION_CREDENTIAL_JSON=gcp-credential-json:latest" \
  --args "--days,1"
```

`--args "--days,1"`: 매일 실행하므로 1일치만 수집. 초기 백필은 `--days,30` 등으로 1회 수동 실행.

---

## 5. Cloud Scheduler 트리거 (매일 새벽 4시 KST)

```bash
gcloud scheduler jobs create http semrush-loader-daily \
  --location asia-northeast3 \
  --schedule "0 4 * * *" \
  --time-zone "Asia/Seoul" \
  --uri "https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$GCP_PROJECT_ID/jobs/semrush-loader:run" \
  --http-method POST \
  --oauth-service-account-email semrush-loader-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com
```

---

## 6. 첫 실행 (수동 트리거)

```bash
# 1일치 — 정상 동작 확인용
gcloud run jobs execute semrush-loader --region asia-northeast3 --wait

# 백필 30일치 (선택, 초기 데이터 채우기)
gcloud run jobs execute semrush-loader --region asia-northeast3 \
  --args "--days,30" --wait
```

실행 결과는 `gcloud run jobs executions describe ...`로 확인. exit code:
- `0`: 성공
- `2`: 부분 실패 (일부 모델만 적재됨, 알림 권장)
- `1`: 전체 실패 (작업 즉시 점검 필요)

---

## 7. 알림 (Cloud Monitoring)

콘솔 → Monitoring → Alerting:
- 메트릭: `run.googleapis.com/job/completed_execution_count` `result=failed`
- 채널: Outlook 이메일 (`§4.6`) 또는 Teams Webhook

---

## 8. 본 레포(`my-geo-newsletter`)의 reader 연결

`routes/bridge.js`(`@google-cloud/bigquery` 사용)가 동일 데이터셋 read-only 권한으로 조회. 해당 서비스 계정은 별도 — `BigQuery Data Viewer` + `BigQuery Job User` 만 부여.

---

## 트러블슈팅

| 증상 | 원인 후보 | 처리 |
|---|---|---|
| `SEMRUSH_API_KEY가 설정되지 않았습니다` | Secret 미바인딩 | `gcloud run jobs describe semrush-loader`로 환경변수 확인 |
| `403 Forbidden` (BQ) | 서비스 계정 권한 부족 | IAM 콘솔에서 데이터셋 접근 확인 |
| 적재 행 수 0 | SEMrush 응답 비어있음 | UI에서 "Generate API Request" 결과 확인 |
| Cloud Build 실패 | Dockerfile 오류 | 로컬 `docker build .` 재현 |
| 한국 timezone 어긋남 | Scheduler tz 미설정 | `--time-zone "Asia/Seoul"` 확인 |

---

*v1.0 · 2026-05-02 — Cloud Run Job 초기 배포 가이드*
