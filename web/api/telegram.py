"""Webhook Telegram; xác thực header secret trước khi xử lý, không nhận đăng ký qua trình duyệt.

Tin nhắn: câu hỏi chỉ đọc (thị trường, cảnh báo, thẻ mã, trạng thái, hướng dẫn) trả lời từ payload website, không
đụng đăng ký; lệnh còn lại đi qua `handle_update` (CAS, chống xử lý lại update cũ). Nút bấm: nút chỉ đọc gửi tin mới
hoặc sửa tin; nút đổi cài đặt đi qua `handle_callback`. Mỗi HTTP response chỉ chứa được một method của Bot API, nên
`answerCallbackQuery` (tắt vòng chờ trên nút) được gọi riêng khi response đang dùng cho method khác.
"""
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "serverpkg"))
from neopulse.analytics.telegram_store import RedisUsers, handle_callback, handle_update  # noqa: E402
from neopulse.analytics.telegram_ui import (  # noqa: E402
    BASE,
    markup_for,
    readonly_answer,
    readonly_callback,
    split_command,
)


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
            with httpx.Client(timeout=12) as client:
                def load_payload():
                    r = client.get(BASE + "/api/data")
                    r.raise_for_status()
                    return r.json()["payload"]
                if update.get("callback_query"):
                    return self.on_callback(update, entries, load_payload, client)
                return self.on_message(update, entries, load_payload, client)
        except (ValueError, TypeError, KeyError):
            return self.reply(400, {"ok": False})
        except Exception:
            # Telegram sẽ retry; không trả 200 giả khi chưa lưu được thay đổi đăng ký.
            return self.reply(503, {"ok": False, "error": "temporary_unavailable"})

    def on_message(self, update, entries, load_payload, client):
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        text = message.get("text") or ""
        # Câu hỏi chỉ đọc không đụng tới đăng ký.
        if chat.get("type") == "private" and isinstance(chat.get("id"), int):
            answer = readonly_answer(text, entries, load_payload)
            if answer:
                return self.method("sendMessage", chat_id=chat["id"], text=answer[0], markup=answer[1])
        response = handle_update(RedisUsers.from_env(client), update, set(entries), time.time())
        if response:
            cid, body, markup = response
            return self.method("sendMessage", chat_id=cid, text=body, markup=markup or markup_for(split_command(text)[0]))
        return self.reply(200, {"ok": True})

    def on_callback(self, update, entries, load_payload, client):
        query = update["callback_query"]
        message = query.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private" or chat.get("id") != (query.get("from") or {}).get("id"):
            return self.method("answerCallbackQuery", callback_query_id=query.get("id"))
        data = query.get("data") or ""
        done = readonly_callback(data, entries, load_payload)
        if done:
            self.answer_async(client, query.get("id"))
            kind, body, markup = done
            if kind == "send":
                return self.method("sendMessage", chat_id=chat["id"], text=body, markup=markup)
            return self.method("editMessageText", chat_id=chat["id"], message_id=message.get("message_id"), text=body, markup=markup)
        result = handle_callback(RedisUsers.from_env(client), update, set(entries), time.time())
        if not result:  # update cũ do Telegram gửi lại: chỉ tắt vòng chờ
            return self.method("answerCallbackQuery", callback_query_id=query.get("id"))
        if result.get("edit"):
            self.answer_async(client, query.get("id"), result.get("toast"))
            body, markup = result["edit"]
            return self.method("editMessageText", chat_id=chat["id"], message_id=message.get("message_id"), text=body, markup=markup)
        return self.method("answerCallbackQuery", callback_query_id=query.get("id"), text=result.get("toast"))

    @staticmethod
    def answer_async(client, query_id, text=None):
        """Tắt vòng chờ trên nút khi response đang dùng cho method khác; lỗi ở đây không ảnh hưởng thao tác chính."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token or not query_id:
            return
        try:
            body = {"callback_query_id": query_id, **({"text": text[:190]} if text else {})}
            client.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json=body, timeout=4)
        except httpx.HTTPError:
            pass

    def method(self, name, *, markup=None, text=None, **fields):
        body = {"method": name, **fields}
        if text is not None:
            body.update({"text": text[:190]} if name == "answerCallbackQuery" else
                        {"text": text[:4096], "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}})
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
