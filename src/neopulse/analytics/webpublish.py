"""TÙY CHỌN, TỐN HẠN MỨC: đẩy JSON web lên Vercel Blob (HTTP PUT) theo chu kỳ; chỉ ĐỌC SQLite.

Gói Hobby chỉ có 2.000 thao tác nâng cao mỗi tháng: đẩy mỗi 20 giây (vài tệp mỗi lần) sẽ hết sau 2-3 phiên.
Cách khuyên dùng là snapshot tĩnh: `neopulse publish-static --deploy` (xem analytics/webstatic.py).

Giao thức lấy từ mã nguồn SDK chính thức `@vercel/blob` 2.9.0 (không sao chép mã):
  PUT https://vercel.com/api/blob/?pathname=<đường dẫn>
  Authorization: Bearer <BLOB_READ_WRITE_TOKEN>; x-api-version: 13; x-vercel-blob-store-id: <id lấy từ token>
  x-vercel-blob-access: public; x-add-random-suffix: 0; x-allow-overwrite: 1; x-content-type; x-cache-control-max-age
Phản hồi JSON có `url` (đường dẫn đọc cố định vì không thêm hậu tố ngẫu nhiên).

Mạng rớt KHÔNG làm chết vòng lặp: lỗi tạm thời được thử lại có lùi dần rồi bỏ qua chu kỳ đó, ghi log.
Token không bao giờ xuất hiện trong log hay thông báo lỗi.
"""
from __future__ import annotations

import logging
import time as _time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import time
from pathlib import Path

import httpx

from ..config import Settings
from ..timeutil import now_vn
from . import webexport as wx

log = logging.getLogger(__name__)

BLOB_API_URL = "https://vercel.com/api/blob/"
BLOB_API_VERSION = "13"
CACHE_MAX_AGE_S = 60  # tối thiểu của Vercel Blob: CDN có thể trả bản cũ tới ~60 giây sau khi ghi đè
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}


class BlobPutError(Exception):
    """Lỗi đẩy lên Blob. Thông điệp không chứa token."""


class BlobClient:
    def __init__(self, token: str, *, prefix: str = "", transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = _time.sleep, max_retries: int = 3):
        parts = token.split("_")
        if len(parts) < 4 or not parts[3]:
            raise BlobPutError("BLOB_READ_WRITE_TOKEN không đúng định dạng (không tách được mã store).")
        self._token, self._store_id = token, parts[3]
        self.prefix = prefix.strip("/")
        self._http = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0), transport=transport)
        self._sleep, self._max_retries = sleep, max_retries

    def pathname(self, rel: str) -> str:
        return f"{self.prefix}/{rel}" if self.prefix else rel

    def put(self, rel: str, data: bytes, content_type: str = "application/json") -> str:
        path = self.pathname(rel)
        headers = {"authorization": f"Bearer {self._token}", "x-api-version": BLOB_API_VERSION,
                   "x-vercel-blob-store-id": self._store_id, "x-vercel-blob-access": "public",
                   "x-add-random-suffix": "0", "x-allow-overwrite": "1", "x-content-type": content_type,
                   "x-cache-control-max-age": str(CACHE_MAX_AGE_S)}
        last = ""
        for attempt in range(self._max_retries + 1):
            try:
                r = self._http.put(BLOB_API_URL, params={"pathname": path}, content=data, headers=headers)
            except httpx.HTTPError as e:
                last = f"lỗi mạng {type(e).__name__}"
            else:
                if r.status_code < 300:
                    try:
                        return str(r.json().get("url", ""))
                    except ValueError:
                        return ""
                if r.status_code in (401, 403):
                    raise BlobPutError(f"Blob từ chối quyền ghi (HTTP {r.status_code}) - kiểm tra BLOB_READ_WRITE_TOKEN.")
                if r.status_code not in RETRYABLE:
                    raise BlobPutError(f"Blob từ chối {rel} (HTTP {r.status_code}).")
                last = f"HTTP {r.status_code}"
            if attempt < self._max_retries:
                wait = min(20.0, 1.0 * 2 ** attempt)
                log.warning("Đẩy %s thất bại (%s) - thử lại sau %.0fs", rel, last, wait)
                self._sleep(wait)
        raise BlobPutError(f"Không đẩy được {rel} sau {self._max_retries + 1} lần ({last}).")

    def close(self) -> None:
        self._http.close()


@dataclass
class PublishStats:
    cycles: int = 0
    uploads: int = 0
    failures: int = 0
    last_error: str | None = None


def _upload_files(client: BlobClient | None, work: Path, rels: list[str], stats: PublishStats) -> None:
    if client is None:
        return
    for rel in rels:
        try:
            client.put(rel, (work / rel).read_bytes())
            stats.uploads += 1
        except BlobPutError as e:
            stats.failures += 1
            stats.last_error = str(e)
            log.warning("%s", e)
        except OSError as e:
            stats.failures += 1
            stats.last_error = f"không đọc được {rel}: {type(e).__name__}"
            log.warning("%s", stats.last_error)


def publish_cycle(db_path: str, source: str, work: Path, client: BlobClient | None, stats: PublishStats, *,
                  index_codes: list[str], validation_block: dict | None, order_value: float = 500e6,
                  final: bool = False) -> list[str]:
    """Một chu kỳ: dựng JSON từ SQLite (chỉ đọc) -> ghi thư mục làm việc -> đẩy lên Blob. Trả danh sách tệp đã ghi."""
    (work / "sessions").mkdir(parents=True, exist_ok=True)
    rels: list[str] = []
    try:
        db = wx.ReadOnlyStorage(db_path)
    except Exception as e:  # noqa: BLE001 - CSDL thiếu/khóa: vẫn đẩy trạng thái lỗi để web hiện rõ
        payload = wx.error_payload(source, f"Không đọc được cơ sở dữ liệu ({type(e).__name__}).")
        (work / "latest.json").write_text(wx.dumps(payload), encoding="utf-8")
        _upload_files(client, work, ["latest.json"], stats)
        return ["latest.json"]
    try:
        dates = db.trading_dates(source)
        day = dates[-1] if dates else None
        entries: list[dict] = []
        for code in index_codes:
            payload = wx.build_payload(db, source, day, code, order_value=order_value, extras=validation_block)
            text = wx.dumps(payload)
            for name in wx.latest_filenames(code, index_codes[0]):
                (work / name).write_text(text, encoding="utf-8")
                rels.append(name)
            if final and day:
                rel = wx.session_filename(source, day, code)
                (work / rel).write_text(text, encoding="utf-8")
                rels.append(rel)
                if (e := wx.index_entry(payload, rel)):
                    entries.append(e)
        if final and entries:
            wx.update_index(work, entries)
            rels.append("index.json")
    finally:
        db.close()
    _upload_files(client, work, rels, stats)
    return rels


def run_publish(settings: Settings, *, source: str, every: float = 20.0, until: time | None = None,
                index_codes: list[str] | None = None, work_dir: str | Path = "out/web", dry_run: bool = False,
                client: BlobClient | None = None, validation_every: float = 600.0, max_cycles: int | None = None,
                sleep: Callable[[float], None] = _time.sleep, now: Callable[[], float] = _time.monotonic,
                should_stop: Callable[[], bool] = lambda: False) -> PublishStats:
    codes = [c.upper() for c in (index_codes or [settings.universe_index])]
    work = Path(work_dir)
    stats = PublishStats()
    own = False
    if client is None and not dry_run:
        if not settings.blob_read_write_token:
            raise BlobPutError("Thiếu BLOB_READ_WRITE_TOKEN trong .env (hoặc dùng --dry-run).")
        client, own = BlobClient(settings.blob_read_write_token, prefix=settings.blob_prefix), True
    val_cache: dict | None = None
    val_at = -1e18
    try:
        while True:
            t0 = now()
            if t0 - val_at >= validation_every:
                try:
                    db = wx.ReadOnlyStorage(settings.db_path)
                    try:
                        val_cache = {"validation": wx.build_validation_block(db, source)}
                    finally:
                        db.close()
                except Exception as e:  # noqa: BLE001
                    log.warning("Không tính được khối kiểm chứng: %s", type(e).__name__)
                val_at = t0
            stop = should_stop() or (until is not None and now_vn().time() >= until) \
                or (max_cycles is not None and stats.cycles + 1 >= max_cycles)
            try:
                publish_cycle(settings.db_path, source, work, client, stats, index_codes=codes,
                              validation_block=val_cache, final=stop)
            except Exception as e:  # noqa: BLE001 - không để lỗi bất ngờ giết vòng publish
                stats.failures += 1
                stats.last_error = f"lỗi chu kỳ: {type(e).__name__}"
                log.exception("Chu kỳ publish lỗi")
            stats.cycles += 1
            if stats.cycles % 15 == 1 or stop:
                log.info("publish: %d chu kỳ · %d tệp đã đẩy · %d lỗi%s", stats.cycles, stats.uploads, stats.failures,
                         f" · lỗi gần nhất: {stats.last_error}" if stats.last_error else "")
            if stop:
                break
            sleep(max(0.0, every - (now() - t0)))
    finally:
        if own and client:
            client.close()
    return stats
