import os
import atexit
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# GCP 서비스 계정 (Render 환경변수에서 JSON 문자열로 전달)
_gcp_creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if _gcp_creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    _tmp.write(_gcp_creds_json)
    _tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
    atexit.register(lambda: os.unlink(_tmp.name))

# SEMrush API
SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY")
SEMRUSH_BASE_URL = "https://api.semrush.com/"
SEMRUSH_PROJECTS_URL = "https://api.semrush.com/reports/v1/projects/"
SEMRUSH_LISTING_URL = "https://api.semrush.com/apis/v4-raw/listing-management/v1/external/"
SEMRUSH_DATABASE = os.getenv("SEMRUSH_DATABASE", "us")
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "example.com")

# SEMrush Enterprise - Project/Campaign IDs
SEMRUSH_PROJECT_ID = os.getenv("SEMRUSH_PROJECT_ID", "")
SEMRUSH_CAMPAIGN_ID = os.getenv("SEMRUSH_CAMPAIGN_ID", "")

# SEMrush Listing Management (OAuth)
SEMRUSH_LISTING_TOKEN = os.getenv("SEMRUSH_LISTING_TOKEN", "")

# BigQuery
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "semrush_data")
