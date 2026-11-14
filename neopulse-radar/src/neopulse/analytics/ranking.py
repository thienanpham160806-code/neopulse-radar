"""Bộ lọc/xếp hạng đa yếu tố trong rổ theo dõi.

Mỗi yếu tố được chuẩn hóa z theo mặt cắt ngang (so giữa các mã tại cùng thời điểm), cắt đuôi ±3 để
một mã cực đoan không chi phối, rồi cộng có trọng số:
  momentum  % thay đổi giá so với tham chiếu            0,30
  flow      OBI_3 (sổ lệnh nghiêng mua)                  0,25
  foreign   net_ratio khối ngoại                         0,20
  liquidity log(giá trị khớp)                            0,15
  cost      -spread_bps (spread hẹp = tốt)               0,10
Điểm xếp hạng chỉ có nghĩa TƯƠNG ĐỐI trong rổ và trong thời điểm tính; không phải khuyến nghị.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..finance.foreign import foreign_table
from ..finance.microstructure import add_book_metrics

FACTOR_WEIGHTS = {"momentum": 0.30, "flow": 0.25, "foreign": 0.20, "liquidity": 0.15, "cost": 0.10}


def zscore_cs(s: pd.Series, clip: float = 3.0) -> pd.Series:
    sd = s.std(ddof=0)
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index).where(s.notna())
    return ((s - s.mean()) / sd).clip(-clip, clip)


def rank_universe(latest: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    if latest.empty:
        return pd.DataFrame()
    w = weights or FACTOR_WEIGHTS
    t = add_book_metrics(latest).set_index("symbol")
    f = foreign_table(latest)
    raw = pd.DataFrame({
        "momentum": t["pct_change"], "flow": t["obi3"], "foreign": f["net_ratio"].reindex(t.index),
        "liquidity": np.log(t["total_value"].where(t["total_value"] > 0)), "cost": -t["spread_bps"],
    })
    z = raw.apply(zscore_cs)
    wser = pd.Series(w)
    # mã thiếu một yếu tố: chuẩn hóa lại trọng số trên các yếu tố còn lại thay vì coi là 0
    score = (z[wser.index] * wser).sum(axis=1, skipna=True) / z[wser.index].notna().mul(wser, axis=1).sum(axis=1)
    out = z.add_prefix("z_")
    out.insert(0, "score", score.round(3))
    out.insert(1, "last", t["last"])
    out.insert(2, "pct_change", t["pct_change"])
    out["obi3"], out["spread_bps"] = t["obi3"], t["spread_bps"]
    out["net_ratio"], out["total_value"] = raw["foreign"], t["total_value"]
    out["n_factors"] = z.notna().sum(axis=1)
    out = out.sort_values("score", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out
