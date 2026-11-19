"""Đổi khung tin streaming của SSI về lược đồ thô của NEO API (stockInfo / marketInfo / marketSession).

SSI phát từng loại tin riêng theo chủ đề (topic), mỗi tin chỉ mang một phần dữ liệu:
    trade.<MÃ>        giá khớp, khối lượng khớp, khối lượng lũy kế, mở/cao/thấp/trung bình
    quote.<MÃ>        các mức giá mua/bán tốt nhất: bids/asks = [[giá, khối lượng], ...] (tốt nhất trước)
    room.<MÃ>         room ngoại (tr, cr) và mua/bán nước ngoài lũy kế (bq, bv, sq, sv)
    market.<MÃ>       giá trần/sàn/tham chiếu (ce, fl, ref)
    market.flag       cờ phiên của sàn (ATO, LO, ATC ...)
    indexsummary.<MÃ> chỉ số: v (giá trị), c, cr (%), adv/dec/nc/ce/fl, tq/tv (KL/GT lũy kế, đồng)
    trade.index.<MÃ>  KHÔNG dùng: chỉ có p (giá trị) + q/v (khối lượng), không có thay đổi hay độ rộng
Adapter giữ trạng thái gộp theo mã và mỗi lần có tin mới phát ra MỘT bản ghi đầy đủ theo lược đồ NEO,
nhờ đó `Ingestor` (chuẩn hóa, khử lặp, kiểm tra chất lượng) dùng lại nguyên vẹn.

Nguồn tên trường: mã nguồn SDK chính thức `ssi-sdk` 3.3.2 (models/streaming.py). Các điểm CHƯA kiểm chứng
trên luồng thật được liệt kê ở docs/ssi_notes.md; thông điệp không nhận diện được đi vào kênh 'unknown'
để ghi lại và hiệu chỉnh, không bị nuốt im lặng.
"""
from __future__ import annotations

import math
from typing import Any

# SSI gọi chỉ số HNX+UPCOM là HNXUPCOMINDEX; hệ thống này dùng tên UPCOMINDEX như NEO API.
INDEX_FROM_SSI = {"HNXUPCOMINDEX": "UPCOMINDEX"}
BOARD_TO_MARKET = {"HOSE": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM", "DER": "FU", "DERIVATIVES": "FU"}
LEVELS = 3


def _num(x: Any) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(str(x).replace(",", "")) if not isinstance(x, (int, float)) else float(x)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _base_topic(topic: str) -> tuple[str, str | None]:
    """'trade.SSI@1m' -> ('trade.SSI', '1m')."""
    head, _, interval = topic.partition("@")
    return head, (interval or None)


class SsiAdapter:
    def __init__(self, *, futures_meta: dict[str, dict] | None = None, price_scale: float = 1.0):
        """`futures_meta`: {mã HĐTL: {"maturityDate": ..., "underlyingSymbol": ...}} lấy từ REST lúc khởi động."""
        self.futures_meta = {k.upper(): v for k, v in (futures_meta or {}).items()}
        self.price_scale = price_scale
        self._state: dict[str, dict[str, Any]] = {}
        self.n_ignored = 0

    # ------------------------------------------------------------------ API
    def feed(self, frame: Any) -> list[tuple[str, dict]]:
        """Một khung tin -> danh sách (kênh kiểu NEO, thân dữ liệu)."""
        if not isinstance(frame, dict):
            return [("unknown", {"raw": frame})]
        topic = frame.get("topic")
        if not isinstance(topic, str):
            # trả lời đăng ký / pong / lỗi máy chủ không có topic
            return [("control", frame)]
        data = frame.get("data")
        if not isinstance(data, dict):
            return [("unknown", frame)]
        head, interval = _base_topic(topic)
        kind = head.lower()
        if interval and interval.lower() != "tick":
            self.n_ignored += 1  # nến 1m/5m: không dùng
            return []
        if kind.startswith("indexsummary."):
            return self._index(head.split(".", 1)[1], data)
        if kind.startswith("trade.index."):
            self.n_ignored += 1  # trường `v` ở đây là khối lượng, không phải giá trị chỉ số (lỗi đã gặp 19/11/2026)
            return []
        sym = (str(data.get("s") or "") or head.partition(".")[2]).strip().upper()
        if kind == "market.flag":
            return self._flag(data)
        if kind.startswith("trade."):
            return self._emit(sym, self._on_trade(sym, data))
        if kind.startswith("quote."):
            return self._emit(sym, self._on_quote(sym, data))
        if kind.startswith("room."):
            return self._emit(sym, self._on_room(sym, data))
        if kind.startswith("market."):
            return self._emit(sym, self._on_master(sym, data))
        if kind.startswith(("oddlot.", "put.")):
            self.n_ignored += 1  # hợp lệ nhưng ngoài phạm vi chỉ báo
            return []
        return [("unknown", frame)]

    # --------------------------------------------------------------- nội bộ
    def _st(self, sym: str, data: dict) -> dict[str, Any]:
        st = self._state.setdefault(sym, {"symbol": sym})
        board = str(data.get("b") or "").upper()
        if board:
            st["marketCode"] = BOARD_TO_MARKET.get(board, board)
        if sym in self.futures_meta or st.get("marketCode") == "FU":
            meta = self.futures_meta.get(sym, {})
            st["stockType"] = "FU"
            st.setdefault("marketCode", "FU")
            if meta.get("maturityDate"):
                st["maturityDate"] = meta["maturityDate"]
            if meta.get("underlyingSymbol"):
                st["underlyingSymbol"] = meta["underlyingSymbol"]
        return st

    def _px(self, x: Any) -> float | None:
        v = _num(x)
        return None if v is None else v * self.price_scale

    def _on_trade(self, sym: str, d: dict) -> dict:
        st = self._st(sym, d)
        last = self._px(d.get("p"))
        if last:  # giá khớp chữ ("ATO"/"ATC") hoặc 0 không cập nhật giá cuối
            st["closePrice"] = last
        for key, name in (("o", "openPrice"), ("h", "highPrice"), ("l", "lowPrice"), ("a", "averagePrice")):
            v = self._px(d.get(key))
            if v:
                st[name] = v
        q, tv = _num(d.get("q")), _num(d.get("v"))
        if q is not None:
            st["closeVol"] = q
        if tv is not None:
            st["totalTradingVolume"] = tv
        # SSI không gửi giá trị giao dịch lũy kế: ước lượng = giá trung bình x khối lượng lũy kế (đã ghi chú trong tài liệu)
        if st.get("averagePrice") and st.get("totalTradingVolume") is not None:
            st["totalTradingValue"] = st["averagePrice"] * st["totalTradingVolume"]
        return st

    def _on_quote(self, sym: str, d: dict) -> dict:
        st = self._st(sym, d)
        for side, key in (("bid", "bids"), ("ask", "asks")):
            levels = d.get(key) if isinstance(d.get(key), (list, tuple)) else []
            for i in range(LEVELS):
                lv = levels[i] if i < len(levels) and isinstance(levels[i], (list, tuple)) and len(levels[i]) >= 2 else None
                raw_p = lv[0] if lv else None
                if isinstance(raw_p, str) and raw_p.strip().upper() in {"ATO", "ATC", "MP", "MTL", "MOK", "MAK", "PLO"}:
                    price: Any = raw_p.strip().upper()  # giữ chữ để normalize gắn auction_flag
                else:
                    price = self._px(raw_p) if lv else None
                st[f"{side}Price{i + 1}"] = price
                st[f"{side}Vol{i + 1}"] = _num(lv[1]) if lv else None
        return st

    def _on_room(self, sym: str, d: dict) -> dict:
        st = self._st(sym, d)
        for key, name in (("tr", "foreignRoom"), ("cr", "foreignRemain"), ("bq", "foreignBuyVolume"),
                          ("sq", "foreignSellVolume")):
            v = _num(d.get(key))
            if v is not None:
                st[name] = v
        for key, name in (("bv", "foreignBuyValue"), ("sv", "foreignSellValue")):
            v = _num(d.get(key))
            if v is not None:
                st[name] = v
        return st

    def _on_master(self, sym: str, d: dict) -> dict:
        st = self._st(sym, d)
        for key, name in (("ce", "ceilingPrice"), ("fl", "floorPrice"), ("ref", "refPrice")):
            v = self._px(d.get(key))
            if v:
                st[name] = v
        return st

    def _emit(self, sym: str, st: dict) -> list[tuple[str, dict]]:
        out = dict(st)
        last, ref = out.get("closePrice"), out.get("refPrice")
        if last is not None and ref:
            out["priceChange"] = last - ref
            out["percentPriceChange"] = (last - ref) / ref * 100.0
        if last is None and ref is None:
            return []  # chưa đủ để chuẩn hóa (cần ít nhất giá cuối hoặc giá tham chiếu)
        return [("stockInfo", out)]

    def _flag(self, d: dict) -> list[tuple[str, dict]]:
        board = str(d.get("b") or "").upper()
        flag = str(d.get("f") or "").upper()
        if not board or not flag:
            return [("unknown", {"topic": "market.flag", "data": d})]
        return [("marketSession", {"marketCode": BOARD_TO_MARKET.get(board, board), "marketStatus": flag})]

    def _index(self, code: str, d: dict) -> list[tuple[str, dict]]:
        code = INDEX_FROM_SSI.get(str(d.get("s") or code).upper(), str(d.get("s") or code).upper())
        # Trường của indexsummary.* đã đối chiếu với luồng thật 19/11/2026 (docs/ssi_notes.md).
        body = {
            "indexCode": code, "indexValue": _num(d.get("v")), "indexChange": _num(d.get("c")),
            "indexPercentChange": _num(d.get("cr")), "advances": _num(d.get("adv")),
            "declines": _num(d.get("dec")), "noChange": _num(d.get("nc")),
            "numberOfCe": _num(d.get("ce")), "numberOfFl": _num(d.get("fl")),
            "totalVolume": _num(d.get("tq")) if d.get("tq") is not None else _num(d.get("tmq")),
            "totalValue": _num(d.get("tv")) if d.get("tv") is not None else _num(d.get("tmv")),
            "marketStatus": d.get("ss") or None,
        }
        return [("marketInfo", body)]
