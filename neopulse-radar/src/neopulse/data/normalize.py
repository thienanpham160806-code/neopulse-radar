"""Chuẩn hóa thông điệp thô của NEO API (camelCase, kiểu lẫn lộn) về lược đồ nội bộ.

Điểm cần lưu ý của dữ liệu nguồn (đối chiếu tài liệu 4.6, 4.9, 6.2):
  * bidPrice1/askPrice1 là CHUỖI, có thể mang "ATO"/"ATC" trong phiên định kỳ.
  * Nhiều trường số có thể là null hoặc chuỗi rỗng.
  * stockInfo trên WebSocket không kèm dấu thời gian -> dùng thời điểm nhận (giờ VN).
  * tradingDate dạng dd/mm/YYYY; indexTime dạng HH:MM:SS hoặc ISO.
Mọi hàm ở đây đều KHÔNG ném lỗi với dữ liệu xấu: trả về giá trị None kèm danh sách vấn đề.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from ..timeutil import iso_vn, parse_event_time, to_vn

AUCTION_FLAGS = {"ATO", "ATC", "PLO", "MP", "MTL", "MOK", "MAK"}

# (cột nội bộ, trường NEO API)
STOCK_NUMERIC = [
    ("ceiling", "ceilingPrice"), ("floor", "floorPrice"), ("ref", "refPrice"),
    ("bid1", "bidPrice1"), ("bid2", "bidPrice2"), ("bid3", "bidPrice3"),
    ("bid_vol1", "bidVol1"), ("bid_vol2", "bidVol2"), ("bid_vol3", "bidVol3"),
    ("ask1", "askPrice1"), ("ask2", "askPrice2"), ("ask3", "askPrice3"),
    ("ask_vol1", "askVol1"), ("ask_vol2", "askVol2"), ("ask_vol3", "askVol3"),
    ("last", "closePrice"), ("last_vol", "closeVol"),
    ("change", "priceChange"), ("pct_change", "percentPriceChange"),
    ("open", "openPrice"), ("high", "highPrice"), ("low", "lowPrice"), ("avg_price", "averagePrice"),
    ("total_volume", "totalTradingVolume"), ("total_value", "totalTradingValue"),
    ("f_buy_vol", "foreignBuyVolume"), ("f_sell_vol", "foreignSellVolume"),
    ("f_buy_val", "foreignBuyValue"), ("f_sell_val", "foreignSellValue"),
    ("f_remain", "foreignRemain"), ("f_room", "foreignRoom"),
    ("open_interest", "openInterest"),
]
QUOTE_COLUMNS = (["ts", "trading_date", "symbol", "instrument", "source", "market_code", "auction_flag"]
                 + [c for c, _ in STOCK_NUMERIC] + ["maturity_date", "underlying"])

INDEX_NUMERIC = [
    ("value", "indexValue"), ("change", "indexChange"), ("pct_change", "indexPercentChange"),
    ("total_volume", "totalVolume"), ("total_value", "totalValue"),
    ("advances", "advances"), ("declines", "declines"), ("no_change", "noChange"),
    ("n_ceiling", "numberOfCe"), ("n_floor", "numberOfFl"),
]
INDEX_COLUMNS = ["ts", "trading_date", "index_code", "source", "market_status"] + [c for c, _ in INDEX_NUMERIC]


def to_float(x: Any) -> float | None:
    """Ép kiểu số an toàn: None/''/chuỗi không phải số/NaN/vô cực -> None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        v = float(x)
    else:
        s = str(x).strip().replace(",", "")
        if not s:
            return None
        try:
            v = float(s)
        except ValueError:
            return None
    return v if math.isfinite(v) else None


def parse_trading_date(x: Any, fallback: datetime) -> str:
    """dd/mm/YYYY hoặc YYYY-MM-DD -> 'YYYY-MM-DD'; không đọc được thì lấy ngày nhận (giờ VN)."""
    if isinstance(x, str) and x.strip():
        s = x.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(s[:10], fmt).date().isoformat()
            except ValueError:
                continue
    return to_vn(fallback).date().isoformat()


def normalize_quote(raw: dict, recv: datetime, source: str,
                    instrument: str | None = None) -> tuple[dict | None, list[str]]:
    """Chuẩn hóa một bản ghi cổ phiếu/HĐTL. Trả về (hàng, vấn đề); hàng=None nếu phải loại bỏ."""
    issues: list[str] = []
    if not isinstance(raw, dict):
        return None, ["not_a_dict"]
    symbol = str(raw.get("symbol") or "").strip().upper()
    if not symbol:
        return None, ["missing_symbol"]
    stock_type = str(raw.get("stockType") or "")
    market = str(raw.get("marketCode") or "").upper() or None
    if instrument is None:
        instrument = "future" if (stock_type.startswith("FU") or market == "FU") else "stock"
    row: dict[str, Any] = {
        "ts": iso_vn(recv), "trading_date": parse_trading_date(raw.get("tradingDate"), recv),
        "symbol": symbol, "instrument": instrument, "source": source, "market_code": market,
        "auction_flag": None,
        "maturity_date": parse_trading_date(raw["maturityDate"], recv) if raw.get("maturityDate") else None,
        "underlying": (str(raw.get("underlyingSymbol") or "").upper() or None),
    }
    for col, key in STOCK_NUMERIC:
        v = raw.get(key)
        if col in ("bid1", "ask1") and isinstance(v, str) and v.strip().upper() in AUCTION_FLAGS:
            row["auction_flag"] = v.strip().upper()
            row[col] = None
            continue
        f = to_float(v)
        if v not in (None, "") and f is None:
            issues.append(f"bad_type:{key}")
        row[col] = f
    # --- kiểm tra miền giá trị: giá/khối lượng âm là dữ liệu hỏng -> bỏ giá trị, giữ bản ghi
    for col, _ in STOCK_NUMERIC:
        if col in ("change", "pct_change"):
            continue
        if row[col] is not None and row[col] < 0:
            issues.append(f"negative:{col}")
            row[col] = None
    # giá 0 ở sổ lệnh nghĩa là không có lệnh chờ ở mức đó
    for side in ("bid", "ask"):
        for lv in (1, 2, 3):
            if row[f"{side}{lv}"] == 0:
                row[f"{side}{lv}"] = None
    if row["last"] is None and row["ref"] is None:
        return None, issues + ["no_price"]
    # --- kiểm tra tính nhất quán (chỉ gắn cờ, không sửa)
    b, a = row["bid1"], row["ask1"]
    if b is not None and a is not None and b >= a and row["auction_flag"] is None:
        issues.append("crossed_book")
    lo, hi, last = row["floor"], row["ceiling"], row["last"]
    if last is not None and lo is not None and hi is not None and lo > 0 and not (lo <= last <= hi):
        issues.append("price_outside_band")
    if row["high"] is not None and row["low"] is not None and row["low"] > 0 and row["high"] < row["low"]:
        issues.append("high_below_low")
    return row, issues


def normalize_index(raw: dict, recv: datetime, source: str) -> tuple[dict | None, list[str]]:
    issues: list[str] = []
    if not isinstance(raw, dict):
        return None, ["not_a_dict"]
    code = str(raw.get("indexCode") or "").strip().upper()
    if not code:
        return None, ["missing_index_code"]
    ts = parse_event_time(raw.get("dateString"), raw.get("indexTime"), recv)
    # dữ liệu đến muộn/đồng hồ lệch: dấu thời gian sự kiện đi trước thời điểm nhận quá 5 phút
    if (ts - to_vn(recv)).total_seconds() > 300:
        issues.append("event_time_in_future")
        ts = to_vn(recv)
    row: dict[str, Any] = {"ts": iso_vn(ts), "trading_date": ts.date().isoformat(), "index_code": code,
                           "source": source, "market_status": (raw.get("marketStatus") or None)}
    for col, key in INDEX_NUMERIC:
        v = raw.get(key)
        f = to_float(v)
        if v not in (None, "") and f is None:
            issues.append(f"bad_type:{key}")
        row[col] = f
    if row["value"] is None or row["value"] <= 0:
        return None, issues + ["no_index_value"]
    return row, issues
