"""Site Audit 관리 페이지"""

import streamlit as st
import pandas as pd
from config import SEMRUSH_PROJECT_ID

st.set_page_config(page_title="Site Audit", page_icon="🏥", layout="wide")
st.title("🏥 Site Audit")

@st.cache_resource
def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

@st.cache_resource
def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

# ── 프로젝트 설정 ──
project_id = st.text_input("Project ID", value=SEMRUSH_PROJECT_ID)

# ── 감사 실행 ──
st.markdown("## 사이트 감사")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 새 감사 실행", type="primary"):
        try:
            client = get_client()
            with st.spinner("사이트 감사 실행 중..."):
                result = client.launch_site_audit(project_id)
            st.success("감사가 시작되었습니다!")
            st.json(result)
        except Exception as e:
            st.error(f"에러: {e}")

with col2:
    if st.button("📊 최신 감사 결과 조회", type="primary"):
        try:
            client = get_client()
            with st.spinner("감사 결과 조회 중..."):
                data = client.get_site_audit_snapshot(project_id)
            st.session_state["audit_raw"] = data
            df = client.get_site_audit_info(project_id)
            st.session_state["audit_df"] = df
            st.success("조회 완료!")
        except Exception as e:
            st.error(f"에러: {e}")

with col3:
    if st.button("💾 BigQuery에 저장"):
        if "audit_df" not in st.session_state:
            st.warning("먼저 감사 결과를 조회하세요.")
        else:
            try:
                loader = get_loader()
                with st.spinner("저장 중..."):
                    result = loader.load_dataframe(
                        st.session_state["audit_df"], "site_audit"
                    )
                st.success(f"✅ 저장 완료!")
            except Exception as e:
                st.error(f"저장 실패: {e}")

# ── 결과 표시 ──
if "audit_raw" in st.session_state:
    data = st.session_state["audit_raw"]
    st.markdown("---")

    # 건강도 점수
    from chart_utils import metric_cards

    quality = data.get("quality", {})
    score = quality.get("value", 0)
    delta = quality.get("delta", 0)

    errors = data.get("errors", [])
    error_count = sum(e.get("count", 0) for e in errors)
    error_delta = -sum(e.get("delta", 0) for e in errors)

    warnings = data.get("warnings", [])
    warning_count = sum(w.get("count", 0) for w in warnings)
    warning_delta = -sum(w.get("delta", 0) for w in warnings)

    pages_crawled = data.get("pages_crawled", 0)

    metric_cards([
        {"label": "건강도 점수", "value": score, "display": f"{score}/100",
         "delta": delta, "color": "#22c55e" if score >= 80 else "#f59e0b" if score >= 50 else "#ef4444"},
        {"label": "에러", "value": error_count, "display": str(error_count),
         "delta": error_delta, "inverse": True, "color": "#ef4444"},
        {"label": "경고", "value": warning_count, "display": str(warning_count),
         "delta": warning_delta, "inverse": True, "color": "#f59e0b"},
        {"label": "크롤링 페이지", "value": pages_crawled, "display": f"{pages_crawled:,}",
         "delta": None, "color": "#3b82f6"},
    ])

    # 상세 이슈 테이블
    st.markdown("### 에러 상세")
    if errors:
        st.dataframe(pd.DataFrame(errors), use_container_width=True)
    else:
        st.info("에러 없음")

    st.markdown("### 경고 상세")
    if warnings:
        st.dataframe(pd.DataFrame(warnings), use_container_width=True)
    else:
        st.info("경고 없음")

    notices = data.get("notices", [])
    st.markdown("### 알림 상세")
    if notices:
        st.dataframe(pd.DataFrame(notices), use_container_width=True)
    else:
        st.info("알림 없음")

# ── 특정 이슈 상세 조회 ──
st.markdown("---")
st.markdown("## 이슈 상세 조회")

col1, col2 = st.columns(2)
with col1:
    snapshot_id = st.text_input("Snapshot ID")
with col2:
    issue_id = st.text_input("Issue ID")

if st.button("🔍 이슈 상세 조회") and snapshot_id and issue_id:
    try:
        client = get_client()
        with st.spinner("조회 중..."):
            result = client.get_site_audit_issues(project_id, snapshot_id, issue_id)
        st.json(result)
    except Exception as e:
        st.error(f"에러: {e}")
