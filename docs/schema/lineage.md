# 데이터 스키마 리니지 (Lineage)

PIC가 BigQuery 쿼리 결과로부터 학습·승인한 스키마 변경 이력 (시간 역순).

각 행은 `docs/schema/lineage/<file>.json` 스냅샷에 대응. 자세한 컬럼 정의는 JSON 참조.

| 시각 | 데이터셋 | 테이블 | 컬럼 수 | 작성자 | 메모 |
|---|---|---|---:|---|---|
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `competitor_brand` | 0 | PIC | [빈 스켈레톤] 본부/제품 카테고리/브랜드 매핑 — LG와 경쟁사 브랜드 분류 기준. 컬럼 미확정. |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `domain_mapping` | 0 | PIC | [빈 스켈레톤] 도메인 주소 → 도메인 유형 매핑 테이블 — domain_type 분류 기준 미확정. PIC가 BigQuery 적재 후 등록 필요. |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `report_citation` | 0 | PIC | [빈 스켈레톤] 리포트용 — citation ⨝ prompt_master ⨝ domain_mapping 결과 — 변환 규칙: Source 정제, Domain 추출, Scnd_depth 생성. 컬럼 명세 미확정. |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `citation` | 0 | PIC | [빈 스켈레톤] 원천 데이터 — 프롬프트 기반 인용 집계 (월 단위 전달) — 시트에 컬럼 정의 없음. PIC가 BigQuery 실테이블에서 schema_learning으로 등록 필요. |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `visibility` | 0 | PIC | [빈 스켈레톤] 원천 데이터 — LG 및 경쟁사 가시성 집계 (기간 단위) — 시트에 예시 행만 존재. prompt_master와 동일 형태로 추정되나 스펙 미확정. PIC schema_learning에서 BigQuery 실데이터 가져와 컬럼 등록 필요. |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `report_visibility` | 10 | PIC | Phase A 초안 — 시트 §4.3 import. Group By: start_date, end_date, cntr, ctg, bns, brand |
| 2026/05/06/073404 | `pj-my-geo.semrush_data` | `prompt_master` | 12 | PIC | Phase A 초안 — 시트 §4.1 import (출처: https://docs.google.com/spreadsheets/d/1zgs-BV4gyhR0uGSCX3Mww8loacpDcWcYV-BVMhbUOno) |
