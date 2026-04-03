"""Site Audit 관리 페이지"""

import streamlit as st
import pandas as pd
from config import SEMRUSH_PROJECT_ID

st.set_page_config(page_title="Site Audit", page_icon="🏥", layout="wide")
st.title("🏥 Site Audit")

def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

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
    quality = data.get("quality", {})
    score = quality.get("value", 0)
    delta = quality.get("delta", 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("건강도 점수", f"{score}/100", delta=delta)
    with col2:
        errors = data.get("errors", [])
        st.metric("에러", sum(e.get("count", 0) for e in errors),
                  delta=-sum(e.get("delta", 0) for e in errors), delta_color="inverse")
    with col3:
        warnings = data.get("warnings", [])
        st.metric("경고", sum(w.get("count", 0) for w in warnings),
                  delta=-sum(w.get("delta", 0) for w in warnings), delta_color="inverse")
    with col4:
        st.metric("크롤링 페이지", data.get("pages_crawled", 0))

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
