"""데이터 리니지 — 테이블별 데이터 흐름

각 테이블의 sources(상류) / downstream(하류) / transforms를 보여준다.
시간 역순 변경 이력 X — 현재 latest 정의만.
"""
import streamlit as st
import schema_store

st.set_page_config(page_title="데이터 리니지", page_icon="📜", layout="wide")
st.title("📜 데이터 리니지")
st.caption("테이블별 데이터 흐름 — 어디서 오고 어디로 가는지")


tables = schema_store.all_tables()
if not tables:
    st.info("저장된 스키마가 없습니다. **스키마 학습** 페이지에서 먼저 등록하세요.")
    st.stop()


# ─── 1. 전체 흐름 mermaid 다이어그램 ─────────────────────────────
st.markdown("## 전체 데이터 흐름")

def _build_mermaid(tables_info: list[dict]) -> str:
    nodes = []
    edges = set()
    for t in tables_info:
        doc = schema_store.load_latest(t["dataset"], t["table"])
        if not doc:
            continue
        lin = doc.get("lineage") or {}
        role = lin.get("role", "unknown")
        node_class = {"raw": "raw", "transform": "trans", "mapping": "map"}.get(role, "raw")
        nodes.append((t["table"], node_class, len(doc.get("columns", []))))
        for src in lin.get("sources", []):
            if "table" in src:
                edges.add((src["table"], t["table"]))
        for ds in lin.get("downstream", []):
            edges.add((t["table"], ds))

    lines = [
        "flowchart LR",
        "  classDef raw fill:#FCE7F3,stroke:#BE185D,color:#831843",
        "  classDef trans fill:#FEF3C7,stroke:#B45309,color:#78350F",
        "  classDef map fill:#D1FAE5,stroke:#047857,color:#064E3B",
    ]
    for name, cls, cnt in nodes:
        lines.append(f'  {name}["{name}<br/><small>{cnt} cols</small>"]:::{cls}')
    for a, b in sorted(edges):
        lines.append(f"  {a} --> {b}")
    return "\n".join(lines)


with st.expander("전체 테이블 의존성 도식 (mermaid)", expanded=True):
    code = _build_mermaid(tables)
    st.code(code, language="text")
    st.caption("Streamlit은 mermaid 직접 렌더 미지원 — 위 코드를 [mermaid.live](https://mermaid.live)에 붙여 시각화")


# ─── 2. 테이블 리스트 + 상세 ─────────────────────────────────────
st.markdown("## 테이블별 리니지")

import pandas as pd
df = pd.DataFrame([{
    "테이블": t["table"],
    "역할": t["lineage_role"] or "—",
    "컬럼": t["column_count"],
    "최종 저장": (t["saved_at"] or "")[:19].replace("T", " "),
} for t in tables])
st.dataframe(df, use_container_width=True, hide_index=True)


# ─── 3. 단일 테이블 상세 ─────────────────────────────────────────
st.markdown("---")
table_names = [t["table"] for t in tables]
selected = st.selectbox("테이블 선택", table_names)

# 선택한 테이블 doc 로드
sel_t = next((t for t in tables if t["table"] == selected), None)
doc = schema_store.load_latest(sel_t["dataset"], sel_t["table"])
lineage = doc.get("lineage") or {}

st.markdown(f"### `{sel_t['dataset']}.{sel_t['table']}`")
if doc.get("note"):
    st.caption(f"메모: {doc['note']}")

# 역할·빈도 요약
c1, c2, c3 = st.columns(3)
c1.metric("역할", lineage.get("role", "—"))
c2.metric("주기", lineage.get("frequency", "—"))
c3.metric("컬럼 수", len(doc.get("columns", [])))

# 상류/하류
left, right = st.columns(2)

with left:
    st.markdown("#### ⬅️ 상류 (Sources)")
    sources = lineage.get("sources", [])
    if not sources:
        st.caption("상류 없음 (raw 또는 매핑 테이블)")
    for src in sources:
        if "system" in src:
            label = f"🌐 외부: **{src['system']}**"
            if src.get("frequency"):
                label += f" ({src['frequency']})"
            st.markdown(label)
        elif "table" in src:
            label = f"📊 테이블: **`{src['table']}`**"
            if src.get("join_on"):
                label += f" — JOIN ON `{src['join_on']}`"
            st.markdown(label)

with right:
    st.markdown("#### ➡️ 하류 (Downstream)")
    downstream = lineage.get("downstream", [])
    if not downstream:
        st.caption("하류 없음 (최종 산출물)")
    for ds in downstream:
        st.markdown(f"📊 **`{ds}`**")

# 변환 규칙
transforms = lineage.get("transforms", [])
if transforms:
    st.markdown("#### 🔧 변환 규칙")
    for t in transforms:
        st.markdown(f"- {t}")

# 컬럼 표
st.markdown("#### 컬럼 정의")
cols = doc.get("columns", [])
if cols:
    rows = []
    for c in cols:
        rows.append({
            "이름": c.get("name"),
            "타입": c.get("bq_type"),
            "Null": c.get("nullable", "Y"),
            "Key": c.get("key", "") or "",
            "분류": c.get("category", ""),
            "설명": c.get("description", ""),
            "원천": c.get("source_file", ""),
            "원천 컬럼": c.get("source_column", ""),
            "생성 규칙": c.get("derivation", ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.warning("컬럼 미정의 — **스키마 학습** 페이지에서 채워주세요.")

with st.expander("원본 JSON 전체 보기"):
    st.json(doc, expanded=False)
