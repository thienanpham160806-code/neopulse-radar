"""Dòng tiền nhà đầu tư nước ngoài theo mã và toàn rổ.

  net_val        = giá trị NN mua - giá trị NN bán                       (đồng)
  net_ratio      = net_val / (mua + bán)                                 trong [-1, 1]: mức độ một chiều
  participation  = (mua + bán) / (2 * tổng giá trị khớp)                 tỷ trọng NN trong giao dịch
  room_used      = 1 - room còn lại / tổng room                          1 = hết room
`net_ratio` tách "chiều" khỏi "quy mô": mua ròng 5 tỷ trên 6 tỷ giao dịch khác hẳn 5 tỷ trên 500 tỷ.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def foreign_table(latest: pd.DataFrame) -> pd.DataFrame:
    if latest.empty:
        return pd.DataFrame()
    t = latest.set_index("symbol")
    buy, sell = t["f_buy_val"].fillna(0), t["f_sell_val"].fillna(0)
    gross = buy + sell
    out = pd.DataFrame({
        "f_buy_val": buy, "f_sell_val": sell, "net_val": buy - sell,
        "net_ratio": np.where(gross > 0, (buy - sell) / gross, np.nan),
        "participation": np.where(t["total_value"] > 0, gross / (2 * t["total_value"]), np.nan),
        "room_used": np.where(t["f_room"] > 0, 1 - t["f_remain"] / t["f_room"], np.nan),
        "total_value": t["total_value"],
    }, index=t.index)
    out["participation"] = out["participation"].clip(0, 1)
    out["room_used"] = out["room_used"].clip(0, 1)
    return out.sort_values("net_val", ascending=False)


def foreign_summary(table: pd.DataFrame) -> dict:
    if table.empty:
        return {"net_val": np.nan, "net_ratio": np.nan, "n_net_buy": 0, "n_net_sell": 0, "participation": np.nan}
    gross = (table["f_buy_val"] + table["f_sell_val"]).sum()
    tv = table["total_value"].sum()
    return {
        "net_val": float(table["net_val"].sum()),
        "net_ratio": float(table["net_val"].sum() / gross) if gross > 0 else np.nan,
        "n_net_buy": int((table["net_val"] > 0).sum()), "n_net_sell": int((table["net_val"] < 0).sum()),
        "participation": float(gross / (2 * tv)) if tv > 0 else np.nan,
    }
