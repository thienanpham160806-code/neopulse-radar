"""Độ rộng thị trường - đo mức lan tỏa của chuyển động giá, độc lập với vốn hóa.

  ad_ratio   = (số mã tăng - số mã giảm) / (số mã tăng + số mã giảm)      trong [-1, 1]
  ad_line    = Σ theo thời gian của (tăng - giảm) trong phiên
  ext_spread = (số mã trần - số mã sàn) / tổng số mã
Chỉ số có thể tăng nhờ vài mã vốn hóa lớn trong khi đa số mã giảm; `divergence()` gắn cờ trường
hợp chỉ số và độ rộng ngược chiều nhau.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_breadth(index_ticks: pd.DataFrame) -> pd.DataFrame:
    out = index_ticks.copy()
    if out.empty:
        return out.assign(ad_ratio=pd.Series(dtype=float), ext_spread=pd.Series(dtype=float))
    adv, dec = out["advances"].fillna(0), out["declines"].fillna(0)
    tot = adv + dec + out["no_change"].fillna(0)
    out["ad_ratio"] = np.where((adv + dec) > 0, (adv - dec) / (adv + dec), np.nan)
    out["pct_advancing"] = np.where(tot > 0, adv / tot * 100, np.nan)
    out["ext_spread"] = np.where(tot > 0, (out["n_ceiling"].fillna(0) - out["n_floor"].fillna(0)) / tot, np.nan)
    return out


def universe_breadth(latest: pd.DataFrame) -> dict:
    """Độ rộng tự tính trên rổ đang theo dõi từ dữ liệu từng mã (đối chiếu với số của sàn)."""
    if latest.empty:
        return {"n": 0, "pct_up": np.nan, "pct_above_vwap": np.nan, "n_ceiling": 0, "n_floor": 0, "ad_ratio": np.nan}
    d = latest.dropna(subset=["last", "ref"])
    up, down = (d["last"] > d["ref"]).sum(), (d["last"] < d["ref"]).sum()
    v = d.dropna(subset=["avg_price"])
    return {
        "n": int(len(d)), "n_up": int(up), "n_down": int(down),
        "pct_up": float(up / len(d) * 100) if len(d) else np.nan,
        "pct_above_vwap": float((v["last"] > v["avg_price"]).mean() * 100) if len(v) else np.nan,
        "n_ceiling": int((d["last"] >= d["ceiling"]).sum()), "n_floor": int((d["last"] <= d["floor"]).sum()),
        "ad_ratio": float((up - down) / (up + down)) if (up + down) else np.nan,
    }


def divergence(pct_change: float | None, ad_ratio: float | None, *, idx_eps: float = 0.15,
               breadth_eps: float = 0.15) -> str | None:
    """Phân kỳ chỉ số - độ rộng. Ngưỡng 0,15% và 0,15 là vùng đệm để bỏ qua dao động quanh 0."""
    if pct_change is None or ad_ratio is None or np.isnan(pct_change) or np.isnan(ad_ratio):
        return None
    if pct_change > idx_eps and ad_ratio < -breadth_eps:
        return "Chỉ số tăng nhưng số mã giảm áp đảo - đà tăng tập trung ở ít mã lớn."
    if pct_change < -idx_eps and ad_ratio > breadth_eps:
        return "Chỉ số giảm nhưng số mã tăng áp đảo - áp lực đến từ ít mã lớn."
    return None
