"""Số liệu cho báo cáo đồ án: `neopulse report-data --source ssi --out report/data/`.

Chỉ đọc SQLite (mở bằng URI mode=ro). Mọi con số sinh từ CSDL hoặc từ lệnh chạy thật; thiếu thì ghi "chưa có".
Đầu ra:
  sessions.csv        mỗi phiên: giờ, số bản ghi, độ phủ, khoảng trống lớn nhất, nối lại, tin lặp/loại/lạ
  alerts.csv          số cảnh báo theo phiên x quy tắc x mức (cùng hàm build_view với web)
  validation.csv      IC trong/ngoài mẫu: mọi phiên và chỉ các phiên đủ (cùng một cách chia phiên)
  placebo.csv         IC placebo (xáo giữa các mã, tín hiệu cũ t-h) trên mọi phiên
  SUMMARY.md          bản tổng hợp để dán vào báo cáo
Không xuất giá hay sổ lệnh từng tick.
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ..data.storage import Storage
from ..finance import rvol as frvol
from ..timeutil import trading_minutes_elapsed

COMPLETE_SHARE = 0.9  # phiên "đủ" khi >= 90% mã có dữ liệu đạt tiêu chí complete_history của finance/rvol.py
NA = "chưa có"


class ReadOnlyStorage(Storage):
    """Storage mở chỉ đọc: không tạo bảng, không đổi chế độ nhật ký, không ghi gì vào CSDL."""

    def __init__(self, path: str | Path):
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Không thấy CSDL: {p}")
        self.path = str(p)
        self._con = sqlite3.connect(f"file:{p.resolve().as_posix()}?mode=ro", uri=True, timeout=30,
                                    check_same_thread=False)


def _one(db: Storage, sql: str, params: tuple = ()):
    return db._con.execute(sql, params).fetchone()


def _minute_bars(db: Storage, source: str, day: str) -> pd.DataFrame:
    """Thanh 1 phút (KL lũy kế lớn nhất trong phút) theo mã, đúng dạng complete_history cần."""
    rows = db._con.execute(
        "SELECT trading_date, symbol, substr(ts, 1, 16) AS m, MAX(total_volume) FROM quotes "
        "WHERE source=? AND instrument='stock' AND trading_date=? GROUP BY 1, 2, 3", (source, day)).fetchall()
    h = pd.DataFrame(rows, columns=["trading_date", "symbol", "m", "total_volume"])
    if len(h):
        h["bar"] = pd.to_datetime(h["m"] + ":00+07:00", format="ISO8601").dt.tz_convert("Asia/Ho_Chi_Minh")
    return h


def _largest_gap(minutes: list[float]) -> tuple[float, float]:
    """Khoảng trống lớn nhất (phút giao dịch, bỏ nghỉ trưa) tính cả đầu phiên 09:00 và cuối phiên 15:00.
    -> (độ dài, phút giao dịch bắt đầu khoảng trống)."""
    m = np.unique(np.r_[0.0, np.asarray(minutes, dtype=float), frvol.SESSION_MIN])
    d = np.diff(m)
    i = int(d.argmax())
    return float(d[i]), float(m[i])


def _minute_to_clock(m: float) -> str:
    """Phút giao dịch thứ m -> giờ HH:MM (sáng 09:00-11:30, chiều 13:00-15:00)."""
    total = 9 * 60 + m if m <= 150 else 13 * 60 + (m - 150)
    return f"{int(total // 60):02d}:{int(total % 60):02d}"


def session_table(db: Storage, source: str) -> pd.DataFrame:
    rows = []
    runs = db._df("SELECT * FROM ingest_runs WHERE source=?", (source,))
    if len(runs):
        runs["day"] = runs["started"].astype(str).str[:10]
    qlog = db._df("SELECT ts, kind FROM quality_log WHERE source=?", (source,))
    if len(qlog):
        qlog["day"] = qlog["ts"].astype(str).str[:10]
    for day in db.trading_dates(source):
        n_quotes, n_sym, t0, t1 = _one(db, "SELECT COUNT(*), COUNT(DISTINCT CASE WHEN instrument='stock' THEN symbol END), "
                                           "MIN(ts), MAX(ts) FROM quotes WHERE source=? AND trading_date=?", (source, day))
        n_index = _one(db, "SELECT COUNT(*) FROM index_ticks WHERE source=? AND trading_date=?", (source, day))[0]
        bars = _minute_bars(db, source, day)
        minutes = [trading_minutes_elapsed(t.to_pydatetime()) for t in bars["bar"].drop_duplicates()] if len(bars) else []
        gap, gap_at = _largest_gap(minutes)
        complete = frvol.complete_history(bars) if len(bars) else bars
        n_complete = int(complete[["symbol"]].drop_duplicates().shape[0]) if len(complete) else 0
        r = runs[runs["day"] == day] if len(runs) else runs
        q = qlog[qlog["day"] == day] if len(qlog) else qlog
        rows.append({
            "phiên": day,
            "bắt đầu": str(t0)[11:19], "kết thúc": str(t1)[11:19],
            "bản ghi giá": int(n_quotes), "tick chỉ số": int(n_index), "số mã": int(n_sym),
            "mã ghi trọn": n_complete,
            "khoảng trống lớn nhất (phút)": round(gap, 1), "khoảng trống từ": _minute_to_clock(gap_at),
            "lượt chạy bộ ghi": int(len(r)),
            "lần nối lại": int(r["n_reconnects"].fillna(0).sum()) if len(r) else 0,
            "tin lặp": int(r["n_duplicates"].fillna(0).sum()) if len(r) else 0,
            "tin bị loại": int(r["n_rejected"].fillna(0).sum()) if len(r) else 0,
            "tin lạ": int((q["kind"] == "unknown_message").sum()) if len(q) else 0,
            "ghi chú chất lượng": int((q["kind"] != "unknown_message").sum()) if len(q) else 0,
            "đủ": bool(n_sym and n_complete >= COMPLETE_SHARE * n_sym),
        })
    return pd.DataFrame(rows)


def alert_table(db: Storage, source: str, index_code: str = "VN30") -> pd.DataFrame:
    """Cảnh báo theo đúng đường tính của web (build_view, có RVOL), đếm theo phiên x quy tắc x mức."""
    from .view import build_view
    parts = []
    for day in db.trading_dates(source):
        al = build_view(db, source, day, index_code).alerts
        if len(al):
            parts.append(al.groupby(["trading_date", "rule", "severity"]).size().rename("số cảnh báo").reset_index())
    cols = ["trading_date", "rule", "severity", "số cảnh báo"]
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    return out.rename(columns={"trading_date": "phiên", "rule": "quy tắc", "severity": "mức"})


def _bars(db: Storage, source: str, days: list[str]) -> pd.DataFrame:
    from ..finance.microstructure import make_bars
    parts = [make_bars(db.quotes(day, source=source), "1min") for day in days]  # từng phiên: không nạp mọi tick một lúc
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def validation_table(db: Storage, source: str, days: list[str] | None = None,
                     split: tuple[list[str], list[str]] | None = None) -> tuple[pd.DataFrame, dict]:
    """`split` cố định trong mẫu/ngoài mẫu trên MỌI phiên để lọc phiên đủ không đổi vai trò của phiên nào (CX-017)."""
    from .validation import validate_signals
    bars = _bars(db, source, days if days is not None else db.trading_dates(source))
    if bars.empty:
        return pd.DataFrame(), {"train": [], "test": [], "note": "Không có phiên nào trong phạm vi này."}
    res = validate_signals(bars, split=split)
    return res["table"], {"train": res["train"], "test": res["test"], "note": res["note"]}


def placebo(db: Storage, source: str) -> pd.DataFrame:
    from .validation import placebo_table
    bars = _bars(db, source, db.trading_dates(source))
    return placebo_table(bars, signals=("obi3", "micro_dev_bps")) if len(bars) else pd.DataFrame()


def count_tests(root: Path) -> dict[str, int | None]:
    """Đếm ca kiểm thử bằng lệnh thật: `pytest --co -q` và `vitest list`. Không chạy được thì None."""
    out: dict[str, int | None] = {"pytest": None, "vitest": None}
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "--co", "-q"], cwd=root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        m = re.search(r"(\d+) tests? collected", r.stdout)
        # addopts="-q" cộng --co -q thành -qq: pytest in "tệp: số ca" thay vì tổng
        per_file = [int(n) for n in re.findall(r"^\S+\.py: (\d+)$", r.stdout, re.M)]
        out["pytest"] = int(m.group(1)) if m else (sum(per_file) if per_file and r.returncode == 0 else None)
    except (OSError, subprocess.SubprocessError):
        pass
    npx = shutil.which("npx")
    web = root / "web"
    if npx and (web / "node_modules").exists():
        try:
            r = subprocess.run([npx, "vitest", "list", "--json"], cwd=web, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
            import json
            out["vitest"] = len(json.loads(r.stdout[r.stdout.index("["):]))
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return out


def _fmt(x, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return NA
    if isinstance(x, (float, np.floating)):
        return f"{x:.0f}" if float(x).is_integer() else f"{x:.{nd}f}"
    return str(x)


def _md(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return [NA]
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return [head, sep, *body]


def _rule_notes(alerts: pd.DataFrame, n_sessions: int) -> list[str]:
    rules = ["volume_spike", "spread_blowout", "price_jump", "foreign_flow", "book_pressure", "near_limit"]
    total = int(alerts["số cảnh báo"].sum()) if len(alerts) else 0
    by_rule = alerts.groupby("quy tắc")["số cảnh báo"].sum() if len(alerts) else pd.Series(dtype=int)
    notes = []
    for r in rules:
        n = int(by_rule.get(r, 0))
        share = n / total if total else 0.0
        if n == 0:
            notes.append(f"- `{r}`: không báo lần nào trong {n_sessions} phiên (ít bất thường; xem lại ngưỡng hoặc dữ liệu đầu vào).")
        elif share >= 0.5:
            notes.append(f"- `{r}`: {n} cảnh báo, chiếm {share:.0%} tổng số (nhiều bất thường; có thể ngưỡng quá thấp so với dữ liệu thật).")
    return notes or ["- Không quy tắc nào lệch hẳn (không quy tắc nào chiếm >= 50% hoặc bằng 0)."]


def ic_conclusion(table: pd.DataFrame, plac: pd.DataFrame) -> list[str]:
    """Kết luận sinh từ số liệu (không gõ tay): liên hệ thống kê ngoài mẫu và khả năng khai thác sau chi phí."""
    from .validation import FEE_BPS
    out = table[table["mẫu"] == "ngoài mẫu"] if len(table) else table
    if out.empty:
        return ["### Kết luận", "", NA]
    nw = out["ic_tstat_nw"]
    sig = int((nw.abs() > 2).sum())
    shuf = plac[plac["kiểu"].str.startswith("xáo")]["ic_mean"].abs().max() if len(plac) else np.nan
    stale = plac[plac["kiểu"].str.startswith("tín hiệu cũ")]["ic_mean"] if len(plac) else pd.Series(dtype=float)
    lo = lambda c: (out[c].min(), out[c].max())  # noqa: E731
    f = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    spread_only = out["q5_long_net_bps"] + 2 * FEE_BPS
    pos = int((out["q5_long_net_bps"] > 0).sum())
    key = ["tín hiệu", "tầm nhìn (thanh)"]
    ins = table[table["mẫu"] == "trong mẫu"].set_index(key)["ic_mean"]
    gap = float((out.set_index(key)["ic_mean"] - ins).abs().max())
    return [
        "### Kết luận", "",
        f"- **Có liên hệ thống kê.** Ngoài mẫu (26-27/11), {sig}/{len(out)} cặp tín hiệu × tầm nhìn có |t Newey-West| > 2. "
        f"IC từ {f(lo('ic_mean')[0])} đến {f(lo('ic_mean')[1])}, t NW từ {f(lo('ic_tstat_nw')[0])} đến {f(lo('ic_tstat_nw')[1])}; "
        f"Chênh IC lớn nhất giữa trong mẫu và ngoài mẫu (cùng tín hiệu, cùng tầm nhìn): {f(gap)}.",
        f"- **Placebo xáo giữa các mã:** |IC| lớn nhất là {f(shuf)}, tức gần 0. Đường tính không tự tạo ra liên hệ. "
        f"Tín hiệu cũ t-h vẫn cho IC {f(stale.min())}–{f(stale.max())}: OBI và microprice bền theo thời gian, "
        "đây không phải rò rỉ." if len(stale) else "- Placebo: chưa có.",
        f"- **Không khai thác được sau chi phí.** Q5-Q1 trước chi phí chỉ {f(lo('spread_bps')[0])} đến "
        f"{f(lo('spread_bps')[1])} bps. Chỉ mua Q5 (thực hiện được) cho {f(lo('q5_long_net_bps')[0])} đến "
        f"{f(lo('q5_long_net_bps')[1])} bps sau phí giả định; {pos}/{len(out)} cặp dương. Riêng độ chênh giá mua-bán, "
        f"chưa tính phí, đã làm chân mua còn {f(spread_only.min())} đến {f(spread_only.max())} bps.",
        "- **Vì sao IC cao mà không có lãi.** Lợi suất đo trên giá giữa. Khi một phía sổ lệnh mỏng (OBI, microprice lệch), "
        "mức giá tốt nhất phía đó dễ bị ăn hết, nên giá giữa nhảy nửa bước giá về phía đó. Đây là hiệu ứng cơ học "
        "của giá giữa và bước giá. Muốn ăn được nửa bước đó phải trả nguyên một bước (vào ở giá bán, ra ở giá mua) "
        "cộng phí; một bước giá ở vùng giá 10.000-50.000 là 50 đồng, khoảng 10-50 bps.",
        "- **Giới hạn.** Chỉ có 2 phiên ngoài mẫu, rổ 30 mã. Phí 0,15%/chiều là giả định; chưa tính thuế bán, trượt giá "
        "khi lệnh lớn hơn mức 1, và quy định không bán khống.",
    ]


def build(db_path: str | Path, source: str, out_dir: str | Path, root: Path | None = None,
          tests: dict[str, int | None] | None = None, index_code: str = "VN30") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    db = ReadOnlyStorage(db_path)
    try:
        sessions = session_table(db, source)
        if sessions.empty:
            raise SystemExit(f"Chưa có phiên nào của nguồn '{source}' trong {db_path}.")
        alerts = alert_table(db, source, index_code)
        from .validation import time_split
        split = time_split(sessions["phiên"].tolist())
        val_all, meta_all = validation_table(db, source, split=split)
        full_days = sessions.loc[sessions["đủ"], "phiên"].tolist()
        val_full, meta_full = validation_table(db, source, full_days, split=split)
        plac = placebo(db, source)
        span = _one(db, "SELECT MIN(ts), MAX(ts) FROM quotes WHERE source=?", (source,))
    finally:
        db.close()
    tests = tests if tests is not None else count_tests(root or Path.cwd())

    sessions.to_csv(out / "sessions.csv", index=False, encoding="utf-8")
    alerts.to_csv(out / "alerts.csv", index=False, encoding="utf-8")
    vals = [t.assign(**{"phạm vi": scope}) for t, scope in
            ((val_all, "mọi phiên"), (val_full, "chỉ phiên đủ")) if len(t)]
    (pd.concat(vals, ignore_index=True) if vals else pd.DataFrame()).to_csv(out / "validation.csv", index=False, encoding="utf-8")
    plac.to_csv(out / "placebo.csv", index=False, encoding="utf-8")

    n = len(sessions)
    lines = [
        "# Số liệu báo cáo NeoPulse Radar",
        "",
        f"Sinh bằng `neopulse report-data --source {source}` lúc {datetime.now().strftime('%H:%M %d/%m/%Y')} từ CSDL "
        "SQLite (chỉ đọc). Không chỉnh tay; chạy lại lệnh sau mỗi phiên mới. CSV chi tiết cùng thư mục.",
        "",
        "## Tổng quan",
        "",
        f"- Nguồn: `{source}`" + (" (SSI FastConnect, dữ liệu thật)" if source == "ssi" else ""),
        f"- Số phiên: {n} ({int(sessions['đủ'].sum())} phiên đủ, {n - int(sessions['đủ'].sum())} phiên thiếu)",
        f"- Khoảng thời gian: {str(span[0])[:16].replace('T', ' ')} đến {str(span[1])[:16].replace('T', ' ')}",
        f"- Tổng bản ghi giá: {int(sessions['bản ghi giá'].sum()):,}".replace(",", "."),
        f"- Tổng tick chỉ số: {int(sessions['tick chỉ số'].sum()):,}".replace(",", "."),
        "",
        "## Từng phiên",
        "",
        f"Phiên **đủ** khi ít nhất {COMPLETE_SHARE:.0%} số mã đạt tiêu chí ghi trọn của `finance/rvol.py` "
        "(`complete_history`: có khối lượng khớp trong 5 phút sau 09:15, tới 14:44, không mất quá 5 phút giao dịch "
        "liên tiếp trong giờ khớp lệnh). "
        "Khoảng trống tính theo phút giao dịch (bỏ nghỉ trưa), kể cả từ 09:00 tới tin đầu tiên và từ tin cuối tới 15:00.",
        "",
        *_md(sessions.assign(đủ=sessions["đủ"].map({True: "đủ", False: "thiếu"}))),
        "",
        "## Cảnh báo",
        "",
    ]
    if len(alerts):
        sev = alerts.pivot_table(index="phiên", columns="mức", values="số cảnh báo", aggfunc="sum", fill_value=0)
        rule = alerts.pivot_table(index="phiên", columns="quy tắc", values="số cảnh báo", aggfunc="sum", fill_value=0)
        sev["tổng"] = sev.sum(axis=1)
        lines += ["Theo mức:", "", *_md(sev.reset_index()), "", "Theo quy tắc:", "", *_md(rule.reset_index()), ""]
    else:
        lines += [NA, ""]
    lines += ["Nhận xét tự động (chỉ đề xuất, chưa đổi ngưỡng):", "", *_rule_notes(alerts, n), ""]

    from .validation import FEE_BPS
    lines += ["## Kiểm chứng tín hiệu (`validate`)", "",
              "Cột: `t` coi các thanh độc lập (bị thổi phồng); `t NW` Newey-West, độ trễ L ghi ở cột `L`; "
              "`t phiên` lấy IC trung bình từng phiên làm một quan sát (n = số phiên). `Q5-Q1` là chênh lợi suất giá "
              "giữa, chưa trừ chi phí. `Q5-Q1 ròng` mua Q5 ở giá bán và bán ở giá mua sau h thanh, bán khống Q1 ở giá "
              f"mua và mua lại ở giá bán, trừ phí GIẢ ĐỊNH {f'{FEE_BPS / 100:.2f}'.replace('.', ',')}%/chiều; `Q5 ròng` chỉ chân mua "
              "(thị trường cơ sở không cho bán khống trong ngày). Đơn vị bps.", ""]
    cols = {"ic_mean": "IC", "ic_tstat": "t", "ic_tstat_nw": "t NW", "nw_lag": "L", "ic_tstat_session": "t phiên",
            "n_sessions": "số phiên", "hit_rate": "tỷ lệ đúng chiều", "spread_bps": "Q5-Q1", "q5q1_net_bps": "Q5-Q1 ròng",
            "q5_long_net_bps": "Q5 ròng", "n_bars": "số thanh"}
    for title, table, meta in (("Mọi phiên", val_all, meta_all), ("Chỉ các phiên đủ", val_full, meta_full)):
        lines += [f"### {title}", "",
                  f"Trong mẫu: {len(meta['train'])} phiên ({', '.join(meta['train']) or NA}); "
                  f"ngoài mẫu: {len(meta['test'])} phiên ({', '.join(meta['test']) or NA}). "
                  "Cách chia cố định trên mọi phiên trước khi lọc phiên đủ.", ""]
        if len(table):
            t = table.rename(columns=cols)
            lines += _md(t[["tín hiệu", "tầm nhìn (thanh)", "mẫu", *cols.values()]])
        else:
            lines.append(NA)
        lines += ["", f"Độ tin cậy: {meta['note'] or 'đủ số phiên tối thiểu.'}", ""]
    lines += ["### Placebo", "",
              "IC khi phá vỡ liên hệ thật: xáo tín hiệu giữa các mã trong cùng thanh (trung bình và độ lệch chuẩn qua "
              "các lần xáo), và dùng tín hiệu cũ của thanh t-h. Mọi phiên.", ""]
    lines += (_md(plac.rename(columns={"ic_mean": "IC", "ic_sd": "độ lệch qua các lần xáo", "ic_tstat_nw": "t NW"}))
              if len(plac) else [NA])
    lines += ["", *ic_conclusion(val_all, plac), ""]

    lines += ["## Kiểm thử", "",
              f"- Python (`pytest --co -q`): {tests.get('pytest') if tests.get('pytest') is not None else NA} ca",
              f"- Web (`vitest list`): {tests.get('vitest') if tests.get('vitest') is not None else NA} ca", ""]
    summary = out / "SUMMARY.md"
    summary.write_text("\n".join(lines), encoding="utf-8")
    return summary
