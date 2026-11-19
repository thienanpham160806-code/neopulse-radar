"""Xuất "ảnh nhìn" của một phiên ra JSON cho giao diện web (Vercel).

Nguyên tắc:
  * MỌI con số do Python tính (`build_view`); web chỉ hiển thị. Không có công thức nào nằm ở JavaScript.
  * Chỉ xuất chỉ báo đã tổng hợp (điểm nhịp, độ rộng, xếp hạng, cảnh báo, tóm tắt sổ lệnh theo mã, ngoại,
    basis). KHÔNG xuất sổ lệnh/giá thô từng tick.
  * Chỉ ĐỌC SQLite (kết nối `mode=ro`), nên chạy song song với bộ ghi an toàn.
  * Không chứa bí mật: không đưa `Settings` vào bất kỳ chỗ nào của đầu ra.
  * NaN/inf -> null để JSON hợp lệ cho trình duyệt.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..data.storage import Storage
from ..finance import microstructure as micro
from ..finance.pulse import COMPONENT_NAMES, WEIGHTS
from ..timeutil import iso_vn, now_vn, to_vn
from . import alerts as alerting
from . import validation
from .explain import template_summary
from .view import SessionView, build_view

SCHEMA_VERSION = 1
SOURCE_LABEL = {"neo": "NEO API (dữ liệu thật)", "ssi": "SSI FastConnect (dữ liệu thật)", "sim": "MÔ PHỎNG"}
DISCLAIMER = "Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."
MAX_ALERTS, MAX_RANK, MAX_BOOK, MAX_FOREIGN_EACH, MAX_SERIES_SYMBOLS = 500, 200, 300, 60, 20
SEVERITIES = ("CAO", "TRUNG BÌNH", "THẤP")


class ReadOnlyStorage(Storage):
    """Mở SQLite ở chế độ chỉ đọc: không PRAGMA ghi, không tạo bảng; thử ghi sẽ báo lỗi."""

    def __init__(self, path: str | Path):
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Không thấy cơ sở dữ liệu: {p}")
        self.path = str(p)
        self._con = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True, timeout=30,
                                    check_same_thread=False)
        self._con.execute("PRAGMA query_only=1")


# --------------------------------------------------------------------------- làm sạch
def clean(obj: Any) -> Any:
    """Đệ quy: numpy/pandas -> kiểu Python; NaN/inf -> None; Timestamp -> ISO có +07:00."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return clean(obj.to_dict("records"))
    if isinstance(obj, pd.Series):
        return clean(obj.to_dict())
    if isinstance(obj, (pd.Timestamp, datetime)):
        return None if pd.isna(obj) else iso_vn(to_vn(obj.to_pydatetime() if isinstance(obj, pd.Timestamp) else obj))
    if isinstance(obj, (date, time)):
        return obj.isoformat()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if math.isnan(f) or math.isinf(f) else f
    if obj is pd.NaT:
        return None
    return obj if isinstance(obj, str) else str(obj)


def dumps(payload: dict) -> str:
    """JSON gọn, hợp lệ nghiêm ngặt (allow_nan=False bảo đảm không lọt NaN)."""
    return json.dumps(clean(payload), ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _r(x: Any, nd: int = 4) -> float | None:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, nd)


def _t(ts: pd.Timestamp) -> str:
    return ts.isoformat(timespec="seconds")


# --------------------------------------------------------------------------- trạng thái
def session_phase(dt: datetime) -> str:
    """pre | open | lunch | closed - theo khung giờ HOSE (T2-T6); 15:00-15:05 vẫn coi là mở để bộ ghi nhận nốt."""
    d = to_vn(dt)
    if d.weekday() >= 5:
        return "closed"
    t = d.time()
    if t < time(9, 0):
        return "pre"
    if t < time(11, 30):
        return "open"
    if t < time(13, 0):
        return "lunch"
    if t <= time(15, 5):
        return "open"
    return "closed"


def data_status(v: SessionView, now: datetime) -> dict:
    """state: fresh | stale | error | closed. `closed` = ngoài giờ / phiên lịch sử (KHÔNG phải lỗi)."""
    phase = session_phase(now)
    is_today = v.trading_date == to_vn(now).date().isoformat()
    base = {"phase": phase, "age_seconds": _r(v.age_seconds, 1), "stale_after_seconds": 120}
    if v.status == "no_data":
        return {**base, "state": "error", "reason": v.status_message}
    if v.is_simulated:
        return {**base, "state": "fresh", "reason": "Dữ liệu MÔ PHỎNG - không phải dữ liệu thị trường."}
    if not is_today:
        return {**base, "state": "closed", "reason": f"Dữ liệu lịch sử của phiên {v.trading_date} (đã đóng)."}
    if phase != "open":
        why = {"pre": "Phiên chưa mở cửa.", "lunch": "Nghỉ trưa (11:30-13:00).",
               "closed": "Phiên đã kết thúc."}[phase]
        return {**base, "state": "closed", "reason": why}
    if v.status == "stale":
        return {**base, "state": "stale", "reason": v.status_message}
    return {**base, "state": "fresh", "reason": v.status_message}


# --------------------------------------------------------------------------- các khối
def _meta(v: SessionView, db: Storage, now: datetime, order_value: float) -> dict:
    n = int(len(v.latest))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": v.source, "source_label": SOURCE_LABEL.get(v.source, v.source),
        "is_simulated": v.is_simulated,
        "generated_at": iso_vn(now), "trading_date": v.trading_date, "index_code": v.index_code,
        "last_update": _t(v.last_update) if v.last_update is not None else None,
        "data_status": data_status(v, now),
        "n_symbols_computed": n, "n_symbols_excluded": 0, "excluded_reason": None,
        "n_sessions": len(db.trading_dates(v.source)),
        "n_history_sessions": v.n_history_sessions,
        "available_dates": db.trading_dates(v.source),
        "order_value_vnd": order_value,
        "disclaimer": DISCLAIMER,
    }


def _pulse(v: SessionView) -> dict:
    p = v.pulse
    comps = [{"key": k, "name": COMPONENT_NAMES[k], "weight": WEIGHTS[k],
              "value": _r(p.components.get(k)) if p else None} for k in WEIGHTS]
    sens = v.sensitivity or {}
    series = []
    if len(v.pulse_series):
        ps = v.pulse_series
        series = [{"t": _t(r.bar), "index": _r(r.index_value, 2), "score": _r(r.score, 1)} for r in ps.itertuples()]
    return {
        "score": _r(p.score, 1) if p else None, "label": p.label if p else "Không đủ dữ liệu",
        "components": comps, "missing": list(p.missing) if p else list(WEIGHTS),
        "sensitivity": {k: _r(sens.get(k)) for k in ("base", "p05", "p95", "label_stability")} if sens else None,
        "sigma_pct": _r(v.sigma_pct), "series": series,
        "summary": template_summary(v), "divergence": v.divergence,
    }


def _index_block(v: SessionView) -> dict:
    r = v.index_row or {}
    keys = ("value", "change", "pct_change", "advances", "declines", "no_change", "n_ceiling", "n_floor",
            "total_value", "total_volume", "ad_ratio", "pct_advancing")
    series = []
    if len(v.index):
        ix = v.index.assign(bar=v.index["ts"].dt.floor("1min")).groupby("bar").last().reset_index()
        series = [{"t": _t(x.bar), "value": _r(x.value, 2), "pct_change": _r(x.pct_change, 3)} for x in ix.itertuples()]
    return {"code": v.index_code, "row": {k: _r(r.get(k)) for k in keys} if r else None, "series": series}


def _breadth(v: SessionView) -> dict:
    r = v.index_row or {}
    return {"exchange": {k: _r(r.get(k)) for k in ("advances", "declines", "no_change", "n_ceiling", "n_floor",
                                                   "ad_ratio", "pct_advancing")} if r else None,
            "universe": {k: _r(x) for k, x in v.breadth_universe.items()}}


def _ranking(v: SessionView) -> list[dict]:
    if v.ranking.empty:
        return []
    out = []
    for sym, r in v.ranking.head(MAX_RANK).iterrows():
        out.append({"symbol": sym, "rank": int(r["rank"]), "score": _r(r["score"], 3), "last": _r(r["last"], 2),
                    "pct_change": _r(r["pct_change"], 2), "obi3": _r(r["obi3"], 3), "net_ratio": _r(r["net_ratio"], 3),
                    "spread_bps": _r(r["spread_bps"], 1), "total_value": _r(r["total_value"], 0),
                    "z": {c[2:]: _r(r[c], 2) for c in v.ranking.columns if c.startswith("z_")},
                    "n_factors": int(r["n_factors"])})
    return out


def _alerts(v: SessionView) -> dict:
    if v.alerts.empty:
        return {"total": 0, "by_severity": {s: 0 for s in SEVERITIES}, "rule_names": alerting.RULE_NAMES, "items": []}
    a = v.alerts.copy()
    order = {s: i for i, s in enumerate(SEVERITIES)}
    a = a.assign(_o=a["severity"].map(order)).sort_values(["_o", "ts"], ascending=[True, False]).head(MAX_ALERTS)
    items = [{"t": _t(r.ts), "symbol": r.symbol, "rule": r.rule, "rule_name": alerting.RULE_NAMES.get(r.rule, r.rule),
              "severity": r.severity, "value": _r(r.value, 3), "threshold": _r(r.threshold, 3), "message": r.message}
             for r in a.itertuples()]
    counts = v.alerts["severity"].value_counts().to_dict()
    return {"total": int(len(v.alerts)), "by_severity": {s: int(counts.get(s, 0)) for s in SEVERITIES},
            "rule_names": alerting.RULE_NAMES, "items": items}


def _book(v: SessionView) -> dict:
    if v.liquidity.empty:
        return {"rows": [], "series": {}}
    lat = micro.add_book_metrics(v.latest).set_index("symbol")
    liq = v.liquidity.sort_values("total_value", ascending=False).head(MAX_BOOK)
    rows = []
    for sym, r in liq.iterrows():
        rows.append({"symbol": sym, "last": _r(r["last"], 2), "pct_change": _r(lat["pct_change"].get(sym), 2),
                     "obi3": _r(r["obi3"], 3), "pressure": _r(r["pressure"], 2), "spread_bps": _r(r["spread_bps"], 1),
                     "depth_value": _r(r["depth_value"], 0), "total_value": _r(r["total_value"], 0),
                     "slippage_bps": _r(r["slippage_bps"], 1), "fill_ratio": _r(r["fill_ratio"], 3),
                     "amihud": _r(r["amihud"], 3), "liq_score": _r(r["liq_score"], 1),
                     "micro_dev_bps": _r(lat["micro_dev_bps"].get(sym), 1),
                     "auction": isinstance(lat["auction_flag"].get(sym), str)})
    series: dict[str, list] = {}
    top = [r["symbol"] for r in rows[:MAX_SERIES_SYMBOLS]]
    if len(v.bars) and top:
        b = v.bars[v.bars["symbol"].isin(top)]
        for sym, g in b.groupby("symbol"):
            # dạng cột, trục thời gian "HH:MM" (giờ VN của meta.trading_date) cho gọn
            series[sym] = {"t": [x.bar.strftime("%H:%M") for x in g.itertuples()],
                           "mid": [_r(x, 2) for x in g["mid"]], "obi3": [_r(x, 3) for x in g["obi3"]]}
    return {"rows": rows, "series": series}


def _foreign(v: SessionView) -> dict:
    s = v.foreign_summary or {}
    if v.foreign.empty:
        return {"summary": None, "rows": []}
    f = v.foreign
    sel = pd.concat([f.head(MAX_FOREIGN_EACH), f.tail(MAX_FOREIGN_EACH)]).loc[lambda d: ~d.index.duplicated()]
    rows = [{"symbol": sym, "buy": _r(r["f_buy_val"], 0), "sell": _r(r["f_sell_val"], 0), "net": _r(r["net_val"], 0),
             "net_ratio": _r(r["net_ratio"], 3), "participation": _r(r["participation"], 3),
             "room_used": _r(r["room_used"], 3), "total_value": _r(r["total_value"], 0)} for sym, r in sel.iterrows()]
    return {"summary": {k: _r(x, 3) for k, x in s.items()}, "rows": rows}


def _futures(v: SessionView) -> dict:
    if v.basis.empty:
        return {"available": False, "state": None, "series": []}
    st = v.basis_state
    b = v.basis.assign(bar=v.basis["ts"].dt.floor("1min")).groupby("bar").last().reset_index()
    return {"available": True,
            "state": {k: (st.get(k) if k in ("symbol", "label") else _r(st.get(k))) for k in
                      ("symbol", "label", "basis", "basis_pct", "z", "dtm", "carry_ann", "mispricing")},
            "future": _r(v.basis["future"].iloc[-1], 2), "spot": _r(v.basis["spot"].iloc[-1], 2),
            "series": [{"t": _t(x.bar), "basis": _r(x.basis, 2), "future": _r(x.future, 2), "spot": _r(x.spot, 2)}
                       for x in b.itertuples()]}


def build_validation_block(db: Storage, source: str, freq: str = "1min") -> dict:
    """Khối kiểm chứng + chất lượng dữ liệu (nặng - gọi thưa, không gọi mỗi 20 giây)."""
    bars = micro.make_bars(db.quotes(source=source), freq)
    res = validation.validate_signals(bars) if len(bars) else {"train": [], "test": [], "table": pd.DataFrame(),
                                                                "note": "Chưa có dữ liệu."}
    per = validation.per_session_ic(bars) if len(bars) else pd.DataFrame()
    dq = validation.data_quality_report(db, source)
    runs = dq["runs"].tail(8)
    return {
        "ic": {"train": res["train"], "test": res["test"], "note": res["note"], "table": res["table"]},
        "ic_by_session": per,
        "simulated_signals_are_planted": source == "sim",
        "data_quality": {
            "n_quotes": dq["n_quotes"], "n_sessions": dq["n_sessions"], "n_symbols": dq["n_symbols"],
            "n_gaps": int(len(dq["gaps"])),
            "issues": dq["issues"].to_dict() if len(dq["issues"]) else {},
            "runs": [{k: r.get(k) for k in ("started", "ended", "source", "n_quotes", "n_index", "n_rejected",
                                            "n_duplicates", "n_reconnects")} for r in runs.to_dict("records")],
        },
    }


# --------------------------------------------------------------------------- lắp ráp
def snapshot_meta(trading_date: str | None, now: datetime) -> dict:
    """Nhãn snapshot tĩnh: 'cuối phiên' khi phiên đã đóng (hoặc là phiên của ngày trước), ngược lại 'giữa phiên'.
    Snapshot KHÔNG phải thời gian thực: số liệu dừng ở thời điểm `snapshot_at`."""
    today = to_vn(now).date().isoformat()
    eod = (trading_date is not None and trading_date < today) or session_phase(now) == "closed"
    label = "Snapshot cuối phiên" if eod else f"Snapshot giữa phiên (dừng lúc {to_vn(now).strftime('%H:%M')})"
    return {"snapshot_at": iso_vn(now), "snapshot_kind": "end_of_session" if eod else "intraday",
            "snapshot_label": label, "snapshot_realtime": False}


def build_payload(db: Storage, source: str, trading_date: str | None = None, index_code: str = "VN30", *,
                  order_value: float = 500e6, extras: dict | None = None, now: datetime | None = None,
                  snapshot: bool = False) -> dict:
    """Dựng toàn bộ JSON của một (nguồn, phiên, chỉ số). Không bao giờ ném lỗi tính toán: lỗi -> data_status=error."""
    now = now or now_vn()
    try:
        v = build_view(db, source, trading_date, index_code, order_value=order_value)
    except Exception as e:  # noqa: BLE001 - một phiên lỗi không được làm sập vòng publish
        return error_payload(source, f"Lỗi khi tính chỉ báo: {type(e).__name__}", trading_date, index_code, now)
    meta = _meta(v, db, now, order_value)
    if snapshot:
        meta.update(snapshot_meta(v.trading_date, now))
    if v.status == "no_data":
        return {"meta": meta}
    payload = {
        "meta": meta, "pulse": _pulse(v), "index": _index_block(v), "breadth": _breadth(v), "ranking": _ranking(v),
        "alerts": _alerts(v), "book": _book(v), "foreign": _foreign(v), "futures": _futures(v),
    }
    if extras:
        payload.update(extras)
    return payload


def error_payload(source: str, reason: str, trading_date: str | None = None, index_code: str = "VN30",
                  now: datetime | None = None) -> dict:
    now = now or now_vn()
    return {"meta": {
        "schema_version": SCHEMA_VERSION, "source": source, "source_label": SOURCE_LABEL.get(source, source),
        "is_simulated": source == "sim", "generated_at": iso_vn(now), "trading_date": trading_date,
        "index_code": index_code, "last_update": None,
        "data_status": {"state": "error", "reason": reason, "phase": session_phase(now), "age_seconds": None,
                        "stale_after_seconds": 120},
        "n_symbols_computed": 0, "n_symbols_excluded": 0, "excluded_reason": None, "n_sessions": 0,
        "n_history_sessions": 0, "available_dates": [], "order_value_vnd": None, "disclaimer": DISCLAIMER}}


def session_filename(source: str, trading_date: str, index_code: str) -> str:
    return f"sessions/{source}_{trading_date}_{index_code}.json"


def latest_filenames(index_code: str, primary: str) -> list[str]:
    """Luôn có latest_<MÃ>.json cho mọi chỉ số (web đọc theo mã); latest.json là bí danh của chỉ số chính."""
    return [f"latest_{index_code}.json"] + (["latest.json"] if index_code == primary else [])


def update_index(out_dir: Path, entries: list[dict]) -> dict:
    """Gộp các phiên đã xuất vào index.json (khóa: nguồn, phiên, chỉ số)."""
    path = out_dir / "index.json"
    cur: dict = {"schema_version": SCHEMA_VERSION, "sessions": []}
    if path.exists():
        try:
            cur = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    by_key = {(s["source"], s["trading_date"], s["index_code"]): s for s in cur.get("sessions", [])}
    for e in entries:
        by_key[(e["source"], e["trading_date"], e["index_code"])] = e
    cur["sessions"] = sorted(by_key.values(), key=lambda s: (s["trading_date"], s["source"], s["index_code"]), reverse=True)
    cur["generated_at"] = iso_vn(now_vn())
    path.write_text(dumps(cur), encoding="utf-8")
    return cur


def index_entry(payload: dict, path: str) -> dict | None:
    m = payload["meta"]
    if not m.get("trading_date"):
        return None
    return {"snapshot_kind": m.get("snapshot_kind"), "source": m["source"], "is_simulated": m["is_simulated"], "trading_date": m["trading_date"],
            "index_code": m["index_code"], "path": path, "generated_at": m["generated_at"],
            "pulse_score": (payload.get("pulse") or {}).get("score"), "n_symbols": m["n_symbols_computed"]}


def export_to_dir(db: Storage, source: str, out_dir: str | Path, *, trading_date: str | None = None,
                  index_codes: list[str] | None = None, all_dates: bool = False, with_validation: bool = True,
                  order_value: float = 500e6, snapshot: bool = False) -> list[dict]:
    """Ghi latest*.json, sessions/*.json và index.json. Trả danh sách mục index đã ghi.

    `snapshot=True` gắn meta.snapshot_at/snapshot_kind/snapshot_label (chế độ web tĩnh, không phải thời gian thực)."""
    out = Path(out_dir)
    (out / "sessions").mkdir(parents=True, exist_ok=True)
    dates = db.trading_dates(source)
    if not dates:
        payload = error_payload(source, f"Chưa có dữ liệu cho nguồn '{source}'.", trading_date)
        (out / "latest.json").write_text(dumps(payload), encoding="utf-8")
        return []
    targets = dates if all_dates else [trading_date if trading_date in dates else dates[-1]]
    codes = [c.upper() for c in (index_codes or ["VN30"])]
    extras = {"validation": build_validation_block(db, source)} if with_validation else None
    entries: list[dict] = []
    for day in targets:
        for code in codes:
            payload = build_payload(db, source, day, code, order_value=order_value, extras=extras, snapshot=snapshot)
            rel = session_filename(source, day, code)
            (out / rel).write_text(dumps(payload), encoding="utf-8")
            if day == targets[-1]:
                for name in latest_filenames(code, codes[0]):
                    (out / name).write_text(dumps(payload), encoding="utf-8")
            if (e := index_entry(payload, rel)):
                entries.append(e)
    update_index(out, entries)
    return entries
