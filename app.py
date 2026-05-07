"""SEMrush Enterprise Dashboard — 메인 (st.navigation)"""

import streamlit as st

# ── 페이지 정의 (섹션별 뎁스) ──
pages = {
    "수집/쿼리": [
        st.Page("pages/semrush_collect.py", title="SEMrush 수집", icon="📡"),
        st.Page("pages/sql_query.py", title="SQL 쿼리", icon="🗄️"),
    ],
    "모니터링": [
        st.Page("pages/data_status.py", title="데이터 현황", icon="📊"),
    ],
    "설정": [
        st.Page("pages/connection_settings.py", title="연결 설정", icon="⚙️"),
    ],
    "문서": [
        st.Page("pages/schema_define.py", title="스키마 정의", icon="🧠"),
        st.Page("pages/data_lineage.py", title="데이터 리니지", icon="📜"),
        st.Page("pages/ddl_generate.py", title="DDL 생성", icon="🛠️"),
    ],
}

pg = st.navigation(pages)

# ── 사이드바 하단: 연결 상태 ──
with st.sidebar:
    st.markdown("---")
    st.markdown("### 연결 상태")

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

pg.run()
