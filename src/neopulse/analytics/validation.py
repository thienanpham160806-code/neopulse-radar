"""Kiểm chứng: tín hiệu sổ lệnh có liên hệ với biến động giá kế tiếp trên dữ liệu ĐÃ THU THẬP hay không.

Thiết kế:
  * Tín hiệu tại cuối thanh t (OBI_3, OBI_w, độ lệch microprice) -> lợi suất mid từ t đến t+h.
    Tín hiệu chỉ dùng thông tin đến t; lợi suất tương lai không vượt qua ranh giới phiên.
  * IC = tương quan hạng Spearman theo MẶT CẮT NGANG từng thanh, rồi lấy trung bình (Fama-MacBeth).
    Ba thống kê t, từ lạc quan nhất đến thận trọng nhất:
      - ic_tstat: mean / (std / sqrt(số thanh)), coi các thanh độc lập (thanh liền kề tự tương quan nên bị thổi phồng);
      - ic_tstat_nw: Newey-West (Bartlett), độ trễ L = max(h, 4(n/100)^(2/9)), tự hiệp phương sai chỉ trong cùng phiên;
      - ic_tstat_session: IC trung bình từng phiên, n = số phiên (mỗi phiên một quan sát).
  * Q5-Q1 (spread_bps) là chênh lợi suất giá giữa nhóm tín hiệu cao nhất - thấp nhất, CHƯA trừ chi phí.
    q5q1_net_bps: mua Q5 ở giá bán_t, bán ở giá mua_{t+h}; bán khống Q1 ở giá mua_t, mua lại ở giá bán_{t+h};
    trừ thêm phí GIẢ ĐỊNH 0,15%/chiều (FEE_BPS) cho mỗi chiều. q5_long_net_bps: benchmark giả định chỉ chân mua Q5
    (không bán khống); chưa kiểm khả năng khớp ở mức 1, tồn kho để bán sau h thanh hay quy định thanh toán (CX-022).
  * Phạm vi: chỉ cổ phiếu (stocks_only); HĐTL có bước giá và chi phí khác nên không trộn vào mặt cắt (CX-023).
  * Placebo (placebo_table): xáo tín hiệu giữa các mã trong cùng thanh, và dùng tín hiệu cũ t-h; IC phải gần 0.
  * Tín hiệu và giá giữa tại t lấy cùng một ảnh chụp sổ lệnh (finance.microstructure.make_bars, CX-016).
  * Tách THEO THỜI GIAN: các phiên đầu (in-sample) dùng để chọn tín hiệu/chiều; các phiên cuối
    (out-of-sample) chỉ để báo cáo. Không xáo trộn ngẫu nhiên.
  * Tỷ lệ đúng chiều và chênh lệch lợi suất nhóm trên - nhóm dưới (theo ngũ phân vị tín hiệu).
Kết quả trên dữ liệu mô phỏng chỉ xác nhận đường ống tính đúng (tín hiệu được cài sẵn do thiết kế).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SIGNALS = ("obi3", "obi_w", "obi1", "micro_dev_bps")
FEE_BPS = 15.0  # GIẢ ĐỊNH phí giao dịch 0,15% mỗi chiều (không phải biểu phí của công ty chứng khoán cụ thể)
PLACEBO_REPS = 20
MIN_SESSIONS_T = 3  # t theo phiên với 2 phiên (1 bậc tự do) không có nghĩa


def stocks_only(quotes: pd.DataFrame) -> pd.DataFrame:
    """Chỉ giữ cổ phiếu cho kiểm chứng; dữ liệu không có cột instrument (mô phỏng cũ, test) giữ nguyên."""
    if "instrument" not in quotes.columns:
        return quotes
    return quotes[quotes["instrument"].fillna("stock") == "stock"]


def add_forward_returns(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5)) -> pd.DataFrame:
    out = bars.sort_values(["trading_date", "symbol", "bar"]).copy()
    g = out.groupby(["trading_date", "symbol"], sort=False)["mid"]
    for h in horizons:
        out[f"fwd_{h}"] = (g.shift(-h) / out["mid"] - 1) * 1e4  # bps; NaN ở cuối phiên
        if {"bid1", "ask1"} <= set(out.columns):
            gb = out.groupby(["trading_date", "symbol"], sort=False)
            # chân mua: vào ở giá bán_t, ra ở giá mua_{t+h}; chân bán khống: vào ở giá mua_t, ra ở giá bán_{t+h}
            out[f"long_{h}"] = (gb["bid1"].shift(-h) / out["ask1"] - 1) * 1e4 - 2 * FEE_BPS
            out[f"short_{h}"] = (1 - gb["ask1"].shift(-h) / out["bid1"]) * 1e4 - 2 * FEE_BPS
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


def newey_west_t(ic: pd.Series, session: pd.Series, lag: int) -> float:
    """t của trung bình IC với sai số chuẩn Newey-West (trọng số Bartlett); tự hiệp phương sai chỉ tính trong cùng phiên."""
    e = ic - ic.mean()
    n = len(e)
    var = float((e * e).sum()) / n
    for k in range(1, lag + 1):
        same = session.eq(session.shift(k))
        var += 2 * (1 - k / (lag + 1)) * float((e * e.shift(k))[same].sum()) / n
    return float(ic.mean() / np.sqrt(var / n)) if var > 0 else np.nan


def nw_lag(n: int, h: int) -> int:
    return max(h, int(np.floor(4 * (n / 100) ** (2 / 9))))


def ic_summary(d: pd.DataFrame, signal: str, target: str, h: int = 1) -> dict:
    ic = _ic_per_bar(d, signal, target)
    n = len(ic)
    empty = {"n_bars": n, "ic_mean": np.nan, "ic_tstat": np.nan, "ic_tstat_nw": np.nan, "nw_lag": np.nan,
             "n_sessions": 0, "ic_tstat_session": np.nan, "hit_rate": np.nan, "spread_bps": np.nan,
             "q5q1_net_bps": np.nan, "q5_long_net_bps": np.nan, "n_obs": int(d[[signal, target]].dropna().shape[0])}
    if n < 5:
        return empty
    x = d[[signal, target, "bar"]].dropna()
    nz = x[(x[signal] != 0) & (x[target] != 0)]
    hit = float((np.sign(nz[signal]) == np.sign(nz[target])).mean()) if len(nz) else np.nan
    q = x.groupby("bar")[signal].rank(pct=True)
    spread = x.loc[q > 0.8, target].mean() - x.loc[q <= 0.2, target].mean()
    bar_day = d.drop_duplicates("bar").set_index("bar")["trading_date"].reindex(ic.index)
    by_day = ic.groupby(bar_day.to_numpy()).mean()
    lag = nw_lag(n, h)
    net = {"q5q1_net_bps": np.nan, "q5_long_net_bps": np.nan}
    if f"long_{h}" in d.columns:
        c = d[[signal, "bar", f"long_{h}", f"short_{h}"]].dropna()
        qc = c.groupby("bar")[signal].rank(pct=True)
        lo, sh = c.loc[qc > 0.8, f"long_{h}"].mean(), c.loc[qc <= 0.2, f"short_{h}"].mean()
        net = {"q5q1_net_bps": float(lo + sh), "q5_long_net_bps": float(lo)}
    return {"n_bars": n, "n_obs": int(len(x)), "ic_mean": float(ic.mean()),
            "ic_tstat": float(ic.mean() / (ic.std(ddof=1) / np.sqrt(n))) if ic.std(ddof=1) > 0 else np.nan,
            "ic_tstat_nw": newey_west_t(ic, bar_day, lag), "nw_lag": lag, "n_sessions": int(len(by_day)),
            "ic_tstat_session": (float(by_day.mean() / (by_day.std(ddof=1) / np.sqrt(len(by_day))))
                                 if len(by_day) >= MIN_SESSIONS_T and by_day.std(ddof=1) > 0 else np.nan),
            "hit_rate": hit, "spread_bps": float(spread), **net}


def time_split(dates: list[str], train_frac: float = 0.6) -> tuple[list[str], list[str]]:
    """Chia danh sách phiên theo thứ tự thời gian; luôn để lại ít nhất 1 phiên ngoài mẫu."""
    dates = sorted(dates)
    if len(dates) < 2:
        return dates, []
    k = min(len(dates) - 1, max(1, int(round(len(dates) * train_frac))))
    return dates[:k], dates[k:]


def validate_signals(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5), train_frac: float = 0.6,
                     split: tuple[list[str], list[str]] | None = None) -> dict:
    """Bảng IC trong mẫu / ngoài mẫu cho từng tín hiệu và từng tầm nhìn.

    `split`: danh sách phiên trong mẫu / ngoài mẫu cố định từ trước (VD chia trên MỌI phiên rồi mới lọc phiên đủ),
    để một phiên không đổi vai trò giữa các bảng (CX-017). Không truyền thì chia theo `train_frac`."""
    if bars.empty:
        return {"table": pd.DataFrame(), "train": [], "test": [], "note": "Không có dữ liệu."}
    d = add_forward_returns(bars, horizons)
    days = sorted(d["trading_date"].unique().tolist())
    if split is not None:
        train, test = [x for x in days if x in set(split[0])], [x for x in days if x in set(split[1])]
    else:
        train, test = time_split(days, train_frac)
    rows = []
    for sig in SIGNALS:
        for h in horizons:
            for name, days in (("trong mẫu", train), ("ngoài mẫu", test)):
                if not days:
                    continue
                s = ic_summary(d[d["trading_date"].isin(days)], sig, f"fwd_{h}", h)
                rows.append({"tín hiệu": sig, "tầm nhìn (thanh)": h, "mẫu": name, **s})
    table = pd.DataFrame(rows)
    note = ("" if len(test) else "Chỉ có 1 phiên: chưa thể tách ngoài mẫu - cần thu thập thêm phiên.")
    n_days = len(train) + len(test)
    if n_days < 5:
        note += f" Mới có {n_days} phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa."
    return {"table": table, "train": train, "test": test, "note": note.strip()}


def placebo_table(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5), signals: tuple[str, ...] = ("obi3",),
                  seed: int = 0) -> pd.DataFrame:
    """Placebo, IC phải gần 0 nếu đường tính không rò rỉ:
      * "xáo giữa các mã": hoán vị tín hiệu giữa các mã trong CÙNG thanh (PLACEBO_REPS lần, báo trung bình và độ lệch);
      * "tín hiệu cũ t-h": tín hiệu của thanh t-h ghép với lợi suất t -> t+h (cùng mã, cùng phiên).
    Tín hiệu bền theo thời gian thì placebo t-h có thể khác 0 một cách chính đáng; xem cột ghi chú khi đọc."""
    if bars.empty:
        return pd.DataFrame()
    d = add_forward_returns(bars, horizons)
    rng = np.random.default_rng(seed)
    rows = []
    for sig in signals:
        for h in horizons:
            target = f"fwd_{h}"
            real = ic_summary(d, sig, target, h)
            shuffled = []
            for _ in range(PLACEBO_REPS):
                p = d[["bar", sig, target]].sort_values("bar", kind="stable").copy()
                p["_r"] = rng.random(len(p))
                p[sig] = p.sort_values(["bar", "_r"])[sig].to_numpy()  # hoán vị trong từng thanh
                shuffled.append(_ic_per_bar(p, sig, target).mean())
            stale = d.copy()
            stale[sig] = stale.groupby(["trading_date", "symbol"], sort=False)[sig].shift(h)
            st = ic_summary(stale, sig, target, h)
            rows += [{"tín hiệu": sig, "tầm nhìn (thanh)": h, "kiểu": "thật", "ic_mean": real["ic_mean"],
                      "ic_sd": np.nan, "ic_tstat_nw": real["ic_tstat_nw"]},
                     {"tín hiệu": sig, "tầm nhìn (thanh)": h, "kiểu": f"xáo giữa các mã ({PLACEBO_REPS} lần)",
                      "ic_mean": float(np.mean(shuffled)), "ic_sd": float(np.std(shuffled, ddof=1)), "ic_tstat_nw": np.nan},
                     {"tín hiệu": sig, "tầm nhìn (thanh)": h, "kiểu": f"tín hiệu cũ t-{h}", "ic_mean": st["ic_mean"],
                      "ic_sd": np.nan, "ic_tstat_nw": st["ic_tstat_nw"]}]
    return pd.DataFrame(rows)


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
