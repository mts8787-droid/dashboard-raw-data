"""스키마 → DDL/쿼리 변환 페이지

저장된 latest schema JSON을 BigQuery DDL·확인용 SELECT·변환 쿼리로 변환.
PIC는 결과를 복사해 BigQuery 콘솔에서 실행.
"""

import streamlit as st
import schema_store
import schema_to_ddl

st.set_page_config(page_title="스키마 DDL", page_icon="🛠️", layout="wide")
st.title("🛠️ 스키마 → DDL/쿼리 변환")
st.caption("저장된 스키마에서 CREATE TABLE / SELECT / 변환 쿼리 자동 생성")


keys = schema_store.all_table_keys()
if not keys:
    st.info("저장된 스키마가 없습니다. **스키마 학습** 페이지에서 먼저 등록하세요.")
    st.stop()

options = [f"{ds}.{tb}" for ds, tb in keys]
selected = st.selectbox("테이블 선택", options)
ds, tb = selected.rsplit(".", 1)

schema = schema_store.load_latest(ds, tb)
if not schema:
    st.error("스키마 로드 실패")
    st.stop()

cols = schema.get("columns", [])
st.markdown(f"### `{selected}` — {len(cols)}개 컬럼")
if schema.get("note"):
    st.caption(f"메모: {schema['note']}")

if not cols:
    st.warning(
        "이 테이블은 빈 스켈레톤입니다 (컬럼 미정의). "
        "**스키마 학습** 페이지에서 BigQuery 실데이터를 학습해 컬럼을 등록한 뒤 다시 시도하세요."
    )
    st.stop()


# ─── DDL 옵션 ─────────────────────────────────────────────────────
st.markdown("### CREATE TABLE 옵션")
col1, col2 = st.columns(2)
with col1:
    if_not_exists = st.checkbox("IF NOT EXISTS", value=True)
    pb_options = ["(없음)"] + [c["name"] for c in cols if c.get("bq_type", "").upper() in {"DATE", "TIMESTAMP", "DATETIME"}]
    pb = st.selectbox("PARTITION BY", pb_options)
    partition_by = None if pb == "(없음)" else pb
with col2:
    cluster_choices = [c["name"] for c in cols if c.get("category", "").startswith("차원")]
    cluster_by = st.multiselect("CLUSTER BY", cluster_choices, max_selections=4)


# ─── DDL 출력 ─────────────────────────────────────────────────────
st.markdown("### 1) `CREATE TABLE` DDL")
ddl = schema_to_ddl.schema_to_create_table(
    schema, if_not_exists=if_not_exists,
    partition_by=partition_by, cluster_by=cluster_by or None,
)
st.code(ddl, language="sql")
st.download_button("⬇ DDL 다운로드", ddl, f"{tb}_create.sql", "text/plain")


# ─── 확인용 SELECT ────────────────────────────────────────────────
st.markdown("### 2) 확인용 `SELECT *`")
limit = st.slider("LIMIT", 10, 1000, 100, key="ddl_limit")
sel = schema_to_ddl.schema_to_select_star(schema, limit=limit)
st.code(sel, language="sql")


# ─── INFORMATION_SCHEMA 대조 ──────────────────────────────────────
st.markdown("### 3) 실제 BigQuery 컬럼 대조 (INFORMATION_SCHEMA)")
st.caption("등록된 스키마와 실 BigQuery 컬럼이 일치하는지 확인용")
desc_sql = schema_to_ddl.schema_to_describe(schema)
st.code(desc_sql, language="sql")


# ─── 변환 쿼리 (해당 테이블에 한정) ──────────────────────────────
st.markdown("### 4) 변환 쿼리 템플릿")
if tb == "report_visibility":
    st.markdown("**시트 §4.3 — `report_visibility = visibility ⨝ prompt_master`**")
    rv = schema_to_ddl.build_report_visibility_query(dataset=ds)
    st.code(rv, language="sql")
    st.download_button("⬇ 변환 쿼리 다운로드", rv, "report_visibility_query.sql", "text/plain")
    st.markdown("---")
    st.markdown("**prompt_id 14자리 분해 SQL (참고)**")
    st.code(schema_to_ddl.parse_prompt_id_sql(), language="sql")
elif tb in ("report_citation",):
    st.info(
        "report_citation 변환 쿼리는 `domain_mapping` 컬럼 정의가 확정된 후 추가 예정. "
        "시트엔 'Source 정제 + Domain 추출 + Scnd_depth 생성' 규칙만 명시되어 있어 컬럼명 확인 필요."
    )
else:
    st.caption("이 테이블에는 변환 쿼리 템플릿이 따로 없습니다 (원천·매핑 테이블).")


# ─── 원본 JSON ─────────────────────────────────────────────────────
with st.expander("스키마 원본 JSON"):
    st.json(schema, expanded=False)
