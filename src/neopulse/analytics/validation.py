"""Kiểm chứng: tín hiệu sổ lệnh có liên hệ với biến động giá kế tiếp trên dữ liệu ĐÃ THU THẬP hay không.

Thiết kế:
  * Tín hiệu tại cuối thanh t (OBI_3, OBI_w, độ lệch microprice) -> lợi suất mid từ t đến t+h.
    Tín hiệu chỉ dùng thông tin đến t; lợi suất tương lai không vượt qua ranh giới phiên.
  * IC = tương quan hạng Spearman theo MẶT CẮT NGANG từng thanh, rồi lấy trung bình (Fama-MacBeth);
    t-stat = mean / (std / sqrt(n)). Thanh liền kề có tự tương quan nên t-stat bị thổi phồng phần nào.
  * Tách THEO THỜI GIAN: các phiên đầu (in-sample) dùng để chọn tín hiệu/chiều; các phiên cuối
    (out-of-sample) chỉ để báo cáo. Không xáo trộn ngẫu nhiên.
  * Tỷ lệ đúng chiều và chênh lệch lợi suất nhóm trên - nhóm dưới (theo ngũ phân vị tín hiệu).
Kết quả trên dữ liệu mô phỏng chỉ xác nhận đường ống tính đúng (tín hiệu được cài sẵn do thiết kế).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SIGNALS = ("obi3", "obi_w", "obi1", "micro_dev_bps")


def add_forward_returns(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5)) -> pd.DataFrame:
    out = bars.sort_values(["trading_date", "symbol", "bar"]).copy()
    g = out.groupby(["trading_date", "symbol"], sort=False)["mid"]
    for h in horizons:
        out[f"fwd_{h}"] = (g.shift(-h) / out["mid"] - 1) * 1e4  # bps; NaN ở cuối phiên
    return out


def _ic_per_bar(d: pd.DataFrame, signal: str, target: str, min_names: int = 8) -> pd.Series:
    """Spearman theo mặt cắt ngang từng thanh = Pearson trên hạng (vector hóa, không lặp từng thanh)."""
    x = d[["bar", signal, target]].dropna()
    if x.empty:
        return pd.Series(dtype=float)
    g = x.groupby("bar")
    r = pd.DataFrame({"bar": x["bar"], "a": g[signal].rank(), "b": g[target].rank()})
    gr = r.groupby("bar")
    da, db = r["a"] - gr["a"].transform("mean"), r["b"] - gr["b"].transform("mean")
    num = (da * db).groupby(r["bar"]).sum()
    den = np.sqrt((da ** 2).groupby(r["bar"]).sum() * (db ** 2).groupby(r["bar"]).sum())
    ic = (num / den.where(den > 0))
    return ic[gr.size() >= min_names].dropna()


def ic_summary(d: pd.DataFrame, signal: str, target: str) -> dict:
    ic = _ic_per_bar(d, signal, target)
    n = len(ic)
    if n < 5:
        return {"n_bars": n, "ic_mean": np.nan, "ic_tstat": np.nan, "hit_rate": np.nan, "spread_bps": np.nan,
                "n_obs": int(d[[signal, target]].dropna().shape[0])}
    x = d[[signal, target, "bar"]].dropna()
    nz = x[(x[signal] != 0) & (x[target] != 0)]
    hit = float((np.sign(nz[signal]) == np.sign(nz[target])).mean()) if len(nz) else np.nan
    q = x.groupby("bar")[signal].rank(pct=True)
    spread = x.loc[q > 0.8, target].mean() - x.loc[q <= 0.2, target].mean()
    return {"n_bars": n, "n_obs": int(len(x)), "ic_mean": float(ic.mean()),
            "ic_tstat": float(ic.mean() / (ic.std(ddof=1) / np.sqrt(n))) if ic.std(ddof=1) > 0 else np.nan,
            "hit_rate": hit, "spread_bps": float(spread)}


def time_split(dates: list[str], train_frac: float = 0.6) -> tuple[list[str], list[str]]:
    """Chia danh sách phiên theo thứ tự thời gian; luôn để lại ít nhất 1 phiên ngoài mẫu."""
    dates = sorted(dates)
    if len(dates) < 2:
        return dates, []
    k = min(len(dates) - 1, max(1, int(round(len(dates) * train_frac))))
    return dates[:k], dates[k:]


def validate_signals(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5), train_frac: float = 0.6) -> dict:
    """Bảng IC trong mẫu / ngoài mẫu cho từng tín hiệu và từng tầm nhìn."""
    if bars.empty:
        return {"table": pd.DataFrame(), "train": [], "test": [], "note": "Không có dữ liệu."}
    d = add_forward_returns(bars, horizons)
    train, test = time_split(d["trading_date"].unique().tolist(), train_frac)
    rows = []
    for sig in SIGNALS:
        for h in horizons:
            for name, days in (("trong mẫu", train), ("ngoài mẫu", test)):
                if not days:
                    continue
                s = ic_summary(d[d["trading_date"].isin(days)], sig, f"fwd_{h}")
                rows.append({"tín hiệu": sig, "tầm nhìn (thanh)": h, "mẫu": name, **s})
    table = pd.DataFrame(rows)
    note = ("" if len(test) else "Chỉ có 1 phiên: chưa thể tách ngoài mẫu - cần thu thập thêm phiên.")
    n_days = len(train) + len(test)
    if n_days < 5:
        note += f" Mới có {n_days} phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa."
    return {"table": table, "train": train, "test": test, "note": note.strip()}


def per_session_ic(bars: pd.DataFrame, signal: str = "obi3", horizon: int = 1) -> pd.DataFrame:
    d = add_forward_returns(bars, (horizon,))
    rows = [{"trading_date": day, **ic_summary(g, signal, f"fwd_{horizon}")} for day, g in d.groupby("trading_date")]
    return pd.DataFrame(rows)


def data_quality_report(storage, source: str | None = None) -> dict:
    """Tổng hợp chất lượng dữ liệu: số bản ghi, vấn đề theo loại, khoảng trống thời gian trong phiên."""
    q = storage.table("quality_log")
    runs = storage.table("ingest_runs")
    if source:
        q, runs = q[q["source"] == source], runs[runs["source"] == source]
    # Quality only needs timestamps and counts; loading the full order book here multiplies peak memory.
    where, params = (" WHERE source=?", (source,)) if source is not None else ("", ())
    n_quotes, n_sessions, n_symbols = storage._con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT trading_date), COUNT(DISTINCT symbol) FROM quotes" + where, params,
    ).fetchone()
    quotes = storage._df("SELECT DISTINCT trading_date, ts FROM quotes" + where + " ORDER BY ts", params)
    gaps = pd.DataFrame()
    if not quotes.empty:
        t = quotes[["trading_date", "ts"]].drop_duplicates().sort_values("ts")
        dt = t.groupby("trading_date")["ts"].diff().dt.total_seconds()
        typical = dt.median()
        t = t.assign(gap_s=dt)
        # khoảng trống > 5 lần nhịp điển hình, trừ giờ nghỉ trưa 11:30-13:00
        lunch = (t["ts"].dt.hour == 13) & (t["ts"].dt.minute < 5)
        gaps = t[(t["gap_s"] > max(5 * typical, 60)) & ~lunch]
    return {"issues": q.groupby("kind").size().sort_values(ascending=False) if len(q) else pd.Series(dtype=int),
            "runs": runs, "gaps": gaps, "n_quotes": int(n_quotes),
            "n_sessions": int(n_sessions), "n_symbols": int(n_symbols)}
