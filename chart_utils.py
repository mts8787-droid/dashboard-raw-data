"""메트릭 카드 유틸리티 — 비율 기반 바로 증감을 시각화"""

import streamlit as st


def _delta_html(delta, inverse=False):
    """delta 값에 따라 색상 화살표 HTML 반환"""
    if delta is None or delta == 0:
        return '<span style="color:#888;">-</span>'
    # inverse: 에러/경고처럼 줄어드는 게 좋은 경우
    if inverse:
        color = "#22c55e" if delta < 0 else "#ef4444"
    else:
        color = "#22c55e" if delta > 0 else "#ef4444"
    arrow = "▲" if delta > 0 else "▼"
    return f'<span style="color:{color};font-weight:700;">{arrow} {abs(delta):g}</span>'


def metric_cards(items: list[dict]):
    """비율 기반 바가 포함된 메트릭 카드 렌더링.

    items: list of dict, 각 항목:
        - label: str          카드 제목
        - value: float         현재 값
        - display: str         표시할 텍스트 (예: "85/100")
        - delta: float|None    증감값
        - inverse: bool        True면 감소=긍정 (에러/경고용)
        - suffix: str          단위 (선택)
        - color: str           바 색상 (선택, 기본 #3b82f6)
    """
    if not items:
        return

    # ── 비율 계산: min-max 정규화, 패딩 적용 ──
    values = [it["value"] for it in items if it.get("value") is not None]
    if not values:
        return

    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min

    # 전부 같은 값이면 50%로 통일
    if v_range == 0:
        for it in items:
            it["_bar_pct"] = 50
    else:
        # 바 높이 범위: 15% ~ 100% (최솟값도 최소 15%는 보이도록)
        for it in items:
            v = it.get("value", v_min)
            ratio = (v - v_min) / v_range  # 0.0 ~ 1.0
            it["_bar_pct"] = 15 + ratio * 85

    # ── HTML 렌더링 ──
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        label = it.get("label", "")
        display = it.get("display", str(it.get("value", "")))
        delta = it.get("delta")
        inverse = it.get("inverse", False)
        color = it.get("color", "#3b82f6")
        suffix = it.get("suffix", "")
        bar_pct = it.get("_bar_pct", 50)

        delta_str = _delta_html(delta, inverse)

        html = f"""
        <div style="
            background: linear-gradient(135deg, #f8f9fa, #ffffff);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 18px;
            text-align: center;
        ">
            <div style="font-size:0.82rem;color:#64748b;margin-bottom:6px;">{label}</div>
            <div style="font-size:1.6rem;font-weight:800;color:#1e293b;line-height:1.2;">
                {display}{suffix}
            </div>
            <div style="margin:6px 0 10px;">{delta_str}</div>
            <div style="
                background:#e2e8f0;
                border-radius:6px;
                height:8px;
                overflow:hidden;
            ">
                <div style="
                    width:{bar_pct:.1f}%;
                    height:100%;
                    background:{color};
                    border-radius:6px;
                    transition: width 0.4s ease;
                "></div>
            </div>
        </div>
        """
        with col:
            st.markdown(html, unsafe_allow_html=True)


def metric_bars_vertical(items: list[dict], height_px: int = 120):
    """세로 막대 비교 차트 — 값들 간 상대 비율로 높이 결정.

    items: list of dict:
        - label: str
        - value: float
        - display: str (표시 텍스트)
        - delta: float|None
        - inverse: bool
        - color: str
    """
    if not items:
        return

    values = [it["value"] for it in items if it.get("value") is not None]
    if not values:
        return

    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min

    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        v = it.get("value", v_min)
        label = it.get("label", "")
        display = it.get("display", str(v))
        delta = it.get("delta")
        inverse = it.get("inverse", False)
        color = it.get("color", "#3b82f6")

        if v_range == 0:
            bar_h = height_px * 0.5
        else:
            ratio = (v - v_min) / v_range
            bar_h = max(height_px * 0.12, height_px * (0.12 + ratio * 0.88))

        delta_str = _delta_html(delta, inverse)
        top_space = height_px - bar_h

        html = f"""
        <div style="text-align:center;">
            <div style="font-size:0.78rem;color:#64748b;margin-bottom:4px;">{label}</div>
            <div style="font-size:1.3rem;font-weight:800;color:#1e293b;">{display}</div>
            <div style="margin:4px 0;">{delta_str}</div>
            <div style="
                display:flex;
                align-items:flex-end;
                justify-content:center;
                height:{height_px}px;
            ">
                <div style="
                    width:60%;
                    height:{bar_h:.1f}px;
                    background: linear-gradient(180deg, {color}, {color}cc);
                    border-radius:6px 6px 0 0;
                    transition: height 0.4s ease;
                "></div>
            </div>
        </div>
        """
        with col:
            st.markdown(html, unsafe_allow_html=True)
