"""Kích hoạt một lượt gửi tin Telegram. Gọi từ cron ngoài (mỗi 5 phút) và từ bộ phát trực tiếp (mỗi phút trong phiên).

Bảo vệ bằng header `Authorization: Bearer <TELEGRAM_TICK_SECRET>`. Một lượt chỉ gửi tin chưa gửi; khóa Redis trong
`telegram_cloud.run` chặn hai lượt chạy song song, nên gọi dày không gây gửi trùng.
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.telegram_cloud import run  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.tick()

    def do_POST(self):
        self.tick()

    def tick(self):
        secret = os.environ.get("TELEGRAM_TICK_SECRET", "")
        if not secret or not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + secret):
            return self.reply(401, {"error": "Không có quyền."})
        token, key = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_STATE_KEY", "")
        if not token or not key or not os.environ.get("KV_REST_API_URL"):
            return self.reply(503, {"error": "Chưa cấu hình gửi tin Telegram."})
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                run(Path("/tmp/telegram.enc"), token, key, client=client, budget_s=40)
        except Exception as exc:  # không trả chi tiết có thể chứa token hoặc chat ID
            return self.reply(503, {"error": type(exc).__name__})
        self.reply(200, {"ok": True})

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, *_args):
        pass
