"""Chuỗi giá và SMA/EMA tính tại Python; web chỉ chọn khung và vẽ."""
from __future__ import annotations

import json
import math
from pathlib import Path

PERIODS = (5, 10, 20, 50, 100, 200)


def build_chart(symbol: str, rows: list, *, source: str, unit: str = "điểm", scale: float = 1) -> dict:
    valid = {}
    for t, v in rows:
        if isinstance(t, str) and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
            valid[t] = float(v) * scale
    points = [{"time": t, "value": v} for t, v in sorted(valid.items())]
    values = [p["value"] for p in points]
    studies = {}
    for n in PERIODS:
        sma, ema, running, last = [], [], 0.0, None
        alpha = 2 / (n + 1)
        for i, v in enumerate(values):
            running += v
            if i >= n:
                running -= values[i - n]
            if i < n - 1:
                continue
            avg = running / n
            last = avg if last is None else alpha * v + (1 - alpha) * last
            sma.append({"time": points[i]["time"], "value": round(avg, 6)})
            ema.append({"time": points[i]["time"], "value": round(last, 6)})
        studies[f"MA{n}"] = sma
        studies[f"EMA{n}"] = ema
    return {"symbol": symbol, "source": source, "unit": unit, "data": points, "studies": studies,
            "from": points[0]["time"] if points else None, "to": points[-1]["time"] if points else None}


def export_cached(raw_dir: str | Path, out_dir: str | Path) -> int:
    raw_dir, out = Path(raw_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reports = {}
    for f in raw_dir.glob("*.json"):
        if f.stem.startswith("_"):
            if f.stem not in {"_VN30", "_VNINDEX"}:
                continue
            symbol, rows, scale, unit = f.stem[1:], json.loads(f.read_text(encoding="utf-8")), 1, "điểm"
        else:
            raw = json.loads(f.read_text(encoding="utf-8"))
            symbol, rows, scale, unit = raw["symbol"], raw.get("prices", []), 1000, "đồng/CP"
        reports[symbol] = build_chart(symbol, rows, source="Vietcap qua vnstock · giá đóng cửa ngày", unit=unit, scale=scale)
    for symbol, report in reports.items():
        if not symbol.isalnum():
            raise ValueError("Mã biểu đồ không hợp lệ")
        target = out / f"{symbol}.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temp.replace(target)
    return len(reports)
