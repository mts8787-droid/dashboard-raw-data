"""BigQuery 데이터 로더 - SEMrush Enterprise 데이터를 BigQuery에 저장"""

from datetime import datetime
import pandas as pd
from google.cloud import bigquery
from config import GCP_PROJECT_ID, BQ_DATASET


class BigQueryLoader:
    # 엔터프라이즈 테이블 정의
    TABLES = {
        # Position Tracking / Visibility
        "visibility_index": "Visibility Index 추이",
        "position_tracking": "키워드 순위 추적",
        # Site Audit
        "site_audit": "사이트 건강도 스냅샷",
        # Listing / Citations
        "citations": "로컬 Citation/리스팅 데이터",
        # Analytics (기본)
        "domain_overview": "도메인 개요",
        "domain_organic_keywords": "오가닉 키워드",
        "domain_adwords_keywords": "유료 키워드",
        "backlinks_overview": "백링크 개요",
        "organic_competitors": "오가닉 경쟁사",
    }

    def __init__(self, project_id=None, dataset_id=None):
        self.project_id = project_id or GCP_PROJECT_ID
        self.dataset_id = dataset_id or BQ_DATASET
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID가 설정되지 않았습니다.")
        self.client = bigquery.Client(project=self.project_id)
        self._ensure_dataset()

    def _ensure_dataset(self):
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        try:
            self.client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset)

    def _full_table_id(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_name}"

    def load_dataframe(self, df: pd.DataFrame, table_name: str,
                       write_mode: str = "WRITE_APPEND") -> dict:
        """DataFrame을 BigQuery 테이블에 저장. 결과 dict 반환."""
        result = {"table": table_name, "rows": 0, "status": "skipped"}

        if df is None or df.empty:
            return result

        df = df.copy()
        df["_loaded_at"] = datetime.utcnow().isoformat()
        df["_source"] = "semrush_enterprise"

        table_id = self._full_table_id(table_name)
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_mode,
            autodetect=True,
        )
        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()

        table = self.client.get_table(table_id)
        result["rows"] = len(df)
        result["total_rows"] = table.num_rows
        result["status"] = "success"
        return result

    def get_table_info(self) -> list:
        """모든 테이블의 현재 상태 조회"""
        tables = []
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        try:
            for table_item in self.client.list_tables(dataset_ref):
                table = self.client.get_table(table_item.reference)
                tables.append({
                    "table_name": table.table_id,
                    "description": self.TABLES.get(table.table_id, ""),
                    "num_rows": table.num_rows,
                    "size_mb": round(table.num_bytes / (1024 * 1024), 2) if table.num_bytes else 0,
                    "last_modified": table.modified.isoformat() if table.modified else None,
                })
        except Exception:
            pass
        return tables

    def query(self, sql: str) -> pd.DataFrame:
        """임의 SQL 쿼리 실행"""
        return self.client.query(sql).to_dataframe()
