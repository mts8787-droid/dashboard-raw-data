"""스키마 저장·로드·diff 유틸리티

저장 위치:
- docs/schema/<dataset>__<table>.json     ← 현재 스키마 (latest)
- docs/schema/lineage/<dataset>__<table>__<YYYY-MM-DD-HHMMSS>.json  ← 버전 스냅샷

각 스키마 파일 구조:
{
  "dataset": "pj-my-geo.semrush_data",
  "table": "ai_visibility",
  "saved_at": "2026-05-06T10:00:00Z",
  "saved_by": "PIC",
  "row_count_at_save": 12345,
  "columns": [
    {
      "name": "tag",
      "dtype": "object",
      "bq_type": "STRING",
      "null_pct": 0.0,
      "distinct_count": 142,
      "sample_values": ["HS__REF__launched__LG", ...],
      "description": "...",   ← PIC 입력
      "category": "차원"        ← PIC 입력 (차원/측정값/메타)
    },
    ...
  ]
}
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SCHEMA_DIR = ROOT / "docs" / "schema"
LINEAGE_DIR = SCHEMA_DIR / "lineage"


def _slug(dataset: str, table: str) -> str:
    """dataset.table → 파일명 안전한 슬러그 (예: pj-my-geo__semrush_data__ai_visibility)."""
    return (dataset.replace(".", "__") + "__" + table).replace("/", "_")


def latest_path(dataset: str, table: str) -> Path:
    return SCHEMA_DIR / f"{_slug(dataset, table)}.json"


def lineage_path(dataset: str, table: str, ts: str) -> Path:
    return LINEAGE_DIR / f"{_slug(dataset, table)}__{ts}.json"


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_schema(dataset: str, table: str, columns: list, row_count: int = 0,
                saved_by: str = "PIC", note: str = "") -> dict:
    """스키마를 latest + lineage 두 곳에 저장."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)

    ts = now_ts()
    doc = {
        "dataset": dataset,
        "table": table,
        "saved_at": now_iso(),
        "saved_by": saved_by,
        "note": note,
        "row_count_at_save": row_count,
        "columns": columns,
    }

    latest = latest_path(dataset, table)
    lineage = lineage_path(dataset, table, ts)
    latest.write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str))
    lineage.write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str))
    update_lineage_md(dataset, table, ts, columns, note)
    return doc


def load_latest(dataset: str, table: str) -> dict | None:
    p = latest_path(dataset, table)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def list_lineage(dataset: str = None, table: str = None) -> list[dict]:
    """lineage 디렉터리의 모든 스냅샷 메타 리스트 (시간 역순)."""
    if not LINEAGE_DIR.exists():
        return []
    items = []
    for p in sorted(LINEAGE_DIR.glob("*.json"), reverse=True):
        try:
            doc = json.loads(p.read_text())
            if dataset and doc.get("dataset") != dataset:
                continue
            if table and doc.get("table") != table:
                continue
            items.append({
                "file": p.name,
                "dataset": doc.get("dataset"),
                "table": doc.get("table"),
                "saved_at": doc.get("saved_at"),
                "saved_by": doc.get("saved_by"),
                "note": doc.get("note", ""),
                "column_count": len(doc.get("columns", [])),
                "row_count_at_save": doc.get("row_count_at_save", 0),
                "_path": str(p),
            })
        except Exception:
            continue
    return items


def load_lineage_doc(path: str) -> dict:
    return json.loads(Path(path).read_text())


def diff_columns(prev_cols: list[dict], curr_cols: list[dict]) -> dict:
    """이전 스키마 vs 현재 스키마 컬럼 단위 diff."""
    prev_by = {c["name"]: c for c in prev_cols or []}
    curr_by = {c["name"]: c for c in curr_cols or []}
    added = [c for n, c in curr_by.items() if n not in prev_by]
    removed = [c for n, c in prev_by.items() if n not in curr_by]
    changed = []
    for name, curr in curr_by.items():
        prev = prev_by.get(name)
        if not prev:
            continue
        diff_fields = {}
        for k in ["dtype", "bq_type", "description", "category"]:
            pv, cv = prev.get(k), curr.get(k)
            if pv != cv:
                diff_fields[k] = {"prev": pv, "curr": cv}
        if diff_fields:
            changed.append({"name": name, "fields": diff_fields})
    return {"added": added, "removed": removed, "changed": changed}


def update_lineage_md(dataset: str, table: str, ts: str, columns: list, note: str = ""):
    """전체 변경 이력을 docs/schema/lineage.md에 append."""
    LINEAGE_MD = SCHEMA_DIR / "lineage.md"
    LINEAGE_MD.parent.mkdir(parents=True, exist_ok=True)

    if not LINEAGE_MD.exists():
        LINEAGE_MD.write_text(
            "# 데이터 스키마 리니지 (Lineage)\n\n"
            "PIC가 BigQuery 쿼리 결과로부터 학습·승인한 스키마 변경 이력 (시간 역순).\n\n"
            "각 행은 `docs/schema/lineage/<file>.json` 스냅샷에 대응. 자세한 컬럼 정의는 JSON 참조.\n\n"
            "| 시각 | 데이터셋 | 테이블 | 컬럼 수 | 작성자 | 메모 |\n"
            "|---|---|---|---:|---|---|\n"
        )

    # 새 행을 헤더 다음에 삽입 (시간 역순)
    lines = LINEAGE_MD.read_text().splitlines()
    header_end = next((i for i, l in enumerate(lines) if l.startswith("|---")), -1)
    if header_end < 0:
        return
    new_row = (
        f"| {ts.replace('-', '/')} | `{dataset}` | `{table}` | "
        f"{len(columns)} | PIC | {note or '—'} |"
    )
    lines.insert(header_end + 1, new_row)
    LINEAGE_MD.write_text("\n".join(lines) + "\n")


def all_table_keys() -> list[tuple[str, str]]:
    """저장된 모든 (dataset, table) 키 반환."""
    if not SCHEMA_DIR.exists():
        return []
    keys = []
    for p in SCHEMA_DIR.glob("*.json"):
        try:
            doc = json.loads(p.read_text())
            ds, tb = doc.get("dataset"), doc.get("table")
            if ds and tb:
                keys.append((ds, tb))
        except Exception:
            continue
    return sorted(set(keys))
