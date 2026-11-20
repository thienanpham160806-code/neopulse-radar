"""Lắp ráp "ảnh nhìn" của một phiên: mọi con số dashboard và bản tin hiển thị đều đi ra từ đây.

Một điểm lắp ráp duy nhất bảo đảm dashboard, bản tin HTML và kiểm thử dùng cùng một phép tính.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..finance import basis as fbasis
from ..finance import breadth as fbreadth
from ..finance import foreign as fforeign
from ..finance import microstructure as micro
from ..finance import pulse as fpulse
from ..finance import rvol as frvol
from ..finance import sectors as fsectors
from ..timeutil import LUNCH_END, LUNCH_START, SESSION_OPEN, now_vn
from . import alerts as alerting
from . import ranking


def elapsed_minutes(ts: pd.Series) -> pd.Series:
    """Số phút giao dịch đã trôi qua kể từ 09:00, bỏ giờ nghỉ trưa (vector hóa)."""
    m = ts.dt.hour * 60 + ts.dt.minute + ts.dt.second / 60
    o, ls, le = (t.hour * 60 + t.minute for t in (SESSION_OPEN, LUNCH_START, LUNCH_END))
    return (m.clip(upper=ls) - o).clip(lower=0) + (m - le).clip(lower=0)


@dataclass
class SessionView:
    source: str
    trading_date: str | None
    index_code: str
    status: str = "no_data"            # ok | stale | no_data
    status_message: str = "Chưa có dữ liệu."
    last_update: pd.Timestamp | None = None
    age_seconds: float | None = None
    quotes: pd.DataFrame = field(default_factory=pd.DataFrame)
    latest: pd.DataFrame = field(default_factory=pd.DataFrame)
    bars: pd.DataFrame = field(default_factory=pd.DataFrame)
    index: pd.DataFrame = field(default_factory=pd.DataFrame)
    index_row: dict | None = None
    pulse: fpulse.Pulse | None = None
    pulse_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    sensitivity: dict = field(default_factory=dict)
    breadth_universe: dict = field(default_factory=dict)
    divergence: str | None = None
    liquidity: pd.DataFrame = field(default_factory=pd.DataFrame)
    foreign: pd.DataFrame = field(default_factory=pd.DataFrame)
    foreign_summary: dict = field(default_factory=dict)
    ranking: pd.DataFrame = field(default_factory=pd.DataFrame)
    alerts: pd.DataFrame = field(default_factory=pd.DataFrame)
    basis: pd.DataFrame = field(default_factory=pd.DataFrame)
    basis_state: dict = field(default_factory=dict)
    sigma_pct: float = 1.0
    n_history_sessions: int = 0
    sectors: pd.DataFrame = field(default_factory=pd.DataFrame)
    rvol_meta: dict = field(default_factory=dict)

    @property
    def is_simulated(self) -> bool:
        return self.source == "sim"


def latest_per_symbol(quotes: pd.DataFrame) -> pd.DataFrame:
    if quotes.empty:
        return quotes
    return quotes.sort_values("ts").groupby("symbol", as_index=False).last()


def pulse_timeseries(bars: pd.DataFrame, index: pd.DataFrame, sigma_pct: float, freq: str = "1min") -> pd.DataFrame:
    """Điểm nhịp theo từng thanh (không gồm thành phần thanh khoản để giữ định nghĩa nhất quán nội phiên)."""
    if bars.empty or index.empty:
        return pd.DataFrame(columns=["bar", "score"])
    w = bars["total_value"].fillna(0)
    book_weight = w.where(bars["obi3"].notna()).groupby(bars["bar"]).sum()
    book = (bars["obi3"] * w).groupby(bars["bar"]).sum().astype(float) / book_weight.astype(float).where(book_weight > 0)
    fb, fs = bars.groupby("bar")["f_buy_val"].sum(), bars.groupby("bar")["f_sell_val"].sum()
    foreign = (fb - fs).astype(float) / (fb + fs).astype(float).where((fb + fs) > 0)
    ix = fbreadth.add_breadth(index).assign(bar=lambda d: d["ts"].dt.floor(freq)).groupby("bar").last()
    df = pd.DataFrame({"breadth": ix["ad_ratio"], "momentum": np.tanh(ix["pct_change"] / max(sigma_pct, 1e-6)),
                       "book": book, "foreign": foreign, "index_value": ix["value"]}).dropna(subset=["index_value"])
    scores = [fpulse.combine({k: (None if pd.isna(v) else float(v)) for k, v in r.items() if k in fpulse.WEIGHTS}).score
              for r in df[["breadth", "momentum", "book", "foreign"]].to_dict("records")]
    df["score"] = scores
    return df.reset_index()


def build_view(storage, source: str, trading_date: str | None = None, index_code: str = "VN30", *,
               symbols: list[str] | None = None, as_of: pd.Timestamp | None = None, bar_freq: str = "1min",
               stale_after_s: float = 120.0, order_value: float = 500e6, refdata: dict | None = None) -> SessionView:
    dates = storage.trading_dates(source)
    if not dates:
        return SessionView(source, trading_date, index_code,
                           status_message=f"Chưa có dữ liệu cho nguồn '{source}'. Hãy chạy bộ ghi hoặc tạo dữ liệu mô phỏng.")
    day = trading_date if trading_date in dates else dates[-1]
    v = SessionView(source, day, index_code)
    quotes = storage.quotes(day, symbols, "stock", source)
    index = storage.index_ticks(day, index_code, source)
    # tick chỉ số không có % thay đổi là không dùng được (VD 19/11/2026 bộ ghi SSI lấy nhầm khối lượng làm giá trị,
    # xem quality_log 'index_mapping_bug'): bỏ để không làm hỏng chuỗi chỉ số, basis và điểm nhịp
    if len(index):
        index = index[pd.to_numeric(index["pct_change"], errors="coerce").notna()]
    futures = storage.quotes(day, None, "future", source)
    if as_of is not None:
        quotes, index, futures = (d[d["ts"] <= as_of] if len(d) else d for d in (quotes, index, futures))
    if quotes.empty and index.empty:
        v.status_message = f"Không có dữ liệu cho phiên {day} với bộ lọc hiện tại."
        return v
    v.quotes, v.index = quotes, fbreadth.add_breadth(index)
    v.latest = latest_per_symbol(quotes)
    v.bars = micro.make_bars(quotes, bar_freq)

    # ---- trạng thái dữ liệu
    stamps = [d["ts"].max() for d in (quotes, index) if len(d)]
    v.last_update = max(stamps)
    v.age_seconds = (now_vn() - v.last_update.to_pydatetime()).total_seconds()
    is_today = day == now_vn().date().isoformat()
    if source == "sim":
        v.status, v.status_message = "ok", "Dữ liệu MÔ PHỎNG - không phải dữ liệu thị trường."
    elif is_today and v.age_seconds <= stale_after_s:
        v.status, v.status_message = "ok", "Đang nhận dữ liệu."
    elif is_today:
        v.status = "stale"
        v.status_message = (f"Dữ liệu đã cũ {v.age_seconds / 60:.0f} phút - bộ ghi có thể đã dừng, mất kết nối "
                            "hoặc thị trường đang nghỉ.")
    else:
        v.status, v.status_message = "ok", f"Dữ liệu lịch sử của phiên {day} (đã đóng)."

    # ---- lịch sử để chuẩn hóa (chỉ các phiên TRƯỚC phiên đang xem)
    prev_days = [d for d in dates if d < day]
    v.n_history_sessions = len(prev_days)
    expected = float("nan")
    if prev_days:
        hist = storage.index_ticks(None, index_code, source)
        hist = hist[hist["trading_date"].isin(prev_days)]
        if len(hist):
            closes = hist.groupby("trading_date")["pct_change"].last()
            if len(closes) >= 5 and closes.std(ddof=1) > 0:
                v.sigma_pct = float(closes.std(ddof=1))
            if len(index):
                hist = hist.assign(elapsed_min=elapsed_minutes(hist["ts"]))
                expected = fpulse.expected_value_at(hist, float(elapsed_minutes(index["ts"]).iloc[-1]))

    # ---- chỉ số & điểm nhịp
    if len(v.index):
        v.index_row = v.index.iloc[-1].to_dict()
    v.pulse = fpulse.compute_pulse(v.index_row, v.latest, sigma_pct=v.sigma_pct, expected_value=expected)
    if v.pulse.components:
        v.sensitivity = fpulse.sensitivity(v.pulse.components)
    v.pulse_series = pulse_timeseries(v.bars, v.index, v.sigma_pct, bar_freq)
    v.breadth_universe = fbreadth.universe_breadth(v.latest)
    if v.index_row:
        v.divergence = fbreadth.divergence(v.index_row.get("pct_change"), v.index_row.get("ad_ratio"))

    # ---- bảng theo mã
    v.liquidity = micro.liquidity_table(v.latest, v.bars, order_value)
    v.foreign = fforeign.foreign_table(v.latest)
    v.foreign_summary = fforeign.foreign_summary(v.foreign)
    v.ranking = ranking.rank_universe(v.latest)
    # ---- RVOL (so với cùng giờ các phiên trước) làm đầu vào cảnh báo khối lượng; ngành trong phiên
    if refdata is None:
        from .refdata import load_refdata
        refdata = load_refdata(getattr(storage, "path", None))
    avg, profile, v.rvol_meta = rvol_inputs(storage, source, day, prev_days, refdata)
    if avg and len(v.bars):
        v.bars = frvol.add_rvol(v.bars, avg, profile)
    v.alerts = alerting.detect(v.bars, source=source)
    ir = v.index_row or {}
    prev = (ir.get("value") - ir.get("change")) if ir.get("value") is not None and ir.get("change") is not None else None
    v.sectors = fsectors.sector_table(v.latest, refdata.get("reference", {}),
                                      prev if prev is not None and not pd.isna(prev) else None)

    # ---- phái sinh
    if len(futures) and len(index):
        front = futures.sort_values("maturity_date")["symbol"].iloc[0] if futures["maturity_date"].notna().any() \
            else futures["symbol"].iloc[0]
        v.basis = fbasis.basis_series(futures[futures["symbol"] == front], index)
        v.basis_state = fbasis.basis_state(v.basis)
    return v


def fmt_money(x: float | None) -> str:
    """Định dạng giá trị đồng theo thói quen Việt Nam: tỷ / triệu."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    a = abs(x)
    if a >= 1e9:
        return f"{x / 1e9:,.1f} tỷ"
    if a >= 1e6:
        return f"{x / 1e6:,.1f} triệu"
    return f"{x:,.0f}"


_RVOL_CACHE: dict[tuple, tuple] = {}


def rvol_inputs(storage, source: str, day: str, prev_days: list[str], refdata: dict) -> tuple[dict, object, dict]:
    """KL trung bình 20 phiên + đường phân bổ KL trong ngày, kèm mô tả nguồn. Lưu cache theo (CSDL, nguồn, phiên).

    KL TB: REST ngày của SSI (refdata) cho nguồn thật; không có thì trung bình các phiên đã ghi trước đó (>= 3 phiên).
    Đường f(m): thực nghiệm từ >= 3 phiên đã ghi trước đó; không đủ thì giả định phân bổ đều theo phút."""
    key = (getattr(storage, "path", id(storage)), source, day, tuple(prev_days), bool(refdata.get("avg_volume")))
    if key in _RVOL_CACHE:
        return _RVOL_CACHE[key]
    hist = pd.DataFrame()
    if prev_days:
        marks = ", ".join("?" * len(prev_days))
        rows = storage._con.execute(
            "SELECT trading_date, symbol, substr(ts, 1, 16) AS m, MAX(total_volume) FROM quotes WHERE source=? "
            f"AND instrument='stock' AND trading_date IN ({marks}) GROUP BY 1, 2, 3", (source, *prev_days)).fetchall()
        if rows:
            hist = pd.DataFrame(rows, columns=["trading_date", "symbol", "m", "total_volume"])
            hist["bar"] = pd.to_datetime(hist["m"] + ":00+07:00", format="ISO8601").dt.tz_convert("Asia/Ho_Chi_Minh")
    if len(hist):
        hist = frvol.complete_history(hist)
    avg, avg_src = {}, None
    if source != "sim" and refdata.get("avg_volume"):
        avg, avg_src = dict(refdata["avg_volume"]), "SSI REST ngày (20 phiên)"
    elif len(hist):
        avg = frvol.avg_volume_from_history(hist)
        avg_src = f"{min(20, hist['trading_date'].nunique())} phiên đã ghi" if avg else None
    profile = frvol.empirical_profile(hist) if len(hist) else None
    meta = {"avg_source": avg_src, "n_symbols": len(avg),
            "profile": "thực nghiệm từ các phiên đã ghi" if profile else "giả định phân bổ đều theo phút",
            "threshold": frvol.RVOL_SPIKE}
    out = (avg, profile, meta)
    if len(_RVOL_CACHE) > 32:
        _RVOL_CACHE.clear()
    _RVOL_CACHE[key] = out
    return out
