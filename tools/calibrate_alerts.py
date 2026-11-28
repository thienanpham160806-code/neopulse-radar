"""Hiệu chỉnh ngưỡng cảnh báo (docs/calibration_log.md). Chỉ đọc CSDL thật; mô phỏng ghi vào CSDL tạm trong --cache.

  python tools/calibrate_alerts.py CACHE prepare          # cache thanh 1 phút từng phiên SSI + 6 phiên mô phỏng seed 7
  python tools/calibrate_alerts.py CACHE old              # cần bản cũ của alerts.py ở neopulse/analytics/_alerts_old.py
  python tools/calibrate_alerts.py CACHE spread '{...}'   # lưới một nhóm tham số, phần còn lại lấy từ base + JSON
  python tools/calibrate_alerts.py CACHE final            # hằng số đang có trong mã

Chỉ CHỌN tham số theo các cột in_* (19, 20, 23, 25/11); out_* (26-27/11) chỉ để báo cáo.
"""

import importlib
import itertools
import json
import sys
from pathlib import Path

import pandas as pd

from neopulse.analytics import alerts as A


def prepare(out: Path) -> None:
    from neopulse.analytics.reportdata import ReadOnlyStorage
    from neopulse.analytics.view import build_view
    from neopulse.data.storage import Storage
    from neopulse.finance.microstructure import make_bars
    from neopulse.neo_api.sim import simulate_sessions
    out.mkdir(parents=True, exist_ok=True)
    db = ReadOnlyStorage("data/neopulse.sqlite")
    for day in db.trading_dates("ssi"):
        build_view(db, "ssi", day, "VN30").bars.to_pickle(out / f"bars_{day}.pkl")  # cùng đường tính với web (có RVOL)
    sim = Storage(out / "sim.sqlite")
    sim.reset("sim")
    simulate_sessions(sim, 6, seed=7, step_seconds=30)
    make_bars(sim.quotes(source="sim"), "1min").to_pickle(out / "sim_bars.pkl")
    sim.table("sim_truth").to_pickle(out / "sim_truth.pkl")


if len(sys.argv) > 2 and sys.argv[2] == "prepare":
    prepare(Path(sys.argv[1]))
    sys.exit()

d = Path(sys.argv[1])
stage = sys.argv[2]
IN = ["2026-11-19", "2026-11-20", "2026-11-23", "2026-11-25"]
OUT = ["2026-11-26", "2026-11-27"]
real = {p.stem[5:]: pd.read_pickle(p) for p in sorted(d.glob("bars_2026-*.pkl"))}
sim = pd.read_pickle(d / "sim_bars.pkl")
truth = pd.read_pickle(d / "sim_truth.pkl")
truth["ts"] = pd.to_datetime(truth["ts"], format="ISO8601").dt.tz_convert("Asia/Ho_Chi_Minh")


def summarize(mod, params):
    for k, v in params.items():
        setattr(mod, k, v)
    rows = {}
    for day, b in real.items():
        a = mod.detect(b, source="ssi")
        n_sym = b["symbol"].nunique()
        rows[day] = {"total": len(a), "CAO": int((a.severity == "CAO").sum()),
                     **{r: int((a.rule == r).sum()) for r in A.RULE_NAMES}, "n_sym": n_sym}
    t = pd.DataFrame(rows).T
    ins, oos = t.loc[IN], t.loc[OUT]
    per = lambda x, c: float((x[c] / x["n_sym"]).mean())  # noqa: E731
    sa = mod.detect(sim, source="sim")
    ev = mod.evaluate_against_truth(sa, truth)
    return {"params": params,
            "in_CAO_per_sym": round(per(ins, "CAO"), 3), "in_total_per_sym": round(per(ins, "total"), 3),
            "in_spread_per_sym": round(per(ins, "spread_blowout"), 3), "in_foreign_per_sym": round(per(ins, "foreign_flow"), 3), "in_volume_per_sym": round(per(ins, "volume_spike"), 3), "in_book_per_sym": round(per(ins, "book_pressure"), 3),
            "out_CAO_per_sym": round(per(oos, "CAO"), 3), "out_total_per_sym": round(per(oos, "total"), 3),
            "sim_recall": {k: round(v["recall"], 3) for k, v in ev["by_kind"].items()},
            "sim_precision": round(ev["precision"], 3), "table": t.drop(columns="n_sym").astype(int).to_dict("index")}


if stage == "old":
    old = importlib.import_module("neopulse.analytics._alerts_old")
    print(json.dumps(summarize(old, {}), ensure_ascii=False))
    sys.exit()
base = {"SPREAD_MIN_TICKS": 3.0, "SPREAD_Q": 0.99, "FOREIGN_MIN_SHARE": 0.30, "FOREIGN_Q": 0.95, "FOREIGN_MIN_VALUE": 0.0, "FOREIGN_WINDOW": 5, "CAO_VALUE": 6.0}
grids = {
    "spread": [{"SPREAD_MIN_TICKS": k, "SPREAD_Q": q} for k, q in itertools.product([2.0, 3.0, 4.0, 5.0], [0.95, 0.99])],
    "foreign": [{"FOREIGN_MIN_SHARE": s, "FOREIGN_Q": q, "FOREIGN_MIN_VALUE": v}
                for s, q, v in itertools.product([0.3, 0.5], [0.95, 0.99], [0.0, 1e9, 2e9, 5e9])],
    "foreign_w": [{"FOREIGN_WINDOW": w, "FOREIGN_MIN_SHARE": 0.3, "FOREIGN_Q": q, "FOREIGN_MIN_VALUE": v}
                  for w, q, v in itertools.product([1, 3], [0.95, 0.99], [0.0, 1e9, 2e9])],
    "volbook": [{"RVOL_SPIKE": r, "OBI_EXTREME": o, "OBI_PERSIST": n}
                for r, o, n in itertools.product([3.0, 4.0, 5.0], [0.6, 0.7, 0.8], [3, 5])],
    "cao": [{"CAO_VALUE": c} for c in (6.0, 8.0, 10.0, 12.0)],
}
extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
for g in grids[stage] if stage in grids else [{}]:
    r = summarize(A, {} if stage == "final" else {**base, **extra, **g})
    if stage != "final":
        r.pop("table")
    print(json.dumps(r, ensure_ascii=False), flush=True)
