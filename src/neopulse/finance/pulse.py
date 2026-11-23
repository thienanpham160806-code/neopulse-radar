"""Điểm Nhịp Thị Trường (Market Pulse Score, 0-100) - tổng hợp 5 thành phần, mỗi thành phần trong [-1, 1].

  Thành phần     Công thức                                              Trọng số
  breadth        (tăng - giảm) / (tăng + giảm)                           0,30
  momentum       tanh(% thay đổi chỉ số / sigma)                         0,25
  book           trung bình OBI_3 có trọng số theo giá trị khớp          0,20
  foreign        Σ mua ròng NN / Σ (mua + bán) NN                        0,15
  liquidity      tanh(ln(GTGD hiện tại / GTGD kỳ vọng cùng thời điểm))   0,10

  score = 50 + 50 * Σ w_i * c_i   (chỉ tính trên thành phần có dữ liệu, chuẩn hóa lại trọng số)

* sigma: độ lệch chuẩn % thay đổi cuối phiên của các phiên đã lưu (>= 5 phiên), mặc định 1,0 điểm %.
* GTGD kỳ vọng: trung vị GTGD lũy kế của các phiên trước tại cùng số phút giao dịch đã trôi qua.
* Trọng số là LỰA CHỌN THIẾT KẾ (ưu tiên độ lan tỏa hơn biên độ chỉ số), không phải ước lượng thống kê;
  `sensitivity()` cho biết nhãn trạng thái thay đổi thế nào khi xáo trộn trọng số.
Điểm mô tả trạng thái HIỆN TẠI, không phải dự báo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .microstructure import add_book_metrics

WEIGHTS = {"breadth": 0.30, "momentum": 0.25, "book": 0.20, "foreign": 0.15, "liquidity": 0.10}
LABELS = [(65, "Tích cực lan tỏa"), (55, "Nghiêng tích cực"), (45, "Trung tính - giằng co"),
          (35, "Nghiêng tiêu cực"), (-1, "Tiêu cực lan tỏa")]
COMPONENT_NAMES = {"breadth": "Độ rộng thị trường", "momentum": "Động lượng chỉ số", "book": "Mất cân bằng sổ lệnh",
                   "foreign": "Khối ngoại", "liquidity": "Thanh khoản"}


def label_for(score: float) -> str:
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "Không đủ dữ liệu"
    return next(name for cut, name in LABELS if score >= cut)


@dataclass
class Pulse:
    score: float
    label: str
    components: dict[str, float] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    inputs: dict[str, float] = field(default_factory=dict)


def combine(components: dict[str, float | None], weights: dict[str, float] | None = None) -> Pulse:
    w = weights or WEIGHTS
    have = {k: float(v) for k, v in components.items()
            if k in w and v is not None and not (isinstance(v, float) and math.isnan(v))}
    missing = [k for k in w if k not in have]
    if not have or sum(w[k] for k in have) < 0.5:  # dưới một nửa trọng số có dữ liệu => không kết luận
        return Pulse(float("nan"), "Không đủ dữ liệu", have, missing)
    wsum = sum(w[k] for k in have)
    raw = sum(w[k] * max(-1.0, min(1.0, have[k])) for k in have) / wsum
    score = round(50 + 50 * raw, 1)
    return Pulse(score, label_for(score), have, missing)


def weighted_obi(latest: pd.DataFrame) -> float:
    if latest.empty:
        return float("nan")
    t = add_book_metrics(latest).dropna(subset=["obi3"])
    w = t["total_value"].fillna(0)
    if t.empty:
        return float("nan")
    return float((t["obi3"] * w).sum() / w.sum()) if w.sum() > 0 else float(t["obi3"].mean())


def expected_value_at(history: pd.DataFrame, minutes: float) -> float:
    """Trung vị GTGD lũy kế của các phiên trước tại cùng số phút giao dịch đã trôi qua.

    `history`: index_ticks của CÁC PHIÊN TRƯỚC (không gồm phiên hiện tại) với cột `elapsed_min`.
    """
    if history.empty or "elapsed_min" not in history:
        return float("nan")
    vals = []
    for _, g in history.groupby("trading_date"):
        g = g[g["elapsed_min"] <= minutes]
        if len(g):
            vals.append(g["total_value"].iloc[-1])
    return float(np.median(vals)) if len(vals) >= 3 else float("nan")


def compute_pulse(index_row: pd.Series | dict | None, latest_quotes: pd.DataFrame, *,
                  sigma_pct: float = 1.0, expected_value: float = float("nan")) -> Pulse:
    comps: dict[str, float | None] = dict.fromkeys(WEIGHTS)
    inputs: dict[str, float] = {}
    if index_row is not None:
        adv, dec = index_row.get("advances"), index_row.get("declines")
        if adv is not None and dec is not None and pd.notna(adv) and pd.notna(dec) and (adv + dec) > 0:
            comps["breadth"] = (adv - dec) / (adv + dec)
            inputs.update(advances=float(adv), declines=float(dec))
        pc = index_row.get("pct_change")
        if pc is not None and pd.notna(pc):
            comps["momentum"] = math.tanh(pc / max(sigma_pct, 1e-6))
            inputs.update(pct_change=float(pc), sigma_pct=float(sigma_pct))
        tv = index_row.get("total_value")
        if tv is not None and pd.notna(tv) and tv > 0 and expected_value and expected_value > 0 and not math.isnan(expected_value):
            comps["liquidity"] = math.tanh(math.log(tv / expected_value))
            inputs.update(total_value=float(tv), expected_value=float(expected_value))
    if not latest_quotes.empty:
        comps["book"] = weighted_obi(latest_quotes)
        buy, sell = latest_quotes["f_buy_val"].fillna(0).sum(), latest_quotes["f_sell_val"].fillna(0).sum()
        if buy + sell > 0:
            comps["foreign"] = (buy - sell) / (buy + sell)
            inputs.update(f_net_val=float(buy - sell))
    p = combine(comps)
    p.inputs = inputs
    return p


def sensitivity(components: dict[str, float], n: int = 500, jitter: float = 0.5, seed: int = 0) -> dict:
    """Độ nhạy theo trọng số: nhân ngẫu nhiên mỗi trọng số với U(1-jitter, 1+jitter) rồi tính lại."""
    base = combine(components)
    if math.isnan(base.score):
        return {"base": float("nan"), "p05": float("nan"), "p95": float("nan"), "label_stability": float("nan")}
    rng = np.random.default_rng(seed)
    scores, same = [], 0
    for _ in range(n):
        w = {k: v * float(rng.uniform(1 - jitter, 1 + jitter)) for k, v in WEIGHTS.items()}
        tot = sum(w.values())
        p = combine(components, {k: v / tot for k, v in w.items()})
        scores.append(p.score)
        same += p.label == base.label
    return {"base": base.score, "p05": float(np.percentile(scores, 5)), "p95": float(np.percentile(scores, 95)),
            "label_stability": same / n}
