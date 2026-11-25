"""Giao diện bot Telegram: bộ icon, menu, nút bấm, định dạng tin (HTML) và các câu trả lời chỉ đọc.

Tổ chức theo cách tách handlers / keyboards / formatters của bot Kumo_VN_bot (đồ án nhóm): tham khảo cấu trúc,
không dùng mã. Bot chỉ đọc kết quả NeoPulse đã tính sẵn (payload `/api/data` của website, catalog doanh nghiệp) để
con số trên bot khớp website; không tính lại chỉ báo, không khuyến nghị mua/bán.
Quy ước trình bày: docs/bot_style.md.
"""
from __future__ import annotations

import html
import re
import time
from datetime import datetime, timedelta, timezone

BASE = "https://neopulse-radar.vercel.app"
BOT = "neopulse_warningbot"  # bấm mã trong tin mở thẻ mã qua link sâu t.me/<bot>?start=ma_<MÃ>
DISCLAIMER = "Không phải lời khuyên đầu tư"
VN = timezone(timedelta(hours=7))
LIMIT = 4000  # Telegram cho tối đa 4096 ký tự; chừa chỗ cho thẻ HTML

# Bộ icon duy nhất của bot (docs/bot_style.md). Không dùng icon trang trí ngoài bộ này.
ICON = {
    "up": "🟢", "down": "🔴", "flat": "🟡", "ceil": "🟣", "floor": "🔵",
    "high": "🚨", "mid": "⚠️", "low": "ℹ️",
    "market": "📊", "pulse": "🧭", "foreign": "🏦", "deriv": "📈", "company": "🏢", "news": "📰", "laws": "⚖️", "world": "🌏",
    "watch": "⭐", "settings": "⚙️", "status": "ℹ️", "help": "❓", "stop": "⏹", "link": "🔗",
}
SEV_ICON = {"CAO": ICON["high"], "TRUNG BÌNH": ICON["mid"], "THẤP": ICON["low"]}
SEV_NAME = {"CAO": "mức cao", "TRUNG BÌNH": "trung bình", "THẤP": "thấp"}
RULE_TITLE = {"volume_spike": "Khối lượng bất thường", "spread_blowout": "Độ chênh giá mua-bán giãn rộng",
              "price_jump": "Giá biến động đột ngột", "foreign_flow": "Khối ngoại giao dịch bất thường",
              "book_pressure": "Mất cân bằng sổ lệnh kéo dài", "near_limit": "Sát trần/sàn"}
TOPICS = {"alerts": "Cảnh báo mức cao", "news": "Bản tin doanh nghiệp, quốc tế", "laws": "Bản tin chính sách, pháp luật",
          "digest_open": "Tóm tắt đầu phiên", "digest_close": "Tổng kết cuối phiên"}
SYMBOL = re.compile(r"[A-Z][A-Z0-9]{1,9}")

# ------------------------------------------------------------------------------------------------ menu và lệnh
MENU = [[f"{ICON['market']} Thị trường", f"{ICON['high']} Cảnh báo", f"{ICON['company']} Tra mã"],
        [f"{ICON['watch']} Theo dõi", f"{ICON['settings']} Cài đặt"],
        [f"{ICON['status']} Trạng thái", f"{ICON['help']} Hướng dẫn"]]
MAIN_KEYBOARD = {"keyboard": [[{"text": t} for t in row] for row in MENU], "resize_keyboard": True, "is_persistent": True}
_MENU_COMMANDS = ["/thitruong", "/canhbao", "/ma", "/theodoi", "/caidat", "/trangthai", "/huongdan"]
BUTTON_COMMANDS = {t.lower(): c for t, c in zip([t for row in MENU for t in row], _MENU_COMMANDS, strict=True)}
# Nhãn menu cũ (bàn phím Telegram đã lưu trên máy người dùng vẫn gửi chữ cũ).
BUTTON_COMMANDS.update({"nhịp thị trường": "/thitruong", "cảnh báo": "/canhbao", "tra doanh nghiệp": "/ma",
                        "mã theo dõi": "/theodoi", "cài đặt nhận tin": "/caidat", "hướng dẫn": "/huongdan"})
# Lệnh cũ -> lệnh mới (chỉ đổi tên; /alerts on|off, /watch, /all vẫn xử lý như cũ trong telegram_cloud.command).
ALIASES = {"/market": "/thitruong", "/company": "/ma", "/status": "/caidat", "/watchlist": "/theodoi",
           "/help": "/huongdan", "/web": "/huongdan", "/website": "/huongdan", "/stop": "/dung", "/delete": "/dung"}
COMMANDS = [("thitruong", f"{ICON['market']} Nhịp thị trường VN30"), ("canhbao", f"{ICON['high']} Cảnh báo trong phiên"),
            ("ma", f"{ICON['company']} Thẻ một mã, ví dụ /ma HPG"), ("theodoi", f"{ICON['watch']} Mã đang theo dõi"),
            ("caidat", f"{ICON['settings']} Bật/tắt từng loại tin"), ("trangthai", f"{ICON['status']} Trạng thái dữ liệu"),
            ("huongdan", f"{ICON['help']} Hướng dẫn"), ("dung", f"{ICON['stop']} Hủy đăng ký")]


def normalize(text: str) -> str:
    """Chữ trên nút menu -> lệnh; giữ nguyên lệnh gõ tay."""
    return BUTTON_COMMANDS.get(text.strip().lower(), text.strip())


def split_command(text: str) -> tuple[str, str, str | None]:
    """-> (lệnh mới, tham số, lệnh cũ nếu người dùng gõ bí danh)."""
    parts = normalize(text).split(maxsplit=1)
    if not parts:
        return "", "", None
    cmd, arg = parts[0].split("@")[0].lower(), (parts[1].strip() if len(parts) > 1 else "")
    if cmd == "/alerts" and not arg:
        return "/canhbao", "", "/alerts"
    if cmd in ALIASES:
        return ALIASES[cmd], arg, cmd
    return cmd, arg, None


def alias_note(old: str | None, new: str) -> str:
    return f"\n\n<i>Lệnh mới: {new}</i>" if old else ""


# ------------------------------------------------------------------------------------------------ định dạng
def esc(x) -> str:
    return html.escape(str(x), quote=False)


def num(x, nd=2, signed=False) -> str:
    """Số kiểu Việt Nam: 1.234,56; dấu âm dùng ký tự −."""
    if x is None:
        return "—"
    s = f"{abs(x):,.{nd}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    if x < 0:
        return "−" + s
    return ("+" + s) if signed and x > 0 else s


def money(x) -> str:
    if x is None:
        return "—"
    a = abs(x)
    if a >= 1e12:
        return f"{num(a / 1e12, 1)} nghìn tỷ đồng"
    if a >= 1e9:
        return f"{num(a / 1e9, 1)} tỷ đồng"
    return f"{num(a / 1e6, 1)} triệu đồng"


def change(pct, pts=None) -> str:
    """Màu + mũi tên + dấu: không phụ thuộc riêng vào màu."""
    if pct is None:
        return "—"
    extra = f" ({num(pts, 2, signed=True)} điểm)" if pts is not None else ""
    if pct > 0:
        return f"{ICON['up']} ▲ {num(pct, 2, signed=True)}%{extra}"
    if pct < 0:
        return f"{ICON['down']} ▼ {num(pct, 2)}%{extra}"
    return f"{ICON['flat']} {num(0, 2)}%{extra}"


def _dt(iso: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(iso).astimezone(VN) if iso else None
    except (TypeError, ValueError):
        return None


def hm(iso: str | None) -> str:
    d = _dt(iso)
    return d.strftime("%H:%M") if d else "—"


def when(iso: str | None) -> str:
    d = _dt(iso)
    return d.strftime("%H:%M, %d/%m/%Y") if d else "chưa rõ thời điểm"


def sim_tag(meta: dict) -> str:
    return "[MÔ PHỎNG] " if meta.get("is_simulated") else ""


def data_state(meta: dict, now: float | None = None) -> str:
    """Trạng thái dữ liệu tính tại thời điểm trả lời; không gọi dữ liệu cũ là đang cập nhật."""
    now = time.time() if now is None else now
    if meta.get("is_simulated"):
        return "Dữ liệu MÔ PHỎNG"
    status = meta.get("data_status") or {}
    if status.get("state") == "error":
        return "Lỗi dữ liệu"
    if status.get("state") == "closed" or status.get("phase") in ("closed", "pre", "lunch"):
        return {"pre": "Chưa mở cửa", "lunch": "Nghỉ trưa"}.get(status.get("phase"), "Phiên đã kết thúc")
    d = _dt(meta.get("last_update"))
    if d is None:
        return "Chưa rõ thời điểm cập nhật"
    age = now - d.timestamp()
    return f"Dữ liệu chậm {age / 60:.0f} phút" if age > 180 else "Trong phiên"


def source_name(meta: dict) -> str:
    if meta.get("is_simulated"):
        return "Bộ mô phỏng"
    return (meta.get("source_label") or meta.get("source") or "—").split(" (")[0]


def footer(meta: dict, now: float | None = None) -> str:
    return f"<i>{esc(source_name(meta))} · {esc(data_state(meta, now))} · {DISCLAIMER}</i>"


def fit(head: list[str], items: list[str], tail: list[str], more: str = "mục", max_items: int = 15) -> str:
    """Ghép tin ≤ LIMIT ký tự, tối đa `max_items` dòng danh sách; phần còn lại ghi "… và N mục khác"."""
    shown = list(items[:max_items])
    while True:
        rest = len(items) - len(shown)
        body = shown + ([f"… và {rest} {more} khác."] if rest else [])
        text = "\n".join([*head, *body, *tail])
        if len(text) <= LIMIT or not shown:
            return text[:LIMIT]
        shown.pop()


def url_buttons(*pairs: tuple[str, str]) -> dict:
    return {"inline_keyboard": [[{"text": text, "url": url} for text, url in pairs]]}


def keyboard(*rows: list[tuple[str, str]]) -> dict:
    """Hàng nút inline; giá trị bắt đầu bằng https:// là nút URL, còn lại là callback_data (≤ 64 byte)."""
    return {"inline_keyboard": [[{"text": t, "url": v} if v.startswith("https://") else {"text": t, "callback_data": v}
                                 for t, v in row] for row in rows if row]}


def web_link(label: str, path: str = "") -> tuple[str, str]:
    return f"{ICON['link']} {label}", BASE + path


# ------------------------------------------------------------------------------------------------ mẫu tin
def _index_line(payload: dict) -> str | None:
    meta, row = payload.get("meta") or {}, (payload.get("index") or {}).get("row") or {}
    if row.get("value") is None:
        return None
    flat = row.get("no_change")
    counts = f"{row.get('advances', 0):.0f} mã tăng / {row.get('declines', 0):.0f} mã giảm" + (f" / {flat:.0f} đứng giá" if flat else "")
    return f"{esc(meta.get('index_code', 'VN30'))} {num(row['value'])} {change(row.get('pct_change'))} · {counts}"


def _foreign_line(payload: dict) -> str | None:
    fs = (payload.get("foreign") or {}).get("summary") or {}
    if fs.get("net_val") is None:
        return None
    return f"{ICON['foreign']} Khối ngoại {'mua ròng' if fs['net_val'] > 0 else 'bán ròng'} {money(fs['net_val'])} trong rổ"


def _top_sector(payload: dict) -> str | None:
    rows = [r for r in (payload.get("sectors") or {}).get("rows") or [] if r.get("contrib_pts") is not None]
    if not rows:
        return None
    top = max(rows, key=lambda r: abs(r["contrib_pts"]))
    return f"ngành đóng góp nhiều nhất: {esc(top['sector'])} {num(top['contrib_pts'], 1, signed=True)} điểm (ước lượng)"


def format_market(payload: dict, now: float | None = None) -> str:
    meta, pulse = payload.get("meta") or {}, payload.get("pulse") or {}
    code = esc(meta.get("index_code", "VN30"))
    head = f"{ICON['market']} <b>{sim_tag(meta)}Nhịp thị trường · {code}</b> · {when(meta.get('last_update'))}"
    if pulse.get("score") is None:
        return "\n".join([head, "Chưa đủ dữ liệu để tính điểm nhịp.", footer(meta, now)])
    lines = [head, f"{ICON['pulse']} Điểm nhịp <b>{num(pulse['score'], 1)}/100</b>: {esc(pulse.get('label', ''))}."]
    if (idx := _index_line(payload)):
        lines.append(idx)
    comps = sorted((c for c in pulse.get("components", []) if c.get("value") is not None), key=lambda c: -abs(c["value"]))
    if comps:
        up = [f"{esc(c['name'])} {num(c['value'], 2, signed=True)}" for c in comps if c["value"] > 0][:2]
        down = [f"{esc(c['name'])} {num(c['value'], 2, signed=True)}" for c in comps if c["value"] < 0][:2]
        parts = ([" và ".join(up) + " kéo điểm lên"] if up else []) + ([" và ".join(down) + " kéo xuống"] if down else [])
        lines.append("<b>Căn cứ:</b> " + "; ".join(parts) + ". Thành phần chuẩn hóa từ −1 đến +1, 0 là trung tính.")
    context = [x for x in (_foreign_line(payload), _top_sector(payload)) if x]
    if context:
        lines.append("<b>Bối cảnh:</b> " + " · ".join(context) + ".")
    if pulse.get("missing"):
        names = {c["key"]: c["name"] for c in pulse.get("components", [])}
        lines.append("Thiếu dữ liệu: " + esc(", ".join(names.get(k, k) for k in pulse["missing"])) + " (điểm tính trên phần còn lại).")
    lines.append(footer(meta, now))
    return "\n".join(lines)


def describe(a: dict) -> str:
    """Câu mô tả cảnh báo bằng lời từ trường gốc (rule, value, threshold); con số z để dành cho dòng "Căn cứ"."""
    rule, v, thr = a.get("rule"), a.get("value"), a.get("threshold")
    if rule == "volume_spike":
        if v is not None and thr is not None and thr < 3.5:
            return f"khớp lệnh gấp {num(v, 1)} lần mức thường thấy cùng khung giờ"
        return "khối lượng khớp cao bất thường so với trước đó trong phiên"
    if rule == "spread_blowout":
        return "độ chênh giá mua-bán giãn rộng bất thường"
    if rule == "price_jump":
        return "giá biến động đột ngột trong một phút" + ("" if v is None else (", theo chiều tăng" if v > 0 else ", theo chiều giảm"))
    if rule == "foreign_flow":
        return "khối ngoại " + ("mua" if (v or 0) > 0 else "bán") + " ròng cao bất thường"
    if rule == "book_pressure":
        return "mất cân bằng sổ lệnh kéo dài, bên " + ("mua" if (v or 0) > 0 else "bán") + " dày hơn"
    if rule == "near_limit":
        return "giá sát " + ("trần" if (v or 0) > 0 else "sàn")
    return a.get("message") or a.get("rule_name") or "cảnh báo"


def sym_link(symbol: str) -> str:
    """Mã bấm được: Telegram gửi "/start ma_<MÃ>" và bot trả thẻ mã (không tạo đăng ký)."""
    if not SYMBOL.fullmatch(symbol or ""):
        return esc(symbol or "")
    return f'<a href="https://t.me/{BOT}?start=ma_{symbol}">{symbol}</a>'


def alert_line(a: dict) -> str:
    return f"{SEV_ICON.get(a.get('severity'), ICON['low'])} {hm(a.get('t'))} <b>{sym_link(a.get('symbol', ''))}</b> · {esc(describe(a))}"


def format_alert_list(payload: dict, now: float | None = None, scope: str = "CAO") -> str:
    """scope: "CAO" = chỉ mức cao; "TB" = từ trung bình trở lên."""
    meta, al = payload.get("meta") or {}, payload.get("alerts") or {}
    head = [f"{ICON['high']} <b>{sim_tag(meta)}Cảnh báo trong phiên · {esc(meta.get('index_code', 'VN30'))}</b> · {hm(meta.get('last_update'))}"]
    if not al.get("total"):
        return "\n".join([*head, "Chưa ghi nhận cảnh báo nào trong phiên.", footer(meta, now)])
    sev = al.get("by_severity") or {}
    head.append(f"{al['total']} lượt: {ICON['high']} {sev.get('CAO', 0)} mức cao · {ICON['mid']} {sev.get('TRUNG BÌNH', 0)} trung bình · {ICON['low']} {sev.get('THẤP', 0)} thấp.")
    keep = {"CAO"} if scope == "CAO" else {"CAO", "TRUNG BÌNH"}
    items = sorted((a for a in al.get("items", []) if a.get("severity") in keep), key=lambda a: a.get("t", ""), reverse=True)
    head.append("Mức cao gần nhất:" if scope == "CAO" else "Từ trung bình trở lên, gần nhất:")
    if not items:
        head.append("Không có cảnh báo ở mức này.")
    tail = ["Bấm vào mã để xem thẻ mã. Cảnh báo là quan sát cần xem lại, chưa cho biết nguyên nhân hay hướng giá.", footer(meta, now)]
    return fit(head, [alert_line(a) for a in items], tail, "cảnh báo")


format_alerts = format_alert_list  # tên cũ


def alert_list_keyboard(scope: str = "CAO") -> dict:
    return keyboard([(("✓ " if scope == "CAO" else "") + f"{ICON['high']} Chỉ mức cao", "cl:CAO"),
                     (("✓ " if scope == "TB" else "") + f"{ICON['mid']} Từ trung bình", "cl:TB")],
                    [web_link("Mở trên web", "/thi-truong?tab=canh-bao")])


def _rows(payload: dict, key: str) -> dict[str, dict]:
    return {r.get("symbol"): r for r in (payload.get(key) or {}).get("rows") or [] if r.get("symbol")}


def _basis(a: dict) -> str | None:
    """Câu "Căn cứ" diễn giải giá trị và ngưỡng của cảnh báo bằng lời."""
    v, thr, rule = a.get("value"), a.get("threshold"), a.get("rule")
    if v is None or thr is None:
        return None
    if rule == "volume_spike" and thr < 3.5:
        return f"vượt ngưỡng cảnh báo {num(thr, 1)} lần mức thường thấy"
    if rule == "near_limit":
        return f"giá đã đi {num(abs(v) * 100, 0)}% khoảng từ tham chiếu đến giá {'trần' if v > 0 else 'sàn'} (ngưỡng {num(thr * 100, 0)}%)"
    if rule == "book_pressure":
        return f"OBI₃ {num(v, 2, signed=True)} vượt ngưỡng ±{num(thr, 2)} liên tục 3 thanh 1 phút"
    if abs(v) >= 50:  # thang điểm z bị chặn ở 50
        return f"điểm z bền vững vượt 50 (ngưỡng {num(thr, 1)}): lệch rất xa so với mức thường thấy trong phiên"
    level = "rất xa" if abs(v) >= 6 else "đáng kể"
    return f"điểm z bền vững {num(v, 1, signed=True)} so với ngưỡng {num(thr, 1)}: lệch {level} so với mức thường thấy trong phiên"


def format_alert_push(alerts: list[dict], payload: dict, now: float | None = None) -> str:
    """Tin cảnh báo tự động của một đợt: một cảnh báo thì chi tiết, nhiều cảnh báo thì gom thành danh sách."""
    meta = payload.get("meta") or {}
    alerts = sorted(alerts, key=lambda a: a.get("t", ""), reverse=True)
    if len(alerts) > 1:
        head = [f"{ICON['high']} <b>{sim_tag(meta)}{len(alerts)} cảnh báo mức cao mới</b> · {hm(alerts[0].get('t'))}"]
        tail = [x for x in [("<b>Bối cảnh:</b> " + _index_line(payload)) if _index_line(payload) else None,
                            "Bấm vào mã để xem thẻ mã.", footer(meta, now)] if x]
        return fit(head, [alert_line(a) for a in alerts], tail, "cảnh báo", max_items=10)
    a = alerts[0]
    sym = esc(a.get("symbol", ""))
    book = _rows(payload, "book").get(a.get("symbol"), {})
    title = RULE_TITLE.get(a.get("rule"), a.get("rule_name") or "Cảnh báo")
    lines = [f"{SEV_ICON.get(a.get('severity'), ICON['high'])} <b>{sim_tag(meta)}{esc(title)} · {sym}</b> · {hm(a.get('t'))}"]
    phrase = describe(a)
    main = f"{sym} {esc(phrase)}" if phrase.startswith("khớp lệnh") else f"{sym}: {esc(phrase)}"
    if book.get("last") is not None:
        main += f"; giá {num(book['last'], 0)} {change(book.get('pct_change'))}"
    lines.append(main + ".")
    basis = [x for x in [_basis(a)] if x]
    obi = book.get("obi3")
    if obi is not None and abs(obi) >= 0.2 and a.get("rule") != "book_pressure":
        basis.append(f"sổ lệnh nghiêng về bên {'mua' if obi > 0 else 'bán'} (OBI₃ {num(obi, 2, signed=True)})")
    if basis:
        lines.append("<b>Căn cứ:</b> " + "; ".join(basis) + ".")
    if (idx := _index_line(payload)):
        lines.append("<b>Bối cảnh:</b> " + idx + ".")
    lines.append(footer(meta, now))
    return "\n".join(lines)


def alert_push_keyboard(alerts: list[dict]) -> dict:
    if len(alerts) == 1:
        s = alerts[0].get("symbol", "")
        return keyboard([(f"{ICON['company']} Thẻ {s}", f"v:ma:{s}"), web_link(f"Xem {s} trên NeoPulse", f"/doanh-nghiep/{s}")])
    return keyboard([web_link("Xem toàn bộ cảnh báo", "/thi-truong?tab=canh-bao")])


def format_card(symbol: str, entry: dict, payload: dict | None, now: float | None = None) -> str:
    meta = (payload or {}).get("meta") or {}
    head = f"{ICON['company']} <b>{sim_tag(meta)}{esc(symbol)} · {esc(entry.get('name') or symbol)}</b>"
    book = _rows(payload or {}, "book").get(symbol)
    tags = [esc(x) for x in (entry.get("exchange"), entry.get("industry")) if x] + (["Trong rổ VN30"] if book else [])
    lines = [head] + ([" · ".join(tags)] if tags else [])
    if not book:
        lines.append("Giá trong phiên chỉ có cho các mã thuộc rổ VN30 đang theo dõi. Hồ sơ doanh nghiệp có báo cáo tài chính, sự kiện và tin tức.")
        return "\n".join(lines + [f"<i>{DISCLAIMER}</i>"])
    price = f"Giá {num(book['last'], 0)} {change(book.get('pct_change'))}" if book.get("last") is not None else None
    value = f"Giá trị khớp {money(book['total_value'])}" if book.get("total_value") else None
    if price or value:
        lines.append(" · ".join(x for x in (price, value) if x) + f" · lúc {hm(meta.get('last_update'))}")
    fr = _rows(payload, "foreign").get(symbol)
    if fr and fr.get("net") is not None:
        share = f" (tỷ trọng {num(fr['participation'] * 100, 1)}% giá trị khớp)" if fr.get("participation") is not None else ""
        lines.append(f"{ICON['foreign']} Khối ngoại {'mua ròng' if fr['net'] > 0 else 'bán ròng'} {money(fr['net'])}{share}")
    if book.get("obi3") is not None:
        side = "bên mua dày hơn" if book["obi3"] > 0 else "bên bán dày hơn" if book["obi3"] < 0 else "hai bên cân bằng"
        lines.append(f"Mất cân bằng sổ lệnh {num(book['obi3'], 2, signed=True)}: {side} trên 3 mức giá tốt nhất.")
    mine = sorted((a for a in (payload.get("alerts") or {}).get("items", []) if a.get("symbol") == symbol), key=lambda a: a.get("t", ""), reverse=True)
    if mine:
        lines.append(f"{SEV_ICON.get(mine[0].get('severity'), ICON['low'])} {len(mine)} cảnh báo trong phiên, gần nhất {hm(mine[0].get('t'))}: {esc(describe(mine[0]))}.")
    else:
        lines.append("Chưa có cảnh báo của mã này trong phiên.")
    return "\n".join(lines + [footer(meta, now)])


def card_keyboard(symbol: str) -> dict:
    return keyboard([(f"{ICON['watch']} Theo dõi / bỏ theo dõi {symbol}", f"c:{symbol}"), web_link(f"Hồ sơ {symbol}", f"/doanh-nghiep/{symbol}")])


def format_status(payload: dict | None, now: float | None = None) -> str:
    if not payload:
        return f"{ICON['status']} <b>Trạng thái dữ liệu</b>\nChưa lấy được dữ liệu từ website. Vui lòng thử lại sau ít phút."
    meta = payload.get("meta") or {}
    lines = [f"{ICON['status']} <b>{sim_tag(meta)}Trạng thái dữ liệu</b>",
             f"Nguồn: {esc(meta.get('source_label') or source_name(meta))}",
             f"Trạng thái: {esc(data_state(meta, now))}",
             f"Dữ liệu đến: {when(meta.get('last_update'))} · phiên {esc('/'.join(reversed(str(meta.get('trading_date', '')).split('-'))))}"]
    if meta.get("snapshot_label") and not meta.get("is_simulated"):
        lines.append(f"Loại bản dữ liệu: {esc(meta['snapshot_label'])}")
    lines.append("Nhịp gửi tin: khoảng mỗi phút trong giờ giao dịch khi bộ ghi dữ liệu chạy; khoảng 5 phút một lần ngoài giờ. "
                 "Số liệu trên bot lấy từ cùng nguồn với website.")
    return "\n".join(lines + [f"<i>{DISCLAIMER}</i>"])


def _digest(payload: dict, now: float | None, title: str) -> str:
    meta, pulse = payload.get("meta") or {}, payload.get("pulse") or {}
    row = (payload.get("index") or {}).get("row") or {}
    lines = [f"{ICON['market']} <b>{sim_tag(meta)}{title} · {esc(meta.get('index_code', 'VN30'))}</b> · {when(meta.get('last_update'))}"]
    if row.get("value") is not None:
        lims = f" · {ICON['ceil']} {row.get('n_ceiling', 0):.0f} trần · {ICON['floor']} {row.get('n_floor', 0):.0f} sàn" if row.get("n_ceiling") is not None else ""
        lines.append(_index_line(payload) + lims)
    if pulse.get("score") is not None:
        lines.append(f"{ICON['pulse']} Điểm nhịp {num(pulse['score'], 1)}/100: {esc(pulse.get('label', ''))}.")
    fr = sorted(_rows(payload, "foreign").values(), key=lambda r: r.get("net") or 0)
    if (fl := _foreign_line(payload)):
        ends = f"; mua ròng nhiều nhất {sym_link(fr[-1]['symbol'])}, bán ròng nhiều nhất {sym_link(fr[0]['symbol'])}" if len(fr) >= 2 else ""
        lines.append(fl + ends + ".")
    fu = (payload.get("futures") or {})
    st = fu.get("state") or {}
    if fu.get("available") and st.get("basis") is not None:
        dtm = f", còn {st['dtm']:.0f} ngày tới đáo hạn" if st.get("dtm") is not None else ""
        lines.append(f"{ICON['deriv']} {esc(st.get('symbol', 'HĐTL'))}: chênh lệch cơ sở {num(st['basis'], 2, signed=True)} điểm{dtm}.")
    al = payload.get("alerts") or {}
    if al.get("total"):
        hot = {}
        for a in al.get("items", []):
            if a.get("severity") == "CAO":
                hot[a["symbol"]] = hot.get(a["symbol"], 0) + 1
        top = ", ".join(sym_link(s) for s, _ in sorted(hot.items(), key=lambda kv: -kv[1])[:3])
        lines.append(f"{ICON['high']} {al['total']} cảnh báo ({(al.get('by_severity') or {}).get('CAO', 0)} mức cao)" + (f", nhiều nhất ở {top}." if top else "."))
    return "\n".join(lines + [footer(meta, now)])


def format_open_digest(payload: dict, now: float | None = None) -> str:
    return _digest(payload, now, "Tóm tắt đầu phiên")


def format_close_digest(payload: dict, now: float | None = None) -> str:
    d = _dt((payload.get("meta") or {}).get("last_update"))
    return _digest(payload, now, "Tổng kết phiên" + (f" {d.strftime('%d/%m/%Y')}" if d else ""))


BULLETIN_MAX = {"news": 8, "world": 5, "laws": 5}
BULLETIN_HEAD = {"news": (ICON["company"], "Doanh nghiệp"), "world": (ICON["world"], "Quốc tế"),
                 "laws": (ICON["laws"], "Chính sách, pháp luật")}


def format_bulletin(kind: str, items: list[dict], start: float, end: float, watched: list[str], basket: set[str]) -> str:
    """Bản tin gộp đầu/cuối phiên: tin doanh nghiệp (mã đang theo dõi, rồi VN30, lên trước), quốc tế, chính sách."""
    title = "Bản tin đầu phiên" if kind == "open" else "Bản tin cuối phiên"
    a, b = datetime.fromtimestamp(start, VN), datetime.fromtimestamp(end, VN)
    lines = [f"{ICON['news']} <b>{title} · {b.strftime('%d/%m/%Y')}</b>",
             f"Tin đáng chú ý từ {a.strftime('%H:%M %d/%m')} đến {b.strftime('%H:%M %d/%m')}."]
    mine = set(watched)
    for cat, (icon, name) in BULLETIN_HEAD.items():
        rows = sorted((n for n in items if n["category"] == cat),
                      key=lambda n: (not set(n["symbols"]) & mine, not set(n["symbols"]) & basket, -n["at"]))
        if not rows:
            continue
        lines += ["", f"{icon} <b>{name}</b>"]
        for n in rows[:BULLETIN_MAX[cat]]:
            tags = " ".join(("⭐" if sym in mine else "") + sym_link(sym) for sym in n["symbols"][:3])
            link = html.escape(n["link"], quote=True)
            when = datetime.fromtimestamp(n["at"], VN).strftime("%H:%M %d/%m")
            lines.append(f"• {'<b>' + tags + '</b> · ' if tags else ''}<a href=\"{link}\">{esc(n['title'])}</a> · {esc(n['host'])} {when}")
        if len(rows) > BULLETIN_MAX[cat]:
            lines.append(f"… và {len(rows) - BULLETIN_MAX[cat]} tin khác")
    if len(lines) == 2:
        lines.append("Không có tin mới đáng chú ý trong khoảng này.")
    if any(n["category"] == "laws" for n in items):
        lines += ["", "<i>Tin chính sách có thể là dự thảo hoặc đề xuất; xem hiệu lực trong văn bản gốc.</i>"]
    text = "\n".join(lines + [f"<i>Nguồn: CafeF, Báo Chính phủ · Bấm tiêu đề để đọc bài gốc · {DISCLAIMER}</i>"])
    return text if len(text) <= LIMIT else text[:LIMIT].rsplit("\n•", 1)[0] + f"\n<i>{DISCLAIMER}</i>"


def settings_text(user: dict) -> str:
    lines = [f"{ICON['settings']} <b>Cài đặt nhận tin</b>", "Bấm để bật/tắt từng loại tin:"]
    lines += [f"{'✅' if user.get(k) else '▫️'} {name}" for k, name in TOPICS.items()]
    lines.append("Tin tức gửi gộp hai lượt mỗi ngày giao dịch: đầu phiên (08:30) và cuối phiên (15:00).")
    lines.append("Cảnh báo chỉ gửi khi phát sinh sau lúc bạn bật. Đổi mã theo dõi: /theodoi.")
    return "\n".join(lines)


def settings_keyboard(user: dict) -> dict:
    rows = [[(f"{'✅' if user.get(k) else '▫️'} {name}", f"t:{k}")] for k, name in TOPICS.items()]
    return keyboard(*rows, [(f"{ICON['watch']} Mã theo dõi", "v:theodoi"), (f"{ICON['stop']} Hủy đăng ký", "stop")])


def watch_text(user: dict) -> str:
    syms = user.get("symbols") or []
    scope = ", ".join(esc(s) for s in syms) if syms else "cả rổ VN30 đang theo dõi"
    return (f"{ICON['watch']} <b>Mã theo dõi</b>\nĐang theo dõi: {scope}.\n"
            "Cảnh báo và tin doanh nghiệp chỉ gửi cho các mã này. Thêm mã: /theodoi HPG hoặc bấm ⭐ trên thẻ mã (/ma HPG). "
            "Bấm một mã dưới đây để bỏ theo dõi.")


def watch_keyboard(user: dict) -> dict:
    syms = user.get("symbols") or []
    rows = [[(f"✖ {s}", f"w-:{s}") for s in syms[i:i + 4]] for i in range(0, len(syms), 4)]
    return keyboard(*rows, [("Theo dõi cả rổ VN30", "wall")] if syms else [], [(f"{ICON['settings']} Cài đặt nhận tin", "v:caidat")])


def subscribe_prompt() -> tuple[str, dict]:
    return ("Bạn chưa đăng ký nhận tin. Đăng ký mặc định chỉ bật cảnh báo mức cao; bạn đổi được trong ⚙️ Cài đặt.",
            keyboard([("✅ Đăng ký nhận cảnh báo", "sub")]))


def start_text(user: dict) -> str:
    on = [name.lower() for k, name in TOPICS.items() if user.get(k)]
    return (f"✅ <b>Đã đăng ký NeoPulse Radar.</b>\nĐang nhận: {', '.join(on) or 'chưa bật loại tin nào'}. "
            f"Chỉ gửi tin phát sinh sau lúc bạn bật; đổi trong {ICON['settings']} Cài đặt.\n\n" + HELP)


HELP = (
    f"{ICON['help']} <b>NeoPulse Radar · Hướng dẫn</b>\n"
    "Bot đọc nhanh kết quả NeoPulse đã tính và gửi tin theo lựa chọn của bạn; phân tích chi tiết nằm trên website.\n\n"
    "<b>Xem ngay</b> (không cần đăng ký)\n"
    f"{ICON['market']} /thitruong · nhịp thị trường VN30\n"
    f"{ICON['high']} /canhbao · cảnh báo trong phiên\n"
    f"{ICON['company']} /ma HPG · thẻ một mã (gõ mã cũng được)\n\n"
    "<b>Cá nhân</b>\n"
    f"{ICON['watch']} /theodoi · xem, thêm, bớt mã theo dõi\n"
    f"{ICON['settings']} /caidat · bật/tắt cảnh báo, bản tin tin tức (08:30 và 15:00), tóm tắt đầu và cuối phiên\n\n"
    "<b>Khác</b>\n"
    f"{ICON['status']} /trangthai · dữ liệu đang trong phiên, đã kết thúc hay MÔ PHỎNG\n"
    f"{ICON['stop']} /dung · hủy và xóa đăng ký\n\n"
    "Tin gửi theo đợt: khoảng mỗi phút trong giờ giao dịch khi bộ ghi dữ liệu chạy, khoảng 5 phút một lần ngoài giờ.\n"
    f"Website: {BASE}\n<i>Công cụ phân tích học thuật. {DISCLAIMER}.</i>"
)


# ------------------------------------------------------------------------------------------------ trả lời chỉ đọc
def readonly_answer(text: str, catalog: dict[str, dict], load_payload) -> tuple[str, dict | None] | None:
    """Trả lời yêu cầu chỉ đọc (không đổi đăng ký). None = để `telegram_cloud.command` xử lý.

    `load_payload()` trả payload NeoPulse đã tính (hoặc ném lỗi); chỉ gọi khi cần.
    """
    cmd, arg, old = split_command(text)
    if not cmd:
        return None
    if cmd == "/start" and arg.startswith("ma_"):  # bấm mã trong tin nhắn
        cmd, arg, old = "/ma", arg[3:].upper(), None
    note = alias_note(old, cmd)

    def payload_or_none():
        try:
            return load_payload()
        except Exception:  # noqa: BLE001 - nguồn lỗi thì báo rõ, không bịa số
            return None

    unavailable = ("Chưa lấy được dữ liệu thị trường từ website. Nguồn có thể đang cập nhật; vui lòng thử lại sau ít phút.",
                   keyboard([web_link("Mở NeoPulse")]))
    if cmd == "/huongdan":
        return HELP + note, MAIN_KEYBOARD
    if cmd in {"/thitruong", "/canhbao", "/trangthai"} and not arg:
        payload = payload_or_none()
        if cmd == "/trangthai":
            return format_status(payload) + note, keyboard([web_link("Mở NeoPulse")])
        if payload is None:
            return unavailable
        if cmd == "/thitruong":
            return format_market(payload) + note, keyboard([(f"{ICON['high']} Xem cảnh báo", "v:canhbao"), web_link("Mở trên web", "/thi-truong?tab=tong-quan")])
        return format_alert_list(payload) + note, alert_list_keyboard("CAO")
    symbol = arg.upper() if cmd == "/ma" else (cmd.upper() if not cmd.startswith("/") and not arg else "")
    if cmd == "/ma" and not arg:
        return (f"{ICON['company']} Gửi mã cổ phiếu để xem thẻ mã, ví dụ: <b>HPG</b> hoặc /ma HPG." + note,
                keyboard([web_link("Danh sách doanh nghiệp", "/doanh-nghiep")]))
    if symbol and SYMBOL.fullmatch(symbol):
        entry = catalog.get(symbol)
        if entry is None:
            if cmd == "/ma":
                return f"Không tìm thấy mã {esc(symbol)} trong danh mục HOSE/HNX/UPCoM. Kiểm tra lại mã, ví dụ: HPG.", None
            return None
        return format_card(symbol, entry, payload_or_none()) + note, card_keyboard(symbol)
    return None


def readonly_callback(data: str, catalog: dict[str, dict], load_payload) -> tuple[str, str, dict | None] | None:
    """Nút chỉ đọc. -> ("send" | "edit", text, markup) hoặc None nếu không phải nút chỉ đọc."""
    if data.startswith("v:ma:"):
        answer = readonly_answer("/ma " + data[5:], catalog, load_payload)
        return ("send", *answer) if answer else None
    if data in {"v:canhbao", "v:thitruong"}:
        answer = readonly_answer("/" + data[2:], catalog, load_payload)
        return ("send", *answer) if answer else None
    if data in {"cl:CAO", "cl:TB"}:
        try:
            payload = load_payload()
        except Exception:  # noqa: BLE001
            return "edit", "Chưa lấy được dữ liệu thị trường. Vui lòng thử lại sau ít phút.", None
        return "edit", format_alert_list(payload, scope=data[3:]), alert_list_keyboard(data[3:])
    return None


def markup_for(cmd: str) -> dict | None:
    """Bàn phím mặc định đi kèm câu trả lời của phần đăng ký khi lệnh không tự chọn nút."""
    return MAIN_KEYBOARD if cmd in {"/start", "/huongdan", "/dung"} or not cmd.startswith("/") else None
