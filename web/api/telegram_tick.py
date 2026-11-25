"""Kích hoạt một lượt gửi tin Telegram. Gọi từ cron ngoài (mỗi 5 phút) và từ bộ phát trực tiếp (mỗi phút trong phiên).

Bảo vệ bằng header `Authorization: Bearer <TELEGRAM_TICK_SECRET>`. `?setup=webhook` đăng ký lại webhook để nhận cả
tin nhắn và nút bấm (callback_query), dùng secret webhook sẵn có trên Vercel; không cần đưa secret ra máy cá nhân.
Một lượt chỉ gửi tin chưa gửi; khóa Redis trong `telegram_cloud.run` chặn hai lượt chạy song song, nên gọi dày không
gây gửi trùng.
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.telegram_cloud import BASE, run  # noqa: E402


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
        if parse_qs(urlparse(self.path).query).get("setup") == ["webhook"]:
            return self.setup_webhook(token)
        if not token or not key or not os.environ.get("KV_REST_API_URL"):
            return self.reply(503, {"error": "Chưa cấu hình gửi tin Telegram."})
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                run(Path("/tmp/telegram.enc"), token, key, client=client, budget_s=40)
        except Exception as exc:  # không trả chi tiết có thể chứa token hoặc chat ID
            return self.reply(503, {"error": type(exc).__name__})
        self.reply(200, {"ok": True})

    def setup_webhook(self, token):
        hook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        if not token or not hook_secret:
            return self.reply(503, {"error": "Chưa cấu hình webhook Telegram."})
        url = f"https://api.telegram.org/bot{token}/"
        with httpx.Client(timeout=15) as client:
            ok = client.post(url + "setWebhook", json={"url": BASE + "/api/telegram", "secret_token": hook_secret,
                                                       "allowed_updates": ["message", "callback_query"]}).json().get("ok")
            info = client.post(url + "getWebhookInfo", json={}).json().get("result", {})
        return self.reply(200 if ok else 502, {"ok": bool(ok), "allowed_updates": info.get("allowed_updates"),
                                                "url_ok": info.get("url") == BASE + "/api/telegram"})

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, *_args):
        pass
