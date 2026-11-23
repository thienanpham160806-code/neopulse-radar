"""Giao diện bot Telegram: menu, định dạng tin và các câu trả lời chỉ đọc (không đổi đăng ký).

Tổ chức theo cách tách handlers / keyboards / formatters của bot Kumo_VN_bot (đồ án nhóm, chỉ tham khảo cấu trúc,
không chép mã). Bot chỉ đọc kết quả NeoPulse đã tính sẵn (payload `/api/data`, catalog doanh nghiệp); không tính lại
chỉ báo, không khuyến nghị mua/bán.
"""
from __future__ import annotations

import re
import time
from datetime import datetime

BASE = "https://neopulse-radar.vercel.app"
DISCLAIMER = "Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."

# Nút menu gửi chữ như người dùng tự gõ; ánh xạ về lệnh tương ứng.
MENU = [["Nhịp thị trường", "Cảnh báo"], ["Tra doanh nghiệp", "Mã theo dõi"], ["Cài đặt nhận tin", "Hướng dẫn"]]
BUTTON_COMMANDS = {"nhịp thị trường": "/market", "cảnh báo": "/alerts", "tra doanh nghiệp": "/company",
                   "mã theo dõi": "/watchlist", "cài đặt nhận tin": "/status", "hướng dẫn": "/help"}
MAIN_KEYBOARD = {"keyboard": [[{"text": t} for t in row] for row in MENU], "resize_keyboard": True, "is_persistent": True}
SYMBOL = re.compile(r"[A-Z][A-Z0-9]{1,9}")

HELP = (
    "NeoPulse Radar · Trợ lý theo dõi thị trường\n\n"
    "Bot đọc nhanh kết quả NeoPulse đã tính và gửi tin theo lựa chọn của bạn. Phân tích chi tiết nằm trên website.\n\n"
    "Xem ngay (không cần đăng ký)\n"
    "/market: nhịp thị trường VN30\n"
    "/alerts: tóm tắt cảnh báo trong phiên\n"
    "/company MWG: mở hồ sơ doanh nghiệp (gõ mã cũng được)\n\n"
    "Nhận tin\n"
    "/start: đăng ký cảnh báo mức cao\n"
    "/alerts on|off, /news on|off, /laws on|off: bật/tắt cảnh báo, tin doanh nghiệp, tin chính sách\n"
    "/watch MWG,FPT: chỉ nhận tin của các mã này (tối đa 30)\n"
    "/all: bỏ lọc mã, nhận cảnh báo của các mã trong rổ VN30 đang theo dõi\n"
    "/watchlist, /status: xem mã theo dõi và cài đặt\n"
    "/stop: hủy và xóa đăng ký\n\n"
    "Tin được gửi theo đợt: khoảng mỗi phút trong giờ giao dịch khi bộ ghi dữ liệu đang chạy, "
    "và khoảng 5 phút một lần ngoài giờ. Cảnh báo mới chỉ có khi dữ liệu thị trường được cập nhật.\n"
    f"Website: {BASE}\n{DISCLAIMER}"
)


def url_buttons(*pairs: tuple[str, str]) -> dict:
    return {"inline_keyboard": [[{"text": text, "url": url} for text, url in pairs]]}


def normalize(text: str) -> str:
    """Chữ trên nút menu -> lệnh; giữ nguyên lệnh gõ tay."""
    return BUTTON_COMMANDS.get(text.strip().lower(), text.strip())


def _vn_time(iso: str | None) -> str:
    if not iso:
        return "chưa rõ thời điểm"
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M:%S, %d/%m/%Y")
    except ValueError:
        return iso


def _num(x, nd=2, signed=False) -> str:
    if x is None:
        return "—"
    s = f"{x:+,.{nd}f}" if signed else f"{x:,.{nd}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _money(x) -> str:
    if x is None:
        return "—"
    return f"{_num(x / 1e9, 1, signed=True)} tỷ đồng" if abs(x) >= 1e9 else f"{_num(x / 1e6, 1, signed=True)} triệu đồng"


def data_state(meta: dict, now: float | None = None) -> str:
    """Trạng thái dữ liệu theo thời điểm trả lời; không gọi dữ liệu cũ là đang cập nhật."""
    now = time.time() if now is None else now
    if meta.get("is_simulated"):
        return "Dữ liệu MÔ PHỎNG, không phải dữ liệu thị trường"
    status = meta.get("data_status") or {}
    state = status.get("state")
    try:
        age = now - datetime.fromisoformat(meta["last_update"]).timestamp()
    except (KeyError, TypeError, ValueError):
        age = None
    if state == "error":
        return "Lỗi dữ liệu: " + (status.get("reason") or "nguồn chưa trả kết quả")
    if state == "closed" or status.get("phase") in ("closed", "pre_open", "lunch"):
        return status.get("reason") or "Ngoài giờ giao dịch"
    if age is None:
        return "Chưa rõ thời điểm cập nhật"
    if age > 180:
        return f"Dữ liệu chưa cập nhật trong {age / 60:.0f} phút; bộ ghi có thể đang dừng"
    return "Trong phiên, dữ liệu vừa cập nhật"


def format_market(payload: dict, now: float | None = None) -> str:
    meta, pulse = payload.get("meta") or {}, payload.get("pulse") or {}
    row = (payload.get("index") or {}).get("row") or {}
    code = meta.get("index_code", "VN30")
    if pulse.get("score") is None:
        return (f"Nhịp thị trường · {code}\nChưa đủ dữ liệu để tính điểm nhịp.\n"
                f"{data_state(meta, now)} · dữ liệu đến {_vn_time(meta.get('last_update'))}\nXem: {BASE}")
    lines = [f"Nhịp thị trường · {code}",
             f"Dữ liệu đến {_vn_time(meta.get('last_update'))} · {data_state(meta, now)}",
             f"Điểm nhịp {_num(pulse['score'], 1)}/100: {pulse.get('label', '')}."]
    evidence = []
    if row.get("value") is not None:
        evidence.append(f"{code} {_num(row['value'])} điểm ({_num(row.get('pct_change'), 2, signed=True)}%), "
                        f"{row.get('advances', 0):.0f} mã tăng / {row.get('declines', 0):.0f} mã giảm")
    comps = sorted((c for c in pulse.get("components", []) if c.get("value") is not None), key=lambda c: -abs(c["value"]))
    if comps:
        evidence.append("Thành phần chi phối: " + ", ".join(f"{c['name']} {_num(c['value'], 2, signed=True)}" for c in comps[:2]))
    fs = (payload.get("foreign") or {}).get("summary") or {}
    if fs.get("net_val") is not None:
        side = "mua ròng" if fs["net_val"] > 0 else "bán ròng"
        evidence.append(f"Khối ngoại {side} {_money(abs(fs['net_val'])).lstrip('+')} trong rổ theo dõi")
    if evidence:
        lines.append("\nVì sao:\n- " + "\n- ".join(evidence))
    if pulse.get("missing"):
        names = {c["key"]: c["name"] for c in pulse.get("components", [])}
        lines.append("Thiếu dữ liệu: " + ", ".join(names.get(k, k) for k in pulse["missing"]) + "; điểm tính trên phần còn lại.")
    high = ((payload.get("alerts") or {}).get("by_severity") or {}).get("CAO", 0)
    if high:
        lines.append(f"\nĐáng chú ý: {high} lượt cảnh báo mức cao trong phiên. Gửi /alerts để xem.")
    lines.append(f"\nNguồn: {meta.get('source_label') or meta.get('source', '—')}\n{DISCLAIMER}")
    return "\n".join(lines)


def format_alerts(payload: dict, now: float | None = None, limit: int = 5) -> str:
    meta, al = payload.get("meta") or {}, payload.get("alerts") or {}
    items = [a for a in al.get("items", []) if a.get("severity") == "CAO"]
    head = f"Cảnh báo trong phiên · {meta.get('index_code', 'VN30')}\n{data_state(meta, now)} · dữ liệu đến {_vn_time(meta.get('last_update'))}"
    if not al.get("total"):
        return head + "\nChưa ghi nhận cảnh báo nào trong phiên."
    sev = al.get("by_severity") or {}
    lines = [head, f"Tổng {al['total']} lượt: {sev.get('CAO', 0)} mức cao, {sev.get('TRUNG BÌNH', 0)} trung bình, {sev.get('THẤP', 0)} thấp."]
    if items:
        lines.append(f"\n{min(limit, len(items))} cảnh báo mức cao gần nhất:")
        for a in sorted(items, key=lambda a: a.get("t", ""), reverse=True)[:limit]:
            lines.append(f"- {a['symbol']} lúc {_vn_time(a.get('t'))[:5]}: {a.get('message', a.get('rule_name', ''))}")
    lines.append("\nCảnh báo là quan sát cần xem lại, chưa cho biết nguyên nhân hay hướng giá.\n"
                 "Nhận tự động: /alerts on · Tắt: /alerts off\n" + DISCLAIMER)
    return "\n".join(lines)


def format_company(symbol: str, entry: dict) -> str:
    parts = [p for p in (entry.get("exchange"), entry.get("industry")) if p]
    return (f"{symbol} · {entry.get('name') or symbol}\n" + (" · ".join(parts) + "\n" if parts else "")
            + f"Hồ sơ doanh nghiệp: {BASE}/doanh-nghiep/{symbol}\n"
            "Gồm tổng quan, báo cáo tài chính, sự kiện và tin tức có link nguồn.")


def readonly_answer(text: str, catalog: dict[str, dict], load_payload) -> tuple[str, dict] | None:
    """Trả lời các yêu cầu chỉ đọc. None = để phần đăng ký (`command`) xử lý.

    `load_payload()` trả payload NeoPulse đã tính (hoặc ném lỗi); chỉ gọi khi cần, không tính lại chỉ báo.
    """
    parts = normalize(text).split(maxsplit=1)
    if not parts:
        return None
    cmd, arg = parts[0].split("@")[0].lower(), (parts[1].strip() if len(parts) > 1 else "")
    if cmd in {"/market", "/alerts"} and not arg:
        try:
            payload = load_payload()
        except Exception:  # noqa: BLE001 - nguồn lỗi thì báo rõ, không bịa số
            return ("Chưa lấy được dữ liệu thị trường. Nguồn có thể đang cập nhật; vui lòng thử lại sau ít phút.\n"
                    f"Website: {BASE}", url_buttons(("Mở NeoPulse", BASE)))
        if cmd == "/market":
            return format_market(payload), url_buttons(("Xem chi tiết", f"{BASE}/?tab=tong-quan"), ("Cảnh báo", f"{BASE}/?tab=canh-bao"))
        return format_alerts(payload), url_buttons(("Xem toàn bộ cảnh báo", f"{BASE}/?tab=canh-bao"))
    symbol = arg.upper() if cmd == "/company" else (parts[0].upper() if len(parts) == 1 and not cmd.startswith("/") else "")
    if cmd == "/company" and not arg:
        return ("Gửi mã cổ phiếu để mở hồ sơ, ví dụ: MWG hoặc /company MWG.\n"
                f"Danh sách doanh nghiệp: {BASE}/doanh-nghiep", url_buttons(("Danh sách doanh nghiệp", f"{BASE}/doanh-nghiep")))
    if symbol and SYMBOL.fullmatch(symbol):
        entry = catalog.get(symbol)
        if entry is None:
            if cmd == "/company":
                return f"Không tìm thấy mã {symbol} trong danh mục HOSE/HNX/UPCoM. Kiểm tra lại mã, ví dụ: MWG.", None
            return None
        return format_company(symbol, entry), url_buttons((f"Mở hồ sơ {symbol}", f"{BASE}/doanh-nghiep/{symbol}"))
    return None


def markup_for(cmd: str) -> dict:
    """Bàn phím đi kèm câu trả lời của phần đăng ký."""
    if cmd in {"/start", "/help"} or not cmd.startswith("/"):
        return MAIN_KEYBOARD
    if cmd in {"/status", "/watchlist", "/alerts", "/news", "/laws", "/watch", "/all"}:
        return url_buttons(("Chọn nhóm tin trên web", f"{BASE}/thong-bao"))
    return url_buttons(("Mở NeoPulse", BASE))
