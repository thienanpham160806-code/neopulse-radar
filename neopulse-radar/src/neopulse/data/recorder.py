"""Bộ ghi dữ liệu thật: WebSocket Market Stream (chính) + REST định kỳ (bổ sung và đối chiếu).

Luồng chạy:
  1. REST /stock/stockDetailByIndex  -> danh sách mã của rổ + ảnh chụp đầu tiên
  2. REST /stock/fuStockDetail       -> mã HĐTL VN30 đang giao dịch
  3. WebSocket: stockInfo (cổ phiếu + HĐTL), marketInfo (chỉ số), marketSession (phiên)
  4. Mỗi `rest_every_s` giây: REST lấy HĐTL + chỉ số và ĐỐI CHIẾU một nhóm mã với dữ liệu WebSocket
Giới hạn tần suất: WebSocket không tốn lượt REST; phần REST định kỳ chỉ ~3 request mỗi chu kỳ.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, time

from ..config import Settings
from ..neo_api.client import NeoClient
from ..neo_api.ws import MarketStream
from ..timeutil import iso_vn, now_vn
from .ingest import Ingestor
from .storage import Storage

log = logging.getLogger(__name__)
LIVE_SOURCE = "neo"


def bootstrap_universe(client: NeoClient, settings: Settings, ing: Ingestor) -> tuple[list[str], list[str]]:
    """Lấy thành phần rổ + HĐTL qua REST và ghi luôn ảnh chụp đầu tiên."""
    now = now_vn()
    members = client.stock_detail_by_index(settings.universe_index)
    stocks = sorted({str(m.get("symbol", "")).upper() for m in members if m.get("stockType", "ST") == "ST"} - {""})
    for m in members:
        ing.add_quote(m, now)
    extra = [s for s in settings.extra_symbols if s not in stocks]
    if extra:
        for m in client.stock_detail(extra):
            ing.add_quote(m, now)
        stocks += extra
    futures = []
    try:
        fus = client.fu_stock_detail("FUVN30")
        for m in fus:
            ing.add_quote(m, now, "future")
        futures = sorted({str(m.get("symbol", "")).upper() for m in fus} - {""})
    except Exception as e:  # noqa: BLE001 - thiếu phái sinh không được làm hỏng phần cơ sở
        log.warning("Không lấy được danh sách HĐTL: %s", e)
        ing.note(now, "futures_bootstrap_failed", "", str(e)[:200])
    ing.flush()
    log.info("Rổ %s: %d cổ phiếu, %d HĐTL", settings.universe_index, len(stocks), len(futures))
    return stocks, futures


def rest_cycle(client: NeoClient, settings: Settings, ing: Ingestor, stocks: list[str],
               last_ws: dict[str, dict] | None = None, reconcile_n: int = 10) -> dict:
    """Một chu kỳ REST: HĐTL, chỉ số, và đối chiếu `reconcile_n` mã đầu với giá WebSocket gần nhất."""
    now = now_vn()
    stats = {"futures": 0, "index": 0, "checked": 0, "mismatch": 0}
    for m in client.fu_stock_detail("FUVN30"):
        stats["futures"] += ing.add_quote(m, now, "future")
    for m in client.market_index_detail("ALL"):
        if str(m.get("indexCode", "")).upper() in settings.indexes:
            stats["index"] += ing.add_index({**m, "indexTime": None}, now)
    if last_ws is not None and stocks:
        for m in client.stock_detail(stocks[:reconcile_n]):
            sym = str(m.get("symbol", "")).upper()
            ws = last_ws.get(sym)
            if not ws:
                continue
            stats["checked"] += 1
            rest_vol, ws_vol = m.get("totalTradingVolume") or 0, ws.get("totalTradingVolume") or 0
            # REST lấy SAU nên khối lượng lũy kế phải >= WebSocket; nhỏ hơn rõ rệt nghĩa là hai nguồn lệch nhau
            if rest_vol < ws_vol * 0.999 or (rest_vol == ws_vol and m.get("closePrice") != ws.get("closePrice")):
                stats["mismatch"] += 1
                ing.note(now, "ws_rest_mismatch", sym,
                         f"REST vol={rest_vol} last={m.get('closePrice')} | WS vol={ws_vol} last={ws.get('closePrice')}")
        ing.note(now, "reconcile", "", f"đối chiếu {stats['checked']} mã, lệch {stats['mismatch']}")
    return stats


async def record(settings: Settings, *, until: time | None = None, rest_every_s: float = 60.0,
                 flush_every_s: float = 5.0, raw_dump_dir: str | None = "raw_dump") -> dict:
    """Chạy bộ ghi cho tới `until` (giờ VN) hoặc khi nhận Ctrl+C. Trả về thống kê lần chạy."""
    db = Storage(settings.db_path)
    ing = Ingestor(db, LIVE_SOURCE, raw_dump_dir=raw_dump_dir)
    client = NeoClient(settings)
    run_id = db.start_run(iso_vn(now_vn()), LIVE_SOURCE, f"rổ={settings.universe_index}")
    last_ws: dict[str, dict] = {}
    stream: MarketStream | None = None
    try:
        stocks, futures = await asyncio.to_thread(bootstrap_universe, client, settings, ing)
        if not stocks:
            raise RuntimeError(f"Rổ {settings.universe_index} không trả về mã nào - kiểm tra NEOPULSE_UNIVERSE_INDEX.")

        def on_message(channel: str, body: dict, recv_ts: float) -> None:
            if channel == "stockInfo" and isinstance(body.get("symbol"), str):
                last_ws[body["symbol"].upper()] = body
            ing.handle(channel, body, recv_ts)

        stream = MarketStream(settings.neo_ws_market_url, client.token, {
            "stockInfo": stocks + futures, "marketInfo": settings.indexes,
            "marketSession": ["HOSE", "HNX", "UPCOM", "FU"]}, on_message)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stream.stop)
            except (NotImplementedError, RuntimeError):  # Windows
                pass

        async def housekeeping() -> None:
            next_rest = loop.time() + rest_every_s
            while not stream._stop.is_set():
                await asyncio.sleep(flush_every_s)
                ing.flush()
                if until and now_vn().time() >= until:
                    log.info("Đã tới giờ dừng %s", until)
                    stream.stop()
                    return
                if loop.time() >= next_rest:
                    next_rest = loop.time() + rest_every_s
                    try:
                        s = await asyncio.to_thread(rest_cycle, client, settings, ing, stocks, last_ws)
                        st = stream.stats
                        log.info("WS %s | %d tin | lặp %d | loại %d | lạ %d | nối lại %d | REST đối chiếu %d lệch %d",
                                 st.state, st.messages, ing.n_duplicates, ing.n_rejected, ing.n_unknown,
                                 st.reconnects, s["checked"], s["mismatch"])
                    except Exception as e:  # noqa: BLE001 - lỗi REST không được làm dừng luồng WebSocket
                        log.warning("Chu kỳ REST lỗi: %s", e)
                        ing.note(now_vn(), "rest_cycle_failed", "", str(e)[:200])

        hk = asyncio.create_task(housekeeping())
        await stream.run()
        hk.cancel()
    finally:
        ing.flush()
        counts = ing.counts()
        db.finish_run(run_id, iso_vn(now_vn()), **counts,
                      n_reconnects=stream.stats.reconnects if stream else 0)
        client.close()
        db.close()
    return {**counts, "unknown": ing.n_unknown, "reconnects": stream.stats.reconnects if stream else 0}


def poll(settings: Settings, *, interval_s: float = 15.0, until: time | None = None,
         max_cycles: int | None = None, client: NeoClient | None = None, sleep=None) -> dict:
    """Phương án dự phòng chỉ dùng REST khi WebSocket không khả dụng (2 nhóm API: stock + market).

    Mỗi chu kỳ ~3 request, cách nhau `interval_s` >= 5 giây => thấp hơn nhiều so với giới hạn 5 req/giây.
    """
    import time as _time
    if interval_s < 5:
        raise ValueError("interval_s phải >= 5 giây: không dùng REST để giả lập luồng thời gian thực.")
    sleep = sleep or _time.sleep
    db = Storage(settings.db_path)
    ing = Ingestor(db, LIVE_SOURCE)
    own = client is None
    client = client or NeoClient(settings)
    run_id = db.start_run(iso_vn(now_vn()), LIVE_SOURCE, f"REST polling {interval_s}s")
    cycles = 0
    try:
        while max_cycles is None or cycles < max_cycles:
            now: datetime = now_vn()
            if until and now.time() >= until:
                break
            try:
                for m in client.stock_detail_by_index(settings.universe_index):
                    ing.add_quote(m, now)
                rest_cycle(client, settings, ing, [])
            except Exception as e:  # noqa: BLE001
                log.warning("Chu kỳ polling lỗi: %s", e)
                ing.note(now, "poll_failed", "", str(e)[:200])
            ing.flush()
            cycles += 1
            sleep(interval_s)
    except KeyboardInterrupt:
        pass
    finally:
        ing.flush()
        db.finish_run(run_id, iso_vn(now_vn()), **ing.counts())
        if own:
            client.close()
        db.close()
    return {**ing.counts(), "cycles": cycles}
