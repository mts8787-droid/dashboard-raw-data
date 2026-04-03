"""Citations & Listing Management 관리 페이지"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Citations Management", page_icon="📍", layout="wide")
st.title("📍 Citations & Listing Management")

def get_client():
    from semrush_client import SEMrushClient
    return SEMrushClient()

def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()

# ── 리스팅 목록 조회 ──
st.markdown("## 로컬 리스팅 목록")

col1, col2 = st.columns([1, 3])
with col1:
    page = st.number_input("페이지", min_value=1, value=1)
    size = st.number_input("페이지당 건수", min_value=1, max_value=50, value=20)

if st.button("📍 리스팅 목록 조회", type="primary"):
    try:
        client = get_client()
        with st.spinner("리스팅 목록 조회 중..."):
            df = client.get_citations_df(page=page, size=size)
        st.session_state["citations_df"] = df
        st.success(f"{len(df)}건 조회 완료!")
    except Exception as e:
        st.error(f"에러: {e}")

if "citations_df" in st.session_state:
    df = st.session_state["citations_df"]
    if not df.empty:
        st.dataframe(df, use_container_width=True)

        # CSV 다운로드
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV 다운로드", csv, "citations.csv", "text/csv")

# ── 개별 위치 상세 ──
st.markdown("---")
st.markdown("## 위치 상세 조회 (NAP 데이터)")

location_id = st.text_input("Location ID", placeholder="조회할 위치 ID를 입력하세요")

if st.button("🔍 위치 상세 조회") and location_id:
    try:
        client = get_client()
        with st.spinner("위치 상세 조회 중..."):
            data = client.get_location(location_id)
        st.session_state["location_detail"] = data
        st.success("조회 완료!")
    except Exception as e:
        st.error(f"에러: {e}")

if "location_detail" in st.session_state:
    data = st.session_state["location_detail"]
    st.json(data)

# ── NAP 데이터 수정 ──
st.markdown("---")
st.markdown("## NAP 데이터 수정")

with st.form("nap_update_form"):
    update_location_id = st.text_input("수정할 Location ID")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("비즈니스 이름")
        phone = st.text_input("전화번호")
        website = st.text_input("웹사이트")
    with col2:
        street = st.text_input("주소 (도로명)")
        city = st.text_input("도시")
        state = st.text_input("주/도")
        zip_code = st.text_input("우편번호")

    submitted = st.form_submit_button("✏️ NAP 정보 업데이트", type="primary")

    if submitted and update_location_id:
        update_data = {}
        if name: update_data["name"] = name
        if phone: update_data["phone"] = phone
        if website: update_data["website"] = website
        address = {}
        if street: address["street"] = street
        if city: address["city"] = city
        if state: address["state"] = state
        if zip_code: address["zip"] = zip_code
        if address: update_data["address"] = address

        if update_data:
            try:
                client = get_client()
                with st.spinner("업데이트 중..."):
                    result = client.update_location(update_location_id, update_data)
                st.success("✅ NAP 정보가 업데이트되었습니다!")
                st.json(result)
            except Exception as e:
                st.error(f"업데이트 실패: {e}")
        else:
            st.warning("수정할 항목을 입력하세요.")

# ── BigQuery 저장 ──
st.markdown("---")
if st.button("💾 Citation 데이터를 BigQuery에 저장", type="primary"):
    if "citations_df" not in st.session_state:
        st.warning("먼저 리스팅 목록을 조회하세요.")
    else:
        df = st.session_state["citations_df"]
        if not df.empty:
            try:
                loader = get_loader()
                with st.spinner("BigQuery 저장 중..."):
                    result = loader.load_dataframe(df, "citations")
                st.success(f"✅ {result['rows']}행 저장 완료!")
            except Exception as e:
                st.error(f"저장 실패: {e}")
