"""Phase A — 시트 기반 7개 테이블 초기 스키마 + lineage 첫 스냅샷 생성

시트(1zgs-...)의 §4.1 prompt_master, §4.3 report_visibility는 컬럼 정의 사용.
나머지 5개(visibility, citation, report_citation, domain_mapping, competitor_brand)는
빈 컬럼 + role/note만 등록 → PIC가 schema_learning 페이지에서 채워넣음.

실행:
    python scripts/init_phase_a.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import schema_store

DATASET = "pj-my-geo.semrush_data"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1zgs-BV4gyhR0uGSCX3Mww8loacpDcWcYV-BVMhbUOno"


def col(name, bq_type, nullable=True, key="", description="", category="기타", **extra):
    """컬럼 dict 생성 헬퍼."""
    return {
        "name": name,
        "bq_type": bq_type,
        "dtype": _bq_to_dtype(bq_type),
        "nullable": "Y" if nullable else "N",
        "key": key,
        "description": description,
        "category": category,
        "null_pct": None,
        "distinct_count": None,
        "sample_values": [],
        **extra,
    }


def _bq_to_dtype(bq_type):
    return {
        "STRING": "object", "INT64": "int64", "FLOAT64": "float64",
        "DATE": "date", "TIMESTAMP": "datetime64[ns]",
        "BOOL": "bool", "NUMERIC": "object",
    }.get(bq_type, "object")


# ─── 1. prompt_master (시트 §4.1) ─────────────────────────────────
PROMPT_MASTER_COLS = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자 (1부터 순차)"),
    col("prompt_id", "STRING", nullable=False, key="FK", category="ID/Key",
        description="프롬프트 식별자 (14자리: Workspace+CNTR+DIV+CTG+STT+BNS+CEJ+시퀀스)"),
    col("start_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 기준 시작일"),
    col("end_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 기준 종료일"),
    col("cntr", "STRING", nullable=False, category="차원(Dimension)",
        description="국가 코드 (예: UK, US, DE)"),
    col("brand", "STRING", category="차원(Dimension)",
        description="브랜드명 (LG·Samsung 등)"),
    col("model", "STRING", category="차원(Dimension)",
        description="LLM 모델명 (Chat GPT·ChatGPT (No Search)·Perplexity 등)"),
    col("position", "STRING", category="측정값(Metric)",
        description="노출 위치 (LLM 응답 내 순위, -1=미노출)"),
    col("mentions", "INT64", category="측정값(Metric)",
        description="언급 수"),
    col("visibility", "STRING", category="측정값(Metric)",
        description="가시성 값 (원천은 STRING으로 적재 — 가공 단계에서 decimal로 변환)"),
    col("input_at", "TIMESTAMP", category="메타(System)",
        description="데이터 추출 시각"),
    col("updated_at", "TIMESTAMP", category="메타(System)",
        description="데이터 수정 시각"),
]


# ─── 2. report_visibility (시트 §4.3) ───────────────────────────
REPORT_VISIBILITY_COLS = [
    col("id", "INT64", key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자 (1부터 순차 부여)",
        source_file="생성", source_column="생성", derivation="1부터 순차 부여"),
    col("start_date", "DATE", category="차원(Dimension)",
        description="데이터 수집 기준 시작일",
        source_file="visibility", source_column="start_date", derivation="원천 사용"),
    col("end_date", "DATE", category="차원(Dimension)",
        description="데이터 수집 기준 종료일",
        source_file="visibility", source_column="end_date", derivation="원천 사용"),
    col("cntr", "STRING", nullable=False, category="차원(Dimension)",
        description="국가 코드",
        source_file="visibility", source_column="cntr", derivation="원천 사용"),
    col("div", "STRING", nullable=False, category="차원(Dimension)",
        description="DIV 분류값 (본부 코드)",
        source_file="prompt_master", source_column="div",
        derivation="prompt_id + cntr 기준 조인"),
    col("ctg", "STRING", nullable=False, category="차원(Dimension)",
        description="CTG 분류값 (제품 카테고리)",
        source_file="prompt_master", source_column="ctg",
        derivation="prompt_id + cntr 기준 조인"),
    col("stt", "STRING", nullable=False, category="차원(Dimension)",
        description="STT 분류값 (Launched=L / Unlaunched=U)",
        source_file="prompt_master", source_column="stt",
        derivation="prompt_id + cntr 기준 조인"),
    col("bns", "STRING", nullable=False, category="차원(Dimension)",
        description="BNS 분류값 (Brand=B / Nonbrand=N)",
        source_file="prompt_master", source_column="bns",
        derivation="prompt_id + cntr 기준 조인"),
    col("brand", "STRING", nullable=False, category="차원(Dimension)",
        description="브랜드명",
        source_file="visibility", source_column="brand", derivation="원천 사용"),
    col("visibility", "NUMERIC", category="측정값(Metric)",
        description="가시성 값 (Group By 후 평균 % — decimal(5,2))",
        source_file="visibility", source_column="visibility",
        derivation="AVG(visibility) %",
        bq_precision="5", bq_scale="2"),
]


# ─── 3~7. 빈 스켈레톤 (PIC가 schema_learning에서 채움) ─────────
EMPTY_TABLES = [
    {
        "table": "visibility",
        "role": "원천 데이터 — LG 및 경쟁사 가시성 집계 (기간 단위)",
        "note": "시트에 예시 행만 존재. prompt_master와 동일 형태로 추정되나 스펙 미확정. PIC schema_learning에서 BigQuery 실데이터 가져와 컬럼 등록 필요.",
    },
    {
        "table": "citation",
        "role": "원천 데이터 — 프롬프트 기반 인용 집계 (월 단위 전달)",
        "note": "시트에 컬럼 정의 없음. PIC가 BigQuery 실테이블에서 schema_learning으로 등록 필요.",
    },
    {
        "table": "report_citation",
        "role": "리포트용 — citation ⨝ prompt_master ⨝ domain_mapping 결과",
        "note": "변환 규칙: Source 정제, Domain 추출, Scnd_depth 생성. 컬럼 명세 미확정.",
    },
    {
        "table": "domain_mapping",
        "role": "도메인 주소 → 도메인 유형 매핑 테이블",
        "note": "domain_type 분류 기준 미확정. PIC가 BigQuery 적재 후 등록 필요.",
    },
    {
        "table": "competitor_brand",
        "role": "본부/제품 카테고리/브랜드 매핑",
        "note": "LG와 경쟁사 브랜드 분류 기준. 컬럼 미확정.",
    },
]


def main():
    print(f"Phase A 초기화 시작 → dataset={DATASET}\n")

    # 1) prompt_master
    schema_store.save_schema(
        dataset=DATASET, table="prompt_master",
        columns=PROMPT_MASTER_COLS, row_count=0,
        saved_by="init-script",
        note=f"Phase A 초안 — 시트 §4.1 import (출처: {SHEET_URL})",
    )
    print(f"  ✓ prompt_master ({len(PROMPT_MASTER_COLS)} cols)")

    # 2) report_visibility
    schema_store.save_schema(
        dataset=DATASET, table="report_visibility",
        columns=REPORT_VISIBILITY_COLS, row_count=0,
        saved_by="init-script",
        note=f"Phase A 초안 — 시트 §4.3 import. Group By: start_date, end_date, cntr, ctg, bns, brand",
    )
    print(f"  ✓ report_visibility ({len(REPORT_VISIBILITY_COLS)} cols)")

    # 3~7) 빈 스켈레톤
    for tb in EMPTY_TABLES:
        schema_store.save_schema(
            dataset=DATASET, table=tb["table"],
            columns=[], row_count=0,
            saved_by="init-script",
            note=f"[빈 스켈레톤] {tb['role']} — {tb['note']}",
        )
        print(f"  ✓ {tb['table']:20s} (skeleton — 컬럼 미정의)")

    print(f"\n완료. lineage.md 7행 추가됨.")
    print(f"PIC 다음 작업: 빈 스켈레톤 5개를 schema_learning 페이지에서 채워주세요.")


if __name__ == "__main__":
    main()
