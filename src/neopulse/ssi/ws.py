"""WebSocket streaming của SSI FastConnect (API v3): xác thực bằng Bearer ở bước bắt tay, đăng ký chủ đề.

Giao thức (theo SDK chính thức `ssi-sdk` 3.3.2, services/streaming.py + transport/websocket_client.py):
  * URL mặc định wss://stream.ssi.com.vn/ws/v3 ; header `Authorization: Bearer <accessToken>` khi kết nối.
  * Đăng ký:  {"method": "subscribe", "channel": "DATA", "topics": ["trade.SSI", "quote.SSI", ...]}
  * Giữ nhịp: {"method": "ping_pong", "channel": "HEARTBEAT"} -> máy chủ trả {"status": "ok", "message": "pong"}
  * Tin dữ liệu: {"topic": "quote.SSI", "data": {...}} ; máy chủ chỉ kiểm tra token lúc kết nối nên ta
    chủ động nối lại trước khi token hết hạn.
Vòng đời kết nối (lùi dần có nhiễu, phát hiện treo, thống kê) dùng lại `MarketStream` của lớp NEO.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from ..neo_api.ws import Handler, MarketStream
from .adapter import SsiAdapter

log = logging.getLogger(__name__)

TOPIC_CHUNK = 50  # số chủ đề mỗi yêu cầu đăng ký (giới hạn thật chưa công bố - chia nhỏ cho an toàn)


def build_topics(stocks: list[str], futures: list[str], indexes: list[str]) -> list[str]:
    """Chủ đề cần đăng ký. HĐTL chỉ cần trade+quote; cổ phiếu thêm room (ngoại) và market (trần/sàn/TC)."""
    topics: list[str] = ["market.flag"]
    for s in stocks:
        topics += [f"trade.{s}", f"quote.{s}", f"room.{s}", f"market.{s}"]
    for s in futures:
        topics += [f"trade.{s}", f"quote.{s}", f"market.{s}"]
    for code in indexes:
        # indexsummary mang giá trị, thay đổi, %, tăng/giảm/đứng/trần/sàn, KL/GT lũy kế (kiểm chứng 19/11/2026);
        # trade.index chỉ có giá trị + khối lượng nên không dùng. UPCOMINDEX đăng ký được trực tiếp.
        topics.append(f"indexsummary.{code}")
    return topics


class SsiStream(MarketStream):
    def __init__(self, url: str, token_provider: Callable[[], str], topics: list[str], adapter: SsiAdapter,
                 on_message: Handler, *, expiry_provider: Callable[[], float] | None = None,
                 ping_every_s: float = 20.0, stale_after_s: float = 60.0, max_backoff_s: float = 60.0,
                 connect: Callable[..., Any] | None = None, clock: Callable[[], float] = time.time):
        super().__init__(url, token_provider, {}, on_message, stale_after_s=stale_after_s,
                         max_backoff_s=max_backoff_s, connect=connect)
        self.topics, self.adapter = list(topics), adapter
        self._expiry_provider, self._ping_every_s, self._clock = expiry_provider, ping_every_s, clock

    async def _session(self) -> None:
        connect = self._connect
        if connect is None:
            import websockets
            connect = websockets.connect
        headers = {"Authorization": f"Bearer {self._token_provider()}"}
        async with connect(self.url, additional_headers=headers) as ws:
            self.stats.connects += 1
            self.stats.state = "authenticated"
            for i in range(0, len(self.topics), TOPIC_CHUNK):
                await ws.send(json.dumps({"method": "subscribe", "channel": "DATA",
                                          "topics": self.topics[i:i + TOPIC_CHUNK]}))
            log.info("SSI WebSocket đã kết nối; đăng ký %d chủ đề", len(self.topics))
            next_ping = self._clock() + self._ping_every_s
            last_frame = self._clock()
            while not self._stop.is_set():
                expiry = self._expiry_provider() if self._expiry_provider else 0.0
                if expiry and self._clock() >= expiry - 120:
                    log.info("Token SSI sắp hết hạn - nối lại với token mới")
                    return  # vòng ngoài sẽ gọi lại token_provider (đăng nhập lại) khi kết nối mới
                if self._clock() >= next_ping:
                    await ws.send(json.dumps({"method": "ping_pong", "channel": "HEARTBEAT"}))
                    next_ping = self._clock() + self._ping_every_s
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(self.stale_after_s, self._ping_every_s))
                except asyncio.TimeoutError:
                    if self._clock() - last_frame > self.stale_after_s:
                        self.stats.state = "stale"
                        raise TimeoutError(f"Không nhận dữ liệu trong {self.stale_after_s:.0f}s - coi như treo") from None
                    continue
                recv_ts = time.time()
                try:
                    frame = json.loads(raw)
                except (ValueError, TypeError):
                    self.stats.parse_errors += 1
                    continue
                self.stats.last_message_at = recv_ts
                last_frame = self._clock()
                for channel, body in self.adapter.feed(frame):
                    self.stats.messages += 1
                    self.stats.per_channel[channel] = self.stats.per_channel.get(channel, 0) + 1
                    if channel == "unknown":
                        self.stats.unknown += 1
                    if channel == "control":
                        if body.get("status") == "error" or "code" in body:
                            log.warning("SSI trả về lỗi/từ chối: %s", {k: body.get(k) for k in ("method", "status", "message", "code", "msg")})
                        continue
                    res = self._on_message(channel, body, recv_ts)
                    if asyncio.iscoroutine(res):
                        await res
