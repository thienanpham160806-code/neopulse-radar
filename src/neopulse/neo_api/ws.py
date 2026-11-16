"""WebSocket Market Stream của NEO API: xác thực, đăng ký kênh, tự kết nối lại, phát hiện treo.

Giao thức (tài liệu mục 6.1, 6.2):
  1. Mở kết nối tới ws://neoapi.vpbanks.com.vn/stock-stream/broker
  2. Gửi {"action": "auth", "data": "<jwt>"}  -> chờ {"type": "auth", "status": "success"}
  3. Gửi {"type": "sub", "channel": "<kênh>", "listId": [...]} cho từng kênh
Kênh: marketInfo, marketSession, marketVolume, stockInfo.

Tài liệu chỉ mô tả phần thân dữ liệu, KHÔNG nêu rõ phong bì (envelope) của thông điệp đẩy về.
`classify_message` vì thế chấp nhận cả thân trần lẫn thân bọc trong {"channel"/"type", "data"} và
suy kênh từ tập trường - thông điệp không nhận diện được sẽ được đếm và ghi lại để hiệu chỉnh.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

CHANNELS = ("marketInfo", "marketSession", "marketVolume", "stockInfo")
Handler = Callable[[str, dict, float], Awaitable[None] | None]


def classify_message(msg: Any) -> list[tuple[str, dict]]:
    """Trả về danh sách (kênh, thân dữ liệu). Kênh 'auth'/'control'/'unknown' cho thông điệp khác."""
    if isinstance(msg, list):
        out: list[tuple[str, dict]] = []
        for m in msg:
            out.extend(classify_message(m))
        return out
    if not isinstance(msg, dict):
        return [("unknown", {"raw": msg})]
    if msg.get("type") == "auth":
        return [("auth", msg)]
    hinted = msg.get("channel") if msg.get("channel") in CHANNELS else None
    if hinted is None and msg.get("type") in CHANNELS:
        hinted = msg["type"]
    body = msg.get("data") if isinstance(msg.get("data"), (dict, list)) else msg
    if isinstance(body, list):
        out = []
        for b in body:
            out.extend([(hinted, b)] if hinted and isinstance(b, dict) else classify_message(b))
        return out
    if hinted:
        return [(hinted, body)]
    if "symbol" in body and ("refPrice" in body or "closePrice" in body or "bidPrice1" in body):
        return [("stockInfo", body)]
    if "rawMarketStatus" in body or ("marketCode" in body and "marketStatus" in body and "indexCode" not in body):
        return [("marketSession", body)]
    if "indexCode" in body:
        return [("marketInfo" if ("advances" in body or "indexPercentChange" in body) else "marketVolume", body)]
    if msg.get("type") in {"sub", "unsub", "ping", "pong", "error"} or "status" in msg:
        return [("control", msg)]
    return [("unknown", msg)]


@dataclass
class StreamStats:
    connects: int = 0
    reconnects: int = 0
    messages: int = 0
    unknown: int = 0
    parse_errors: int = 0
    last_message_at: float | None = None
    last_error: str | None = None
    state: str = "disconnected"  # disconnected | connecting | authenticated | stale
    per_channel: dict[str, int] = field(default_factory=dict)


class MarketStream:
    """Vòng đời một kết nối WebSocket bền: kết nối -> auth -> sub -> đọc; lỗi thì lùi dần rồi nối lại."""

    def __init__(self, url: str, token_provider: Callable[[], str],
                 subscriptions: dict[str, list[str]], on_message: Handler, *,
                 stale_after_s: float = 45.0, max_backoff_s: float = 60.0,
                 connect: Callable[..., Any] | None = None):
        self.url, self._token_provider = url, token_provider
        self.subscriptions = {k: list(v) for k, v in subscriptions.items() if v}
        self._on_message = on_message
        self.stale_after_s, self.max_backoff_s = stale_after_s, max_backoff_s
        self._connect = connect
        self.stats = StreamStats()
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    def backoff(self, attempt: int) -> float:
        """Lùi theo cấp số nhân có nhiễu ngẫu nhiên (tránh dồn kết nối lại cùng lúc)."""
        base = min(self.max_backoff_s, 1.0 * 2 ** min(attempt, 10))
        return base * (0.5 + random.random() / 2)

    async def run(self, max_sessions: int | None = None) -> None:
        attempt = sessions = 0
        while not self._stop.is_set():
            self.stats.state = "connecting"
            try:
                await self._session()
                attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - mọi lỗi kết nối đều dẫn tới thử lại
                self.stats.last_error = f"{type(e).__name__}: {e}"
                log.warning("WebSocket lỗi: %s", self.stats.last_error)
            self.stats.state = "disconnected"
            sessions += 1
            if self._stop.is_set() or (max_sessions is not None and sessions >= max_sessions):
                break
            delay = self.backoff(attempt)
            attempt += 1
            self.stats.reconnects += 1
            log.info("Kết nối lại sau %.1fs (lần %d)", delay, attempt)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    async def _session(self) -> None:
        connect = self._connect
        if connect is None:
            import websockets
            connect = websockets.connect
        async with connect(self.url) as ws:
            self.stats.connects += 1
            await ws.send(json.dumps({"action": "auth", "data": self._token_provider()}))
            authed = False
            while not self._stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.stale_after_s)
                except asyncio.TimeoutError:
                    self.stats.state = "stale"
                    raise TimeoutError(f"Không nhận dữ liệu trong {self.stale_after_s:.0f}s - coi như treo") from None
                recv_ts = time.time()
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    self.stats.parse_errors += 1
                    continue
                for channel, body in classify_message(msg):
                    if channel == "auth":
                        if body.get("status") != "success":
                            raise PermissionError(f"Xác thực WebSocket thất bại: {body.get('data')}")
                        authed = True
                        self.stats.state = "authenticated"
                        for ch, ids in self.subscriptions.items():
                            await ws.send(json.dumps({"type": "sub", "channel": ch, "listId": ids}))
                        log.info("WebSocket đã xác thực; đăng ký %s", {k: len(v) for k, v in self.subscriptions.items()})
                        continue
                    if not authed and channel != "control":
                        continue
                    self.stats.messages += 1
                    self.stats.last_message_at = recv_ts
                    self.stats.per_channel[channel] = self.stats.per_channel.get(channel, 0) + 1
                    if channel == "unknown":
                        self.stats.unknown += 1
                    res = self._on_message(channel, body, recv_ts)
                    if asyncio.iscoroutine(res):
                        await res
