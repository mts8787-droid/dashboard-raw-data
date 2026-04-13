import os
import atexit
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# GCP 서비스 계정 (Render 환경변수에서 JSON 문자열로 전달)
_gcp_creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if _gcp_creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    # Render가 줄바꿈을 제거하거나 이스케이프할 수 있으므로 정리
    _gcp_creds_json = _gcp_creds_json.strip()
    # JSON 유효성 검증
    try:
        json.loads(_gcp_creds_json)
    except json.JSONDecodeError:
        # 이스케이프된 줄바꿈 복원 시도
        _gcp_creds_json = _gcp_creds_json.replace("\\n", "\n")
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    _tmp.write(_gcp_creds_json)
    _tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
    atexit.register(lambda: os.unlink(_tmp.name))

# SEMrush Enterprise API
SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY")
SEMRUSH_ENTERPRISE_URL = "https://api.semrush.com/apis/v4-raw/external-api/v1"
SEMRUSH_WORKSPACE_ID = os.getenv("SEMRUSH_WORKSPACE_ID", "")
SEMRUSH_PROJECT_ID = os.getenv("SEMRUSH_PROJECT_ID", "")
SEMRUSH_DATABASE = os.getenv("SEMRUSH_DATABASE", "us")
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "example.com")

# BigQuery
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "semrush_data")
