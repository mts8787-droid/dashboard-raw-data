"""BigQuery 데이터 관리 페이지"""

import streamlit as st
import pandas as pd
from config import GCP_PROJECT_ID, BQ_DATASET

st.set_page_config(page_title="BigQuery 관리", page_icon="🗄️", layout="wide")
st.title("🗄️ BigQuery 데이터 관리")

@st.cache_resource
def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

# ── 테이블 현황 ──
st.markdown("## 테이블 현황")

if st.button("🔄 테이블 목록 새로고침", type="primary"):
    try:
        loader = get_loader()
        tables = loader.get_table_info()
        st.session_state["bq_tables"] = tables
    except Exception as e:
        st.error(f"에러: {e}")

if "bq_tables" in st.session_state:
    tables = st.session_state["bq_tables"]
    if tables:
        df = pd.DataFrame(tables)
        st.dataframe(df, use_container_width=True)

        # 요약 메트릭
        from chart_utils import metric_cards

        total_rows = sum(t.get("num_rows", 0) for t in tables)
        total_size = sum(t.get("size_mb", 0) for t in tables)

        metric_cards([
            {"label": "총 테이블 수", "value": len(tables), "display": str(len(tables)),
             "delta": None, "color": "#6366f1"},
            {"label": "총 행 수", "value": total_rows, "display": f"{total_rows:,}",
             "delta": None, "color": "#3b82f6"},
            {"label": "총 크기", "value": total_size, "display": f"{total_size:.1f}", "suffix": " MB",
             "delta": None, "color": "#8b5cf6"},
        ])
    else:
        st.info("아직 생성된 테이블이 없습니다.")

# ── SQL 쿼리 ──
st.markdown("---")
st.markdown("## SQL 쿼리")

dataset = f"{GCP_PROJECT_ID}.{BQ_DATASET}" if GCP_PROJECT_ID else "project.dataset"

default_query = f"SELECT * FROM `{dataset}.domain_overview` ORDER BY _loaded_at DESC LIMIT 100"
query = st.text_area("SQL 쿼리", value=default_query, height=120)

if st.button("▶️ 쿼리 실행", type="primary"):
    try:
        loader = get_loader()
        with st.spinner("쿼리 실행 중..."):
            df = loader.query(query)
        st.session_state["query_result"] = df
        st.success(f"{len(df)}행 반환")
    except Exception as e:
        st.error(f"쿼리 실패: {e}")

if "query_result" in st.session_state:
    df = st.session_state["query_result"]
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 결과 CSV 다운로드", csv, "query_result.csv", "text/csv")

# ── 빠른 조회 ──
st.markdown("---")
st.markdown("## 빠른 테이블 조회")

table_options = [
    "visibility_index", "position_tracking", "site_audit", "citations",
    "domain_overview", "domain_organic_keywords", "domain_adwords_keywords",
    "backlinks_overview", "organic_competitors",
]
selected_table = st.selectbox("테이블 선택", table_options)
row_limit = st.slider("조회 행 수", 10, 1000, 100)

if st.button("🔍 조회"):
    table_id = f"`{GCP_PROJECT_ID}.{BQ_DATASET}.{selected_table}`"
    sql = f"SELECT * FROM {table_id} ORDER BY _loaded_at DESC LIMIT {row_limit}"
    try:
        loader = get_loader()
        with st.spinner("조회 중..."):
            df = loader.query(sql)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")
    except Exception as e:
        st.error(f"조회 실패: {e}")
