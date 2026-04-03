"""Visibility & Position Tracking 관리 페이지"""

import streamlit as st
import pandas as pd
from config import SEMRUSH_CAMPAIGN_ID, TARGET_DOMAIN

st.set_page_config(page_title="Visibility Tracking", page_icon="📈", layout="wide")
st.title("📈 Visibility & Position Tracking")

# ── 초기화 ──
def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

# ── Visibility Index ──
st.markdown("## Visibility Index")

campaign_id = st.text_input("Campaign ID", value=SEMRUSH_CAMPAIGN_ID,
                             help="SEMrush Position Tracking 캠페인 ID (예: 6647718_272401)")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Visibility 데이터 조회", type="primary"):
        try:
            client = get_client()
            with st.spinner("Visibility Index 조회 중..."):
                data = client.get_visibility(campaign_id)
            st.session_state["visibility_data"] = data
            st.success("데이터 조회 완료!")
        except Exception as e:
            st.error(f"에러: {e}")

with col2:
    if st.button("📜 Visibility 히스토리 조회"):
        try:
            client = get_client()
            with st.spinner("히스토리 조회 중..."):
                df = client.get_visibility_history(campaign_id)
            st.session_state["visibility_history"] = df
            st.success(f"{len(df)}건 조회 완료!")
        except Exception as e:
            st.error(f"에러: {e}")

# 결과 표시
if "visibility_data" in st.session_state:
    data = st.session_state["visibility_data"]
    if isinstance(data, dict):
        st.json(data)
    elif isinstance(data, list):
        st.dataframe(pd.DataFrame(data))

if "visibility_history" in st.session_state:
    df = st.session_state["visibility_history"]
    if not df.empty:
        st.markdown("### Visibility 추이")
        st.line_chart(df)
        st.dataframe(df)

# ── Position Tracking ──
st.markdown("---")
st.markdown("## Position Tracking (키워드 순위)")

url_filter = st.text_input("URL 필터 (선택)", placeholder=f"*.{TARGET_DOMAIN}/*",
                            help="특정 URL 패턴의 순위만 조회")

if st.button("🔍 키워드 순위 조회", type="primary"):
    try:
        client = get_client()
        with st.spinner("순위 데이터 조회 중..."):
            df = client.get_position_tracking(campaign_id, url_filter or None)
        st.session_state["position_data"] = df
        st.success(f"{len(df)}건 조회 완료!")
    except Exception as e:
        st.error(f"에러: {e}")

if "position_data" in st.session_state:
    df = st.session_state["position_data"]
    if not df.empty:
        st.dataframe(df, use_container_width=True)

# ── BigQuery 저장 ──
st.markdown("---")
st.markdown("## BigQuery 저장")

save_target = st.selectbox("저장할 데이터", ["visibility_history", "position_data"])
write_mode = st.radio("저장 방식", ["추가 (APPEND)", "덮어쓰기 (TRUNCATE)"], horizontal=True)

if st.button("💾 BigQuery에 저장", type="primary"):
    if save_target not in st.session_state:
        st.warning("먼저 데이터를 조회하세요.")
    else:
        df = st.session_state[save_target]
        if isinstance(df, pd.DataFrame) and not df.empty:
            try:
                loader = get_loader()
                table = "visibility_index" if save_target == "visibility_history" else "position_tracking"
                mode = "WRITE_APPEND" if "APPEND" in write_mode else "WRITE_TRUNCATE"
                with st.spinner("BigQuery 저장 중..."):
                    result = loader.load_dataframe(df, table, mode)
                st.success(f"✅ {result['rows']}행 저장 완료! (총 {result.get('total_rows', '?')}행)")
            except Exception as e:
                st.error(f"저장 실패: {e}")
        else:
            st.warning("저장할 데이터가 없습니다.")
