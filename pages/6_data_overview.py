"""AI Visibility 데이터 개요 — 스키마, 통계, 일별 추이"""

import streamlit as st
import pandas as pd
from config import GCP_PROJECT_ID, BQ_DATASET

st.set_page_config(page_title="Data Overview", page_icon="📋", layout="wide")
st.title("📋 Data Overview")

@st.cache_resource
def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

DATASET = f"{GCP_PROJECT_ID}.{BQ_DATASET}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 데이터 로드 (캐싱)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(ttl=300)
def load_overview():
    loader = get_loader()
    total = loader.query(f"SELECT COUNT(*) as cnt FROM `{DATASET}.ai_visibility`")
    return int(total["cnt"].iloc[0])

@st.cache_data(ttl=300)
def load_schema():
    loader = get_loader()
    return loader.query(f"""
        SELECT column_name, data_type, is_nullable
        FROM `{GCP_PROJECT_ID}.semrush_data.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = 'ai_visibility'
        ORDER BY ordinal_position
    """)

@st.cache_data(ttl=300)
def load_daily_stats():
    loader = get_loader()
    return loader.query(f"""
        SELECT
            model,
            date,
            COUNT(*) as tag_count,
            ROUND(AVG(visibility), 4) as avg_visibility,
            ROUND(AVG(sov), 4) as avg_sov,
            ROUND(AVG(avg_position), 2) as avg_position,
            SUM(mentions) as total_mentions,
            SUM(prompts) as total_prompts,
            SUM(prompts_mentioned) as total_prompts_mentioned,
            COUNT(DISTINCT tag) as unique_tags
        FROM `{DATASET}.ai_visibility`
        GROUP BY model, date
        ORDER BY model, date
    """)

@st.cache_data(ttl=300)
def load_model_summary():
    loader = get_loader()
    return loader.query(f"""
        SELECT
            model,
            COUNT(DISTINCT date) as days,
            COUNT(*) as total_rows,
            ROUND(AVG(visibility), 4) as avg_visibility,
            ROUND(AVG(sov), 4) as avg_sov,
            ROUND(AVG(avg_position), 2) as avg_position,
            ROUND(SUM(mentions) * 1.0 / COUNT(DISTINCT date), 0) as avg_daily_mentions,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM `{DATASET}.ai_visibility`
        GROUP BY model
        ORDER BY avg_visibility DESC
    """)

@st.cache_data(ttl=300)
def load_column_stats():
    loader = get_loader()
    return loader.query(f"""
        SELECT
            ROUND(AVG(visibility), 4) as avg_visibility,
            ROUND(MIN(visibility), 4) as min_visibility,
            ROUND(MAX(visibility), 4) as max_visibility,
            ROUND(AVG(sov), 4) as avg_sov,
            ROUND(MIN(sov), 4) as min_sov,
            ROUND(MAX(sov), 4) as max_sov,
            ROUND(AVG(avg_position), 2) as avg_position,
            ROUND(MIN(avg_position), 2) as min_position,
            ROUND(MAX(avg_position), 2) as max_position,
            ROUND(AVG(mentions), 1) as avg_mentions,
            CAST(MIN(mentions) AS INT64) as min_mentions,
            CAST(MAX(mentions) AS INT64) as max_mentions,
            COUNT(DISTINCT model) as model_count,
            COUNT(DISTINCT date) as date_count,
            COUNT(DISTINCT tag) as tag_count
        FROM `{DATASET}.ai_visibility`
    """)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 렌더링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

try:
    total_rows = load_overview()
except Exception as e:
    st.error(f"BigQuery 연결 실패: {e}")
    st.info("Settings 페이지에서 BigQuery 연결을 먼저 설정하세요.")
    st.stop()

# ── 상단 요약 카드 ──
from chart_utils import metric_cards

try:
    col_stats = load_column_stats()
    cs = col_stats.iloc[0]

    metric_cards([
        {"label": "총 데이터 행", "value": total_rows,
         "display": f"{total_rows:,}", "delta": None, "color": "#6366f1"},
        {"label": "AI 모델 수", "value": int(cs["model_count"]),
         "display": str(int(cs["model_count"])), "delta": None, "color": "#3b82f6"},
        {"label": "수집 일수", "value": int(cs["date_count"]),
         "display": str(int(cs["date_count"])), "delta": None, "color": "#22c55e"},
        {"label": "태그 종류", "value": int(cs["tag_count"]),
         "display": str(int(cs["tag_count"])), "delta": None, "color": "#f59e0b"},
    ])
except Exception:
    st.metric("총 데이터 행", f"{total_rows:,}")

st.markdown("")

# ── 1. 스키마 ──
st.markdown("---")
st.markdown("## 테이블 스키마")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### `ai_visibility` 컬럼 정의")
    try:
        schema_df = load_schema()
        st.dataframe(schema_df, use_container_width=True, hide_index=True)
    except Exception:
        st.info("INFORMATION_SCHEMA 접근 불가 — 샘플 데이터에서 추론합니다.")

with col_right:
    st.markdown("### 컬럼 설명")
    desc_data = [
        {"컬럼": "tag", "설명": "카테고리/제품 태그 (계층 구조: HS__REF__launched__Brand)", "타입": "STRING"},
        {"컬럼": "visibility", "설명": "AI 검색 가시성 (0~1, 높을수록 좋음)", "타입": "FLOAT"},
        {"컬럼": "sov", "설명": "Share of Voice — 점유율", "타입": "FLOAT"},
        {"컬럼": "avg_position", "설명": "AI 응답 내 평균 순위 (낮을수록 좋음)", "타입": "FLOAT"},
        {"컬럼": "mentions", "설명": "AI 응답에서 브랜드 언급 횟수", "타입": "INT"},
        {"컬럼": "prompts", "설명": "전체 프롬프트(질문) 수", "타입": "INT"},
        {"컬럼": "prompts_mentioned", "설명": "브랜드가 언급된 프롬프트 수", "타입": "FLOAT"},
        {"컬럼": "unique_prompts", "설명": "고유 프롬프트 수", "타입": "INT"},
        {"컬럼": "model", "설명": "AI 모델 (search-gpt, perplexity, gpt-5, gemini-2.5-flash)", "타입": "STRING"},
        {"컬럼": "date", "설명": "수집 날짜 (일별)", "타입": "STRING"},
        {"컬럼": "_loaded_at", "설명": "BigQuery 적재 시간 (자동)", "타입": "TIMESTAMP"},
        {"컬럼": "_source", "설명": "데이터 소스 (semrush_enterprise)", "타입": "STRING"},
    ]
    st.dataframe(pd.DataFrame(desc_data), use_container_width=True, hide_index=True)

# ── 2. 수치 컬럼 통계 ──
st.markdown("---")
st.markdown("## 수치 컬럼 통계")

try:
    cs = load_column_stats().iloc[0]

    stats_data = [
        {"지표": "Visibility", "평균": f"{cs['avg_visibility']:.4f}",
         "최소": f"{cs['min_visibility']:.4f}", "최대": f"{cs['max_visibility']:.4f}",
         "해석": "1에 가까울수록 AI 검색에 잘 노출"},
        {"지표": "Share of Voice", "평균": f"{cs['avg_sov']:.4f}",
         "최소": f"{cs['min_sov']:.4f}", "최대": f"{cs['max_sov']:.4f}",
         "해석": "1에 가까울수록 해당 카테고리 점유율 높음"},
        {"지표": "Avg Position", "평균": f"{cs['avg_position']:.2f}",
         "최소": f"{cs['min_position']:.2f}", "최대": f"{cs['max_position']:.2f}",
         "해석": "1에 가까울수록 AI 응답 상단에 위치"},
        {"지표": "Mentions (per tag)", "평균": f"{cs['avg_mentions']:.1f}",
         "최소": str(cs['min_mentions']), "최대": str(cs['max_mentions']),
         "해석": "AI가 브랜드를 언급한 횟수"},
    ]
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"통계 조회 실패: {e}")

# ── 3. 모델별 요약 ──
st.markdown("---")
st.markdown("## 모델별 요약")

try:
    model_df = load_model_summary()
    st.dataframe(model_df, use_container_width=True, hide_index=True)

    # 모델별 평균 Visibility 비교 차트
    st.markdown("### 모델별 평균 Visibility")
    chart_data = model_df.set_index("model")[["avg_visibility"]].sort_values("avg_visibility", ascending=True)
    st.bar_chart(chart_data)

    # 모델별 평균 Position 비교
    st.markdown("### 모델별 평균 Position (낮을수록 좋음)")
    chart_pos = model_df.set_index("model")[["avg_position"]].sort_values("avg_position", ascending=False)
    st.bar_chart(chart_pos)

except Exception as e:
    st.error(f"모델 요약 조회 실패: {e}")

# ── 4. 일별 추이 ──
st.markdown("---")
st.markdown("## 일별 추이")

try:
    daily_df = load_daily_stats()

    tab1, tab2, tab3 = st.tabs(["Visibility", "Share of Voice", "Position"])

    with tab1:
        pivot = daily_df.pivot(index="date", columns="model", values="avg_visibility")
        st.line_chart(pivot)

    with tab2:
        pivot_sov = daily_df.pivot(index="date", columns="model", values="avg_sov")
        st.line_chart(pivot_sov)

    with tab3:
        pivot_pos = daily_df.pivot(index="date", columns="model", values="avg_position")
        st.line_chart(pivot_pos)

    # 일별 상세 테이블
    with st.expander("일별 상세 데이터 테이블"):
        st.dataframe(daily_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"일별 추이 조회 실패: {e}")

# ── 5. 태그 분포 ──
st.markdown("---")
st.markdown("## 태그 Top 20 (Visibility 기준)")

try:
    loader = get_loader()
    top_tags = loader.query(f"""
        SELECT
            tag,
            ROUND(AVG(visibility), 4) as avg_visibility,
            ROUND(AVG(sov), 4) as avg_sov,
            ROUND(AVG(avg_position), 2) as avg_position,
            CAST(ROUND(AVG(mentions), 0) AS INT64) as avg_mentions,
            COUNT(DISTINCT model) as models,
            COUNT(DISTINCT date) as days
        FROM `{DATASET}.ai_visibility`
        WHERE visibility > 0
        GROUP BY tag
        ORDER BY avg_visibility DESC
        LIMIT 20
    """)
    st.dataframe(top_tags, use_container_width=True, hide_index=True)

    st.markdown("### Top 20 태그 Visibility")
    chart_tags = top_tags.set_index("tag")[["avg_visibility"]].sort_values("avg_visibility", ascending=True)
    st.bar_chart(chart_tags)

except Exception as e:
    st.error(f"태그 조회 실패: {e}")

# ── 6. Raw SQL ──
st.markdown("---")
with st.expander("커스텀 SQL 쿼리"):
    default_q = f"SELECT * FROM `{DATASET}.ai_visibility` WHERE tag = 'HS__REF' ORDER BY model, date LIMIT 100"
    query = st.text_area("SQL", value=default_q, height=100)
    if st.button("실행", type="primary"):
        try:
            loader = get_loader()
            result = loader.query(query)
            st.dataframe(result, use_container_width=True, hide_index=True)
            csv = result.to_csv(index=False).encode("utf-8")
            st.download_button("CSV 다운로드", csv, "query_result.csv", "text/csv")
        except Exception as e:
            st.error(f"쿼리 실패: {e}")
