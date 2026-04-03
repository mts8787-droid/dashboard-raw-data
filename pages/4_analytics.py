"""Domain Analytics 페이지"""

import streamlit as st
import pandas as pd
from config import TARGET_DOMAIN

st.set_page_config(page_title="Domain Analytics", page_icon="📊", layout="wide")
st.title("📊 Domain Analytics")

def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

# ── 도메인 입력 ──
domain = st.text_input("도메인", value=TARGET_DOMAIN)

# ── 데이터 수집 ──
st.markdown("## 데이터 수집")

data_types = st.multiselect(
    "수집할 데이터 선택",
    ["도메인 개요", "오가닉 키워드", "유료 키워드", "백링크 개요", "오가닉 경쟁사"],
    default=["도메인 개요"],
)

max_rows = st.slider("최대 행 수 (키워드 데이터)", 100, 50000, 10000, step=1000)

if st.button("🚀 데이터 수집 시작", type="primary"):
    client = get_client()
    results = {}

    mapping = {
        "도메인 개요": ("domain_overview", lambda: client.domain_overview(domain)),
        "오가닉 키워드": ("domain_organic_keywords", lambda: client.domain_organic_keywords(domain, max_rows)),
        "유료 키워드": ("domain_adwords_keywords", lambda: client.domain_adwords_keywords(domain, max_rows)),
        "백링크 개요": ("backlinks_overview", lambda: client.domain_backlinks_overview(domain)),
        "오가닉 경쟁사": ("organic_competitors", lambda: client.organic_competitors(domain)),
    }

    progress = st.progress(0)
    for i, dtype in enumerate(data_types):
        key, func = mapping[dtype]
        with st.spinner(f"{dtype} 수집 중..."):
            try:
                df = func()
                results[key] = df
                st.session_state[f"analytics_{key}"] = df
            except Exception as e:
                st.error(f"{dtype} 수집 실패: {e}")
        progress.progress((i + 1) / len(data_types))

    st.success(f"✅ {len(results)}개 데이터 수집 완료!")

# ── 결과 표시 ──
tabs_data = []
for key in ["domain_overview", "domain_organic_keywords", "domain_adwords_keywords",
            "backlinks_overview", "organic_competitors"]:
    session_key = f"analytics_{key}"
    if session_key in st.session_state:
        tabs_data.append((key, st.session_state[session_key]))

if tabs_data:
    st.markdown("---")
    st.markdown("## 수집 결과")
    tab_names = [name for name, _ in tabs_data]
    tabs = st.tabs(tab_names)

    for tab, (name, df) in zip(tabs, tabs_data):
        with tab:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(f"📥 {name}.csv", csv, f"{name}.csv", "text/csv", key=f"dl_{name}")

# ── BigQuery 일괄 저장 ──
st.markdown("---")
st.markdown("## BigQuery 저장")

write_mode = st.radio("저장 방식", ["추가 (APPEND)", "덮어쓰기 (TRUNCATE)"], horizontal=True)

if st.button("💾 수집 데이터 전체 BigQuery 저장", type="primary"):
    mode = "WRITE_APPEND" if "APPEND" in write_mode else "WRITE_TRUNCATE"
    saved = []
    try:
        loader = get_loader()
        for key in ["domain_overview", "domain_organic_keywords", "domain_adwords_keywords",
                     "backlinks_overview", "organic_competitors"]:
            session_key = f"analytics_{key}"
            if session_key in st.session_state:
                df = st.session_state[session_key]
                if not df.empty:
                    with st.spinner(f"{key} 저장 중..."):
                        result = loader.load_dataframe(df, key, mode)
                    saved.append(f"{key}: {result['rows']}행")
        if saved:
            st.success("✅ 저장 완료!\n" + "\n".join(saved))
        else:
            st.warning("저장할 데이터가 없습니다. 먼저 데이터를 수집하세요.")
    except Exception as e:
        st.error(f"저장 실패: {e}")
