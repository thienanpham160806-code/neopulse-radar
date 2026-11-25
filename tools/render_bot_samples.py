"""In 5 mẫu tin bot Telegram ra docs/bot_samples.md từ một payload MÔ PHỎNG.

Cách tạo payload bằng mã hiện tại (không đụng dữ liệu thật):
    NEOPULSE_MODE=sim NEOPULSE_DB_PATH=<tệp tạm>.sqlite neopulse simulate
    NEOPULSE_MODE=sim NEOPULSE_DB_PATH=<tệp tạm>.sqlite neopulse export-web --source sim --out <thư mục>
    python tools/render_bot_samples.py <thư mục>/latest.json
Mặc định dùng web/public/sample/latest.json.

Dùng đúng các hàm định dạng của bot (telegram_ui) nên tài liệu luôn khớp mã. Không gọi mạng, không gửi tin.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from neopulse.analytics import telegram_ui as ui

ROOT = Path(__file__).resolve().parents[1]


def buttons(markup):
    rows = (markup or {}).get("inline_keyboard", [])
    return "  ".join(f"[{b['text']}]" for row in rows for b in row)


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web/public/sample/latest.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    assert payload["meta"]["is_simulated"], "Mẫu tin chỉ dựng từ dữ liệu MÔ PHỎNG"
    now = datetime.fromisoformat(payload["meta"]["last_update"]).timestamp()
    items = payload["alerts"]["items"]
    high = sorted((a for a in items if a["severity"] == "CAO"), key=lambda a: a["t"], reverse=True)
    in_book = {r["symbol"] for r in payload["book"]["rows"]}
    one = next((a for a in high if a["symbol"] in in_book), high[0])
    card_sym = one["symbol"]
    catalog = json.loads((ROOT / "web/reference/catalog.json").read_text(encoding="utf-8"))
    entry = next((r for r in catalog["symbols"] if r["symbol"] == card_sym), {"symbol": card_sym})
    samples = [
        ("Nhịp thị trường (/thitruong)", ui.format_market(payload, now), ui.keyboard([("🚨 Xem cảnh báo", "v:canhbao"), ui.web_link("Mở trên web")])),
        ("Danh sách cảnh báo (/canhbao)", ui.format_alert_list(payload, now), ui.alert_list_keyboard("CAO")),
        ("Một cảnh báo tự động", ui.format_alert_push([one], payload, now), ui.alert_push_keyboard([one])),
        (f"Thẻ mã (/ma {card_sym})", ui.format_card(card_sym, entry, payload, now), ui.card_keyboard(card_sym)),
        ("Tổng kết cuối phiên", ui.format_close_digest(payload, now), ui.keyboard([ui.web_link("Xem bản tin phiên trên web")])),
    ]
    out = ["# Mẫu tin bot Telegram", "",
           "Sinh bằng `tools/render_bot_samples.py` từ payload **MÔ PHỎNG** (bộ mô phỏng `neopulse simulate`, xuất bằng mã hiện tại); "
           "số liệu không phải dữ liệu thị trường. Tin thật gửi dạng HTML (`parse_mode=HTML`); dưới đây giữ nguyên thẻ `<b>`, `<i>`. "
           "Dòng `[…]` cuối mỗi mẫu là các nút bấm đi kèm.", ""]
    for title, text, markup in samples:
        out += [f"## {title}", "", "```text", text, buttons(markup), "```", ""]
    (ROOT / "docs/bot_samples.md").write_text("\n".join(out), encoding="utf-8")
    print("Đã ghi docs/bot_samples.md")


if __name__ == "__main__":
    main()
