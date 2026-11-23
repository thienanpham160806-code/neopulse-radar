"""Shared latest-session bootstrap for the web; only derived public indicators leave SQLite."""
from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from ..timeutil import iso_vn, now_vn
from . import webexport as wx

TTL = 7 * 86400
log = logging.getLogger(__name__)


def calculate_validation(db_path, source):
    db = wx.ReadOnlyStorage(db_path)
    try:
        # One consistent read snapshot while the recorder continues writing in WAL mode.
        db._con.execute("BEGIN")
        block = wx.clean(wx.build_validation_block(db, source))
        block["data_until"] = db._con.execute("SELECT MAX(ts) FROM quotes WHERE source=?", (source,)).fetchone()[0]
        block.update(source=source, generated_at=iso_vn(now_vn()))
        return block
    finally:
        db.close()


TICK_URL = "https://neopulse-radar.vercel.app/api/telegram_tick"


def trigger_telegram() -> threading.Thread | None:
    """Báo endpoint gửi tin Telegram có dữ liệu mới. Chạy nền, mọi lỗi bị bỏ qua: không bao giờ chặn bộ phát."""
    secret = os.environ.get("TELEGRAM_TICK_SECRET")
    if not secret:
        return None

    def call():
        try:
            httpx.post(os.environ.get("TELEGRAM_TICK_URL", TICK_URL), headers={"Authorization": "Bearer " + secret}, timeout=55)
        except httpx.HTTPError:
            pass

    thread = threading.Thread(target=call, daemon=True, name="telegram-tick")
    thread.start()
    return thread


class MarketSnapshots:
    def __init__(self, url: str, token: str, *, client=None, mono=time.monotonic, executor=None):
        self.url, self.token = url.rstrip("/"), token
        self.client = client or httpx.Client(timeout=12)
        self.mono, self.next_write = mono, 0.0
        self._pool = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-validation")
        self._validation, self._validation_job, self._validation_identity = None, None, None
        self._validation_due = 0.0

    def validation_extras(self, view, db):
        identity = (view.source, view.trading_date)
        if identity != self._validation_identity:
            self._validation, self._validation_due, self._validation_identity = None, 0.0, identity
        if self._validation_job and self._validation_job[1].done():
            job_identity, future = self._validation_job
            try:
                result = future.result()
                if job_identity == identity:
                    self._validation = result
            except Exception as error:  # noqa: BLE001 - retain last successful result; never stop live ticks
                log.warning("Tính kiểm chứng lỗi: %s", type(error).__name__)
                self._validation_due = min(self._validation_due, self.mono() + 60)
            self._validation_job = None
        if self._validation_job is None and self.mono() >= self._validation_due:
            future = self._pool.submit(calculate_validation, db.path, view.source)
            self._validation_job = (identity, future)
            self._validation_due = self.mono() + 600
        return {"validation": self._validation} if self._validation else None

    @classmethod
    def from_env(cls):
        url, token = os.environ.get("KV_REST_API_URL"), os.environ.get("KV_REST_API_TOKEN")
        return cls(url, token) if url and token else None

    def __call__(self, view, db):
        if view.source == "sim" or view.status not in ("ok", "stale") or self.mono() < self.next_write:
            return
        # Limit full payload writes; Ably still carries ticks and pulse between these refreshes.
        self.next_write = self.mono() + 60
        extras = self.validation_extras(view, db)
        payloads = [wx.payload_from_view(view, db, extras=extras)]
        if view.index_code != "VNINDEX":
            other = wx.build_payload(db, view.source, view.trading_date, "VNINDEX", extras=extras)
            if other.get("pulse") and other["meta"]["trading_date"] == view.trading_date:
                payloads.append(other)
        commands = []
        for payload in payloads:
            meta = payload["meta"]
            code, day = meta["index_code"], meta["trading_date"]
            encoded = wx.dumps(payload)
            commands += [["SETEX", f"neopulse:market:latest:{code}", TTL, encoded],
                         ["SETEX", f"neopulse:market:session:{day}:{code}", TTL, encoded]]
        response = self.client.post(self.url + "/pipeline", json=commands, headers={"Authorization": "Bearer " + self.token})
        response.raise_for_status()
        if any(r.get("error") for r in response.json()):
            raise RuntimeError("Market snapshot store rejected update")
        trigger_telegram()

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)
        self.client.close()
