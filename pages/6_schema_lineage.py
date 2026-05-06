"""스키마 리니지 (Lineage) — 시간순 변경 이력

- 좌측: 저장된 스냅샷 시간 역순 리스트
- 우측: 선택한 스냅샷 상세 + 직전 버전과의 diff
"""

import streamlit as st
import schema_store

st.set_page_config(page_title="스키마 리니지", page_icon="📜", layout="wide")
st.title("📜 데이터 스키마 리니지")
st.caption("PIC가 학습·승인한 스키마 스냅샷의 시간 역순 이력")


# 필터
keys = schema_store.all_table_keys()
table_filter = None
if keys:
    options = ["(전체)"] + [f"{ds}.{tb}" for ds, tb in keys]
    selected = st.selectbox("테이블 필터", options)
    if selected != "(전체)":
        ds, tb = selected.rsplit(".", 1)
        table_filter = (ds, tb)

items = schema_store.list_lineage(
    dataset=table_filter[0] if table_filter else None,
    table=table_filter[1] if table_filter else None,
)

if not items:
    st.info(
        "아직 저장된 스키마 스냅샷이 없습니다.\n\n"
        "**스키마 학습** 페이지에서 BigQuery 쿼리를 학습하고 저장하면 여기에 시간 역순으로 누적됩니다."
    )
    st.stop()

st.markdown(f"### 스냅샷 {len(items)}건")

# 리스트
left, right = st.columns([2, 3])

with left:
    st.markdown("#### 시간 역순 이력")
    selected_idx = None
    for i, item in enumerate(items):
        ts_short = item["saved_at"][:19].replace("T", " ")
        label = f"{ts_short}\n`{item['dataset']}.{item['table']}` · {item['column_count']} cols"
        note = item.get("note") or "—"
        with st.container(border=True):
            st.markdown(f"**{ts_short}**")
            st.markdown(f"`{item['dataset']}.{item['table']}`")
            st.caption(f"컬럼 {item['column_count']}개 · {item['row_count_at_save']}행 · {note}")
            if st.button("선택", key=f"sel_{i}", use_container_width=True):
                st.session_state["lin_selected"] = i

with right:
    sel = st.session_state.get("lin_selected")
    if sel is None:
        st.info("좌측에서 스냅샷을 선택하세요.")
        st.stop()

    item = items[sel]
    doc = schema_store.load_lineage_doc(item["_path"])

    st.markdown(f"### {item['dataset']}.{item['table']}")
    st.caption(f"저장 시각: {doc.get('saved_at')} · 저장자: {doc.get('saved_by')}")
    if doc.get("note"):
        st.info(f"메모: {doc['note']}")

    # 직전 버전과 diff
    prev_items = [x for x in items[sel + 1:] if x["dataset"] == item["dataset"] and x["table"] == item["table"]]
    if prev_items:
        prev_doc = schema_store.load_lineage_doc(prev_items[0]["_path"])
        diff = schema_store.diff_columns(prev_doc.get("columns", []), doc.get("columns", []))
        st.markdown("#### 직전 버전 대비 변경")
        c1, c2, c3 = st.columns(3)
        c1.metric("추가", len(diff["added"]))
        c2.metric("삭제", len(diff["removed"]))
        c3.metric("변경", len(diff["changed"]))
        if diff["added"]:
            st.markdown("**추가된 컬럼**: " + ", ".join(f"`{c['name']}`" for c in diff["added"]))
        if diff["removed"]:
            st.markdown("**삭제된 컬럼**: " + ", ".join(f"`{c['name']}`" for c in diff["removed"]))
        if diff["changed"]:
            with st.expander(f"변경된 컬럼 {len(diff['changed'])}개"):
                for ch in diff["changed"]:
                    st.markdown(f"**`{ch['name']}`**")
                    for fk, fv in ch["fields"].items():
                        st.markdown(f"- `{fk}`: ~~{fv['prev']}~~ → **{fv['curr']}**")

    # 컬럼 표
    st.markdown("#### 전체 컬럼")
    rows = []
    for col in doc.get("columns", []):
        rows.append({
            "이름": col.get("name"),
            "BQ 타입": col.get("bq_type"),
            "분류": col.get("category", ""),
            "설명": col.get("description", ""),
            "null %": col.get("null_pct"),
            "distinct": col.get("distinct_count"),
        })
    if rows:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 원본 JSON
    with st.expander("원본 JSON 전체 보기"):
        st.json(doc, expanded=False)
