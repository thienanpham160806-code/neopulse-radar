"""Giao diện dòng lệnh: `neopulse <lệnh>`.

  check      kiểm tra cấu hình và kết nối NEO API (không in bí mật)
  simulate   sinh dữ liệu MÔ PHỎNG nhiều phiên để chạy thử toàn bộ sản phẩm
  record     ghi luồng WebSocket thật + REST đối chiếu (cần NEOPULSE_MODE=live)
  poll       phương án dự phòng chỉ dùng REST
  alerts     chạy bộ cảnh báo trên dữ liệu đã lưu, lưu vào CSDL, tùy chọn gửi Telegram
  briefing   xuất bản tin HTML của một phiên
  validate   báo cáo kiểm chứng tín hiệu + chất lượng dữ liệu
  export     xuất dữ liệu một phiên ra CSV/Parquet
  export-web xuất JSON chỉ báo tổng hợp cho giao diện web (chỉ đọc SQLite)
  publish-static  xuất snapshot tĩnh vào web/public/data/ (+ --deploy lên Vercel) - cách khuyên dùng
  publish    TÙY CHỌN, tốn hạn mức: đẩy JSON lên Vercel Blob theo chu kỳ (--dry-run để thử cục bộ)
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
    if settings.is_live and settings.live_source in srcs:
        return settings.live_source
    real = [x for x in ("neo", "ssi") if x in srcs]
    return real[0] if (real and "sim" not in srcs) else "sim"


def _check_ssi(s: Settings) -> int:
    from .ssi.client import SsiApiError, SsiClient
    if not s.has_ssi_credentials:
        print("\nLỖI: thiếu SSI_API_KEY/SSI_API_SECRET trong .env (tạo tại https://developers.ssi.com.vn).")
        return 2
    try:
        with SsiClient(s) as c:
            c.login()
            members = c.securities_by_index(s.universe_index)
            print(f"\nKết nối REST SSI: OK. Rổ {s.universe_index}: {len(members)} mã. Số request đã gửi: {c.request_count}")
        return 0
    except SsiApiError as e:
        print(f"\nLỖI SSI API: {e}")
        return 1


def cmd_check(args, s: Settings) -> int:
    from .neo_api.client import NeoClient
    from .neo_api.errors import NeoApiError
    print("Cấu hình (bí mật đã che):")
    print(json.dumps(s.redacted(), ensure_ascii=False, indent=2))
    if not s.is_live:
        print("\nNEOPULSE_MODE=sim -> không gọi API thật. Đặt NEOPULSE_MODE=live và điền .env để kiểm tra kết nối.")
        return 0
    if s.source == "ssi":
        return _check_ssi(s)
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


def _positive_seconds(v: str) -> float:
    x = float(v)
    if not 0.2 <= x <= 60:
        raise argparse.ArgumentTypeError("phải trong khoảng 0,2-60 giây")
    return x


def _parse_until(v: str | None) -> time | None:
    return time.fromisoformat(v) if v else None


def cmd_record(args, s: Settings) -> int:
    from .data.recorder import record
    if not s.is_live:
        print("Bộ ghi cần NEOPULSE_MODE=live. (Dùng `neopulse simulate` nếu chỉ muốn chạy thử.)")
        return 2
    if s.source == "ssi":
        from .data.recorder_ssi import record_ssi
        if not s.has_ssi_credentials:
            print("Thiếu SSI_API_KEY/SSI_API_SECRET trong .env.")
            return 2
        res = asyncio.run(record_ssi(s, until=_parse_until(args.until), flush_every_s=args.flush_every))
        print("Kết thúc ghi (SSI):", json.dumps(res, ensure_ascii=False))
        return 0
    if not s.has_neo_credentials:
        print("Thiếu thông tin đăng nhập NEO API trong .env.")
        return 2
    res = asyncio.run(record(s, until=_parse_until(args.until), rest_every_s=args.rest_every,
                             flush_every_s=args.flush_every))
    print("Kết thúc ghi:", json.dumps(res, ensure_ascii=False))
    return 0


def cmd_poll(args, s: Settings) -> int:
    from .data.recorder import poll
    if s.source == "ssi":
        print("SSI không có endpoint REST giá/sổ lệnh thời gian thực nên không có chế độ polling; dùng `neopulse record`.")
        return 2
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


def cmd_export_web(args, s: Settings) -> int:
    from pathlib import Path

    from .analytics import webexport as wx
    try:
        db = wx.ReadOnlyStorage(s.db_path)
    except FileNotFoundError as e:
        print(e)
        return 1
    src = _source(args, s, db)
    codes = [c.strip().upper() for c in args.indexes.split(",")] if args.indexes else [args.index.upper()]
    entries = wx.export_to_dir(db, src, args.out, trading_date=args.date, index_codes=codes, all_dates=args.all_dates,
                               with_validation=not args.no_validation, order_value=args.order_value_mn * 1e6)
    for e in entries:
        print(f"{Path(args.out) / e['path']}  (phiên {e['trading_date']}, {e['index_code']}, điểm nhịp {e['pulse_score']})")
    print(f"Đã xuất {len(entries)} tệp JSON{' MÔ PHỎNG' if src == 'sim' else ''} vào {args.out} (latest.json, sessions/, index.json).")
    return 0 if entries else 1


def cmd_publish_static(args, s: Settings) -> int:
    from .analytics import webstatic as ws
    src = args.source or (s.live_source if s.is_live else "sim")
    codes = [c.strip().upper() for c in args.indexes.split(",")] if args.indexes else [args.index.upper()]
    date = None if args.date in (None, "", "latest", "moi-nhat") else args.date
    try:
        res = ws.publish_static(s.db_path, src, trading_date=date, index_codes=codes, out_dir=args.out,
                                all_dates=args.all_dates, with_validation=not args.no_validation,
                                order_value=args.order_value_mn * 1e6, deploy=args.deploy, web_dir=args.web_dir)
    except ws.StaticPublishError as e:
        print(f"LỖI: {e}")
        return 1
    for e in res.entries:
        print(f"{res.out_dir / e['path']}  (phiên {e['trading_date']}, {e['index_code']}, {e.get('snapshot_kind')})")
    print(f"Đã ghi snapshot{' MÔ PHỎNG' if src == 'sim' else ''} vào {res.out_dir} ({len(res.entries)} tệp phiên + latest + index).")
    if args.deploy:
        print(f"Đã triển khai: {res.url or '(không đọc được URL từ đầu ra vercel)'}")
    else:
        print("Chưa triển khai. Thêm --deploy (hoặc chạy `vercel --prod` trong web/) để đưa lên Vercel.")
    return 0


def cmd_publish(args, s: Settings) -> int:
    from .analytics import webpublish as wp
    src = args.source or (s.live_source if s.is_live else "sim")
    codes = [c.strip().upper() for c in args.indexes.split(",")] if args.indexes else [args.index.upper()]
    try:
        stats = wp.run_publish(s, source=src, every=args.every, until=_parse_until(args.until), index_codes=codes,
                               work_dir=args.out, dry_run=args.dry_run)
    except wp.BlobPutError as e:
        print(f"LỖI: {e}")
        return 2
    except KeyboardInterrupt:
        print("Đã dừng publish.")
        return 0
    print(f"Kết thúc publish: {stats.cycles} chu kỳ, {stats.uploads} tệp đã đẩy, {stats.failures} lỗi"
          + (" (dry-run: chỉ ghi cục bộ)" if args.dry_run else ""))
    return 0 if stats.failures == 0 or stats.uploads else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neopulse", description="NeoPulse Radar - radar nhịp thị trường trên NEO API")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--env-file", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--source", choices=["neo", "ssi", "sim"], help="nguồn dữ liệu (mặc định: tự chọn)")
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
    sp.add_argument("--flush-every", type=_positive_seconds, default=5.0,
                    help="giây giữa hai lần ghi lô xuống SQLite (mặc định 5; dùng 1 khi chạy live-relay)")
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
    sp.add_argument("--source", choices=["neo", "ssi", "sim"])
    sp.add_argument("--freq", default="1min")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_validate)
    sp = sub.add_parser("export")
    common(sp)
    sp.add_argument("--format", choices=["csv", "parquet"], default="csv")
    sp.add_argument("--out-dir", default="out")
    sp.set_defaults(fn=cmd_export)
    sp = sub.add_parser("export-web", help="xuất JSON cho giao diện web (chỉ đọc SQLite)")
    common(sp)
    sp.add_argument("--indexes", help="nhiều chỉ số, cách nhau dấu phẩy (VD VN30,VNINDEX); chỉ số đầu là latest.json")
    sp.add_argument("--out", default="out/web")
    sp.add_argument("--all-dates", action="store_true", help="xuất mọi phiên đã lưu")
    sp.add_argument("--no-validation", action="store_true", help="bỏ khối kiểm chứng (nhanh hơn)")
    sp.add_argument("--order-value-mn", type=float, default=500.0, help="lệnh giả định đo trượt giá (triệu đồng)")
    sp.set_defaults(fn=cmd_export_web)
    sp = sub.add_parser("publish-static", help="xuất snapshot tĩnh vào web/public/data/ và tùy chọn --deploy lên Vercel (khuyên dùng)")
    sp.add_argument("--source", choices=["neo", "ssi", "sim"], help="mặc định: nguồn thật đang cấu hình, hoặc sim")
    sp.add_argument("--date", default="latest", help="phiên YYYY-MM-DD hoặc 'latest' (mặc định)")
    sp.add_argument("--index", default="VN30")
    sp.add_argument("--indexes", help="nhiều chỉ số, cách nhau dấu phẩy (VD VN30,VNINDEX)")
    sp.add_argument("--out", default="web/public/data", help="thư mục ghi JSON (đã .gitignore)")
    sp.add_argument("--web-dir", default="web")
    sp.add_argument("--all-dates", action="store_true", help="xuất mọi phiên đã lưu")
    sp.add_argument("--no-validation", action="store_true")
    sp.add_argument("--order-value-mn", type=float, default=500.0)
    sp.add_argument("--deploy", action="store_true", help="chạy `vercel --prod --yes` trong web/ và in URL")
    sp.set_defaults(fn=cmd_publish_static)
    sp = sub.add_parser("publish", help="TÙY CHỌN, tốn hạn mức: đẩy JSON lên Vercel Blob theo chu kỳ (Hobby chỉ 2.000 thao tác/tháng)")
    sp.add_argument("--source", choices=["neo", "ssi", "sim"], help="mặc định: nguồn thật đang cấu hình, hoặc sim")
    sp.add_argument("--index", default="VN30")
    sp.add_argument("--indexes")
    sp.add_argument("--every", type=float, default=20.0, help="giây giữa hai lần đẩy")
    sp.add_argument("--until", default="15:05", help="giờ dừng HH:MM (giờ VN)")
    sp.add_argument("--out", default="out/web", help="thư mục làm việc cục bộ")
    sp.add_argument("--dry-run", action="store_true", help="chỉ ghi cục bộ, không gọi mạng")
    sp.set_defaults(fn=cmd_publish)
    return p


def _utf8_console() -> None:
    """Console Windows mặc định cp1252 không in được tiếng Việt: ép UTF-8 cho stdout/stderr."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
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
