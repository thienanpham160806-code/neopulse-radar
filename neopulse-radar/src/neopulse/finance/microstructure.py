"""Chỉ báo vi cấu trúc từ sổ lệnh 3 mức giá của NEO API.

Ký hiệu: b_i, a_i là giá mua/bán mức i; Bv_i, Av_i là khối lượng chờ tương ứng (i = 1..3).

  mid          = (a_1 + b_1) / 2
  spread_bps   = (a_1 - b_1) / mid * 10^4                      chi phí khứ hồi tức thời
  OBI_k        = (ΣBv_i - ΣAv_i) / (ΣBv_i + ΣAv_i), i<=k        trong [-1, 1]; >0: bên mua dày hơn
  OBI_w        = như trên với trọng số 1/i                      mức giá gần được coi trọng hơn
  microprice   = (a_1*Bv_1 + b_1*Av_1) / (Bv_1 + Av_1)          Stoikov (2018)
  pressure     = ΣAv_i / ΣBv_i                                  >1: áp lực chào bán lớn hơn
  band_pos     = (last - ref) / (ceiling - ref)                 +1 = trần, -1 = sàn

Cơ sở: Cont, Kukanov & Stoikov (2014) cho thấy mất cân bằng dòng lệnh giải thích biến động giá
ngắn hạn; Chordia, Roll & Subrahmanyam (2002) về mất cân bằng lệnh và lợi suất. Với chỉ 3 mức giá,
OBI ở đây là xấp xỉ thô của độ sâu thật và KHÔNG nhìn thấy lệnh ẩn hay lệnh ngoài 3 mức.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LEVELS = (1, 2, 3)


def add_book_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm các cột chỉ báo sổ lệnh. Hàng thiếu một phía sổ lệnh nhận NaN (không suy diễn)."""
    out = df.copy()
    if out.empty:
        for c in ("mid", "spread", "spread_bps", "bid_depth", "ask_depth", "depth_value", "obi1",
                  "obi3", "obi_w", "microprice", "micro_dev_bps", "pressure", "band_pos"):
            out[c] = pd.Series(dtype=float)
        return out
    b1, a1 = out["bid1"], out["ask1"]
    valid = b1.notna() & a1.notna() & (a1 > b1)
    out["mid"] = ((a1 + b1) / 2).where(valid)
    out["spread"] = (a1 - b1).where(valid)
    out["spread_bps"] = out["spread"] / out["mid"] * 1e4
    bv = out[[f"bid_vol{i}" for i in LEVELS]].fillna(0.0).to_numpy(float)
    av = out[[f"ask_vol{i}" for i in LEVELS]].fillna(0.0).to_numpy(float)
    bp = out[[f"bid{i}" for i in LEVELS]].to_numpy(float)
    ap = out[[f"ask{i}" for i in LEVELS]].to_numpy(float)
    bv = np.where(np.isnan(bp), 0.0, bv)  # không có giá => không có độ sâu ở mức đó
    av = np.where(np.isnan(ap), 0.0, av)
    out["bid_depth"], out["ask_depth"] = bv.sum(1), av.sum(1)
    out["depth_value"] = np.nansum(bv * np.nan_to_num(bp), 1) + np.nansum(av * np.nan_to_num(ap), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        tot1 = bv[:, 0] + av[:, 0]
        out["obi1"] = np.where(tot1 > 0, (bv[:, 0] - av[:, 0]) / tot1, np.nan)
        tot3 = bv.sum(1) + av.sum(1)
        out["obi3"] = np.where(tot3 > 0, (bv.sum(1) - av.sum(1)) / tot3, np.nan)
        w = np.array([1.0, 0.5, 1 / 3])
        totw = (bv * w).sum(1) + (av * w).sum(1)
        out["obi_w"] = np.where(totw > 0, ((bv * w).sum(1) - (av * w).sum(1)) / totw, np.nan)
        micro = np.where(tot1 > 0, (ap[:, 0] * bv[:, 0] + bp[:, 0] * av[:, 0]) / tot1, np.nan)
        out["pressure"] = np.where(bv.sum(1) > 0, av.sum(1) / bv.sum(1), np.nan)
    out["microprice"] = pd.Series(micro, index=out.index).where(valid)
    out["micro_dev_bps"] = (out["microprice"] - out["mid"]) / out["mid"] * 1e4
    for c in ("obi1", "obi3", "obi_w", "pressure"):
        out[c] = out[c].where(valid)
    half = (out["ceiling"] - out["ref"]).where(out["ceiling"] > out["ref"])
    out["band_pos"] = ((out["last"] - out["ref"]) / half).clip(-1, 1)
    return out


def walk_book(row: pd.Series | dict, qty: float, side: str = "buy") -> dict:
    """Ước lượng chi phí khớp ngay một lệnh `qty` cổ phiếu bằng cách "đi" qua 3 mức giá.

    Trả về khối lượng khớp được, giá bình quân, trượt giá so với mid (bps) và phần không khớp.
    Đây là CẬN DƯỚI của chi phí: giả định sổ lệnh đứng yên và không có lệnh nào khác chen vào.
    """
    px = "ask" if side == "buy" else "bid"
    b1, a1 = row.get("bid1"), row.get("ask1")
    if pd.isna(b1) or pd.isna(a1) or a1 <= b1 or qty <= 0:
        return {"filled": 0.0, "avg_price": np.nan, "slippage_bps": np.nan, "unfilled": float(max(qty, 0)),
                "fill_ratio": 0.0}
    mid = (a1 + b1) / 2
    left, cost = float(qty), 0.0
    for i in LEVELS:
        p, v = row.get(f"{px}{i}"), row.get(f"{px}_vol{i}")
        if pd.isna(p) or pd.isna(v) or v <= 0:
            continue
        take = min(left, float(v))
        cost += take * float(p)
        left -= take
        if left <= 0:
            break
    filled = qty - left
    if filled <= 0:
        return {"filled": 0.0, "avg_price": np.nan, "slippage_bps": np.nan, "unfilled": float(qty), "fill_ratio": 0.0}
    avg = cost / filled
    slip = (avg - mid) / mid * 1e4 * (1 if side == "buy" else -1)
    return {"filled": filled, "avg_price": avg, "slippage_bps": slip, "unfilled": left, "fill_ratio": filled / qty}


def make_bars(quotes: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """Gom ảnh chụp sổ lệnh thành thanh thời gian theo từng mã trong từng phiên.

    Mỗi thanh lấy trạng thái CUỐI thanh (tránh nhìn trước), khối lượng/giá trị là phần tăng của số
    lũy kế. Thanh không có ảnh chụp nào bị bỏ (không nội suy).
    """
    if quotes.empty:
        return pd.DataFrame()
    q = add_book_metrics(quotes).sort_values("ts")
    q["bar"] = q["ts"].dt.floor(freq)
    keep = ["mid", "last", "spread_bps", "obi1", "obi3", "obi_w", "micro_dev_bps", "pressure", "depth_value",
            "bid_depth", "ask_depth", "total_volume", "total_value", "f_buy_val", "f_sell_val", "band_pos",
            "ref", "pct_change"]
    bars = q.groupby(["trading_date", "symbol", "bar"], sort=True)[keep].last().reset_index()
    g = bars.groupby(["trading_date", "symbol"], sort=False)
    bars["vol"] = g["total_volume"].diff()
    bars["val"] = g["total_value"].diff()
    bars["f_net_val"] = g["f_buy_val"].diff() - g["f_sell_val"].diff()
    bars["ret"] = g["mid"].pct_change(fill_method=None)
    # phần tăng âm = dữ liệu lũy kế bị đặt lại => coi là thiếu
    for c in ("vol", "val"):
        bars[c] = bars[c].where(bars[c] >= 0)
    return bars


def liquidity_table(latest: pd.DataFrame, bars: pd.DataFrame | None = None,
                    order_value: float = 500e6) -> pd.DataFrame:
    """Bảng thanh khoản theo mã tại thời điểm gần nhất.

    * spread_bps, depth_value: từ ảnh chụp mới nhất.
    * slippage_bps: trượt giá ước lượng khi MUA ngay một lệnh trị giá `order_value` đồng.
    * amihud: trung vị |lợi suất thanh, bps| / giá trị khớp thanh (tỷ đồng) - Amihud (2002) ở tần suất phút.
    * liq_score: xếp hạng phân vị tổng hợp (0-100, cao = thanh khoản tốt) trong rổ đang theo dõi.
    """
    if latest.empty:
        return pd.DataFrame()
    t = add_book_metrics(latest).set_index("symbol")
    rows = {}
    for sym, r in t.iterrows():
        ref_px = r["mid"] if pd.notna(r["mid"]) else r["last"]
        qty = order_value / ref_px if ref_px and ref_px > 0 else 0
        w = walk_book(r, qty, "buy")
        rows[sym] = {"slippage_bps": w["slippage_bps"], "fill_ratio": w["fill_ratio"]}
    out = t[["last", "spread_bps", "depth_value", "total_value", "obi3", "pressure"]].join(pd.DataFrame(rows).T)
    if bars is not None and not bars.empty:
        b = bars[(bars["val"] > 0) & bars["ret"].notna()]
        ami = (b["ret"].abs() * 1e4 / (b["val"] / 1e9)).groupby(b["symbol"]).median()  # bps / tỷ đồng
        out["amihud"] = ami
    else:
        out["amihud"] = np.nan
    pct = lambda s, asc: s.rank(pct=True, ascending=asc)  # noqa: E731
    parts = pd.concat([pct(out["spread_bps"], False), pct(out["depth_value"], True),
                       pct(out["total_value"], True), pct(out["amihud"], False)], axis=1)
    out["liq_score"] = (parts.mean(axis=1, skipna=True) * 100).round(1)
    return out.sort_values("liq_score", ascending=False)
