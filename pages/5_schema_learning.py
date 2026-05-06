"""스키마 학습 페이지 (human-in-the-loop)

흐름:
1. 데이터셋·테이블 선택 (또는 임의 SQL)
2. 시스템이 컬럼별 자동 분석 (dtype, null%, distinct count, sample values)
3. PIC가 컬럼별 description·category 입력
4. 저장 → docs/schema/<table>.json + lineage 스냅샷 + lineage.md
"""

import streamlit as st
import pandas as pd
from config import GCP_PROJECT_ID, BQ_DATASET
import schema_store

st.set_page_config(page_title="스키마 학습", page_icon="🧠", layout="wide")
st.title("🧠 스키마 학습 (Human-in-the-Loop)")
st.caption("BigQuery 쿼리 결과를 분석하고 PIC 검수 후 데이터 스키마 문서로 저장")

@st.cache_resource
def get_loader():
    from bigquery_loader import BigQueryLoader
    return BigQueryLoader()


# ── 1단계: 데이터 가져오기 ──────────────────────────────────────────
st.markdown("## 1단계 — 데이터 가져오기")

dataset_full = f"{GCP_PROJECT_ID}.{BQ_DATASET}" if GCP_PROJECT_ID else "project.dataset"

mode = st.radio("방식", ["테이블에서 직접 학습 (권장)", "임의 SQL 결과로부터 학습"],
                horizontal=True, label_visibility="collapsed")

df = None
table_name = None

if mode.startswith("테이블"):
    col1, col2 = st.columns([2, 1])
    with col1:
        table_name = st.text_input("테이블 이름", value="ai_visibility")
    with col2:
        sample_size = st.number_input("샘플 행 수 (분석 정확도 ↔ 비용)", 100, 10000, 1000, step=100)
    if st.button("📥 가져와서 분석", type="primary"):
        sql = f"SELECT * FROM `{dataset_full}.{table_name}` LIMIT {sample_size}"
        try:
            with st.spinner(f"{sample_size}행 조회 중..."):
                df = get_loader().query(sql)
            st.session_state["learn_df"] = df
            st.session_state["learn_table"] = table_name
            st.session_state["learn_dataset"] = dataset_full
        except Exception as e:
            st.error(f"조회 실패: {e}")
else:
    sql = st.text_area("SQL", value=f"SELECT * FROM `{dataset_full}.ai_visibility` LIMIT 1000", height=100)
    table_label = st.text_input("이 결과를 어떤 테이블 이름으로 저장할까요?", value="ai_visibility")
    if st.button("▶️ 실행하고 분석", type="primary"):
        try:
            with st.spinner("쿼리 실행 중..."):
                df = get_loader().query(sql)
            st.session_state["learn_df"] = df
            st.session_state["learn_table"] = table_label
            st.session_state["learn_dataset"] = dataset_full
        except Exception as e:
            st.error(f"실패: {e}")


# ── 2단계: 자동 분석 + PIC 검수 ──────────────────────────────────────
df = st.session_state.get("learn_df")
table_name = st.session_state.get("learn_table")
dataset_full = st.session_state.get("learn_dataset", dataset_full)

if df is None or df.empty:
    st.info("위에서 데이터를 가져오면 분석 결과가 여기에 표시됩니다.")
    st.stop()

st.markdown(f"## 2단계 — 분석 결과 (`{table_name}`, {len(df)}행)")

# 기존 스키마(있다면) 로드 — PIC 입력 기본값으로 활용
prev = schema_store.load_latest(dataset_full, table_name) or {}
prev_cols_by_name = {c["name"]: c for c in prev.get("columns", [])}

st.dataframe(df.head(10), use_container_width=True)

st.markdown("### 컬럼별 검수")
st.caption("자동 분석 결과를 확인하고, **설명**·**분류**를 작성·확인하세요. "
           "기존 스키마가 있으면 입력값이 자동 채워져 있습니다.")

CATEGORY_OPTIONS = ["차원(Dimension)", "측정값(Metric)", "메타(System)", "ID/Key", "기타"]


def analyze_column(s: pd.Series) -> dict:
    """단일 컬럼 자동 분석."""
    info = {
        "name": s.name,
        "dtype": str(s.dtype),
        "null_count": int(s.isna().sum()),
        "null_pct": round(s.isna().mean() * 100, 1) if len(s) else 0,
        "distinct_count": int(s.nunique(dropna=True)),
        "sample_values": s.dropna().astype(str).head(5).tolist(),
    }
    if pd.api.types.is_numeric_dtype(s):
        if s.notna().any():
            info["min"] = float(s.min())
            info["max"] = float(s.max())
            info["mean"] = round(float(s.mean()), 3)
        info["bq_type"] = "FLOAT" if pd.api.types.is_float_dtype(s) else "INTEGER"
    elif pd.api.types.is_datetime64_any_dtype(s):
        info["bq_type"] = "TIMESTAMP"
    elif pd.api.types.is_bool_dtype(s):
        info["bq_type"] = "BOOLEAN"
    else:
        info["bq_type"] = "STRING"
    return info


analyzed = [analyze_column(df[c]) for c in df.columns]
edited_cols = []

# 컬럼별 입력 폼
for i, col in enumerate(analyzed):
    with st.expander(f"**`{col['name']}`** ({col['bq_type']}) — null {col['null_pct']}%, distinct {col['distinct_count']}",
                     expanded=False):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            st.markdown(f"**dtype**: `{col['dtype']}`")
            st.markdown(f"**bq_type**: `{col['bq_type']}`")
        with c2:
            st.markdown(f"**distinct**: {col['distinct_count']}")
            st.markdown(f"**null**: {col['null_count']} ({col['null_pct']}%)")
            if "min" in col:
                st.markdown(f"**range**: {col['min']} ~ {col['max']}")
        with c3:
            st.markdown("**샘플 값**")
            st.code("\n".join(col["sample_values"][:5]))

        # PIC 입력
        prev_col = prev_cols_by_name.get(col["name"], {})
        desc = st.text_area(
            "설명",
            value=prev_col.get("description", ""),
            key=f"desc_{col['name']}",
            height=60,
            placeholder="예: AI 검색 가시성 (0~1, 높을수록 좋음)",
        )
        prev_cat = prev_col.get("category", "기타")
        try:
            cat_idx = CATEGORY_OPTIONS.index(prev_cat)
        except ValueError:
            cat_idx = CATEGORY_OPTIONS.index("기타")
        category = st.selectbox(
            "분류",
            CATEGORY_OPTIONS,
            index=cat_idx,
            key=f"cat_{col['name']}",
        )

        edited = dict(col)
        edited["description"] = desc
        edited["category"] = category
        edited_cols.append(edited)


# ── 3단계: 저장 (lineage 스냅샷 추가) ──────────────────────────────────
st.markdown("## 3단계 — 저장")
note = st.text_input("변경 메모 (lineage.md에 기록됨)",
                     placeholder="예: 컬럼 sov 정의 보강, prompts_mentioned 의미 명시")

if st.button("💾 스키마 저장", type="primary"):
    try:
        doc = schema_store.save_schema(
            dataset=dataset_full,
            table=table_name,
            columns=edited_cols,
            row_count=len(df),
            note=note,
        )
        st.success(f"저장 완료. lineage 스냅샷에 추가됨.")
        st.json(doc, expanded=False)
    except Exception as e:
        st.error(f"저장 실패: {e}")
