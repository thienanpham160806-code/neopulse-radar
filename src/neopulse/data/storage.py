"""Lưu trữ SQLite (chế độ WAL: bộ ghi và dashboard đọc/ghi đồng thời không khóa nhau).

Bảng:
  quotes       - ảnh chụp sổ lệnh 3 mức + giá + khối lượng + khối ngoại theo mã (cổ phiếu, HĐTL)
  index_ticks  - chỉ số, độ rộng, thanh khoản toàn thị trường
  sessions     - trạng thái phiên theo sàn
  alerts       - cảnh báo đã phát (khóa chống lặp)
  quality_log  - nhật ký vấn đề chất lượng dữ liệu
  ingest_runs  - mỗi lần chạy bộ ghi: nguồn, thời gian, số bản ghi (truy vết nguồn gốc)
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .normalize import INDEX_COLUMNS, QUOTE_COLUMNS

_TEXT_Q = {"ts", "trading_date", "symbol", "instrument", "source", "market_code", "auction_flag",
           "maturity_date", "underlying"}
_TEXT_I = {"ts", "trading_date", "index_code", "source", "market_status"}


def _cols(cols: list[str], text: set[str]) -> str:
    return ", ".join(f"{c} {'TEXT' if c in text else 'REAL'}" for c in cols)


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS quotes ({_cols(QUOTE_COLUMNS, _TEXT_Q)}, UNIQUE(symbol, ts, source));
CREATE INDEX IF NOT EXISTS ix_quotes_date_sym ON quotes(trading_date, symbol, ts);
CREATE TABLE IF NOT EXISTS index_ticks ({_cols(INDEX_COLUMNS, _TEXT_I)}, UNIQUE(index_code, ts, source));
CREATE INDEX IF NOT EXISTS ix_index_date ON index_ticks(trading_date, index_code, ts);
CREATE TABLE IF NOT EXISTS sessions (ts TEXT, market_code TEXT, market_status TEXT, source TEXT,
    UNIQUE(market_code, ts));
CREATE TABLE IF NOT EXISTS alerts (ts TEXT, trading_date TEXT, symbol TEXT, rule TEXT, severity TEXT,
    value REAL, threshold REAL, message TEXT, source TEXT, dedupe_key TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS quality_log (ts TEXT, source TEXT, kind TEXT, subject TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS ingest_runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT,
    ended TEXT, source TEXT, note TEXT, n_quotes INTEGER DEFAULT 0, n_index INTEGER DEFAULT 0,
    n_rejected INTEGER DEFAULT 0, n_duplicates INTEGER DEFAULT 0, n_reconnects INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sim_truth (ts TEXT, trading_date TEXT, symbol TEXT, kind TEXT, detail TEXT);
"""


class Storage:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.executescript(SCHEMA)
        self._con.commit()

    @contextmanager
    def _tx(self):
        try:
            yield self._con
            self._con.commit()
        except Exception:
            self._con.rollback()
            raise

    def _insert(self, table: str, cols: list[str], rows: Iterable[dict]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        sql = f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
        with self._tx() as con:
            cur = con.executemany(sql, [[r.get(c) for c in cols] for r in rows])
            return cur.rowcount if cur.rowcount is not None else len(rows)

    # ------------------------------------------------------------------ ghi
    def insert_quotes(self, rows: Iterable[dict]) -> int:
        return self._insert("quotes", QUOTE_COLUMNS, rows)

    def insert_index(self, rows: Iterable[dict]) -> int:
        return self._insert("index_ticks", INDEX_COLUMNS, rows)

    def insert_sessions(self, rows: Iterable[dict]) -> int:
        return self._insert("sessions", ["ts", "market_code", "market_status", "source"], rows)

    def insert_alerts(self, rows: Iterable[dict]) -> int:
        return self._insert("alerts", ["ts", "trading_date", "symbol", "rule", "severity", "value",
                                       "threshold", "message", "source", "dedupe_key"], rows)

    def log_quality(self, rows: Iterable[dict]) -> int:
        return self._insert("quality_log", ["ts", "source", "kind", "subject", "detail"], rows)

    def insert_sim_truth(self, rows: Iterable[dict]) -> int:
        return self._insert("sim_truth", ["ts", "trading_date", "symbol", "kind", "detail"], rows)

    def start_run(self, started: str, source: str, note: str = "") -> int:
        with self._tx() as con:
            return con.execute("INSERT INTO ingest_runs (started, source, note) VALUES (?,?,?)",
                               (started, source, note)).lastrowid

    def finish_run(self, run_id: int, ended: str, **counts: int) -> None:
        sets = ", ".join(f"{k}=?" for k in counts)
        with self._tx() as con:
            con.execute(f"UPDATE ingest_runs SET ended=?{', ' + sets if sets else ''} WHERE run_id=?",
                        (ended, *counts.values(), run_id))

    def reset(self, source: str | None = None) -> None:
        """Xóa dữ liệu (toàn bộ, hoặc chỉ một nguồn - ví dụ xóa dữ liệu mô phỏng trước khi ghi thật)."""
        with self._tx() as con:
            for t in ("quotes", "index_ticks", "sessions", "alerts", "quality_log", "ingest_runs"):
                con.execute(f"DELETE FROM {t}" + (" WHERE source=?" if source else ""),
                            (source,) if source else ())
            if source in (None, "sim"):
                con.execute("DELETE FROM sim_truth")

    # ------------------------------------------------------------------ đọc
    def _df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        df = pd.read_sql_query(sql, self._con, params=params)
        if "ts" in df.columns and len(df):
            df["ts"] = pd.to_datetime(df["ts"], format="ISO8601").dt.tz_convert("Asia/Ho_Chi_Minh")
        return df

    def sources(self) -> list[str]:
        return [r[0] for r in self._con.execute("SELECT DISTINCT source FROM quotes ORDER BY 1")]

    def trading_dates(self, source: str | None = None) -> list[str]:
        q = "SELECT DISTINCT trading_date FROM quotes" + (" WHERE source=?" if source else "") + " ORDER BY 1"
        return [r[0] for r in self._con.execute(q, (source,) if source else ())]

    def symbols(self, instrument: str = "stock", source: str | None = None) -> list[str]:
        q = "SELECT DISTINCT symbol FROM quotes WHERE instrument=?" + (" AND source=?" if source else "")
        return sorted(r[0] for r in self._con.execute(q, (instrument, source) if source else (instrument,)))

    def quotes(self, trading_date: str | None = None, symbols: list[str] | None = None,
               instrument: str | None = "stock", source: str | None = None) -> pd.DataFrame:
        where, params = [], []
        for col, val in (("trading_date", trading_date), ("instrument", instrument), ("source", source)):
            if val is not None:
                where.append(f"{col}=?")
                params.append(val)
        if symbols:
            where.append(f"symbol IN ({', '.join('?' * len(symbols))})")
            params += list(symbols)
        sql = "SELECT * FROM quotes" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts"
        return self._df(sql, tuple(params))

    def index_ticks(self, trading_date: str | None = None, index_code: str | None = None,
                    source: str | None = None) -> pd.DataFrame:
        where, params = [], []
        for col, val in (("trading_date", trading_date), ("index_code", index_code), ("source", source)):
            if val is not None:
                where.append(f"{col}=?")
                params.append(val)
        sql = "SELECT * FROM index_ticks" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts"
        return self._df(sql, tuple(params))

    def alerts(self, trading_date: str | None = None, source: str | None = None) -> pd.DataFrame:
        where, params = [], []
        for col, val in (("trading_date", trading_date), ("source", source)):
            if val is not None:
                where.append(f"{col}=?")
                params.append(val)
        return self._df("SELECT * FROM alerts" + (" WHERE " + " AND ".join(where) if where else "")
                        + " ORDER BY ts DESC", tuple(params))

    def table(self, name: str) -> pd.DataFrame:
        if name not in {"quality_log", "ingest_runs", "sim_truth", "sessions"}:
            raise ValueError(name)
        return self._df(f"SELECT * FROM {name}")

    def last_update(self, source: str | None = None) -> pd.Timestamp | None:
        q = "SELECT MAX(ts) FROM quotes" + (" WHERE source=?" if source else "")
        v = self._con.execute(q, (source,) if source else ()).fetchone()[0]
        return pd.Timestamp(v) if v else None

    def counts(self) -> dict[str, int]:
        return {t: self._con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("quotes", "index_ticks", "alerts", "quality_log", "ingest_runs")}

    def close(self) -> None:
        self._con.close()
