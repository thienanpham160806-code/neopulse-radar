"""Đường ống nhập liệu dùng chung cho cả WebSocket thật, REST và bộ mô phỏng.

thông điệp thô -> chuẩn hóa -> kiểm tra chất lượng -> khử lặp -> gom lô -> SQLite
Mọi vấn đề được ghi vào `quality_log` thay vì bị nuốt im lặng.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..timeutil import VN_TZ, iso_vn
from .normalize import STOCK_NUMERIC, normalize_index, normalize_quote
from .storage import Storage

log = logging.getLogger(__name__)
_CONTENT_COLS = [c for c, _ in STOCK_NUMERIC] + ["auction_flag"]


class Ingestor:
    def __init__(self, storage: Storage, source: str, *, batch_size: int = 500,
                 raw_dump_dir: str | None = None, raw_dump_limit: int = 200):
        self.db, self.source, self.batch_size = storage, source, batch_size
        self._quotes: list[dict] = []
        self._index: list[dict] = []
        self._sessions: list[dict] = []
        self._quality: list[dict] = []
        self._last_sig: dict[str, tuple] = {}
        self._last_cumvol: dict[tuple[str, str], float] = {}
        self._last_index_sig: dict[str, tuple] = {}
        self._pending: dict[tuple[str, str], int] = {}  # (mã, ts) -> vị trí trong lô đang chờ ghi
        self.n_quotes = self.n_index = self.n_rejected = self.n_duplicates = self.n_unknown = 0
        self._raw_dir = Path(raw_dump_dir) if raw_dump_dir else None
        self._raw_left = raw_dump_limit

    # ---------------------------------------------------------------- nhận
    def handle(self, channel: str, body: dict, recv_ts: float) -> None:
        recv = datetime.fromtimestamp(recv_ts, VN_TZ)
        if channel == "stockInfo":
            self.add_quote(body, recv)
        elif channel == "marketInfo":
            self.add_index(body, recv)
        elif channel == "marketSession":
            code = str(body.get("marketCode") or "").upper()
            if code:
                self._sessions.append({"ts": iso_vn(recv), "market_code": code,
                                       "market_status": body.get("marketStatus"), "source": self.source})
        elif channel == "marketVolume":
            pass  # khối lượng lũy kế đã có trong marketInfo; không lưu trùng
        elif channel == "unknown":
            self.n_unknown += 1
            self._q(recv, "unknown_message", "", json.dumps(body, ensure_ascii=False)[:300])
            self._dump_raw(body)
        if len(self._quotes) + len(self._index) >= self.batch_size:
            self.flush()

    def add_quote(self, raw: dict, recv: datetime, instrument: str | None = None) -> bool:
        row, issues = normalize_quote(raw, recv, self.source, instrument)
        subject = str((raw or {}).get("symbol") or "") if isinstance(raw, dict) else ""
        for i in issues:
            self._q(recv, i, subject, "")
        if row is None:
            self.n_rejected += 1
            return False
        sig = tuple(row[c] for c in _CONTENT_COLS)
        if self._last_sig.get(row["symbol"]) == sig:
            self.n_duplicates += 1  # thông điệp lặp nguyên văn: không lưu
            return False
        key = (row["symbol"], row["trading_date"])
        prev = self._last_cumvol.get(key)
        if row["total_volume"] is not None:
            if prev is not None and row["total_volume"] < prev:
                # khối lượng lũy kế giảm trong cùng phiên => thông điệp đến muộn/sai thứ tự
                self.n_rejected += 1
                self._q(recv, "late_or_out_of_order", row["symbol"],
                        f"total_volume {row['total_volume']:.0f} < {prev:.0f}")
                return False
            self._last_cumvol[key] = row["total_volume"]
        self._last_sig[row["symbol"]] = sig
        # Nhiều khung tin của cùng một mã có thể tới trong cùng một mili-giây (nguồn SSI tách trade/quote/room):
        # khóa duy nhất (mã, ts) sẽ bỏ bản ghi đến sau, nên bản đến sau - luôn là trạng thái đầy đủ hơn - thay bản trước.
        slot = self._pending.get((row["symbol"], row["ts"]))
        if slot is not None:
            self._quotes[slot] = row
            return True
        self._pending[(row["symbol"], row["ts"])] = len(self._quotes)
        self._quotes.append(row)
        self.n_quotes += 1
        return True

    def add_index(self, raw: dict, recv: datetime) -> bool:
        row, issues = normalize_index(raw, recv, self.source)
        for i in issues:
            self._q(recv, i, str((raw or {}).get("indexCode") or ""), "")
        if row is None:
            self.n_rejected += 1
            return False
        sig = tuple(v for k, v in row.items() if k != "ts")
        if self._last_index_sig.get(row["index_code"]) == sig:
            self.n_duplicates += 1
            return False
        self._last_index_sig[row["index_code"]] = sig
        self._index.append(row)
        self.n_index += 1
        return True

    def note(self, recv: datetime, kind: str, subject: str = "", detail: str = "") -> None:
        self._q(recv, kind, subject, detail)

    def _q(self, recv: datetime, kind: str, subject: str, detail: str) -> None:
        self._quality.append({"ts": iso_vn(recv), "source": self.source, "kind": kind,
                              "subject": subject, "detail": detail})

    def _dump_raw(self, body) -> None:
        if not self._raw_dir or self._raw_left <= 0:
            return
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        with open(self._raw_dir / "unknown_messages.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(body, ensure_ascii=False) + "\n")
        self._raw_left -= 1

    # ----------------------------------------------------------------- ghi
    def flush(self) -> None:
        self._pending.clear()
        if self._quotes:
            self.db.insert_quotes(self._quotes)
            self._quotes = []
        if self._index:
            self.db.insert_index(self._index)
            self._index = []
        if self._sessions:
            self.db.insert_sessions(self._sessions)
            self._sessions = []
        if self._quality:
            self.db.log_quality(self._quality)
            self._quality = []

    def counts(self) -> dict[str, int]:
        return {"n_quotes": self.n_quotes, "n_index": self.n_index,
                "n_rejected": self.n_rejected, "n_duplicates": self.n_duplicates}
