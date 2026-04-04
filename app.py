"""SEMrush Enterprise 관리 포털 - 메인 대시보드"""

import streamlit as st

st.set_page_config(
    page_title="SEMrush Enterprise Admin",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SEMrush Enterprise Admin Portal")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔍 Visibility & Position Tracking")
    st.markdown("""
    - Visibility Index 조회 및 추이
    - 키워드 순위 추적
    - BigQuery 저장
    """)
    st.page_link("pages/1_visibility.py", label="Visibility 관리 →", icon="📈")

with col2:
    st.markdown("### 📍 Citations & Listings")
    st.markdown("""
    - 로컬 리스팅 관리
    - NAP 데이터 조회/수정
    - Citation 현황
    """)
    st.page_link("pages/2_citations.py", label="Citations 관리 →", icon="📍")

with col3:
    st.markdown("### 🏥 Site Audit")
    st.markdown("""
    - 사이트 건강도 점수
    - 에러/경고/알림 현황
    - 감사 실행
    """)
    st.page_link("pages/3_site_audit.py", label="Site Audit →", icon="🏥")

st.markdown("---")

col4, col5 = st.columns(2)

with col4:
    st.markdown("### 📊 Domain Analytics")
    st.markdown("도메인 오가닉/유료 트래픽, 백링크, 경쟁사 분석")
    st.page_link("pages/4_analytics.py", label="Analytics →", icon="📊")

with col5:
    st.markdown("### 🗄️ BigQuery 데이터 관리")
    st.markdown("테이블 현황, 데이터 조회, 수집 이력")
    st.page_link("pages/5_bigquery.py", label="BigQuery 관리 →", icon="🗄️")

st.markdown("---")

# 사이드바 - 설정 상태
with st.sidebar:
    st.markdown("## ⚙️ 설정 상태")

    from config import (
        SEMRUSH_API_KEY, SEMRUSH_PROJECT_ID, SEMRUSH_CAMPAIGN_ID,
        SEMRUSH_LISTING_TOKEN, GCP_PROJECT_ID, TARGET_DOMAIN,
    )

    checks = {
        "SEMrush API Key": bool(SEMRUSH_API_KEY),
        "Project ID": bool(SEMRUSH_PROJECT_ID),
        "Campaign ID": bool(SEMRUSH_CAMPAIGN_ID),
        "Listing Token": bool(SEMRUSH_LISTING_TOKEN),
        "GCP Project": bool(GCP_PROJECT_ID),
    }

    for name, ok in checks.items():
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} {name}")

    if TARGET_DOMAIN:
        st.markdown(f"\n**대상 도메인:** `{TARGET_DOMAIN}`")

    st.markdown("---")
    st.page_link("pages/0_settings.py", label="⚙️ 연결 설정 & 가이드", icon="🔧")
    st.markdown("`.env` 파일에서도 설정을 변경할 수 있습니다.")
