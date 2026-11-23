"""Chênh lệch (basis) giữa hợp đồng tương lai VN30 và chỉ số cơ sở.

  basis        = F - S                                  (điểm)
  basis_pct    = (F - S) / S * 100
  carry_ann    = (F / S - 1) * 365 / số ngày tới đáo hạn    lãi suất hàm ý quy năm
  fair_value   = S * (1 + (r - q) * T)                  mô hình chi phí lưu giữ (r: lãi suất, q: cổ tức)
  mispricing   = F - fair_value
Basis phải hội tụ về 0 khi đáo hạn; basis âm sâu thường phản ánh nhu cầu phòng vệ/bi quan ngắn hạn,
nhưng ở Việt Nam còn chịu ảnh hưởng của hạn chế bán khống cơ sở nên KHÔNG tự động là cơ hội arbitrage.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def days_to_maturity(trading_date: str | date, maturity: str | date | None) -> float:
    if maturity is None or (isinstance(maturity, float) and np.isnan(maturity)):
        return np.nan
    d0 = date.fromisoformat(trading_date) if isinstance(trading_date, str) else trading_date
    d1 = date.fromisoformat(maturity) if isinstance(maturity, str) else maturity
    return float((d1 - d0).days)


def basis_series(futures: pd.DataFrame, index_ticks: pd.DataFrame, *, r: float = 0.045, q: float = 0.0,
                 tolerance: str = "2min") -> pd.DataFrame:
    """Ghép từng ảnh chụp HĐTL với giá trị chỉ số GẦN NHẤT TRƯỚC ĐÓ (merge_asof lùi, không nhìn trước).

    `tolerance`: bỏ cặp ghép nếu chỉ số cũ hơn ngưỡng này (dữ liệu chỉ số bị trễ/mất kết nối).
    """
    cols = ["ts", "symbol", "future", "spot", "basis", "basis_pct", "dtm", "carry_ann", "fair_value", "mispricing"]
    if futures.empty or index_ticks.empty:
        return pd.DataFrame(columns=cols)
    f = futures.dropna(subset=["last"]).sort_values("ts")[["ts", "trading_date", "symbol", "last", "maturity_date"]]
    s = index_ticks.sort_values("ts")[["ts", "value"]].rename(columns={"value": "spot"})
    m = pd.merge_asof(f, s, on="ts", direction="backward", tolerance=pd.Timedelta(tolerance)).dropna(subset=["spot"])
    if m.empty:
        return pd.DataFrame(columns=cols)
    m = m.rename(columns={"last": "future"})
    m["basis"] = m["future"] - m["spot"]
    m["basis_pct"] = m["basis"] / m["spot"] * 100
    m["dtm"] = [days_to_maturity(d, mt) for d, mt in zip(m["trading_date"], m["maturity_date"], strict=True)]
    T = m["dtm"] / 365.0
    m["carry_ann"] = np.where(m["dtm"] > 0, (m["future"] / m["spot"] - 1) / T, np.nan)
    m["fair_value"] = m["spot"] * (1 + (r - q) * T.fillna(0))
    m["mispricing"] = m["future"] - m["fair_value"]
    return m[cols].reset_index(drop=True)


def basis_state(b: pd.DataFrame) -> dict:
    """Trạng thái hiện tại + z-score bền vững của basis so với phân phối trong cửa sổ dữ liệu."""
    if b.empty:
        return {"basis": np.nan, "basis_pct": np.nan, "z": np.nan, "label": "Không có dữ liệu", "dtm": np.nan}
    last = b.iloc[-1]
    hist = b["basis_pct"].iloc[:-1]
    med = hist.median() if len(hist) >= 30 else np.nan
    mad = (hist - med).abs().median() if len(hist) >= 30 else np.nan
    z = 0.6745 * (last["basis_pct"] - med) / mad if mad and mad > 0 else np.nan
    label = ("Hợp đồng tương lai cao hơn chỉ số cơ sở (contango)" if last["basis"] > 0 else
             "Hợp đồng tương lai thấp hơn chỉ số cơ sở (backwardation)" if last["basis"] < 0 else "Hội tụ")
    return {"basis": float(last["basis"]), "basis_pct": float(last["basis_pct"]), "z": float(z) if pd.notna(z) else np.nan,
            "label": label, "dtm": float(last["dtm"]) if pd.notna(last["dtm"]) else np.nan,
            "carry_ann": float(last["carry_ann"]) if pd.notna(last["carry_ann"]) else np.nan,
            "mispricing": float(last["mispricing"]), "symbol": last["symbol"]}
