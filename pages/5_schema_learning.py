"""스키마 학습 페이지 (human-in-the-loop)

흐름:
1. 데이터셋·테이블 선택 (또는 임의 SQL)
2. 시스템이 컬럼별 자동 분석 (dtype, null%, distinct count, sample values)
3. PIC가 컬럼별 description·category + 테이블 lineage 입력
4. 저장 → docs/schema/<table>.json (테이블별 단일 latest, 시간 스냅샷 X)
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
        table_name = st.text_input("테이블 이름", value="L0_Raw_visibility")
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
    sql = st.text_area("SQL", value=f"SELECT * FROM `{dataset_full}.L0_Raw_visibility` LIMIT 1000", height=100)
    table_label = st.text_input("이 결과를 어떤 테이블 이름으로 저장할까요?", value="L0_Raw_visibility")
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


# ── 3단계: 리니지 입력 (이 테이블의 데이터 흐름) ────────────────
st.markdown("## 3단계 — 데이터 리니지")
st.caption("이 테이블이 어디서 왔고 어디로 가는지 기록 — 테이블별 단일 latest")

prev_lin = prev.get("lineage") or {}

c1, c2 = st.columns(2)
with c1:
    role = st.selectbox(
        "역할",
        ["raw", "transform", "mapping"],
        index=["raw", "transform", "mapping"].index(prev_lin.get("role", "raw"))
            if prev_lin.get("role") in {"raw", "transform", "mapping"} else 0,
    )
with c2:
    freq = st.selectbox(
        "주기",
        ["daily", "weekly", "monthly", "static"],
        index=["daily", "weekly", "monthly", "static"].index(prev_lin.get("frequency", "weekly"))
            if prev_lin.get("frequency") in {"daily", "weekly", "monthly", "static"} else 1,
    )

st.markdown("#### 상류 (Sources)")
st.caption("외부 시스템: `system: SEMrush API`. 다른 테이블: `table: visibility, join_on: prompt_id`")
sources_raw = st.text_area(
    "한 줄에 하나씩 입력 (JSON 객체)",
    value="\n".join([
        ('{"system": "' + s.get("system", "") + '", "frequency": "' + s.get("frequency", "") + '"}')
        if "system" in s else
        ('{"table": "' + s.get("table", "") + '", "join_on": "' + s.get("join_on", "") + '"}')
        for s in (prev_lin.get("sources") or [])
    ]),
    height=80,
    placeholder='{"system": "SEMrush API", "frequency": "weekly"}\n{"table": "L0_Raw_prompt_master", "join_on": "prompt_id"}',
)

st.markdown("#### 하류 (Downstream)")
downstream_raw = st.text_input(
    "쉼표로 구분된 하류 테이블 이름",
    value=", ".join(prev_lin.get("downstream") or []),
    placeholder="L1_report_visibility, L1_report_citation",
)

st.markdown("#### 변환 규칙 (transforms)")
transforms_raw = st.text_area(
    "한 줄에 하나",
    value="\n".join(prev_lin.get("transforms") or []),
    height=80,
    placeholder="GROUP BY start_date, end_date, cntr, ctg, bns, brand\nAVG(visibility) → visibility (decimal(5,2))",
)


# ── 4단계: 저장 ──────────────────────────────────────────────────────
import json as _json

st.markdown("## 4단계 — 저장")
note = st.text_input("변경 메모", placeholder="예: ERD 기반 컬럼 정의 보강")

if st.button("💾 스키마 저장", type="primary"):
    # lineage 파싱
    sources = []
    for line in (sources_raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = _json.loads(line)
            if isinstance(obj, dict):
                sources.append(obj)
        except Exception:
            st.warning(f"sources 파싱 무시: {line}")

    downstream = [s.strip() for s in (downstream_raw or "").split(",") if s.strip()]
    transforms = [s.strip() for s in (transforms_raw or "").splitlines() if s.strip()]

    lineage = {
        "role": role,
        "frequency": freq,
        "sources": sources,
        "downstream": downstream,
        "transforms": transforms,
    }
    try:
        doc = schema_store.save_schema(
            dataset=dataset_full,
            table=table_name,
            columns=edited_cols,
            lineage=lineage,
            row_count=len(df),
            note=note,
        )
        st.success(f"저장 완료. `{table_name}.json` 갱신됨.")
        st.json(doc, expanded=False)
    except Exception as e:
        st.error(f"저장 실패: {e}")
