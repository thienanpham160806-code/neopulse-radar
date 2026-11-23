"""Tin và sự kiện mới nhất cho một mã trong catalog. CDN Vercel giữ 15 phút, nên trang luôn có tin trễ tối đa ~15 phút
mà không cần máy cá nhân hay cron."""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.company import fetch_disclosures  # noqa: E402
from neopulse.timeutil import iso_vn, now_vn  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "serverpkg/data"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        symbol = parse_qs(urlparse(self.path).query).get("symbol", [""])[0].upper()
        catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
        if not any(r["symbol"] == symbol for r in catalog["symbols"]):
            return self.reply(404, {"error": "Mã không có trong danh mục cổ phiếu."})
        try:
            with httpx.Client(timeout=15) as client:
                got = fetch_disclosures(symbol, client)
        except Exception:
            got = {"events": [], "news": []}
        if not got["events"] and not got["news"]:
            return self.reply(503, {"error": "Nguồn tin tạm thời chưa trả dữ liệu."})
        self.reply(200, {"symbol": symbol, "updated_at": iso_vn(now_vn()), **got})

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Nguồn lỗi một nửa (VD Vietcap chặn sự kiện) chỉ cache ngắn để lần sau lấy lại đủ.
        full = status == 200 and body.get("events") and body.get("news")
        self.send_header("Cache-Control", "public, s-maxage=900, stale-while-revalidate=300" if full
                         else "public, s-maxage=60" if status == 200 else "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, *_args):
        pass
