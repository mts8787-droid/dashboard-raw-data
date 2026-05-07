"""BigQuery 데이터 로더 - SEMrush Enterprise 데이터를 BigQuery에 저장"""

import logging
from datetime import datetime, timezone
import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from config import GCP_PROJECT_ID, BQ_DATASET

logger = logging.getLogger(__name__)


class BigQueryLoader:
    # Enterprise Element API 테이블 정의
    TABLES = {
        "L0_Raw_visibility": "AI Visibility — 모델별 일별 브랜드 가시성",
    }

    # 명시적 스키마 정의 (autodetect 대체)
    SCHEMAS = {
        "L0_Raw_visibility": [
            bigquery.SchemaField("tag", "STRING"),
            bigquery.SchemaField("visibility", "FLOAT"),
            bigquery.SchemaField("sov", "FLOAT"),
            bigquery.SchemaField("avg_position", "FLOAT"),
            bigquery.SchemaField("mentions", "INTEGER"),
            bigquery.SchemaField("prompts", "INTEGER"),
            bigquery.SchemaField("prompts_mentioned", "FLOAT"),
            bigquery.SchemaField("unique_prompts", "INTEGER"),
            bigquery.SchemaField("model", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("_loaded_at", "STRING"),
            bigquery.SchemaField("_source", "STRING"),
        ],
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
        except NotFound:
            logger.info("데이터셋 %s 생성 중...", dataset_ref)
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset)

    def _full_table_id(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_name}"

    def _delete_existing(self, table_id: str, df: pd.DataFrame) -> int:
        """적재 전 동일 date+model 조합의 기존 행을 삭제하여 중복 방지."""
        if "date" not in df.columns or "model" not in df.columns:
            return 0

        dates = df["date"].dropna().unique().tolist()
        models = df["model"].dropna().unique().tolist()
        if not dates or not models:
            return 0

        date_list = ", ".join(f"'{d}'" for d in dates)
        model_list = ", ".join(f"'{m}'" for m in models)
        sql = (
            f"DELETE FROM `{table_id}` "
            f"WHERE date IN ({date_list}) AND model IN ({model_list})"
        )
        job = self.client.query(sql)
        job.result()
        deleted = job.num_dml_affected_rows or 0
        if deleted:
            logger.info("중복 제거: %s에서 %d행 삭제 (dates=%s, models=%s)",
                        table_id, deleted, dates, models)
        return deleted

    def load_dataframe(self, df: pd.DataFrame, table_name: str,
                       write_mode: str = "WRITE_APPEND") -> dict:
        """DataFrame을 BigQuery 테이블에 저장. 중복 date+model 데이터는 자동 교체."""
        result = {"table": table_name, "rows": 0, "status": "skipped"}

        if df is None or df.empty:
            return result

        df = df.copy()
        df["_loaded_at"] = datetime.now(timezone.utc).isoformat()
        df["_source"] = "semrush_enterprise"

        table_id = self._full_table_id(table_name)

        # 테이블이 존재하면 중복 행 삭제
        try:
            self.client.get_table(table_id)
            result["deleted"] = self._delete_existing(table_id, df)
        except NotFound:
            result["deleted"] = 0

        schema = self.SCHEMAS.get(table_name)
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_mode,
            schema=schema,
            autodetect=(schema is None),
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
        except Exception as e:
            logger.warning("테이블 목록 조회 실패: %s", e)
        return tables

    # 대시보드에서 허용하지 않는 SQL 키워드 (읽기 전용 보호)
    _BLOCKED_SQL = {"DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE", "MERGE",
                    "CREATE", "ALTER", "GRANT", "REVOKE"}

    def query(self, sql: str, max_bytes: int = 1_000_000_000) -> pd.DataFrame:
        """임의 SQL 쿼리 실행 (읽기 전용, 바이트 상한 적용)."""
        # 위험 키워드 차단
        first_token = sql.strip().split()[0].upper() if sql.strip() else ""
        if first_token in self._BLOCKED_SQL:
            raise ValueError(f"쓰기 쿼리는 허용되지 않습니다: {first_token}")

        # DRY_RUN 으로 예상 비용 확인
        dry_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        dry_job = self.client.query(sql, job_config=dry_config)
        estimated = dry_job.total_bytes_processed or 0
        if estimated > max_bytes:
            raise ValueError(
                f"쿼리 예상 스캔량 {estimated / 1e9:.2f} GB — "
                f"상한 {max_bytes / 1e9:.2f} GB 초과"
            )

        return self.client.query(sql).to_dataframe()
