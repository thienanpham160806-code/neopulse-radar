"""Khối lượng tương đối theo thời điểm trong phiên (RVOL).

  KL kỳ vọng tới phút m      = KL trung bình 20 phiên x f(m)
  RVOL lũy kế (tại m)        = KL lũy kế tới m / KL kỳ vọng tới m
  RVOL thanh [m0, m1]        = KL khớp trong thanh / (KL trung bình 20 phiên x (f(m1) - f(m0)))

f(m) là tỷ lệ khối lượng cả ngày thường đã khớp tới phút giao dịch thứ m (0..270, bỏ nghỉ trưa).
So với CÙNG THỜI ĐIỂM của các phiên trước, không so với cả ngày, nên 10:00 không bị coi là "ít" chỉ vì mới đầu phiên.

f(m) mặc định = m / 270 (phân bổ đều theo phút) - GIẢ ĐỊNH đơn giản, ghi rõ trong kết quả. Khi đã có >= 3 phiên ghi
trọn trước đó, dùng đường lũy kế thực nghiệm (trung vị theo mã và phiên) của chính dữ liệu đã ghi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..timeutil import trading_minutes_elapsed

SESSION_MIN = 270.0
RVOL_SPIKE = 5.0  # thanh có KL >= 5 lần mức thường thấy cùng thời điểm; 3 -> 5 ngày 28/11 (docs/calibration_log.md)


def linear_profile(minutes: np.ndarray | float) -> np.ndarray:
    return np.clip(np.asarray(minutes, dtype=float) / SESSION_MIN, 0.0, 1.0)


MATCH_START_MIN = 15.0  # 09:15: hết ATO, khối lượng khớp đầu tiên của phiên
MATCH_END_MIN = 255.0   # 14:45: hết ATC; sau đó chỉ còn thỏa thuận, sổ lệnh gần như đứng yên


def complete_history(history_bars: pd.DataFrame) -> pd.DataFrame:
    """Giữ từng mã/phiên ghi trọn giờ khớp lệnh: có khối lượng trong 5 phút sau 09:15, tới 14:44, và không mất quá
    5 phút giao dịch liên tiếp trong khoảng đó. (Mốc cũ 09:05-14:59 không phiên SSI thật nào đạt, xem report/data.)"""
    parts = []
    for _, g in history_bars.dropna(subset=["total_volume"]).groupby(["trading_date", "symbol"]):
        m = np.sort([trading_minutes_elapsed(t.to_pydatetime()) for t in g["bar"]])
        m = m[m <= MATCH_END_MIN]
        if (len(m) and m[0] <= MATCH_START_MIN + 5 and m[-1] >= MATCH_END_MIN - 1
                and np.diff(m).max(initial=0) <= 5 and g["total_volume"].max() > 0):
            parts.append(g)
    return pd.concat(parts) if parts else history_bars.iloc[:0].copy()


def empirical_profile(history_bars: pd.DataFrame, min_sessions: int = 3):
    """Đường f(m) thực nghiệm từ các phiên ĐÃ GHI TRỌN trước đó (cột trading_date, symbol, bar, total_volume).

    Trả hàm m -> f(m) (nội suy tuyến tính, đơn điệu), hoặc None nếu chưa đủ phiên."""
    if history_bars.empty:
        return None
    history_bars = complete_history(history_bars)
    # Mỗi mã phải có đủ phiên, không ghép ba ngày rời rạc của ba mã khác nhau.
    counts = history_bars.groupby("symbol")["trading_date"].transform("nunique")
    history_bars = history_bars[counts >= min_sessions]
    if history_bars.empty:
        return None
    h = history_bars.dropna(subset=["total_volume"]).copy()
    h["m"] = [trading_minutes_elapsed(t.to_pydatetime()) for t in h["bar"]]
    final = h.groupby(["trading_date", "symbol"])["total_volume"].transform("max")
    h = h[final > 0]
    h["share"] = h["total_volume"] / final[final > 0]
    grid = np.arange(0, SESSION_MIN + 1, 5.0)
    curves = []
    for _, g in h.groupby(["trading_date", "symbol"]):
        g = g.sort_values("m")
        curves.append(np.interp(grid, g["m"], g["share"], left=0.0, right=1.0))
    if not curves:
        return None
    prof = np.maximum.accumulate(np.median(np.vstack(curves), axis=0))
    return lambda m: np.interp(np.asarray(m, dtype=float), grid, prof)


def add_rvol(bars: pd.DataFrame, avg_volume: dict[str, float], profile=None) -> pd.DataFrame:
    """Thêm cột rvol_cum, rvol_bar vào bảng thanh (cần cột bar, symbol, vol, total_volume). Thiếu KL TB 20 phiên -> NaN."""
    out = bars.copy()
    if out.empty:
        return out.assign(rvol_cum=pd.Series(dtype=float), rvol_bar=pd.Series(dtype=float))
    f = profile or linear_profile
    m1 = np.array([trading_minutes_elapsed(t.to_pydatetime()) for t in out["bar"]])
    minutes = pd.Series(m1, index=out.index)
    m0 = minutes.groupby([out["trading_date"], out["symbol"]]).shift()
    m0 = m0.fillna(minutes - 1).clip(lower=0).to_numpy()
    avg = out["symbol"].map(lambda s: avg_volume.get(s, np.nan)).astype(float)
    exp_cum = avg * f(m1)
    exp_bar = avg * (f(m1) - f(m0))
    out["rvol_cum"] = (out["total_volume"] / exp_cum).where(exp_cum > 0)
    out["rvol_bar"] = (out["vol"] / exp_bar).where(exp_bar > 0)
    return out


def avg_volume_from_history(history_bars: pd.DataFrame, min_sessions: int = 3, last_n: int = 20) -> dict[str, float]:
    """Dự phòng khi không có REST ngày: KL cả ngày trung bình của tối đa `last_n` phiên đã ghi trước đó (>= 3 phiên)."""
    if history_bars.empty:
        return {}
    history_bars = complete_history(history_bars)
    daily = history_bars.groupby(["symbol", "trading_date"])["total_volume"].max().reset_index()
    out = {}
    for sym, g in daily.groupby("symbol"):
        g = g.sort_values("trading_date").tail(last_n)
        if len(g) >= min_sessions:
            out[sym] = float(g["total_volume"].mean())
    return out
