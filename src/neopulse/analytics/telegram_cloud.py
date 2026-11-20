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

BASE = "https://neopulse-radar.vercel.app"
HELP = ("NEOPULSE RADAR — TRỢ LÝ THEO DÕI THỊ TRƯỜNG\n\n"
        "Bot gửi cảnh báo bất thường, tin doanh nghiệp và tin chính sách theo lựa chọn của bạn. Không đặt lệnh, không khuyến nghị mua/bán.\n\n"
        f"Mở website: {BASE}\nChọn nhóm tin: {BASE}/thong-bao\nXem doanh nghiệp: {BASE}/doanh-nghiep\n\n"
        "BẮT ĐẦU\n/start: đăng ký cảnh báo mức CAO\n/help: xem hướng dẫn này\n"
        "/news on hoặc off: tin doanh nghiệp\n/laws on hoặc off: tin chính sách từ Chính phủ\n"
        "/watch MWG,FPT: lọc mã (tối đa 30)\n/all: toàn bộ VN30\n/status: xem cài đặt\n"
        "/stop hoặc /delete: hủy và xóa đăng ký\n"
        "Tin tự động gửi theo đợt khoảng 15 phút; lịch cloud có thể trễ. Nguồn giá cần được NeoPulse cập nhật để có cảnh báo mới. Không phải lời khuyên đầu tư.")


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

    def send(self, chat: str, text: str):
        return self.call("sendMessage", {"chat_id": chat, "text": text[:4000], "link_preview_options": {"is_disabled": True}})


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


def command(state: dict, update: dict, valid: set[str], now: float) -> tuple[str, str] | None:
    m = update.get("message", {})
    chat = m.get("chat", {})
    if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
        return None
    cid = str(chat["id"])
    args = (m.get("text") or "").strip().split(maxsplit=1)
    if not args:
        return None
    cmd, value = args[0].split("@")[0].lower(), args[1].strip() if len(args) > 1 else ""
    requested_at = min(now, float(m.get("date", now)))
    if cmd in {"/stop", "/delete"}:
        state["users"].pop(cid, None)
        return cid, "Đã hủy và xóa đăng ký NeoPulse. Bot sẽ không gửi thêm tin. /start để đăng ký lại."
    if cmd == "/start":
        state["users"].setdefault(cid, {"since": requested_at, "alerts": True, "news": False, "laws": False, "symbols": [], "delivered": {}, "enabled_since": {"alerts": requested_at}})
        topics = value.split("_")
        if value and set(topics) <= {"alerts", "news", "laws"}:
            user = state["users"][cid]
            for topic in ("alerts", "news", "laws"):
                user[topic] = topic in topics
                if user[topic]:
                    user.setdefault("enabled_since", {})[topic] = requested_at
        return cid, HELP
    if cmd == "/help":
        return cid, HELP
    if cmd in {"/web", "/website"}:
        return cid, f"NeoPulse Radar\n{BASE}\nHồ sơ doanh nghiệp: {BASE}/doanh-nghiep\nNhóm tin: {BASE}/thong-bao"
    user = state["users"].get(cid)
    if not user:
        return (cid, "Bạn chưa đăng ký. Gửi /start nếu muốn nhận thông báo.") if cmd.startswith("/") else None
    if cmd in {"/alerts", "/news", "/laws"}:
        if value.lower() not in {"on", "off"}:
            return cid, f"Dùng {cmd} on hoặc {cmd} off."
        user[cmd[1:]] = value.lower() == "on"
        if value.lower() == "on":
            user.setdefault("enabled_since", {})[cmd[1:]] = requested_at
    elif cmd == "/watch":
        symbols = sorted(set(re.split(r"[,\s]+", value.upper())))
        if not symbols or len(symbols) > 30 or not set(symbols) <= valid:
            return cid, "Mã không hợp lệ hoặc chưa có trong danh sách hồ sơ. Ví dụ /watch MWG,FPT; tối đa 30 mã."
        user["symbols"] = symbols
    elif cmd == "/all":
        user["symbols"] = []
    elif cmd != "/status":
        return cid, HELP
    def flag(key):
        return "Bật" if user[key] else "Tắt"
    return cid, (f"Cài đặt nhận tin NeoPulse\nCảnh báo: {flag('alerts')}\nTin doanh nghiệp: {flag('news')}\nChính sách: {flag('laws')}\n"
                 f"Mã theo dõi: {', '.join(user['symbols']) or 'Toàn bộ VN30'}\n/stop để hủy và xóa đăng ký.")


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
        suffix = "\nTin/bài chính sách; có thể là dự thảo/đề xuất. Hiệu lực: xem văn bản gốc, không suy ra từ ngày đăng." if category == "laws" else ""
        out.append({"id": hashlib.sha256(link.encode()).hexdigest(), "category": category, "at": when,
                    "symbols": matched, "text": f"[{allowed_host}] {title}\nĐăng: {item.findtext('pubDate')}\n{link}{suffix}"})
    return out


def should_send(user: dict, event: dict, now: float) -> bool:
    since = max(user["since"], user.get("enabled_since", {}).get(event["category"], user["since"]))
    return (bool(user.get(event["category"])) and since <= event["at"] <= now + 300
            and event["at"] >= now - 86400 and event["id"] not in user["delivered"]
            and (event["category"] == "laws" or not user["symbols"] or bool(set(user["symbols"]) & set(event["symbols"]))))


def run(path: Path, token: str, key: str, *, client: httpx.Client, now: float | None = None):
    now = time.time() if now is None else now
    state = load_state(path, key)
    api = Telegram(token, client)
    store = None
    if os.environ.get("KV_REST_API_URL") and os.environ.get("KV_REST_API_TOKEN"):
        from .telegram_store import RedisUsers
        store = RedisUsers.from_env(client)
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
                               "symbols": [a["symbol"]], "text": f"[CẢNH BÁO CAO] {a['symbol']} · {a['t']}\n{a['message']}\n{BASE}/doanh-nghiep/{a['symbol']}\nKhông phải khuyến nghị đầu tư."})
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
        for event in sorted(events, key=lambda e: e["at"]):
            if store:
                current = store.read(cid).get("user")
                if not current:
                    break  # /stop có hiệu lực trước những lần gửi tiếp theo
                user = current
            if not user["symbols"] and event["category"] != "laws" and not set(event["symbols"]) & basket:
                continue
            if not should_send(user, event, now):
                continue
            result = api.send(cid, event["text"])
            if isinstance(result, dict) and result.get("blocked"):
                state["users"].pop(cid, None)
                if store:
                    store.update(cid, lambda r: {**r, "user": None})
                save_state(path, key, state)
                break
            user["delivered"][event["id"]] = now
            if store:
                def acknowledge(record, identity=event["id"]):
                    if not record.get("user"):
                        return None
                    delivered = record["user"].setdefault("delivered", {})
                    delivered[identity] = now
                    record["user"]["delivered"] = {k: v for k, v in delivered.items() if v >= now - 7 * 86400}
                    return record
                store.update(cid, acknowledge)
            save_state(path, key, state)
            sent += 1
            user_sent += 1
            time.sleep(1.1)  # giới hạn Telegram theo từng cuộc trò chuyện
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
