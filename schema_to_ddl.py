"""스키마 JSON → BigQuery DDL/SELECT 변환

용도:
- latest schema JSON을 받아 CREATE TABLE 문 생성
- (선택) 변환 쿼리 (L1_report_visibility = L1_visibility ⨝ L0_Raw_prompt_master) 템플릿 생성
"""
from __future__ import annotations

# ─── BigQuery 타입 정규화 ────────────────────────────────────────
# 원천 시트엔 bigint/varchar/integer/decimal(5,2) 등 표준 SQL 타입이 적혀있어
# BigQuery 표준으로 매핑.
_BQ_TYPE_MAP = {
    "BIGINT": "INT64",
    "INT": "INT64",
    "INTEGER": "INT64",
    "INT64": "INT64",
    "VARCHAR": "STRING",
    "TEXT": "STRING",
    "STRING": "STRING",
    "DATE": "DATE",
    "DATETIME": "DATETIME",
    "TIMESTAMP": "TIMESTAMP",
    "BOOL": "BOOL",
    "BOOLEAN": "BOOL",
    "FLOAT": "FLOAT64",
    "FLOAT64": "FLOAT64",
    "DOUBLE": "FLOAT64",
    "DECIMAL": "NUMERIC",
    "NUMERIC": "NUMERIC",
}


def normalize_bq_type(bq_type: str | None, precision: str | None = None, scale: str | None = None) -> str:
    if not bq_type:
        return "STRING"
    t = str(bq_type).strip().upper()
    # decimal(5,2) 같은 형식 처리
    if t.startswith("DECIMAL") or t.startswith("NUMERIC"):
        if precision and scale:
            return f"NUMERIC({precision}, {scale})"
        return "NUMERIC"
    return _BQ_TYPE_MAP.get(t, t)


def column_to_ddl_line(col: dict) -> str:
    """단일 컬럼 → DDL 한 줄."""
    name = col["name"]
    bq_type = normalize_bq_type(col.get("bq_type"), col.get("bq_precision"), col.get("bq_scale"))
    nullable = col.get("nullable", "Y")
    null_clause = "" if nullable == "Y" else " NOT NULL"
    desc = (col.get("description") or "").replace('"', '\\"').replace("\n", " ")
    options = f' OPTIONS(description="{desc}")' if desc else ""
    return f"  `{name}` {bq_type}{null_clause}{options}"


def schema_to_create_table(schema: dict, *, if_not_exists: bool = True,
                            partition_by: str = None, cluster_by: list[str] = None) -> str:
    """스키마 JSON → BigQuery CREATE TABLE DDL."""
    dataset = schema["dataset"]
    table = schema["table"]
    cols = schema.get("columns", [])
    if not cols:
        return f"-- {dataset}.{table}: 컬럼 미정의 (PIC가 schema_learning에서 채워주세요)\n"

    fq = f"`{dataset.replace('-', '-')}.{table}`"  # backtick for hyphenated project
    head = f"CREATE TABLE{' IF NOT EXISTS' if if_not_exists else ''} {fq}"
    cols_ddl = ",\n".join(column_to_ddl_line(c) for c in cols)
    body = f"(\n{cols_ddl}\n)"

    extras = []
    if partition_by:
        extras.append(f"PARTITION BY {partition_by}")
    if cluster_by:
        extras.append(f"CLUSTER BY {', '.join(f'`{c}`' for c in cluster_by)}")

    table_desc = schema.get("note") or f"{table} — {dataset}"
    extras.append(f'OPTIONS(description="{table_desc[:1000]}")')

    return head + "\n" + body + "\n" + "\n".join(extras) + ";\n"


def schema_to_select_star(schema: dict, limit: int = 100) -> str:
    """확인용 SELECT * (limit)."""
    fq = f"`{schema['dataset']}.{schema['table']}`"
    return f"SELECT * FROM {fq}\nORDER BY _loaded_at DESC, 1 ASC\nLIMIT {limit};\n"


def schema_to_describe(schema: dict) -> str:
    """INFORMATION_SCHEMA 조회 (실제 BQ 컬럼 vs 등록된 컬럼 대조)."""
    ds = schema["dataset"]
    project, dataset_only = ds.split(".", 1) if "." in ds else (ds, "")
    return (
        f"SELECT column_name, data_type, is_nullable, description\n"
        f"FROM `{project}.{dataset_only}.INFORMATION_SCHEMA.COLUMNS`\n"
        f"WHERE table_name = '{schema['table']}'\n"
        f"ORDER BY ordinal_position;\n"
    )


# ─── 변환 쿼리: L1_report_visibility = L1_visibility ⨝ L0_Raw_prompt_master ─
def build_L1_report_visibility_query(*,
                                  visibility_table: str = "L1_visibility",
                                  prompt_master_table: str = "L0_Raw_prompt_master",
                                  dataset: str = "pj-my-geo.semrush_data") -> str:
    """시트 §4.3 L1_report_visibility 생성 쿼리 템플릿.

    Group By 기준: start_date, end_date, cntr, ctg, bns, brand
    visibility = AVG(visibility) %
    div/ctg/stt/bns는 L0_Raw_prompt_master에서 prompt_id+cntr 조인으로 가져옴.

    ※ L0_Raw_prompt_master에 div/ctg/stt/bns 컬럼이 없으면 prompt_id에서 SUBSTR로 파싱해야 함.
    아래 템플릿은 L0_Raw_prompt_master에 컬럼이 있다고 가정 — PIC가 실 스키마에 맞춰 조정 필요.
    """
    fq_v = f"`{dataset}.{visibility_table}`"
    fq_pm = f"`{dataset}.{prompt_master_table}`"
    return f"""-- L1_report_visibility 생성 (시트 §4.3 변환 규칙)
-- Group By: start_date, end_date, cntr, ctg, bns, brand
-- visibility = AVG(visibility) %
-- ⚠️ L0_Raw_prompt_master.div/ctg/stt/bns가 실재 컬럼인지 확인 필요.
--    없으면 prompt_id에서 SUBSTR(prompt_id, 4, 2) 등으로 파싱.

WITH joined AS (
  SELECT
    v.start_date,
    v.end_date,
    v.cntr,
    pm.div,
    pm.ctg,
    pm.stt,
    pm.bns,
    v.brand,
    SAFE_CAST(v.visibility AS FLOAT64) AS visibility_num
  FROM {fq_v} v
  LEFT JOIN {fq_pm} pm
    ON pm.prompt_id = v.prompt_id
   AND pm.cntr = v.cntr
)
SELECT
  ROW_NUMBER() OVER (ORDER BY start_date, end_date, cntr, ctg, bns, brand) AS id,
  start_date,
  end_date,
  cntr,
  div,
  ctg,
  stt,
  bns,
  brand,
  ROUND(AVG(visibility_num), 2) AS visibility
FROM joined
WHERE visibility_num IS NOT NULL
GROUP BY start_date, end_date, cntr, div, ctg, stt, bns, brand
ORDER BY start_date DESC, cntr, brand;
"""


def parse_prompt_id_sql(prompt_id_col: str = "prompt_id") -> str:
    """prompt_id에서 14자리 분해 SQL (SUBSTR 기반).

    예: '1UKHSDWLNC0070' → workspace=1, cntr=UK, div=HS, ctg=DW, stt=L, bns=N, cej=C, seq=0070
    """
    p = prompt_id_col
    return f"""-- prompt_id 분해 (14자리: 1+2+2+2+1+1+1+4)
SELECT
  SUBSTR({p}, 1, 1)  AS workspace,
  SUBSTR({p}, 2, 2)  AS cntr,
  SUBSTR({p}, 4, 2)  AS div,
  SUBSTR({p}, 6, 2)  AS ctg,
  SUBSTR({p}, 8, 1)  AS stt,
  SUBSTR({p}, 9, 1)  AS bns,
  SUBSTR({p}, 10, 1) AS cej,
  SUBSTR({p}, 11)    AS seq
FROM ...
"""
