"""Dữ liệu tham chiếu ngoài phiên: phân ngành + số CP niêm yết (SSI securitiesByBoard) và KL trung bình 20 phiên
(SSI REST ngày /api/v3/data/ohlc; dự phòng Vietcap qua thư viện vnstock). Lưu ở <thư mục CSDL>/refdata.json.

Chạy trước phiên: `neopulse refdata --refresh` (khoảng 3 + số mã request, dưới giới hạn 5 request/giây).
Tái sử dụng: cách nạp lười vnstock và chặn SystemExit (vnai tự thoát khi chạm giới hạn) lấy từ
invest-system-phase2/src/invest_system/data/vietcap.py (VietcapProvider._modules/_guard), cùng tác giả, đã rút gọn.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from ..finance.sectors import bundled_reference
from ..timeutil import iso_vn, now_vn

log = logging.getLogger(__name__)
AVG_SESSIONS = 20


def refdata_path(db_path: str | Path) -> Path:
    return Path(db_path).parent / "refdata.json"


def load_refdata(db_path: str | Path | None) -> dict:
    """{'reference': {mã: {...}}, 'avg_volume': {mã: KL}}; thiếu tệp -> ảnh chụp đi kèm cho phân ngành, không có KL TB."""
    data: dict = {}
    if db_path and str(db_path) != ":memory:":
        try:
            data = json.loads(refdata_path(db_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    ref = {**bundled_reference(), **data.get("reference", {})}
    avg = {k: v["avg"] for k, v in data.get("avg_volume", {}).items() if v.get("avg")}
    return {"reference": ref, "avg_volume": avg, "generated_at": data.get("generated_at")}


def _vnstock_daily_volumes(symbol: str, start: date, end: date) -> list[float]:
    try:
        from vnstock import Market  # type: ignore
    except (ImportError, Exception, SystemExit) as e:  # noqa: BLE001 - vnai có thể sys.exit() ngay khi import
        raise RuntimeError(f"không dùng được vnstock: {type(e).__name__}") from e
    try:
        raw = Market().equity(symbol=symbol).ohlcv(start=start.isoformat(), end=end.isoformat(), interval="1D")
    except SystemExit as e:  # vnai gọi sys.exit() khi chạm giới hạn: không để giết tiến trình
        raise RuntimeError("vnstock bị chặn giới hạn") from e
    return [float(v) for v in raw["volume"].tolist()]


def fetch_refdata(client, symbols: list[str], *, today: date | None = None, sessions: int = AVG_SESSIONS,
                  boards: tuple[str, ...] = ("HOSE", "HNX", "UPCOM"), vnstock_fallback=_vnstock_daily_volumes) -> dict:
    """Gọi REST thật (chỉ dữ liệu thị trường). KL TB tính trên `sessions` phiên gần nhất TRƯỚC hôm nay."""
    today = today or now_vn().date()
    want = {s.upper() for s in symbols}
    reference: dict[str, dict] = {}
    for b in boards:
        try:
            for r in client.securities_by_board(b):
                s = str(r.get("symbol") or "").upper()
                if s in want:
                    reference[s] = {"board": r.get("board"), "icb_code": r.get("icbCode"), "icb_name": r.get("icbName"),
                                    "listed_share": float(r.get("listedShare") or 0) or None}
        except Exception as e:  # noqa: BLE001 - thiếu một sàn vẫn dùng ảnh chụp đi kèm
            log.warning("securitiesByBoard %s lỗi: %s", b, type(e).__name__)
    start, end = today - timedelta(days=sessions * 2 + 10), today - timedelta(days=1)
    avg: dict[str, dict] = {}
    for s in sorted(want):
        vols, src = [], "ssi"
        try:
            rows = client.daily_ohlc(s, start.strftime("%Y/%m/%d 00:00:00"), end.strftime("%Y/%m/%d 23:59:59"))
            rows = sorted(rows, key=lambda r: str(r.get("tradingDate")))
            vols = [float(r["volume"]) for r in rows if r.get("volume") not in (None, "")]
        except Exception as e:  # noqa: BLE001
            log.warning("SSI ohlc %s lỗi (%s) - thử Vietcap", s, type(e).__name__)
        if not vols:
            try:
                vols, src = vnstock_fallback(s, start, end), "vietcap"
            except Exception as e:  # noqa: BLE001
                log.warning("Vietcap %s lỗi: %s", s, e)
        vols = [v for v in vols if v > 0][-sessions:]
        if vols:
            avg[s] = {"avg": sum(vols) / len(vols), "n": len(vols), "source": src}
    return {"generated_at": iso_vn(now_vn()), "sessions": sessions, "reference": reference, "avg_volume": avg}


def save_refdata(db_path: str | Path, data: dict) -> Path:
    p = refdata_path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
