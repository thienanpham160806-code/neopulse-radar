"""Báo cáo theo yêu cầu, chỉ mã có trong catalog, cache 6 giờ để tránh tải nguồn lặp lại."""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.company_remote import fetch_report  # noqa: E402

_CACHE = {}
DATA = Path(__file__).resolve().parents[1] / "serverpkg/data"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        symbol = parse_qs(urlparse(self.path).query).get("symbol", [""])[0].upper()
        catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
        entry = next((r for r in catalog["symbols"] if r["symbol"] == symbol), None)
        if not entry:
            return self.reply(404, {"error": "Mã không có trong danh mục cổ phiếu."})
        key = "neopulse:report:" + symbol
        try:
            with httpx.Client(timeout=18) as client:
                url, token = os.environ.get("KV_REST_API_URL"), os.environ.get("KV_REST_API_TOKEN")
                def redis(*args):
                    if not url or not token:
                        return None
                    r = client.post(url, headers={"Authorization": "Bearer " + token}, json=list(args))
                    r.raise_for_status()
                    return r.json().get("result")
                cached = redis("GET", key)
                if cached:
                    return self.reply(200, json.loads(cached))
                memory = _CACHE.get(symbol)
                if memory and memory[0] > time.time():
                    return self.reply(200, memory[1])
                # Chặn dồn yêu cầu tải lại cho cùng một mã trên nhiều function instance.
                if url and not redis("SET", key + ":loading", "1", "NX", "EX", 45):
                    return self.reply(429, {"error": "Báo cáo đang được tải. Vui lòng thử lại sau ít giây."})
                try:
                    aliases = json.loads((DATA / "field-aliases.json").read_text(encoding="utf-8"))
                    index_path = DATA / "VNINDEX.json"
                    index_prices = [[r["time"], r["value"]] for r in json.loads(index_path.read_text())["data"]] if index_path.exists() else []
                    report = fetch_report(symbol, entry, aliases, client, index_prices)
                    redis("SETEX", key, 21600, json.dumps(report, ensure_ascii=False))
                    if len(_CACHE) >= 64:
                        _CACHE.pop(next(iter(_CACHE)))
                    _CACHE[symbol] = (time.time() + 21600, report)
                finally:
                    if url:
                        redis("DEL", key + ":loading")
            return self.reply(200, report)
        except Exception:
            return self.reply(503, {"error": "Nguồn dữ liệu chưa trả được báo cáo. Thông tin cơ bản vẫn dùng được; vui lòng thử lại sau."})

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, s-maxage=3600, stale-while-revalidate=3600" if status == 200 else "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, *_args):
        pass
