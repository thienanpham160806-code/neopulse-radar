"""Webhook Telegram; xác thực header secret trước khi xử lý, không nhận đăng ký qua trình duyệt."""
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.telegram_store import RedisUsers, handle_update  # noqa: E402
from neopulse.analytics.telegram_ui import BASE, markup_for, normalize, readonly_answer  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        if not secret or not hmac.compare_digest(self.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), secret):
            return self.reply(403, {"ok": False})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                return self.reply(400, {"ok": False})
            update = json.loads(self.rfile.read(length))
            catalog = json.loads((Path(__file__).resolve().parents[1] / "serverpkg/data/catalog.json").read_text(encoding="utf-8"))
            entries = {r["symbol"]: r for r in catalog["symbols"]}
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            text = message.get("text") or ""
            with httpx.Client(timeout=12) as client:
                # Câu hỏi chỉ đọc (nhịp thị trường, cảnh báo, tra mã) không đụng tới đăng ký.
                if chat.get("type") == "private" and isinstance(chat.get("id"), int):
                    def load_payload():
                        r = client.get(BASE + "/api/data")
                        r.raise_for_status()
                        return r.json()["payload"]
                    answer = readonly_answer(text, entries, load_payload)
                    if answer:
                        return self.send(chat["id"], answer[0], answer[1])
                response = handle_update(RedisUsers.from_env(client), update, set(entries), time.time())
            if response:
                command = normalize(text).split(maxsplit=1)[0].split("@")[0].lower() if text.strip() else ""
                return self.send(response[0], response[1], markup_for(command))
            return self.reply(200, {"ok": True})
        except (ValueError, TypeError, KeyError):
            return self.reply(400, {"ok": False})
        except Exception:
            # Telegram sẽ retry; không trả 200 giả khi chưa lưu được thay đổi đăng ký.
            return self.reply(503, {"ok": False, "error": "temporary_unavailable"})

    def send(self, chat_id, text, markup):
        body = {"method": "sendMessage", "chat_id": chat_id, "text": text[:4000], "link_preview_options": {"is_disabled": True}}
        if markup:
            body["reply_markup"] = markup
        return self.reply(200, body)

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def log_message(self, *_args):
        pass
