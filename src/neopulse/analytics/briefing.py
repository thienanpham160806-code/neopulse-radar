"""Bản tin cuối phiên dạng HTML tự chứa (không cần mạng, không JavaScript) - gửi/in/lưu trữ được."""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from ..finance.pulse import COMPONENT_NAMES, WEIGHTS
from ..timeutil import now_vn
from .explain import template_summary
from .formatting import vn_digits
from .view import SessionView, fmt_money


def sparkline(values: list[float], width: int = 560, height: int = 110, color: str = "#1d4ed8",
              baseline: float | None = None) -> str:
    """Đồ thị đường SVG tối giản (đủ để đọc xu hướng trong bản tin tĩnh)."""
    vals = [float(x) for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if len(vals) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    lo, hi = min(vals + ([baseline] if baseline is not None else [])), max(vals + ([baseline] if baseline is not None else []))
    span = (hi - lo) or 1.0
    pad = 6
    xs = [pad + i * (width - 2 * pad) / (len(vals) - 1) for i in range(len(vals))]
    ys = [height - pad - (v - lo) / span * (height - 2 * pad) for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys, strict=True))
    base = ""
    if baseline is not None:
        by = height - pad - (baseline - lo) / span * (height - 2 * pad)
        base = f'<line x1="{pad}" x2="{width - pad}" y1="{by:.1f}" y2="{by:.1f}" stroke="#94a3b8" stroke-dasharray="4 4"/>'
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img">{base}'
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}"/></svg>')


def render_briefing(v: SessionView, out_path: str | Path | None = None) -> str:
    env = Environment(loader=PackageLoader("neopulse.analytics", "templates"),
                      autoescape=select_autoescape(["html", "j2"]))
    # Định dạng số kiểu Việt Nam (1.234,56) cho mọi con số hiển thị trong bản tin.
    env.filters["money"] = lambda x: vn_digits(fmt_money(x))
    env.filters["num"] = lambda x, nd=2: "—" if x is None or pd.isna(x) else vn_digits(f"{x:,.{nd}f}")
    env.filters["signed"] = lambda x, nd=2: "—" if x is None or pd.isna(x) else vn_digits(f"{x:+,.{nd}f}")
    env.filters["vn"] = vn_digits
    env.filters["dmy"] = lambda d: "/".join(reversed(str(d)[:10].split("-")))
    comps = []
    if v.pulse:
        for k, w in WEIGHTS.items():
            val = v.pulse.components.get(k)
            comps.append({"name": COMPONENT_NAMES[k], "weight": w, "value": val,
                          "pct": 50 if val is None else 50 + 50 * max(-1, min(1, val))})
    html = env.get_template("briefing.html.j2").render(
        v=v, generated=now_vn().strftime("%H:%M, %d/%m/%Y"), summary=template_summary(v), comps=comps,
        index_svg=sparkline(v.index["value"].tolist() if len(v.index) else [],
                            baseline=(v.index_row["value"] - v.index_row["change"]) if v.index_row and v.index_row.get("change") is not None else None),
        pulse_svg=sparkline(v.pulse_series["score"].tolist() if len(v.pulse_series) else [], color="#7c3aed", baseline=50),
        basis_svg=sparkline(v.basis["basis"].tolist() if len(v.basis) else [], color="#b45309", baseline=0),
        top_rank=v.ranking.head(8).reset_index().to_dict("records") if len(v.ranking) else [],
        illiquid=v.liquidity.sort_values("liq_score").head(5).reset_index().to_dict("records") if len(v.liquidity) else [],
        f_buy=v.foreign.head(5).reset_index().to_dict("records") if len(v.foreign) else [],
        f_sell=v.foreign.tail(5).iloc[::-1].reset_index().to_dict("records") if len(v.foreign) else [],
        alerts=v.alerts.sort_values(["severity", "ts"], key=lambda s: s.map({"CAO": 0, "TRUNG BÌNH": 1, "THẤP": 2}) if s.name == "severity" else s,
                                    ascending=[True, False]).head(20).to_dict("records") if len(v.alerts) else [],
    )
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(html, encoding="utf-8")
    return html
