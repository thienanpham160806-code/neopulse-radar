"""Phát hiện bất thường bằng z-score bền vững (median/MAD) trên cửa sổ trượt.

  z_t = 0,6745 * (x_t - median(x_{t-W..t-1})) / MAD(x_{t-W..t-1})

* Median/MAD thay cho mean/std vì chính các điểm bất thường làm phình độ lệch chuẩn và che lẫn nhau.
* Hằng số 0,6745 làm z tương đương z chuẩn khi dữ liệu phân phối chuẩn.
* Ngưỡng mặc định |z| >= 3,5 theo khuyến nghị của Iglewicz & Hoaglin (1993).
* Cửa sổ chỉ gồm quan sát TRƯỚC thời điểm t (shift 1) nên không nhìn trước tương lai.
* Khối lượng được lấy log(1+x) trước khi tính vì phân phối lệch phải mạnh.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Z_THRESHOLD = 3.5
MAD_SCALE = 0.6745
Z_CAP = 50.0  # chuỗi gần như đứng yên cho MAD rất nhỏ => z khổng lồ vô nghĩa; chặn để dễ đọc


def robust_z(x: pd.Series, window: int = 60, min_periods: int = 20) -> pd.Series:
    """z-score bền vững của từng điểm so với cửa sổ `window` điểm liền trước nó."""
    prev = x.shift(1).rolling(window, min_periods=min_periods)
    med = prev.median()
    # MAD của đúng cửa sổ x_{t-W..t-1} quanh median của chính cửa sổ đó (không phải median trượt lần hai)
    mad = prev.apply(lambda a: np.median(np.abs(a[~np.isnan(a)] - np.median(a[~np.isnan(a)]))), raw=True)
    # MAD = 0 (chuỗi đứng yên) => không xác định được độ lệch, trả NaN thay vì vô cực
    return (MAD_SCALE * (x - med) / mad.where(mad > 0)).clip(-Z_CAP, Z_CAP)


def score_bars(bars: pd.DataFrame, window: int = 60, min_periods: int = 20) -> pd.DataFrame:
    """Gắn z-score cho khối lượng, spread, lợi suất và dòng ròng NN của từng mã, tính riêng từng phiên."""
    if bars.empty:
        return bars.assign(z_vol=pd.Series(dtype=float), z_spread=pd.Series(dtype=float),
                           z_ret=pd.Series(dtype=float), z_fnet=pd.Series(dtype=float))
    out = bars.sort_values(["trading_date", "symbol", "bar"]).copy()
    g = out.groupby(["trading_date", "symbol"], sort=False, group_keys=False)
    rz = lambda s: robust_z(s, window, min_periods)  # noqa: E731
    out["z_vol"] = g["vol"].apply(lambda s: rz(np.log1p(s)))
    out["z_spread"] = g["spread_bps"].apply(rz)
    out["z_ret"] = g["ret"].apply(rz)
    out["z_fnet"] = g["f_net_val"].apply(rz)
    return out
