"""실제 ERD 다이어그램 기반 7개 테이블 컬럼 정의 import (Phase A 갱신)

이전 init_phase_a.py는 시트 텍스트 §4.1·§4.3만 import → 일부 잘못된 컬럼.
실제 ERD(2026-05-06 PIC 공유)로 정확한 컬럼 정의 등록 → 새 lineage 스냅샷.

이 스크립트 실행 시:
- prompt_master: 12개 → 14개 컬럼 (brand·model·mentions·visibility 제거 + prompt_text·prompt_hash·cej·tpc·active 추가)
- visibility: 빈 스켈레톤 → 12개 컬럼 (이전 잘못 import된 prompt_master가 실은 이 테이블)
- citation·report_citation·domain_mapping·competitor_brand: 빈 → 컬럼 등록
- report_visibility: 10개 → 9개 (stt 제거 — 시트엔 있었으나 ERD엔 없음)

실행:
    python scripts/import_actual_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import schema_store

DATASET = "pj-my-geo.semrush_data"
NOTE_BASE = "ERD 다이어그램 기반 컬럼 정의 import (PIC 2026-05-06 공유)"


def col(name, bq_type, nullable=True, key="", description="", category="기타", **extra):
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


def _bq_to_dtype(t):
    return {"STRING": "object", "INT64": "int64", "FLOAT64": "float64",
            "DATE": "date", "TIMESTAMP": "datetime64[ns]",
            "BOOL": "bool", "NUMERIC": "object"}.get(t, "object")


# ─── 1. prompt_master (14컬럼, 분류체계 마스터) ────────────────────
PROMPT_MASTER = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("prompt_id", "STRING", nullable=False, key="PK/FK", category="ID/Key",
        description="프롬프트 식별자 (14자리: Workspace+CNTR+DIV+CTG+STT+BNS+CEJ+시퀀스). visibility·citation의 FK"),
    col("cntr", "STRING", nullable=False, category="차원(Dimension)",
        description="국가 코드 (UK/US/DE/...)"),
    col("prompt_text", "STRING", nullable=False, category="기타",
        description="프롬프트 원문 본문"),
    col("div", "STRING", category="차원(Dimension)",
        description="본부 분류 (ES/MS/HS)"),
    col("ctg", "STRING", category="차원(Dimension)",
        description="제품 카테고리 (TV/AC/RA/CO/DW/...)"),
    col("stt", "STRING", category="차원(Dimension)",
        description="출시 상태 (L=Launched / U=Unlaunched)"),
    col("bns", "STRING", category="차원(Dimension)",
        description="브랜드/논브랜드 (B=Brand / N=Nonbrand)"),
    col("cej", "STRING", category="차원(Dimension)",
        description="CEJ 단계 (I=Interest / C=Conversion / E=Experience)"),
    col("tpc", "STRING", category="차원(Dimension)",
        description="토픽 분류 (PIC 정의 필요)"),
    col("prompt_hash", "STRING", nullable=False, category="ID/Key",
        description="프롬프트 본문 해시 (중복 검출용)"),
    col("input_at", "TIMESTAMP", category="메타(System)",
        description="최초 적재 시각"),
    col("updated_at", "TIMESTAMP", category="메타(System)",
        description="마지막 수정 시각"),
    col("active", "INT64", category="차원(Dimension)",
        description="활성 플래그 (tinyint 0/1: 1=활성, 0=비활성)",
        bq_note="MySQL tinyint(0,1) → BigQuery INT64로 매핑"),
]


# ─── 2. visibility (12컬럼, LG·경쟁사 가시성 원천) ────────────────
VISIBILITY = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("prompt_id", "STRING", key="FK", category="ID/Key",
        description="prompt_master FK"),
    col("start_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 시작일"),
    col("end_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 종료일"),
    col("cntr", "STRING", category="차원(Dimension)",
        description="국가 코드"),
    col("brand", "STRING", category="차원(Dimension)",
        description="브랜드명 (LG·Samsung 등)"),
    col("model", "STRING", category="차원(Dimension)",
        description="LLM 모델명"),
    col("position", "STRING", category="측정값(Metric)",
        description="LLM 응답 내 노출 위치 (-1=미노출)"),
    col("mentions", "INT64", category="측정값(Metric)",
        description="언급 수"),
    col("visibility", "STRING", category="측정값(Metric)",
        description="가시성 값 (원천 STRING — report에서 평균%로 가공)"),
    col("input_at", "TIMESTAMP", category="메타(System)",
        description="적재 시각"),
    col("updated_at", "TIMESTAMP", category="메타(System)",
        description="수정 시각"),
]


# ─── 3. citation (13컬럼, 인용 원천) ──────────────────────────────
CITATION = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("start_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 시작일"),
    col("end_date", "DATE", nullable=False, category="차원(Dimension)",
        description="데이터 수집 종료일"),
    col("prompt_id", "STRING", key="FK", category="ID/Key",
        description="prompt_master FK"),
    col("cntr", "STRING", category="차원(Dimension)",
        description="국가 코드"),
    col("model", "STRING", category="차원(Dimension)",
        description="LLM 모델명"),
    col("domain_type", "STRING", category="차원(Dimension)",
        description="도메인 유형 (domain_mapping 조인 결과)"),
    col("position", "INT64", category="측정값(Metric)",
        description="인용 노출 순위"),
    col("source", "STRING", category="기타",
        description="원천 인용 텍스트/URL"),
    col("url_cbf", "STRING", category="기타",
        description="정제된 URL (CBF=Citation By Filter? PIC 확인 필요)"),
    col("tag_group", "STRING", category="차원(Dimension)",
        description="태그 그룹"),
    col("input_at", "TIMESTAMP", category="메타(System)",
        description="적재 시각"),
    col("updated_at", "TIMESTAMP", category="메타(System)",
        description="수정 시각"),
]


# ─── 4. report_visibility (9컬럼, ERD 기준 — stt 제외) ────────────
REPORT_VISIBILITY = [
    col("id", "INT64", key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("start_date", "DATE", category="차원(Dimension)",
        description="수집 시작일",
        source_file="visibility", source_column="start_date", derivation="원천 사용"),
    col("end_date", "DATE", category="차원(Dimension)",
        description="수집 종료일",
        source_file="visibility", source_column="end_date", derivation="원천 사용"),
    col("cntr", "STRING", nullable=False, category="차원(Dimension)",
        description="국가 코드",
        source_file="visibility", source_column="cntr", derivation="원천 사용"),
    col("div", "STRING", category="차원(Dimension)",
        description="본부 분류 (HS/MS/ES)",
        source_file="prompt_master", source_column="div", derivation="prompt_id+cntr 조인"),
    col("ctg", "STRING", nullable=False, category="차원(Dimension)",
        description="제품 카테고리",
        source_file="prompt_master", source_column="ctg", derivation="prompt_id+cntr 조인"),
    col("bns", "STRING", nullable=False, category="차원(Dimension)",
        description="브랜드/논브랜드",
        source_file="prompt_master", source_column="bns", derivation="prompt_id+cntr 조인"),
    col("brand", "STRING", nullable=False, category="차원(Dimension)",
        description="브랜드명",
        source_file="visibility", source_column="brand", derivation="원천 사용"),
    col("visibility", "NUMERIC", category="측정값(Metric)",
        description="가시성 값 (Group By 후 평균 %, decimal(5,2))",
        source_file="visibility", source_column="visibility",
        derivation="AVG(visibility) %",
        bq_precision="5", bq_scale="2"),
]


# ─── 5. report_citation (24컬럼, 인용 리포트) ─────────────────────
REPORT_CITATION = [
    col("id", "INT64", key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("start_date", "DATE", nullable=False, category="차원(Dimension)",
        description="수집 시작일", source_file="citation", source_column="start_date"),
    col("end_date", "DATE", nullable=False, category="차원(Dimension)",
        description="수집 종료일", source_file="citation", source_column="end_date"),
    col("prompt_id", "STRING", key="FK", category="ID/Key",
        description="prompt_master FK", source_file="citation", source_column="prompt_id"),
    col("prompt", "STRING", nullable=False, category="기타",
        description="프롬프트 원문", source_file="prompt_master", source_column="prompt_text",
        derivation="prompt_id 기준 조인"),
    col("cntr", "STRING", nullable=False, category="차원(Dimension)",
        description="국가 코드", source_file="citation", source_column="cntr"),
    col("model", "STRING", nullable=False, category="차원(Dimension)",
        description="LLM 모델", source_file="citation", source_column="model"),
    col("source", "STRING", category="기타",
        description="원천 인용 텍스트", source_file="citation", source_column="source"),
    col("source_clnd", "STRING", category="기타",
        description="정제된 source 텍스트 (Source 정제 단계)",
        derivation="citation.source에서 정제"),
    col("domain", "STRING", category="차원(Dimension)",
        description="추출된 도메인",
        derivation="citation.source/url_cbf에서 도메인 추출"),
    col("scnd_depth", "STRING", category="차원(Dimension)",
        description="2차 depth 도메인 (예: lg.com/products → products)",
        derivation="domain에서 두 번째 path 파싱"),
    col("div", "STRING", category="차원(Dimension)",
        description="본부 분류", source_file="prompt_master", source_column="div",
        derivation="prompt_id 조인"),
    col("ctg", "STRING", category="차원(Dimension)",
        description="제품 카테고리", source_file="prompt_master", source_column="ctg",
        derivation="prompt_id 조인"),
    col("stt", "STRING", category="차원(Dimension)",
        description="출시 상태", source_file="prompt_master", source_column="stt",
        derivation="prompt_id 조인"),
    col("bns", "STRING", category="차원(Dimension)",
        description="브랜드/논브랜드", source_file="prompt_master", source_column="bns",
        derivation="prompt_id 조인"),
    col("cej", "STRING", category="차원(Dimension)",
        description="CEJ", source_file="prompt_master", source_column="cej",
        derivation="prompt_id 조인"),
    col("tpc", "STRING", category="차원(Dimension)",
        description="토픽", source_file="prompt_master", source_column="tpc",
        derivation="prompt_id 조인"),
    col("tags", "STRING", category="차원(Dimension)",
        description="추가 태그 묶음 (PIC 정의 필요)"),
    col("source_count", "INT64", category="측정값(Metric)",
        description="해당 도메인이 source로 등장한 횟수"),
    col("position_sum", "INT64", category="측정값(Metric)",
        description="position 누적 합 (평균 산출용)"),
    col("average_position", "NUMERIC", category="측정값(Metric)",
        description="평균 노출 순위 (decimal(10,4))",
        bq_precision="10", bq_scale="4"),
    col("lg_ss", "STRING", category="차원(Dimension)",
        description="LG SoS(Share of Source) 관련 분류 (PIC 확인 필요)"),
    col("page_type", "STRING", category="차원(Dimension)",
        description="페이지 유형 (PLP/PDP/Microsite/...)"),
    col("domain_type", "STRING", category="차원(Dimension)",
        description="도메인 유형", source_file="domain_mapping", source_column="type",
        derivation="domain 조인"),
]


# ─── 6. competitor_brand (4컬럼, 브랜드 분류 매핑) ────────────────
COMPETITOR_BRAND = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("div", "STRING", category="차원(Dimension)",
        description="본부 분류"),
    col("ctg", "STRING", category="차원(Dimension)",
        description="제품 카테고리"),
    col("c_brand", "STRING", category="차원(Dimension)",
        description="경쟁사 브랜드명"),
]


# ─── 7. domain_mapping (3컬럼, 도메인 유형 매핑) ──────────────────
# ※ ERD 이미지에 'domaim_mapping' 오타가 있으나 시트·관례에 따라 'domain_mapping' 사용
DOMAIN_MAPPING = [
    col("id", "INT64", nullable=False, key="PK", category="ID/Key",
        description="테이블 내부 고유 식별자"),
    col("domain", "STRING", category="차원(Dimension)",
        description="도메인 주소 (lg.com 등)"),
    col("type", "STRING", category="차원(Dimension)",
        description="도메인 유형 (Owned/Earned/Paid/Competitor 등 — PIC 분류 기준 정의 필요)"),
]


LINEAGE = {
    "prompt_master": {
        "role": "raw",
        "frequency": "weekly",
        "sources": [{"system": "SEMrush API + 분류체계 정의", "frequency": "weekly"}],
        "downstream": ["visibility", "citation", "report_visibility", "report_citation"],
        "transforms": [
            "prompt_id 14자리 인코딩: Workspace(1) + CNTR(2) + DIV(2) + CTG(2) + STT(1) + BNS(1) + CEJ(1) + 시퀀스(4)",
            "prompt_hash로 중복 검출",
        ],
    },
    "visibility": {
        "role": "raw",
        "frequency": "weekly",
        "sources": [
            {"system": "SEMrush API", "frequency": "weekly"},
            {"table": "prompt_master", "join_on": "prompt_id"},
        ],
        "downstream": ["report_visibility"],
        "transforms": [],
    },
    "citation": {
        "role": "raw",
        "frequency": "monthly",
        "sources": [
            {"system": "SEMrush API", "frequency": "monthly"},
            {"table": "prompt_master", "join_on": "prompt_id"},
        ],
        "downstream": ["report_citation"],
        "transforms": [],
    },
    "report_visibility": {
        "role": "transform",
        "frequency": "weekly",
        "sources": [
            {"table": "visibility", "join_on": "prompt_id"},
            {"table": "prompt_master", "join_on": "prompt_id, cntr"},
        ],
        "downstream": [],
        "transforms": [
            "JOIN visibility ⨝ prompt_master ON prompt_id + cntr",
            "GROUP BY start_date, end_date, cntr, ctg, bns, brand",
            "AVG(visibility) → visibility (decimal(5,2))",
        ],
    },
    "report_citation": {
        "role": "transform",
        "frequency": "monthly",
        "sources": [
            {"table": "citation", "join_on": "prompt_id"},
            {"table": "prompt_master", "join_on": "prompt_id"},
            {"table": "domain_mapping", "join_on": "domain"},
        ],
        "downstream": [],
        "transforms": [
            "JOIN citation ⨝ prompt_master ⨝ domain_mapping",
            "Source 정제: source → source_clnd",
            "Domain 추출: source_clnd → domain",
            "Scnd_depth 생성: domain의 두 번째 path 파싱",
            "tags·page_type·lg_ss 분류 (PIC 정의 필요)",
        ],
    },
    "competitor_brand": {
        "role": "mapping",
        "frequency": "static",
        "sources": [{"system": "PIC 수동 입력 (LG 및 경쟁사 분류)", "frequency": "static"}],
        "downstream": ["report_visibility", "report_citation"],
        "transforms": [],
    },
    "domain_mapping": {
        "role": "mapping",
        "frequency": "static",
        "sources": [{"system": "PIC 수동 입력 (도메인 유형 분류)", "frequency": "static"}],
        "downstream": ["report_citation"],
        "transforms": [],
    },
}


TABLES = [
    ("prompt_master", PROMPT_MASTER, "분류체계 마스터 — 14컬럼"),
    ("visibility", VISIBILITY, "원천 가시성 — 12컬럼"),
    ("citation", CITATION, "원천 인용 — 13컬럼"),
    ("report_visibility", REPORT_VISIBILITY, "리포트 가시성 — 9컬럼"),
    ("report_citation", REPORT_CITATION, "리포트 인용 — 24컬럼"),
    ("competitor_brand", COMPETITOR_BRAND, "경쟁사 브랜드 매핑 — 4컬럼"),
    ("domain_mapping", DOMAIN_MAPPING, "도메인 유형 매핑 — 3컬럼"),
]


def main():
    print(f"ERD + 리니지 import → dataset={DATASET}\n")
    for table, columns, summary in TABLES:
        schema_store.save_schema(
            dataset=DATASET, table=table, columns=columns,
            lineage=LINEAGE.get(table, {}),
            row_count=0, saved_by="ERD-import",
            note=f"{NOTE_BASE} — {summary}",
        )
        print(f"  ✓ {table:20s} ({len(columns)} cols, role={LINEAGE[table]['role']})")
    print(f"\n완료. 7개 테이블 latest 갱신 + 리니지 메타 등록.")


if __name__ == "__main__":
    main()
