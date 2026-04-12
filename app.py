"""SEMrush Enterprise Dashboard — 메인"""

import streamlit as st

st.set_page_config(
    page_title="SEMrush Enterprise Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SEMrush Enterprise Dashboard")
st.caption("SEMrush Enterprise Element API → BigQuery 데이터 파이프라인")
st.markdown("---")

# ── 메인 카드 ──
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🤖 AI Visibility")
    st.markdown("""
    - AI 모델별 브랜드 가시성 데이터 수집
    - 일별 데이터 수집 (search-gpt, perplexity, gpt-5, gemini)
    - BigQuery 저장 & 조회
    """)
    st.page_link("pages/1_ai_visibility.py", label="AI Visibility →", icon="🤖")

with col2:
    st.markdown("### 📋 Data Overview")
    st.markdown("""
    - 스키마 & 컬럼 설명
    - 모델별 평균값 비교
    - 일별 Visibility / SoV / Position 추이
    """)
    st.page_link("pages/2_data_overview.py", label="Data Overview →", icon="📋")

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    st.markdown("### 🗄️ BigQuery 관리")
    st.markdown("""
    - 테이블 현황 (행 수, 크기)
    - SQL 쿼리 실행
    - 빠른 테이블 조회
    """)
    st.page_link("pages/3_bigquery.py", label="BigQuery 관리 →", icon="🗄️")

with col4:
    st.markdown("### ⚙️ 설정")
    st.markdown("""
    - BigQuery 연결 설정
    - SEMrush API Key 관리
    - 연결 상태 진단
    """)
    st.page_link("pages/4_settings.py", label="설정 →", icon="⚙️")

# ── 사이드바 ──
with st.sidebar:
    st.markdown("## 연결 상태")

    from config import (
        SEMRUSH_API_KEY, SEMRUSH_WORKSPACE_ID,
        SEMRUSH_PROJECT_ID, GCP_PROJECT_ID, TARGET_DOMAIN,
    )

    checks = {
        "SEMrush API Key": bool(SEMRUSH_API_KEY),
        "Workspace ID": bool(SEMRUSH_WORKSPACE_ID),
        "Project ID": bool(SEMRUSH_PROJECT_ID),
        "GCP Project": bool(GCP_PROJECT_ID),
    }

    for name, ok in checks.items():
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} {name}")

    if TARGET_DOMAIN:
        st.markdown(f"\n**대상 도메인:** `{TARGET_DOMAIN}`")

    st.markdown("---")
    st.page_link("pages/4_settings.py", label="⚙️ 연결 설정", icon="🔧")
