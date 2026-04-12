"""AI Visibility 데이터 수집 & 조회"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import GCP_PROJECT_ID, BQ_DATASET

st.set_page_config(page_title="AI Visibility", page_icon="🤖", layout="wide")
st.title("🤖 AI Visibility")

@st.cache_resource
def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

@st.cache_resource
def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

DATASET = f"{GCP_PROJECT_ID}.{BQ_DATASET}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 데이터 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("## 데이터 수집")

client = get_client()

col1, col2, col3 = st.columns(3)
with col1:
    brand = st.text_input("브랜드", value="LG")
with col2:
    today = datetime.now().date()
    start_date = st.date_input("시작일", value=today - timedelta(days=6))
with col3:
    end_date = st.date_input("종료일", value=today)

models = st.multiselect(
    "AI 모델 선택",
    client.AI_MODELS,
    default=["search-gpt", "perplexity", "gpt-5", "gemini-2.5-flash"],
)

days = (end_date - start_date).days + 1
total_calls = days * len(models)
est_time = total_calls * 4.5 / 60

st.caption(f"예상: {days}일 x {len(models)}모델 = **{total_calls}회 호출** (약 {est_time:.1f}분)")

col_fetch, col_save = st.columns(2)

with col_fetch:
    if st.button("🚀 데이터 수집", type="primary", disabled=not models):
        all_frames = []
        progress = st.progress(0)
        status = st.empty()

        for i, model in enumerate(models):
            status.text(f"{model} 수집 중... ({i+1}/{len(models)})")
            try:
                df = client.fetch_ai_visibility(
                    model=model,
                    brand=brand,
                    date_range=(start_date.strftime("%Y-%m-%d"),
                                end_date.strftime("%Y-%m-%d")),
                )
                if not df.empty:
                    all_frames.append(df)
            except Exception as e:
                st.warning(f"{model} 수집 실패: {e}")
            progress.progress((i + 1) / len(models))

        if all_frames:
            result_df = pd.concat(all_frames, ignore_index=True)
            st.session_state["collected_df"] = result_df
            status.empty()
            progress.empty()
            st.success(f"수집 완료! {len(result_df):,}행 ({len(all_frames)}개 모델)")
        else:
            st.error("수집된 데이터가 없습니다.")

with col_save:
    if st.button("💾 BigQuery에 저장", type="primary"):
        if "collected_df" not in st.session_state:
            st.warning("먼저 데이터를 수집하세요.")
        else:
            try:
                loader = get_loader()
                df = st.session_state["collected_df"]
                with st.spinner("저장 중..."):
                    result = loader.load_dataframe(df, "ai_visibility")
                st.success(f"저장 완료! {result['rows']:,}행 (총 {result.get('total_rows', '?'):,}행)")
            except Exception as e:
                st.error(f"저장 실패: {e}")

# 수집 결과 미리보기
if "collected_df" in st.session_state:
    df = st.session_state["collected_df"]
    st.markdown("---")
    st.markdown("### 수집 결과 미리보기")

    from chart_utils import metric_cards
    metric_cards([
        {"label": "총 행 수", "value": len(df),
         "display": f"{len(df):,}", "delta": None, "color": "#6366f1"},
        {"label": "모델 수", "value": df["model"].nunique(),
         "display": str(df["model"].nunique()), "delta": None, "color": "#3b82f6"},
        {"label": "일수", "value": df["date"].nunique(),
         "display": str(df["date"].nunique()), "delta": None, "color": "#22c55e"},
        {"label": "평균 Visibility", "value": df["visibility"].mean(),
         "display": f"{df['visibility'].mean():.3f}", "delta": None, "color": "#f59e0b"},
    ])

    st.markdown("")
    tab_preview, tab_model, tab_csv = st.tabs(["데이터 미리보기", "모델별 요약", "CSV 다운로드"])

    with tab_preview:
        st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    with tab_model:
        summary = df.groupby("model").agg(
            rows=("tag", "count"),
            avg_visibility=("visibility", "mean"),
            avg_sov=("sov", "mean"),
            avg_position=("avg_position", "mean"),
            total_mentions=("mentions", "sum"),
        ).round(4).reset_index()
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab_csv:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV 다운로드", csv, "ai_visibility.csv", "text/csv")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. BigQuery 저장 데이터 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown("## BigQuery 저장 데이터 조회")

col1, col2 = st.columns(2)
with col1:
    q_model = st.selectbox("모델 필터", ["전체"] + client.AI_MODELS)
with col2:
    q_limit = st.slider("조회 행 수", 50, 5000, 500)

if st.button("🔍 조회", type="primary"):
    try:
        loader = get_loader()
        where = ""
        if q_model != "전체":
            where = f"WHERE model = '{q_model}'"
        sql = f"""
            SELECT * FROM `{DATASET}.ai_visibility`
            {where}
            ORDER BY date DESC, model, tag
            LIMIT {q_limit}
        """
        with st.spinner("조회 중..."):
            bq_df = loader.query(sql)
        st.session_state["bq_result"] = bq_df
        st.success(f"{len(bq_df):,}행 조회")
    except Exception as e:
        st.error(f"조회 실패: {e}")

if "bq_result" in st.session_state:
    bq_df = st.session_state["bq_result"]
    st.dataframe(bq_df, use_container_width=True, hide_index=True)
    csv = bq_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 BigQuery 결과 CSV", csv, "bq_ai_visibility.csv", "text/csv")
