"""SEMrush Enterprise API 클라이언트

지원 API:
- Position Tracking (Visibility Index, 키워드 순위)
- Listing Management (Citations, NAP 데이터)
- Site Audit (사이트 건강도)
- Projects (프로젝트/캠페인 관리)
- Analytics (도메인/키워드 분석 - 기본 API)
"""

import io
import time
import requests
import pandas as pd
from config import (
    SEMRUSH_API_KEY, SEMRUSH_BASE_URL, SEMRUSH_PROJECTS_URL,
    SEMRUSH_LISTING_URL, SEMRUSH_DATABASE, TARGET_DOMAIN,
    SEMRUSH_PROJECT_ID, SEMRUSH_CAMPAIGN_ID, SEMRUSH_LISTING_TOKEN,
)


class SEMrushClient:
    def __init__(self, api_key=None, database=None, project_id=None,
                 campaign_id=None, listing_token=None):
        self.api_key = api_key or SEMRUSH_API_KEY
        self.database = database or SEMRUSH_DATABASE
        self.project_id = project_id or SEMRUSH_PROJECT_ID
        self.campaign_id = campaign_id or SEMRUSH_CAMPAIGN_ID
        self.listing_token = listing_token or SEMRUSH_LISTING_TOKEN
        if not self.api_key:
            raise ValueError("SEMRUSH_API_KEY가 설정되지 않았습니다.")

    # ── 공통 요청 헬퍼 ───────────────────────────────────────────

    def _analytics_request(self, params: dict) -> pd.DataFrame:
        """기본 Analytics API 호출 (CSV 응답)"""
        params["key"] = self.api_key
        params["database"] = params.get("database", self.database)
        resp = requests.get(SEMRUSH_BASE_URL, params=params, timeout=60)
        resp.raise_for_status()
        text = resp.text.strip()
        if text.startswith("ERROR"):
            raise RuntimeError(f"SEMrush API 에러: {text}")
        return pd.read_csv(io.StringIO(text), sep=";")

    def _projects_request(self, path: str, method="GET", json_body=None) -> dict:
        """Projects API 호출 (JSON 응답)"""
        url = f"{SEMRUSH_PROJECTS_URL}{path}"
        params = {"key": self.api_key}
        resp = requests.request(method, url, params=params, json=json_body, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _listing_request(self, path: str, method="GET", json_body=None) -> dict:
        """Listing Management API 호출 (OAuth Bearer)"""
        if not self.listing_token:
            raise ValueError("SEMRUSH_LISTING_TOKEN이 설정되지 않았습니다.")
        url = f"{SEMRUSH_LISTING_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self.listing_token}",
            "Content-Type": "application/json",
        }
        resp = requests.request(method, url, headers=headers, json=json_body, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _paginated_analytics(self, params: dict, max_rows: int = 10000) -> pd.DataFrame:
        """Analytics API 페이지네이션"""
        all_frames = []
        limit = min(max_rows, 10000)
        offset = 0
        while offset < max_rows:
            params["display_limit"] = limit
            params["display_offset"] = offset
            try:
                df = self._analytics_request(params.copy())
            except (RuntimeError, requests.exceptions.RequestException):
                break
            if df.empty:
                break
            all_frames.append(df)
            offset += len(df)
            if len(df) < limit:
                break
            time.sleep(0.2)
        if not all_frames:
            return pd.DataFrame()
        return pd.concat(all_frames, ignore_index=True)

    # ── Projects 관리 ────────────────────────────────────────────

    def list_projects(self) -> list:
        """모든 프로젝트 목록"""
        return self._projects_request("")

    def get_project(self, project_id: str = None) -> dict:
        """특정 프로젝트 정보"""
        pid = project_id or self.project_id
        return self._projects_request(f"{pid}/")

    # ── Position Tracking (Visibility) ───────────────────────────

    def get_visibility(self, campaign_id: str = None) -> dict:
        """Visibility Index 데이터"""
        cid = campaign_id or self.campaign_id
        return self._projects_request(
            f"{cid}/tracking/?type=tracking_position_organic&action=report"
        )

    def get_position_tracking(self, campaign_id: str = None,
                               url_filter: str = None) -> pd.DataFrame:
        """Position Tracking 키워드 순위 데이터"""
        cid = campaign_id or self.campaign_id
        path = f"{cid}/tracking/?type=tracking_position_organic&action=report"
        if url_filter:
            path += f"&url={url_filter}"
        data = self._projects_request(path)
        if isinstance(data, list):
            return pd.DataFrame(data)
        return pd.DataFrame([data]) if data else pd.DataFrame()

    def get_visibility_history(self, campaign_id: str = None) -> pd.DataFrame:
        """Visibility Index 히스토리"""
        cid = campaign_id or self.campaign_id
        data = self._projects_request(
            f"{cid}/tracking/?type=tracking_position_organic&action=history"
        )
        if isinstance(data, list):
            return pd.DataFrame(data)
        return pd.DataFrame()

    # ── Site Audit ───────────────────────────────────────────────

    def launch_site_audit(self, project_id: str = None) -> dict:
        """사이트 감사 실행"""
        pid = project_id or self.project_id
        return self._projects_request(
            f"{pid}/siteaudit/launch", method="POST"
        )

    def get_site_audit_snapshot(self, project_id: str = None,
                                 snapshot_id: str = None) -> dict:
        """사이트 감사 스냅샷 결과 (건강도 점수 포함)"""
        pid = project_id or self.project_id
        path = f"{pid}/siteaudit/snapshot"
        if snapshot_id:
            path += f"?snapshot_id={snapshot_id}"
        return self._projects_request(path)

    def get_site_audit_issues(self, project_id: str = None,
                               snapshot_id: str = None,
                               issue_id: str = None) -> dict:
        """사이트 감사 이슈 상세"""
        pid = project_id or self.project_id
        path = f"{pid}/siteaudit/snapshot/{snapshot_id}/issue/{issue_id}"
        return self._projects_request(path)

    def get_site_audit_info(self, project_id: str = None) -> pd.DataFrame:
        """사이트 감사 결과를 DataFrame으로 반환"""
        data = self.get_site_audit_snapshot(project_id)
        if not data:
            return pd.DataFrame()

        rows = []
        row = {
            "health_score": data.get("quality", {}).get("value"),
            "health_delta": data.get("quality", {}).get("delta"),
            "pages_crawled": data.get("pages_crawled"),
            "snapshot_id": data.get("snapshot_id"),
            "finish_date": data.get("finish_date"),
            "errors_count": sum(e.get("count", 0) for e in data.get("errors", [])),
            "warnings_count": sum(w.get("count", 0) for w in data.get("warnings", [])),
            "notices_count": sum(n.get("count", 0) for n in data.get("notices", [])),
        }
        rows.append(row)
        return pd.DataFrame(rows)

    # ── Listing Management (Citations) ───────────────────────────

    def get_locations(self, page: int = 1, size: int = 50) -> dict:
        """로컬 리스팅 위치 목록"""
        return self._listing_request(f"locations?page={page}&size={size}")

    def get_location(self, location_id: str) -> dict:
        """특정 위치 상세 정보 (NAP 데이터)"""
        return self._listing_request(f"locations/{location_id}")

    def update_location(self, location_id: str, data: dict) -> dict:
        """위치 정보(NAP) 업데이트"""
        return self._listing_request(
            f"locations/{location_id}", method="PUT", json_body=data
        )

    def get_citations_df(self, page: int = 1, size: int = 50) -> pd.DataFrame:
        """Citation/Listing 데이터를 DataFrame으로 반환"""
        data = self.get_locations(page, size)
        locations = data if isinstance(data, list) else data.get("content", data.get("locations", []))
        if not locations:
            return pd.DataFrame()
        return pd.json_normalize(locations)

    # ── Analytics API (기본) ─────────────────────────────────────

    def domain_overview(self, domain: str = None) -> pd.DataFrame:
        return self._analytics_request({
            "type": "domain_overview",
            "domain": domain or TARGET_DOMAIN,
            "export_columns": "Dn,Rk,Or,Ot,Oc,Ad,At,Ac",
        })

    def domain_organic_keywords(self, domain: str = None, max_rows: int = 10000) -> pd.DataFrame:
        return self._paginated_analytics({
            "type": "domain_organic",
            "domain": domain or TARGET_DOMAIN,
            "export_columns": "Ph,Po,Pp,Pd,Nq,Cp,Ur,Tr,Tc,Co,Nr,Td",
        }, max_rows=max_rows)

    def domain_adwords_keywords(self, domain: str = None, max_rows: int = 10000) -> pd.DataFrame:
        return self._paginated_analytics({
            "type": "domain_adwords",
            "domain": domain or TARGET_DOMAIN,
            "export_columns": "Ph,Po,Pp,Nq,Cp,Ur,Tr,Tc,Co,Nr,Td",
        }, max_rows=max_rows)

    def domain_backlinks_overview(self, domain: str = None) -> pd.DataFrame:
        return self._analytics_request({
            "type": "backlinks_overview",
            "target": domain or TARGET_DOMAIN,
            "target_type": "root_domain",
            "export_columns": "total,domains_num,urls_num,ips_num,follows_num,nofollows_num,texts_num,images_num",
        })

    def organic_competitors(self, domain: str = None, max_rows: int = 100) -> pd.DataFrame:
        return self._analytics_request({
            "type": "domain_organic_organic",
            "domain": domain or TARGET_DOMAIN,
            "display_limit": max_rows,
            "export_columns": "Dn,Cr,Np,Or,Ot,Oc,Ad",
        })
