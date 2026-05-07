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

# ── 쿼리 ──
st.markdown("## 쿼리")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🤖 AI Visibility 수집")
    st.markdown("""
    - SEMrush API → `L0_Raw_visibility` 적재
    - 모델별·일별 데이터 수집
    - BigQuery 저장 & 조회
    """)
    st.page_link("pages/1_ai_visibility.py", label="AI Visibility →", icon="🤖")

with col2:
    st.markdown("### 🗄️ BigQuery SQL")
    st.markdown("""
    - 테이블 현황 (행 수, 크기)
    - SQL 쿼리 실행
    - 빠른 테이블 조회
    """)
    st.page_link("pages/2_bigquery.py", label="BigQuery →", icon="🗄️")

# ── 모니터링 ──
st.markdown("---")
st.markdown("## 모니터링")
col3, _ = st.columns(2)

with col3:
    st.markdown("### 📋 Data Overview")
    st.markdown("""
    - 모델별 평균값 비교
    - 일별 Visibility / SoV / Position 추이
    - 태그 분포·수치 통계
    """)
    st.page_link("pages/3_data_overview.py", label="Data Overview →", icon="📋")

# ── 셋팅 ──
st.markdown("---")
st.markdown("## 셋팅")
col4, _ = st.columns(2)

with col4:
    st.markdown("### ⚙️ 연결 설정")
    st.markdown("""
    - BigQuery 연결 설정
    - SEMrush API Key 관리
    - 연결 상태 진단
    """)
    st.page_link("pages/4_settings.py", label="설정 →", icon="⚙️")

# ── 문서 ──
st.markdown("---")
st.markdown("## 문서")
col5, col6, col7 = st.columns(3)

with col5:
    st.markdown("### 🧠 스키마 학습")
    st.markdown("""
    - BigQuery 실데이터 자동 분석
    - PIC 검수 (컬럼 설명·분류)
    - JSON + lineage 저장
    """)
    st.page_link("pages/5_schema_learning.py", label="스키마 학습 →", icon="🧠")

with col6:
    st.markdown("### 📜 데이터 리니지")
    st.markdown("""
    - L0/L1 테이블 데이터 흐름
    - 상류·하류 의존성
    - 컬럼 정의·변환 규칙
    """)
    st.page_link("pages/6_schema_lineage.py", label="리니지 →", icon="📜")

with col7:
    st.markdown("### 🛠️ 스키마 DDL")
    st.markdown("""
    - CREATE TABLE 자동 생성
    - 파티션·클러스터링 옵션
    - 변환 쿼리 템플릿
    """)
    st.page_link("pages/7_schema_ddl.py", label="DDL →", icon="🛠️")

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
