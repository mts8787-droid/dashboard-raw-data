"""BigQuery 연결 설정 & 가이드 페이지"""

import os
import json
import tempfile
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ BigQuery 연결 설정")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1단계: BigQuery 연결 가이드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("## 1단계: GCP 프로젝트 & 서비스 계정 준비")

with st.expander("📖 상세 가이드 (처음 설정하는 경우 펼쳐서 읽어주세요)", expanded=False):
    st.markdown("""
### A. GCP 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 상단 프로젝트 선택 드롭다운 클릭 → **새 프로젝트** 클릭
3. 프로젝트 이름 입력 (예: `my-semrush-project`) → **만들기**
4. 생성 후 프로젝트 ID를 메모 (예: `my-semrush-project-12345`)

---

### B. BigQuery API 활성화

1. GCP Console 좌측 메뉴 → **API 및 서비스** → **라이브러리**
2. 검색창에 `BigQuery API` 입력
3. **BigQuery API** 클릭 → **사용 설정** 버튼 클릭

---

### C. 서비스 계정 생성 & JSON 키 발급

1. GCP Console 좌측 메뉴 → **IAM 및 관리자** → **서비스 계정**
2. **+ 서비스 계정 만들기** 클릭
3. 서비스 계정 정보 입력:
   - **이름**: `semrush-dashboard` (원하는 이름)
   - **ID**: 자동 생성됨
4. **만들고 계속** 클릭
5. 역할(Role) 부여:
   - **BigQuery 데이터 편집자** (`roles/bigquery.dataEditor`)
   - **BigQuery 작업 사용자** (`roles/bigquery.jobUser`)
   - 두 역할 모두 추가해야 합니다
6. **완료** 클릭
7. 생성된 서비스 계정 클릭 → **키** 탭 → **키 추가** → **새 키 만들기**
8. **JSON** 선택 → **만들기** → JSON 파일이 자동 다운로드됩니다

> 다운로드된 JSON 파일이 **서비스 계정 키**입니다.
> 이 파일을 아래 2단계에서 업로드하세요.

---

### D. BigQuery 데이터셋 (선택)

데이터셋은 앱이 자동으로 생성하지만, 미리 만들고 싶다면:

1. [BigQuery Console](https://console.cloud.google.com/bigquery) 접속
2. 프로젝트 옆 **⋮** → **데이터 세트 만들기**
3. 데이터셋 ID: `semrush_data` (아래 설정과 동일하게)
4. 위치: `US` (기본값)
""")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2단계: 연결 정보 입력
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown("## 2단계: 연결 정보 입력")

# 현재 설정 상태 로드
from config import GCP_PROJECT_ID, BQ_DATASET

tab_upload, tab_json, tab_env = st.tabs([
    "📁 JSON 파일 업로드",
    "📋 JSON 직접 붙여넣기",
    "🔧 .env 파일 수동 설정",
])

# ── 탭 1: 파일 업로드 ──
with tab_upload:
    st.markdown("서비스 계정 키 JSON 파일을 업로드하세요.")

    uploaded_file = st.file_uploader(
        "서비스 계정 키 (.json)",
        type=["json"],
        help="GCP Console에서 다운로드한 서비스 계정 키 JSON 파일",
    )

    col1, col2 = st.columns(2)
    with col1:
        gcp_project_upload = st.text_input(
            "GCP 프로젝트 ID",
            value=GCP_PROJECT_ID or "",
            help="GCP Console 상단에서 확인 가능 (예: my-project-12345)",
            key="project_upload",
        )
    with col2:
        bq_dataset_upload = st.text_input(
            "BigQuery 데이터셋 이름",
            value=BQ_DATASET or "semrush_data",
            help="데이터가 저장될 BigQuery 데이터셋 (없으면 자동 생성)",
            key="dataset_upload",
        )

    if uploaded_file is not None:
        try:
            creds_data = json.loads(uploaded_file.read().decode("utf-8"))
            uploaded_file.seek(0)

            # JSON 내용 미리보기
            with st.expander("업로드된 키 정보 확인"):
                safe_info = {
                    "type": creds_data.get("type"),
                    "project_id": creds_data.get("project_id"),
                    "client_email": creds_data.get("client_email"),
                    "token_uri": creds_data.get("token_uri"),
                }
                st.json(safe_info)

            # 프로젝트 ID 자동 채우기
            if not gcp_project_upload and creds_data.get("project_id"):
                gcp_project_upload = creds_data["project_id"]
                st.info(f"프로젝트 ID가 JSON에서 자동 감지되었습니다: `{gcp_project_upload}`")

        except json.JSONDecodeError:
            st.error("유효한 JSON 파일이 아닙니다.")
            creds_data = None

    if st.button("🔗 BigQuery 연결 테스트", type="primary", key="test_upload"):
        if uploaded_file is None:
            st.warning("먼저 서비스 계정 키 파일을 업로드하세요.")
        elif not gcp_project_upload:
            st.warning("GCP 프로젝트 ID를 입력하세요.")
        else:
            try:
                # 임시 파일로 저장 후 연결
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                )
                uploaded_file.seek(0)
                tmp.write(uploaded_file.read().decode("utf-8"))
                tmp.close()

                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
                os.environ["GCP_PROJECT_ID"] = gcp_project_upload
                os.environ["BQ_DATASET"] = bq_dataset_upload

                from google.cloud import bigquery
                client = bigquery.Client(project=gcp_project_upload)

                # 데이터셋 확인/생성
                dataset_ref = f"{gcp_project_upload}.{bq_dataset_upload}"
                try:
                    client.get_dataset(dataset_ref)
                    dataset_status = "기존 데이터셋 확인됨"
                except Exception:
                    dataset = bigquery.Dataset(dataset_ref)
                    dataset.location = "US"
                    client.create_dataset(dataset)
                    dataset_status = "새 데이터셋 생성됨"

                st.success(f"BigQuery 연결 성공! ({dataset_status})")

                # 연결 정보를 세션에 저장
                st.session_state["bq_connected"] = True
                st.session_state["gcp_project_id"] = gcp_project_upload
                st.session_state["bq_dataset"] = bq_dataset_upload

                # BigQueryLoader 캐시 초기화
                if "get_loader" in st.session_state:
                    del st.session_state["get_loader"]

                st.info(
                    "연결 설정이 현재 세션에 적용되었습니다.\n\n"
                    "**영구 저장하려면** 아래 `.env 파일 수동 설정` 탭을 참고하세요."
                )
            except Exception as e:
                st.error(f"연결 실패: {e}")

# ── 탭 2: JSON 직접 붙여넣기 ──
with tab_json:
    st.markdown("서비스 계정 키 JSON 내용을 직접 붙여넣으세요.")
    st.markdown("*(Render 등 클라우드 배포 시 환경변수로 전달할 때 유용)*")

    creds_json_input = st.text_area(
        "서비스 계정 키 JSON",
        height=200,
        placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}',
        help="JSON 파일의 전체 내용을 붙여넣으세요",
    )

    col1, col2 = st.columns(2)
    with col1:
        gcp_project_json = st.text_input(
            "GCP 프로젝트 ID",
            value=GCP_PROJECT_ID or "",
            key="project_json",
        )
    with col2:
        bq_dataset_json = st.text_input(
            "BigQuery 데이터셋 이름",
            value=BQ_DATASET or "semrush_data",
            key="dataset_json",
        )

    if st.button("🔗 BigQuery 연결 테스트", type="primary", key="test_json"):
        if not creds_json_input.strip():
            st.warning("JSON 내용을 붙여넣으세요.")
        else:
            try:
                # JSON 유효성 검증
                creds_data = json.loads(creds_json_input)

                if not gcp_project_json and creds_data.get("project_id"):
                    gcp_project_json = creds_data["project_id"]

                if not gcp_project_json:
                    st.warning("GCP 프로젝트 ID를 입력하세요.")
                else:
                    # 임시 파일로 저장
                    tmp = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    )
                    tmp.write(creds_json_input)
                    tmp.close()

                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
                    os.environ["GCP_PROJECT_ID"] = gcp_project_json
                    os.environ["BQ_DATASET"] = bq_dataset_json

                    from google.cloud import bigquery
                    client = bigquery.Client(project=gcp_project_json)

                    dataset_ref = f"{gcp_project_json}.{bq_dataset_json}"
                    try:
                        client.get_dataset(dataset_ref)
                        dataset_status = "기존 데이터셋 확인됨"
                    except Exception:
                        dataset = bigquery.Dataset(dataset_ref)
                        dataset.location = "US"
                        client.create_dataset(dataset)
                        dataset_status = "새 데이터셋 생성됨"

                    st.success(f"BigQuery 연결 성공! ({dataset_status})")
                    st.session_state["bq_connected"] = True
                    st.session_state["gcp_project_id"] = gcp_project_json
                    st.session_state["bq_dataset"] = bq_dataset_json

                    st.info(
                        "연결 설정이 현재 세션에 적용되었습니다.\n\n"
                        "**Render 배포 시** 환경변수 `GOOGLE_APPLICATION_CREDENTIALS_JSON`에 "
                        "이 JSON 내용을 그대로 넣으면 됩니다."
                    )
            except json.JSONDecodeError:
                st.error("유효한 JSON 형식이 아닙니다. 형식을 확인해주세요.")
            except Exception as e:
                st.error(f"연결 실패: {e}")

# ── 탭 3: .env 파일 수동 설정 ──
with tab_env:
    st.markdown("`.env` 파일을 직접 편집하여 영구 설정하는 방법입니다.")

    st.code("""# .env 파일 예시

# Google Cloud / BigQuery
GCP_PROJECT_ID=your-gcp-project-id
BQ_DATASET=semrush_data

# 방법 A: 로컬 - JSON 파일 경로 지정
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 방법 B: Render 등 클라우드 - JSON 문자열 직접 입력
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"...","private_key":"...","client_email":"...","token_uri":"..."}
""", language="bash")

    st.markdown("""
**설정 후 앱을 재시작하면 자동으로 적용됩니다.**

```bash
# 로컬 실행
streamlit run app.py
```
""")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3단계: 연결 상태 확인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown("## 3단계: 현재 연결 상태")

col1, col2, col3 = st.columns(3)

current_project = os.getenv("GCP_PROJECT_ID", "")
current_dataset = os.getenv("BQ_DATASET", "semrush_data")
has_creds_file = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
has_creds_json = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
session_connected = st.session_state.get("bq_connected", False)

with col1:
    if current_project:
        st.success(f"GCP 프로젝트: `{current_project}`")
    else:
        st.error("GCP 프로젝트 ID 미설정")

with col2:
    st.info(f"데이터셋: `{current_dataset}`")

with col3:
    if has_creds_file:
        st.success("인증: JSON 파일 경로")
    elif has_creds_json:
        st.success("인증: JSON 환경변수")
    elif session_connected:
        st.success("인증: 세션 내 설정됨")
    else:
        st.error("인증 정보 미설정")

# 연결 테스트 버튼
if st.button("🔍 전체 연결 상태 진단"):
    results = []

    # GCP 인증
    try:
        from google.cloud import bigquery
        project = os.getenv("GCP_PROJECT_ID")
        if not project:
            results.append(("GCP 프로젝트 ID", "❌", "환경변수 GCP_PROJECT_ID가 비어 있습니다"))
        else:
            results.append(("GCP 프로젝트 ID", "✅", project))
    except ImportError:
        results.append(("google-cloud-bigquery", "❌", "패키지가 설치되지 않았습니다"))

    # 인증 파일
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        results.append(("서비스 계정 키", "✅", f"파일 확인됨: {creds_path}"))
    elif creds_path:
        results.append(("서비스 계정 키", "❌", f"파일 없음: {creds_path}"))
    elif has_creds_json:
        results.append(("서비스 계정 키", "✅", "환경변수에서 JSON 로드됨"))
    else:
        results.append(("서비스 계정 키", "❌", "GOOGLE_APPLICATION_CREDENTIALS 미설정"))

    # BigQuery 연결
    try:
        from google.cloud import bigquery
        project = os.getenv("GCP_PROJECT_ID")
        if project:
            client = bigquery.Client(project=project)
            dataset_ref = f"{project}.{current_dataset}"
            try:
                ds = client.get_dataset(dataset_ref)
                table_count = sum(1 for _ in client.list_tables(dataset_ref))
                results.append(("BigQuery 연결", "✅", f"데이터셋 확인됨 (테이블 {table_count}개)"))
            except Exception:
                results.append(("BigQuery 연결", "⚠️", "인증은 성공했으나 데이터셋이 없습니다 (자동 생성 가능)"))
        else:
            results.append(("BigQuery 연결", "⏭️", "프로젝트 ID 설정 후 테스트 가능"))
    except Exception as e:
        results.append(("BigQuery 연결", "❌", str(e)))

    # 결과 표시
    for name, status, detail in results:
        st.markdown(f"{status} **{name}** — {detail}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEMrush 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown("## SEMrush API 설정")

from config import (
    SEMRUSH_API_KEY, SEMRUSH_PROJECT_ID, SEMRUSH_CAMPAIGN_ID,
    SEMRUSH_LISTING_TOKEN, SEMRUSH_DATABASE, TARGET_DOMAIN,
)

with st.form("semrush_settings"):
    st.markdown("현재 세션에서 SEMrush 설정을 변경할 수 있습니다.")

    col1, col2 = st.columns(2)
    with col1:
        new_api_key = st.text_input(
            "SEMrush API Key",
            value=SEMRUSH_API_KEY or "",
            type="password",
            help="SEMrush 계정 > Subscription Info에서 확인",
        )
        new_project_id = st.text_input(
            "Project ID",
            value=SEMRUSH_PROJECT_ID or "",
            help="SEMrush Projects 페이지 URL에서 확인 (숫자)",
        )
        new_campaign_id = st.text_input(
            "Campaign ID",
            value=SEMRUSH_CAMPAIGN_ID or "",
            help="Position Tracking 캠페인 ID (예: 6647718_272401)",
        )
    with col2:
        new_listing_token = st.text_input(
            "Listing Management Token",
            value=SEMRUSH_LISTING_TOKEN or "",
            type="password",
            help="Listing Management OAuth Bearer Token",
        )
        new_database = st.text_input(
            "SEMrush Database",
            value=SEMRUSH_DATABASE or "us",
            help="국가 DB 코드 (us, kr, jp, uk 등)",
        )
        new_domain = st.text_input(
            "Target Domain",
            value=TARGET_DOMAIN or "",
            help="분석 대상 도메인 (예: example.com)",
        )

    submitted = st.form_submit_button("💾 세션에 설정 적용", type="primary")

    if submitted:
        env_updates = {
            "SEMRUSH_API_KEY": new_api_key,
            "SEMRUSH_PROJECT_ID": new_project_id,
            "SEMRUSH_CAMPAIGN_ID": new_campaign_id,
            "SEMRUSH_LISTING_TOKEN": new_listing_token,
            "SEMRUSH_DATABASE": new_database,
            "TARGET_DOMAIN": new_domain,
        }
        for key, val in env_updates.items():
            if val:
                os.environ[key] = val

        # cache_resource 초기화 (새 설정으로 클라이언트 재생성)
        st.cache_resource.clear()

        st.success("설정이 현재 세션에 적용되었습니다.")
        st.info("영구 저장하려면 `.env` 파일을 직접 수정하세요.")
