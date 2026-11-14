"""Giao diện dòng lệnh: `neopulse <lệnh>`.

  check      kiểm tra cấu hình và kết nối NEO API (không in bí mật)
  simulate   sinh dữ liệu MÔ PHỎNG nhiều phiên để chạy thử toàn bộ sản phẩm
  record     ghi luồng WebSocket thật + REST đối chiếu (cần NEOPULSE_MODE=live)
  poll       phương án dự phòng chỉ dùng REST
  alerts     chạy bộ cảnh báo trên dữ liệu đã lưu, lưu vào CSDL, tùy chọn gửi Telegram
  briefing   xuất bản tin HTML của một phiên
  validate   báo cáo kiểm chứng tín hiệu + chất lượng dữ liệu
  export     xuất dữ liệu một phiên ra CSV/Parquet
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import time

from .config import Settings, load_settings
from .logging_setup import setup_logging

log = logging.getLogger("neopulse")


def _source(args, settings: Settings, db) -> str:
    if getattr(args, "source", None):
        return args.source
    srcs = db.sources()
    if settings.is_live and "neo" in srcs:
        return "neo"
    return "neo" if ("neo" in srcs and "sim" not in srcs) else "sim"


def cmd_check(args, s: Settings) -> int:
    from .neo_api.client import NeoClient
    from .neo_api.errors import NeoApiError
    print("Cấu hình (bí mật đã che):")
    print(json.dumps(s.redacted(), ensure_ascii=False, indent=2))
    if not s.is_live:
        print("\nNEOPULSE_MODE=sim -> không gọi NEO API. Đặt NEOPULSE_MODE=live và điền .env để kiểm tra kết nối.")
        return 0
    if not s.has_neo_credentials:
        print("\nLỖI: thiếu NEO_USERNAME/NEO_PASSWORD (hoặc NEO_ACCESS_TOKEN) trong .env.")
        return 2
    try:
        with NeoClient(s) as c:
            status = c.market_status("ALL")
            print("\nKết nối REST: OK. Trạng thái phiên:", {m.get("marketCode"): m.get("marketStatus") for m in status})
            members = c.stock_detail_by_index(s.universe_index)
            print(f"Rổ {s.universe_index}: {len(members)} mã. Tổng số request đã gửi: {c.request_count}")
        return 0
    except NeoApiError as e:
        print(f"\nLỖI NEO API: {e}")
        return 1


def cmd_simulate(args, s: Settings) -> int:
    from .data.storage import Storage
    from .neo_api.sim import simulate_sessions
    db = Storage(s.db_path)
    if args.reset:
        db.reset("sim")
    res = simulate_sessions(db, args.sessions, seed=args.seed, step_seconds=args.step)
    print(f"Đã sinh dữ liệu MÔ PHỎNG vào {s.db_path}: {json.dumps(res, ensure_ascii=False)}")
    return 0


def _parse_until(v: str | None) -> time | None:
    return time.fromisoformat(v) if v else None


def cmd_record(args, s: Settings) -> int:
    from .data.recorder import record
    if not s.is_live:
        print("Bộ ghi cần NEOPULSE_MODE=live. (Dùng `neopulse simulate` nếu chỉ muốn chạy thử.)")
        return 2
    if not s.has_neo_credentials:
        print("Thiếu thông tin đăng nhập NEO API trong .env.")
        return 2
    res = asyncio.run(record(s, until=_parse_until(args.until), rest_every_s=args.rest_every))
    print("Kết thúc ghi:", json.dumps(res, ensure_ascii=False))
    return 0


def cmd_poll(args, s: Settings) -> int:
    from .data.recorder import poll
    if not (s.is_live and s.has_neo_credentials):
        print("Polling cần NEOPULSE_MODE=live và thông tin đăng nhập trong .env.")
        return 2
    print("Kết thúc polling:", json.dumps(poll(s, interval_s=args.interval, until=_parse_until(args.until)), ensure_ascii=False))
    return 0


def cmd_alerts(args, s: Settings) -> int:
    from .analytics.notify import push_new_alerts
    from .analytics.view import build_view
    from .data.storage import Storage
    db = Storage(s.db_path)
    v = build_view(db, _source(args, s, db), args.date, args.index)
    if v.status == "no_data":
        print(v.status_message)
        return 1
    if args.notify:
        sent = push_new_alerts(s, db, v.alerts)
    else:
        from .analytics.alerts import to_rows
        db.insert_alerts(to_rows(v.alerts))
        sent = 0
    print(f"Phiên {v.trading_date}: {len(v.alerts)} cảnh báo "
          f"({(v.alerts['severity'] == 'CAO').sum() if len(v.alerts) else 0} mức CAO); đã gửi Telegram: {sent}")
    if len(v.alerts):
        print(v.alerts.head(args.top)[["ts", "symbol", "severity", "message"]].to_string(index=False))
    return 0


def cmd_briefing(args, s: Settings) -> int:
    from .analytics.briefing import render_briefing
    from .analytics.view import build_view
    from .data.storage import Storage
    db = Storage(s.db_path)
    v = build_view(db, _source(args, s, db), args.date, args.index)
    if v.status == "no_data":
        print(v.status_message)
        return 1
    out = args.out or f"out/briefing_{v.source}_{v.trading_date}.html"
    render_briefing(v, out)
    print(f"Đã xuất bản tin: {out}")
    return 0


def cmd_validate(args, s: Settings) -> int:
    import pandas as pd

    from .analytics import alerts as alerting
    from .analytics import validation
    from .data.storage import Storage
    from .finance.microstructure import make_bars
    db = Storage(s.db_path)
    src = _source(args, s, db)
    quotes = db.quotes(source=src)
    if quotes.empty:
        print(f"Chưa có dữ liệu nguồn '{src}'.")
        return 1
    pd.set_option("display.width", 200)
    bars = make_bars(quotes, args.freq)
    print(f"== KIỂM CHỨNG · nguồn={src}{' (MÔ PHỎNG)' if src == 'sim' else ''} · thanh={args.freq} ==")
    dq = validation.data_quality_report(db, src)
    print(f"\n[1] Dữ liệu: {dq['n_quotes']:,} ảnh chụp · {dq['n_symbols']} mã · {dq['n_sessions']} phiên · "
          f"{len(dq['gaps'])} khoảng trống bất thường")
    print("Vấn đề chất lượng theo loại:", dq["issues"].to_dict() if len(dq["issues"]) else "không có")
    res = validation.validate_signals(bars)
    print(f"\n[2] Tín hiệu sổ lệnh -> lợi suất kế tiếp (bps). Trong mẫu: {res['train']} · Ngoài mẫu: {res['test']}")
    print(res["table"].round(4).to_string(index=False))
    if res["note"]:
        print("LƯU Ý:", res["note"])
    print("\n[3] IC theo từng phiên (obi3, 1 thanh):")
    print(validation.per_session_ic(bars).round(4).to_string(index=False))
    al = alerting.detect(bars, source=src)
    print(f"\n[4] Cảnh báo: {len(al)} trên {dq['n_sessions']} phiên; theo quy tắc: {al['rule'].value_counts().to_dict() if len(al) else {}}")
    if src == "sim":
        ev = alerting.evaluate_against_truth(al, db.table("sim_truth"))
        print("Đối chiếu với sự kiện cài sẵn (chỉ có ở dữ liệu mô phỏng):", json.dumps(ev, ensure_ascii=False, default=float))
        print("\nNHẮC LẠI: dữ liệu mô phỏng có tín hiệu được cài sẵn - các con số trên chỉ xác nhận mã nguồn tính đúng.")
    if args.out:
        res["table"].to_csv(args.out, index=False)
        print(f"Đã lưu bảng IC: {args.out}")
    return 0


def cmd_export(args, s: Settings) -> int:
    from pathlib import Path

    from .data.storage import Storage
    db = Storage(s.db_path)
    src = _source(args, s, db)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in (("quotes", db.quotes(args.date, None, None, src)), ("index_ticks", db.index_ticks(args.date, None, src))):
        p = out / f"{name}_{src}_{args.date or 'all'}.{args.format}"
        df.to_parquet(p, index=False) if args.format == "parquet" else df.to_csv(p, index=False)
        print(f"{p}: {len(df):,} dòng")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neopulse", description="NeoPulse Radar - radar nhịp thị trường trên NEO API")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--env-file", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--source", choices=["neo", "sim"], help="nguồn dữ liệu (mặc định: tự chọn)")
        sp.add_argument("--date", help="phiên YYYY-MM-DD (mặc định: phiên mới nhất)")
        sp.add_argument("--index", default="VN30")

    sub.add_parser("check").set_defaults(fn=cmd_check)
    sp = sub.add_parser("simulate")
    sp.add_argument("--sessions", type=int, default=6)
    sp.add_argument("--seed", type=int, default=7)
    sp.add_argument("--step", type=int, default=30, help="bước thời gian (giây)")
    sp.add_argument("--reset", action="store_true", help="xóa dữ liệu mô phỏng cũ trước khi sinh")
    sp.set_defaults(fn=cmd_simulate)
    sp = sub.add_parser("record")
    sp.add_argument("--until", default="15:05", help="giờ dừng HH:MM (giờ VN)")
    sp.add_argument("--rest-every", type=float, default=60.0)
    sp.set_defaults(fn=cmd_record)
    sp = sub.add_parser("poll")
    sp.add_argument("--interval", type=float, default=15.0)
    sp.add_argument("--until", default="15:05")
    sp.set_defaults(fn=cmd_poll)
    sp = sub.add_parser("alerts")
    common(sp)
    sp.add_argument("--notify", action="store_true", help="gửi cảnh báo mức CAO qua Telegram")
    sp.add_argument("--top", type=int, default=15)
    sp.set_defaults(fn=cmd_alerts)
    sp = sub.add_parser("briefing")
    common(sp)
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_briefing)
    sp = sub.add_parser("validate")
    sp.add_argument("--source", choices=["neo", "sim"])
    sp.add_argument("--freq", default="1min")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_validate)
    sp = sub.add_parser("export")
    common(sp)
    sp.add_argument("--format", choices=["csv", "parquet"], default="csv")
    sp.add_argument("--out-dir", default="out")
    sp.set_defaults(fn=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    try:
        settings = load_settings(args.env_file)
    except ValueError as e:
        print(f"Cấu hình không hợp lệ: {e}")
        return 2
    return args.fn(args, settings)


if __name__ == "__main__":
    sys.exit(main())
