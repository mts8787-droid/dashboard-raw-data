"""SEMrush Enterprise Element-level API 클라이언트

Enterprise API는 워크스페이스 내 리포트 요소(element)별로 데이터를 조회합니다.
각 element_id는 SEMrush Enterprise UI에서 "Generate API Request"로 확인할 수 있습니다.

사용법:
    client = SEMrushClient()

    # 등록된 요소 조회
    df = client.fetch_element("ai_visibility")

    # 커스텀 필터로 조회
    df = client.fetch_element("ai_visibility", filters={
        "simple": {"start_date": "2026-03-01", "end_date": "2026-04-01", "CBF_brand": "LG"},
        "advanced": {"op": "and", "filters": [{"op": "eq", "val": "search-gpt", "col": "CBF_model"}]}
    })

    # element_id 직접 지정
    df = client.fetch_raw("66faab96-...", product="ai", filters={...})
"""

import requests
import pandas as pd
from config import (
    SEMRUSH_API_KEY, SEMRUSH_ENTERPRISE_URL,
    SEMRUSH_WORKSPACE_ID, SEMRUSH_PROJECT_ID,
)


class SEMrushClient:
    """SEMrush Enterprise Element-level API 클라이언트."""

    def __init__(self, api_key=None, workspace_id=None, project_id=None):
        self.api_key = api_key or SEMRUSH_API_KEY
        self.workspace_id = workspace_id or SEMRUSH_WORKSPACE_ID
        self.project_id = project_id or SEMRUSH_PROJECT_ID
        if not self.api_key:
            raise ValueError("SEMRUSH_API_KEY가 설정되지 않았습니다.")
        if not self.workspace_id:
            raise ValueError("SEMRUSH_WORKSPACE_ID가 설정되지 않았습니다.")

    # ── 등록된 요소 (element) 레지스트리 ─────────────────────────
    # SEMrush UI에서 "Generate API Request"로 얻은 element_id를 여기에 등록합니다.
    # key: 사용자 지정 이름, value: (product, element_id, 기본 필터)

    # 지원하는 AI 모델 목록
    AI_MODELS = ["search-gpt", "perplexity", "gpt-5", "gemini-2.5-flash", "copilot", "claude", "meta-ai"]

    ELEMENTS: dict[str, dict] = {
        "ai_visibility": {
            "product": "ai",
            "element_id": "66faab96-0c22-496d-aea1-54c119ac6c5d",
            "description": "AI Visibility — 브랜드별 AI 검색 가시성",
            "default_filters": {
                "simple": {
                    "CBF_brand": "LG",
                },
            },
        },
        # 새 요소를 추가하려면 여기에 등록하세요:
        # "seo_rankings": {
        #     "product": "seo",
        #     "element_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        #     "description": "SEO 키워드 순위",
        #     "default_filters": {...},
        # },
    }

    # ── API 호출 ─────────────────────────────────────────────────

    def _build_url(self, product: str, element_id: str) -> str:
        return (
            f"{SEMRUSH_ENTERPRISE_URL}/workspaces/{self.workspace_id}"
            f"/products/{product}/elements/{element_id}"
        )

    def _request(self, product: str, element_id: str,
                 filters: dict = None, project_id: str = None,
                 target_id: str = None,
                 limit: int = None, offset: int = None) -> dict:
        """Enterprise Element API 호출. JSON dict 반환."""
        url = self._build_url(product, element_id)
        headers = {
            "accept": "application/json",
            "Authorization": f"Apikey {self.api_key}",
            "Content-Type": "application/json",
        }

        render_data = {}
        pid = project_id or self.project_id
        if pid:
            render_data["project_id"] = pid
        if target_id:
            render_data["target_id"] = target_id
        if filters:
            render_data["filters"] = filters
        if limit is not None:
            render_data["limit"] = limit
        if offset is not None:
            render_data["offset"] = offset

        body = {"render_data": render_data} if render_data else {}

        resp = requests.post(url, headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def _to_dataframe(self, response: dict) -> pd.DataFrame:
        """API 응답에서 blocks.data를 DataFrame으로 변환."""
        blocks = response.get("blocks", {})
        data = blocks.get("data", [])
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    # ── 공개 메서드 ──────────────────────────────────────────────

    def fetch_element(self, name: str, filters: dict = None,
                      date_range: tuple = None,
                      limit: int = None, offset: int = None) -> pd.DataFrame:
        """등록된 요소 이름으로 데이터 조회.

        Args:
            name: ELEMENTS에 등록된 키 (예: "ai_visibility")
            filters: 커스텀 필터 (없으면 기본 필터 사용)
            date_range: (start_date, end_date) 튜플 — 기본 필터에 날짜 오버라이드
            limit: 결과 행 수 제한
            offset: 결과 오프셋

        Returns:
            pd.DataFrame
        """
        if name not in self.ELEMENTS:
            available = ", ".join(self.ELEMENTS.keys())
            raise ValueError(f"등록되지 않은 요소: '{name}'. 가능한 값: {available}")

        elem = self.ELEMENTS[name]
        product = elem["product"]
        element_id = elem["element_id"]

        # 필터 결정: 커스텀 > 기본
        if filters is None:
            filters = elem.get("default_filters", {}).copy()
            if filters:
                filters = {"simple": dict(filters.get("simple", {})),
                           "advanced": filters.get("advanced")}

        # 날짜 오버라이드
        if date_range and filters:
            if "simple" not in filters:
                filters["simple"] = {}
            filters["simple"]["start_date"] = date_range[0]
            filters["simple"]["end_date"] = date_range[1]

        # advanced가 None이면 제거
        if filters and filters.get("advanced") is None:
            filters.pop("advanced", None)

        response = self._request(product, element_id, filters,
                                 limit=limit, offset=offset)
        return self._to_dataframe(response)

    def fetch_raw(self, element_id: str, product: str = "seo",
                  filters: dict = None, project_id: str = None,
                  target_id: str = None,
                  limit: int = None, offset: int = None) -> pd.DataFrame:
        """element_id를 직접 지정하여 데이터 조회 (등록 없이 사용).

        Args:
            element_id: SEMrush에서 생성한 element UUID
            product: 제품 카테고리 (seo, ai, advertising 등)
            filters: 필터 dict
            project_id: 프로젝트 ID (없으면 기본값 사용)
            target_id: 타겟 ID (일부 요소에서 필요)
            limit: 결과 행 수 제한
            offset: 결과 오프셋

        Returns:
            pd.DataFrame
        """
        response = self._request(product, element_id, filters,
                                 project_id, target_id, limit, offset)
        return self._to_dataframe(response)

    def fetch_raw_json(self, element_id: str, product: str = "seo",
                       filters: dict = None, project_id: str = None,
                       target_id: str = None) -> dict:
        """element_id로 원본 JSON 응답 반환 (디버깅/분석용)."""
        return self._request(product, element_id, filters,
                             project_id, target_id)

    def _fetch_ai_visibility_single(self, model: str = None,
                                     brand: str = "LG",
                                     date: str = None) -> pd.DataFrame:
        """단일 날짜, 단일 모델 AI Visibility 조회 (내부용)."""
        filters = {"simple": {"CBF_brand": brand}}
        if model:
            filters["advanced"] = {
                "op": "and",
                "filters": [{"op": "eq", "val": model, "col": "CBF_model"}],
            }
        date_range = (date, date) if date else None
        df = self.fetch_element("ai_visibility", filters=filters,
                                date_range=date_range)
        if not df.empty:
            if model:
                df["model"] = model
            if date:
                df["date"] = date
        return df

    def fetch_ai_visibility(self, model: str = None,
                            brand: str = "LG",
                            date_range: tuple = None) -> pd.DataFrame:
        """AI Visibility 데이터를 일별로 조회.

        Args:
            model: AI 모델 (search-gpt, perplexity, gpt-5 등)
                   None이면 모델 필터 없이 전체 조회
            brand: 브랜드 필터 (기본: LG)
            date_range: (start_date, end_date) 튜플

        Returns:
            pd.DataFrame — date, model 컬럼 자동 추가
        """
        if not date_range:
            return self._fetch_ai_visibility_single(model=model, brand=brand)

        from datetime import datetime, timedelta
        import time

        start = datetime.strptime(date_range[0], "%Y-%m-%d")
        end = datetime.strptime(date_range[1], "%Y-%m-%d")

        all_frames = []
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            try:
                df = self._fetch_ai_visibility_single(
                    model=model, brand=brand, date=date_str)
                if not df.empty:
                    all_frames.append(df)
            except Exception:
                pass
            current += timedelta(days=1)
            time.sleep(0.15)

        if not all_frames:
            return pd.DataFrame()
        return pd.concat(all_frames, ignore_index=True)

    def fetch_ai_visibility_all_models(self, brand: str = "LG",
                                        date_range: tuple = None) -> pd.DataFrame:
        """모든 AI 모델의 Visibility 데이터를 일별로 한번에 조회.

        Returns:
            pd.DataFrame — date, model 컬럼 포함
        """
        import time
        all_frames = []
        for model in self.AI_MODELS:
            try:
                df = self.fetch_ai_visibility(model=model, brand=brand,
                                              date_range=date_range)
                if not df.empty:
                    all_frames.append(df)
            except Exception:
                pass
            time.sleep(0.1)
        if not all_frames:
            return pd.DataFrame()
        return pd.concat(all_frames, ignore_index=True)

    def list_elements(self) -> pd.DataFrame:
        """등록된 요소 목록 반환."""
        rows = []
        for name, elem in self.ELEMENTS.items():
            rows.append({
                "name": name,
                "product": elem["product"],
                "element_id": elem["element_id"],
                "description": elem.get("description", ""),
            })
        return pd.DataFrame(rows)
