"""Bộ ghi dữ liệu thật từ SSI FastConnect: REST lấy rổ cổ phiếu + WebSocket streaming theo chủ đề.

Luồng chạy:
  1. REST /api/v3/data/securitiesByBoard?index=VN30 -> danh sách mã của rổ
  2. WebSocket: trade/quote/room/market cho từng mã, trade.index.<mã> cho chỉ số, market.flag cho cờ phiên
  3. `SsiAdapter` gộp các tin rời rạc thành bản ghi theo lược đồ NEO -> `Ingestor` (dùng chung với NEO)
Dữ liệu ghi với source='ssi' để luôn truy vết được nguồn.
"""
from __future__ import annotations

import asyncio
import calendar
import logging
import signal
from datetime import date, time, timedelta

from ..config import Settings
from ..ssi.adapter import SsiAdapter
from ..ssi.client import SsiClient
from ..ssi.ws import SsiStream, build_topics
from ..timeutil import iso_vn, now_vn
from .ingest import Ingestor
from .storage import Storage

log = logging.getLogger(__name__)
LIVE_SOURCE = "ssi"


def vn30f_maturity(code: str) -> str | None:
    """VN30F2612 -> ngày đáo hạn = thứ Năm thứ ba của tháng 12/2026 (quy ước HĐTL chỉ số HNX). Không đúng mẫu -> None."""
    c = code.upper()
    if not (c.startswith("VN30F") and len(c) == 9 and c[5:].isdigit()):
        return None
    year, month = 2000 + int(c[5:7]), int(c[7:9])
    if not 1 <= month <= 12:
        return None
    first = date(year, month, 1)
    thursdays = [first + timedelta(days=d) for d in range(calendar.monthrange(year, month)[1])
                 if (first + timedelta(days=d)).weekday() == 3]
    return thursdays[2].isoformat()


def futures_meta(codes: list[str]) -> dict[str, dict]:
    return {c: {"maturityDate": vn30f_maturity(c), "underlyingSymbol": "VN30"} for c in codes}


def bootstrap_universe(client: SsiClient, settings: Settings) -> list[str]:
    members = client.securities_by_index(settings.universe_index)
    stocks = sorted({str(m.get("symbol", "")).upper() for m in members} - {""})
    extra = [s for s in settings.extra_symbols if s not in stocks]
    log.info("Rổ %s: %d cổ phiếu (+%d mã bổ sung)", settings.universe_index, len(stocks), len(extra))
    return stocks + extra


async def record_ssi(settings: Settings, *, until: time | None = None, flush_every_s: float = 5.0,
                     raw_dump_dir: str | None = "raw_dump") -> dict:
    db = Storage(settings.db_path)
    ing = Ingestor(db, LIVE_SOURCE, raw_dump_dir=raw_dump_dir)
    client = SsiClient(settings)
    run_id = db.start_run(iso_vn(now_vn()), LIVE_SOURCE, f"rổ={settings.universe_index}")
    stream: SsiStream | None = None
    try:
        stocks = await asyncio.to_thread(bootstrap_universe, client, settings)
        if not stocks:
            raise RuntimeError(f"Rổ {settings.universe_index} không trả về mã nào - kiểm tra NEOPULSE_UNIVERSE_INDEX.")
        adapter = SsiAdapter(futures_meta=futures_meta(settings.futures), price_scale=settings.ssi_price_scale)
        adapter.watch = set(stocks)
        try:  # luồng market.<mã> không gửi trần/sàn/tham chiếu trong phiên -> nạp từ REST masterdata
            n = adapter.preload_master(await asyncio.to_thread(client.masterdata))
            log.info("Đã nạp trần/sàn/tham chiếu cho %d/%d mã từ REST masterdata", n, len(stocks) + len(settings.futures))
        except Exception as e:  # noqa: BLE001 - thiếu giá tham chiếu không được làm dừng bộ ghi
            log.warning("Không nạp được masterdata (%s): %% thay đổi và trần/sàn sẽ trống", type(e).__name__)
            db.log_quality([{"ts": iso_vn(now_vn()), "source": LIVE_SOURCE, "kind": "masterdata_failed",
                             "subject": "masterdata", "detail": type(e).__name__}])

        def on_message(channel: str, body: dict, recv_ts: float) -> None:
            ing.handle(channel, body, recv_ts)

        stream = SsiStream(settings.ssi_stream_url, client.token,
                           build_topics(stocks, settings.futures, settings.indexes), adapter, on_message,
                           expiry_provider=lambda: client.token_expiry)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stream.stop)
            except (NotImplementedError, RuntimeError):  # Windows
                pass

        async def housekeeping() -> None:
            while not stream._stop.is_set():
                await asyncio.sleep(flush_every_s)
                ing.flush()
                if until and now_vn().time() >= until:
                    log.info("Đã tới giờ dừng %s", until)
                    stream.stop()
                    return
                st = stream.stats
                log.info("SSI WS %s | %d tin | lặp %d | loại %d | lạ %d | nối lại %d",
                         st.state, st.messages, ing.n_duplicates, ing.n_rejected, ing.n_unknown, st.reconnects)

        hk = asyncio.create_task(housekeeping())
        await stream.run()
        hk.cancel()
    finally:
        ing.flush()
        counts = ing.counts()
        db.finish_run(run_id, iso_vn(now_vn()), **counts, n_reconnects=stream.stats.reconnects if stream else 0)
        client.close()
        db.close()
    return {**counts, "unknown": ing.n_unknown, "reconnects": stream.stats.reconnects if stream else 0}
