"""Điểm cắm cho SSI FastConnect Data (https://developers.ssi.com.vn/) - CHƯA triển khai.

Lý do để sẵn: NEO API không có dữ liệu lịch sử nhiều phiên; nếu cần OHLC ngày để tính MA20/độ rộng
dài hạn thì SSI FastConnect là nguồn bổ trợ được đề cho phép. Khi triển khai:
  * đọc SSI_CONSUMER_ID / SSI_CONSUMER_SECRET từ `Settings` (không hard-code),
  * ghi dữ liệu với source='ssi' để luôn truy vết được nguồn,
  * NEO API vẫn phải là nguồn cốt lõi của mọi chỉ báo chính.
"""
from __future__ import annotations

from ..config import Settings


class SsiFastConnect:
    def __init__(self, settings: Settings):
        if not (settings.ssi_consumer_id and settings.ssi_consumer_secret):
            raise RuntimeError("Chưa điền SSI_CONSUMER_ID / SSI_CONSUMER_SECRET trong .env.")
        self._settings = settings

    def daily_ohlc(self, symbol: str, from_date: str, to_date: str):
        raise NotImplementedError("TODO: gọi API DailyOhlc của SSI FastConnect Data và chuẩn hóa về lược đồ nội bộ.")
