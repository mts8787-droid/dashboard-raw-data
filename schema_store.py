"""스키마 저장·로드 유틸리티 (테이블별 단일 리니지)
"""
from __future__ import annotations

_DOC = """
저장 위치:
- docs/schema/<dataset>__<table>.json — 테이블별 1개 (latest only, 시간 스냅샷 없음)

각 스키마 파일 구조:
{
  "dataset": "pj-my-geo.semrush_data",
  "table": "ai_visibility",
  "saved_at": "2026-05-06T10:00:00Z",
  "saved_by": "PIC",
  "note": "...",
  "row_count_at_save": 12345,
  "columns": [
    {"name": "tag", "bq_type": "STRING", "nullable": "Y", "key": "",
     "description": "...", "category": "차원(Dimension)",
     "source_file": "...", "source_column": "...", "derivation": "..."},
    ...
  ],
  "lineage": {
    "role": "raw" | "transform" | "mapping",
    "frequency": "daily" | "weekly" | "monthly" | "static",
    "sources": [
      {"system": "SEMrush API", "frequency": "weekly"} |
      {"table": "visibility", "join_on": "prompt_id"}
    ],
    "downstream": ["report_visibility", ...],
    "transforms": ["GROUP BY ...", "AVG(...) ..."]
  }
}
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SCHEMA_DIR = ROOT / "docs" / "schema"


def _slug(dataset: str, table: str) -> str:
    return (dataset.replace(".", "__") + "__" + table).replace("/", "_")


def latest_path(dataset: str, table: str) -> Path:
    return SCHEMA_DIR / f"{_slug(dataset, table)}.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_schema(dataset: str, table: str, columns: list, *,
                lineage: dict | None = None,
                row_count: int = 0,
                saved_by: str = "PIC",
                note: str = "") -> dict:
    """테이블별 단일 스키마 저장 (시간 스냅샷 없음)."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    doc = {
        "dataset": dataset,
        "table": table,
        "saved_at": now_iso(),
        "saved_by": saved_by,
        "note": note,
        "row_count_at_save": row_count,
        "columns": columns,
        "lineage": lineage or {},
    }
    latest_path(dataset, table).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str)
    )
    return doc


def load_latest(dataset: str, table: str) -> dict | None:
    p = latest_path(dataset, table)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def all_tables() -> list[dict]:
    """저장된 모든 테이블 메타 + 컬럼 수 (요약)."""
    if not SCHEMA_DIR.exists():
        return []
    out = []
    for p in sorted(SCHEMA_DIR.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
            ds, tb = doc.get("dataset"), doc.get("table")
            if not ds or not tb:
                continue
            out.append({
                "dataset": ds,
                "table": tb,
                "column_count": len(doc.get("columns", [])),
                "saved_at": doc.get("saved_at"),
                "lineage_role": (doc.get("lineage") or {}).get("role", ""),
                "_path": str(p),
            })
        except Exception:
            continue
    return out


def all_table_keys() -> list[tuple[str, str]]:
    return [(t["dataset"], t["table"]) for t in all_tables()]
