"""Worker Telegram tự nguyện; trạng thái mã hóa trước khi rời runner, không lưu chat ID vào Git/log."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..timeutil import VN_TZ
from .telegram_ui import (  # noqa: F401 - BASE/HELP giữ cho mã gọi cũ
    BASE,
    HELP,
    alert_push_keyboard,
    format_alert_push,
    format_close_digest,
    format_news,
    format_open_digest,
    keyboard,
    news_keyboard,
    web_link,
)


class Telegram:
    def __init__(self, token: str, client: httpx.Client):
        self.token, self.client = token, client

    def call(self, method: str, payload: dict):
        try:
            r = self.client.post(f"https://api.telegram.org/bot{self.token}/{method}", json=payload)
            doc = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise RuntimeError(f"Telegram {method}: {type(e).__name__}") from None
        if r.status_code == 403:
            return {"blocked": True}
        if r.status_code != 200 or not doc.get("ok"):
            raise RuntimeError(f"Telegram {method}: HTTP {r.status_code}")
        return doc["result"]

    def send(self, chat: str, text: str, markup: dict | None = None):
        payload = {"chat_id": chat, "text": text[:4096], "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}}
        if markup:
            payload["reply_markup"] = markup
        return self.call("sendMessage", payload)


def load_state(path: Path, key: str) -> dict:
    from cryptography.fernet import Fernet
    if not path.exists():
        return {"offset": 0, "users": {}}
    # Sai khóa / dữ liệu hỏng phải dừng, không reset danh sách người đăng ký.
    return json.loads(Fernet(key.encode()).decrypt(path.read_bytes()))


def save_state(path: Path, key: str, state: dict):
    from cryptography.fernet import Fernet
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(Fernet(key.encode()).encrypt(json.dumps(state, separators=(",", ":")).encode()))
    temp.replace(path)


def new_user(at: float) -> dict:
    """Đăng ký mặc định: chỉ cảnh báo mức cao. Bản ghi cũ thiếu digest_* được đọc là tắt."""
    return {"since": at, "alerts": True, "news": False, "laws": False, "digest_open": False, "digest_close": False,
            "symbols": [], "delivered": {}, "enabled_since": {"alerts": at}}


def _set_topic(user: dict, topic: str, on: bool, at: float):
    user[topic] = on
    if on:
        user.setdefault("enabled_since", {})[topic] = at


def _watch_add(user: dict, symbols: list[str], valid: set[str]) -> str | None:
    if not symbols or not set(symbols) <= valid:
        return "Mã không hợp lệ hoặc chưa có trong danh mục. Ví dụ: /theodoi HPG."
    merged = sorted(set(user.get("symbols") or []) | set(symbols))
    if len(merged) > 30:
        return "Tối đa 30 mã theo dõi. Bỏ bớt mã trong /theodoi rồi thêm lại."
    user["symbols"] = merged
    return None


def command(state: dict, update: dict, valid: set[str], now: float) -> tuple[str, str, dict | None] | None:
    """Lệnh làm thay đổi hoặc cần đọc đăng ký. -> (chat_id, văn bản HTML, bàn phím) hoặc None."""
    from .telegram_ui import (
        MAIN_KEYBOARD,
        alias_note,
        settings_keyboard,
        settings_text,
        split_command,
        start_text,
        subscribe_prompt,
        watch_keyboard,
        watch_text,
    )
    m = update.get("message", {})
    chat = m.get("chat", {})
    if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
        return None
    cid = str(chat["id"])
    cmd, value, old = split_command(m.get("text") or "")
    if not cmd:
        return None
    note = alias_note(old, cmd)
    requested_at = min(now, float(m.get("date", now)))
    if cmd == "/dung":
        state["users"].pop(cid, None)
        return cid, "⏹ Đã hủy và xóa đăng ký NeoPulse. Bạn sẽ không nhận thêm tin. Gửi /start để đăng ký lại." + note, MAIN_KEYBOARD
    if cmd == "/start":
        user = state["users"].setdefault(cid, new_user(requested_at))
        topics = value.split("_")
        if value and set(topics) <= {"alerts", "news", "laws"}:
            for topic in ("alerts", "news", "laws"):
                _set_topic(user, topic, topic in topics, requested_at)
        return cid, start_text(user), MAIN_KEYBOARD
    if cmd == "/huongdan":
        return cid, HELP + note, MAIN_KEYBOARD
    user = state["users"].get(cid)
    if not user:
        if cmd in {"/caidat", "/theodoi", "/alerts", "/news", "/laws", "/watch", "/all"}:
            return cid, *subscribe_prompt()
        return cid, ("Chưa hiểu yêu cầu. Gõ mã cổ phiếu (ví dụ HPG) hoặc dùng menu bên dưới; /huongdan để xem các lệnh."), MAIN_KEYBOARD
    if cmd in {"/alerts", "/news", "/laws"}:
        if value.lower() not in {"on", "off"}:
            return cid, f"Dùng {cmd} on hoặc {cmd} off, hoặc bấm nút trong /caidat.", None
        _set_topic(user, cmd[1:], value.lower() == "on", requested_at)
        return cid, settings_text(user) + "\n\n<i>Lệnh mới: /caidat</i>", settings_keyboard(user)
    if cmd == "/caidat":
        return cid, settings_text(user) + note, settings_keyboard(user)
    if cmd == "/watch":
        symbols = sorted(set(re.split(r"[,\s]+", value.upper())) - {""})
        if not symbols or len(symbols) > 30 or not set(symbols) <= valid:
            return cid, "Mã không hợp lệ hoặc chưa có trong danh mục. Ví dụ /watch MWG,FPT; tối đa 30 mã.", None
        user["symbols"] = symbols
        return cid, watch_text(user) + "\n\n<i>Lệnh mới: /theodoi</i>", watch_keyboard(user)
    if cmd == "/all":
        user["symbols"] = []
        return cid, watch_text(user) + "\n\n<i>Lệnh mới: /theodoi</i>", watch_keyboard(user)
    if cmd == "/theodoi":
        if value:
            error = _watch_add(user, sorted(set(re.split(r"[,\s]+", value.upper())) - {""}), valid)
            if error:
                return cid, error, None
        return cid, watch_text(user) + note, watch_keyboard(user)
    return cid, "Chưa hiểu yêu cầu. Gõ mã cổ phiếu (ví dụ HPG) hoặc dùng menu; /huongdan để xem các lệnh.", MAIN_KEYBOARD


def callback(state: dict, cid: str, data: str, valid: set[str], now: float) -> dict:
    """Nút bấm thay đổi đăng ký. -> {"toast": str} và/hoặc {"edit": (văn bản, bàn phím)}."""
    from .telegram_ui import (
        TOPICS,
        settings_keyboard,
        settings_text,
        subscribe_prompt,
        watch_keyboard,
        watch_text,
    )
    user = state["users"].get(cid)
    if data == "sub":
        user = state["users"].setdefault(cid, new_user(now))
        return {"toast": "Đã đăng ký: bật cảnh báo mức cao.", "edit": (settings_text(user), settings_keyboard(user))}
    if not user:
        return {"toast": "Bạn chưa đăng ký. Bấm Đăng ký hoặc gửi /start.", "edit": subscribe_prompt()}
    if data == "stop":
        state["users"].pop(cid, None)
        return {"toast": "Đã hủy đăng ký.", "edit": ("⏹ Đã hủy và xóa đăng ký NeoPulse. Gửi /start để đăng ký lại.", None)}
    if data.startswith("t:") and data[2:] in TOPICS:
        on = not user.get(data[2:])
        _set_topic(user, data[2:], on, now)
        return {"toast": f"{TOPICS[data[2:]]}: {'bật' if on else 'tắt'}", "edit": (settings_text(user), settings_keyboard(user))}
    if data == "v:caidat":
        return {"edit": (settings_text(user), settings_keyboard(user))}
    if data == "v:theodoi":
        return {"edit": (watch_text(user), watch_keyboard(user))}
    if data == "wall":
        user["symbols"] = []
        return {"toast": "Đã chuyển sang theo dõi cả rổ VN30.", "edit": (watch_text(user), watch_keyboard(user))}
    sym = data[3:] if data.startswith("w-:") else data[2:] if data.startswith("c:") else ""
    if sym and sym in valid:
        mine = list(user.get("symbols") or [])
        if data.startswith("w-:"):
            user["symbols"] = [s for s in mine if s != sym]
            return {"toast": f"Đã bỏ theo dõi {sym}.", "edit": (watch_text(user), watch_keyboard(user))}
        if sym in mine:
            user["symbols"] = [s for s in mine if s != sym]
            return {"toast": f"Đã bỏ {sym} khỏi danh sách theo dõi."}
        error = _watch_add(user, [sym], valid)
        return {"toast": error or f"Đã thêm {sym} vào danh sách theo dõi."}
    return {"toast": "Nút này không còn hiệu lực."}


def timestamp(value: str) -> float | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        try:
            return parsedate_to_datetime(value).timestamp()
        except (ValueError, TypeError):
            try:
                from zoneinfo import ZoneInfo
                return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")).timestamp()
            except (ValueError, TypeError):
                return None


def rss_items(content: bytes, category: str, allowed_host: str, symbols: set[str]) -> list[dict]:
    if len(content) > 2_000_000 or b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("RSS không an toàn")
    root = ET.fromstring(content)
    out = []
    for item in root.findall(".//item"):
        title, link = item.findtext("title", "").strip(), item.findtext("link", "").strip()
        if urlparse(link).scheme != "https" or urlparse(link).hostname != allowed_host:
            continue
        when = timestamp(item.findtext("pubDate", ""))
        if not title or when is None:
            continue
        matched = sorted(s for s in symbols if re.search(rf"\b{re.escape(s)}\b", title, re.I))
        if category == "news" and not matched:
            continue
        if category == "laws" and not re.search(r"nghị định|thông tư|luật|thuế|chứng khoán|trái phiếu|chính sách|dự thảo", title, re.I):
            continue
        out.append({"id": hashlib.sha256(link.encode()).hexdigest(), "category": category, "at": when, "symbols": matched,
                    "text": format_news(category, allowed_host, title, link, when, matched), "markup": news_keyboard(link)})
    return out


def should_send(user: dict, event: dict, now: float) -> bool:
    since = max(user["since"], user.get("enabled_since", {}).get(event["category"], user["since"]))
    return (bool(user.get(event["category"])) and since <= event["at"] <= now + 300
            and event["at"] >= now - 86400 and event["id"] not in user["delivered"]
            and (event["category"] in MARKET_WIDE or not user["symbols"] or bool(set(user["symbols"]) & set(event["symbols"]))))


MARKET_WIDE = {"laws", "digest_open", "digest_close"}


def digest_events(payload: dict, now: float) -> list[dict]:
    """Tóm tắt đầu phiên (từ 09:15) và tổng kết cuối phiên (sau 15:00), mỗi loại một lần mỗi ngày giao dịch."""
    meta = payload.get("meta") or {}
    if meta.get("is_simulated") or not payload.get("pulse"):
        return []
    try:
        last = datetime.fromisoformat(meta["last_update"]).astimezone(VN_TZ)
    except (KeyError, TypeError, ValueError):
        return []
    today = datetime.fromtimestamp(now, VN_TZ).date().isoformat()
    if meta.get("trading_date") != today or last.date().isoformat() != today:
        return []
    out = []
    hm = last.strftime("%H:%M")
    closed = (meta.get("data_status") or {}).get("phase") == "closed"
    if "09:15" <= hm < "11:30":
        out.append({"id": f"digest_open|{today}", "category": "digest_open", "at": now, "symbols": [],
                    "text": format_open_digest(payload, now), "markup": keyboard([web_link("Mở trên web", "/?tab=tong-quan")])})
    if closed and hm >= "14:45":
        out.append({"id": f"digest_close|{today}", "category": "digest_close", "at": now, "symbols": [],
                    "text": format_close_digest(payload, now), "markup": keyboard([web_link("Xem bản tin phiên trên web", "/?tab=tong-quan")])})
    return out


def outbox(user: dict, events: list[dict], basket: set[str], payload: dict, now: float) -> list[dict]:
    """Tin cần gửi cho một người: lọc theo cài đặt và mã; các cảnh báo cùng đợt gom thành một tin."""
    due = [e for e in sorted(events, key=lambda e: e["at"])
           if (user["symbols"] or e["category"] in MARKET_WIDE or set(e["symbols"]) & basket) and should_send(user, e, now)]
    alerts = [e for e in due if e["category"] == "alerts"]
    out = []
    if alerts:
        raw = [e["alert"] for e in alerts]
        out.append({"ids": [e["id"] for e in alerts], "text": format_alert_push(raw, payload, now),
                    "markup": alert_push_keyboard(raw)})
    out += [{"ids": [e["id"]], "text": e["text"], "markup": e.get("markup")} for e in due if e["category"] != "alerts"]
    return out


LOCK_KEY = "neopulse:telegram:lock"


def run(path: Path, token: str, key: str, *, client: httpx.Client, now: float | None = None, budget_s: float | None = None):
    """Một lượt xử lý. Có Redis thì giữ khóa để cron, relay và GitHub không gửi trùng cùng lúc."""
    store = None
    if os.environ.get("KV_REST_API_URL") and os.environ.get("KV_REST_API_TOKEN"):
        from .telegram_store import RedisUsers
        store = RedisUsers.from_env(client)
        if not store.call("SET", LOCK_KEY, "1", "NX", "EX", "120"):
            print("Một lượt khác đang chạy; bỏ qua lượt này.")
            return
    try:
        _run(path, token, key, client=client, now=now, store=store,
             deadline=None if budget_s is None else time.monotonic() + budget_s)
    finally:
        if store:
            store.call("DEL", LOCK_KEY)


def _run(path: Path, token: str, key: str, *, client: httpx.Client, now: float | None, store, deadline: float | None):
    now = time.time() if now is None else now
    state = load_state(path, key)
    api = Telegram(token, client)
    if store:
        state["users"] = store.users()
    index = client.get(BASE + ("/data/company/catalog.json" if store else "/data/company/index.json"))
    index.raise_for_status()
    valid = {r["symbol"] for r in index.json()["symbols"]}
    # Khi webhook đã bật, Telegram không cho dùng getUpdates; webhook sở hữu lệnh và đăng ký.
    updates = [] if store else api.call("getUpdates", {"offset": state["offset"], "timeout": 0, "limit": 100, "allowed_updates": ["message"]})
    for update in updates:
        reply = command(state, update, valid, now)
        # Lưu đăng ký/hủy trước xác nhận; không để lỗi gửi làm mất /stop.
        save_state(path, key, state)
        if reply:
            result = api.send(*reply)
            if isinstance(result, dict) and result.get("blocked"):
                state["users"].pop(reply[0], None)
        state["offset"] = update["update_id"] + 1
        save_state(path, key, state)
    if not state["users"]:
        save_state(path, key, state)
        print("Worker sẵn sàng; chưa có đăng ký đang hoạt động.")
        return
    events = []
    snap = client.get(BASE + "/api/data")
    snap.raise_for_status()
    payload = snap.json()["payload"]
    vn30 = client.get(BASE + "/data/latest_VN30.json")
    vn30.raise_for_status()
    basket = {r["symbol"] for r in vn30.json().get("book", {}).get("rows", [])}
    if not payload["meta"]["is_simulated"]:
        for a in payload.get("alerts", {}).get("items", []):
            at = timestamp(a["t"])
            if at and a["severity"] == "CAO":
                identity = f"{a['t']}|{a['symbol']}|{a['rule']}"
                events.append({"id": hashlib.sha256(identity.encode()).hexdigest(), "category": "alerts", "at": at,
                               "symbols": [a["symbol"]], "alert": a})
    events += digest_events(payload, now)
    for category, url, host in [("news", "https://cafef.vn/thi-truong-chung-khoan.rss", "cafef.vn"),
                                ("laws", "https://baochinhphu.vn/home.rss", "baochinhphu.vn")]:
        try:
            response = client.get(url)
            response.raise_for_status()
            events += rss_items(response.content, category, host, valid)
        except (httpx.HTTPError, ValueError, ET.ParseError):
            print(f"Nguồn {category} tạm không truy cập được; sẽ thử ở lượt sau.")
    sent = 0
    recipients = list(state["users"].items())
    cursor = state.get("cursor", 0) % max(1, len(recipients))
    recipients = recipients[cursor:] + recipients[:cursor]
    for position, (cid, user) in enumerate(recipients):
        user_sent = 0
        user["delivered"] = {k: v for k, v in user["delivered"].items() if v >= now - 7 * 86400}
        if store:
            user = store.read(cid).get("user") or user
        messages = outbox(user, events, basket, payload, now)
        for message in messages:
            if store:
                current = store.read(cid).get("user")
                if not current:
                    break  # /stop có hiệu lực trước những lần gửi tiếp theo
                user = current
            if all(i in user.get("delivered", {}) for i in message["ids"]):
                continue
            result = api.send(cid, message["text"], message.get("markup"))
            if isinstance(result, dict) and result.get("blocked"):
                state["users"].pop(cid, None)
                if store:
                    store.update(cid, lambda r: {**r, "user": None})
                save_state(path, key, state)
                break
            for identity in message["ids"]:
                user.setdefault("delivered", {})[identity] = now
            if store:
                def acknowledge(record, ids=tuple(message["ids"])):
                    if not record.get("user"):
                        return None
                    delivered = record["user"].setdefault("delivered", {})
                    for identity in ids:
                        delivered[identity] = now
                    record["user"]["delivered"] = {k: v for k, v in delivered.items() if v >= now - 7 * 86400}
                    return record
                store.update(cid, acknowledge)
            save_state(path, key, state)
            sent += 1
            user_sent += 1
            time.sleep(1.1)  # giới hạn Telegram theo từng cuộc trò chuyện
            if deadline is not None and time.monotonic() > deadline:  # hàm serverless có giới hạn thời gian
                save_state(path, key, state)
                print(f"Hết thời gian lượt; đã gửi {sent} tin, phần còn lại gửi ở lượt sau.")
                return
            if sent >= 100:  # ngân sách mỗi lượt, phần còn lại được retry ở lượt sau
                state["cursor"] = (cursor + position + 1) % max(1, len(recipients))
                save_state(path, key, state)
                return
            if user_sent >= 10:
                break
    save_state(path, key, state)
    print(f"Worker hoàn tất; đã gửi {sent} tin mới. Không ghi người nhận vào log.")


def main():
    token, key = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_STATE_KEY", "")
    if not token or not key:
        raise RuntimeError("Thiếu Secret Telegram của worker cloud")
    with httpx.Client(timeout=25, follow_redirects=True) as client:
        run(Path("state/telegram.enc"), token, key, client=client)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # không in traceback có thể chứa URL token/chat ID
        print(f"Worker chưa hoàn tất: {type(exc).__name__}; trạng thái đã lưu sẽ được giữ lại để retry.")
        raise SystemExit(1) from None
