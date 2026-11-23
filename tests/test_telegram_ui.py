import importlib.util
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from neopulse.analytics import telegram_ui as ui
from neopulse.analytics.telegram_cloud import command

VN = timezone(timedelta(hours=7))
CATALOG = {"MWG": {"symbol": "MWG", "name": "Công ty Cổ phần Đầu tư Thế Giới Di Động", "exchange": "HOSE", "industry": "Bán lẻ"}}


def payload(state="closed", phase="closed", last=datetime(2026, 11, 23, 15, 5, tzinfo=VN)):
    return {
        "meta": {"index_code": "VN30", "source_label": "SSI FastConnect (dữ liệu thật)", "is_simulated": False,
                 "last_update": last.isoformat(), "data_status": {"state": state, "phase": phase, "reason": "Phiên đã kết thúc."}},
        "pulse": {"score": 53.2, "label": "Trung tính - giằng co", "missing": ["liquidity"],
                  "components": [{"key": "breadth", "name": "Độ rộng thị trường", "value": 0.12},
                                 {"key": "momentum", "name": "Động lượng chỉ số", "value": 0.2355},
                                 {"key": "liquidity", "name": "Thanh khoản", "value": None}]},
        "index": {"row": {"value": 1791.12, "pct_change": 0.24, "advances": 14, "declines": 11}},
        "foreign": {"summary": {"net_val": -378.6e9}},
        "alerts": {"total": 3, "by_severity": {"CAO": 2, "TRUNG BÌNH": 1, "THẤP": 0},
                   "items": [{"t": "2026-11-23T14:45:00+07:00", "symbol": "VRE", "severity": "CAO", "message": "Khối lượng cao gấp 23,4 lần"},
                             {"t": "2026-11-23T10:05:00+07:00", "symbol": "BID", "severity": "CAO", "message": "Giá biến động đột ngột"},
                             {"t": "2026-11-23T11:00:00+07:00", "symbol": "FPT", "severity": "TRUNG BÌNH", "message": "x"}]},
    }


def test_menu_buttons_map_to_commands():
    assert ui.normalize("Nhịp thị trường") == "/market"
    assert ui.normalize(" hướng dẫn ") == "/help"
    assert ui.normalize("/watch MWG") == "/watch MWG"
    assert [b["text"] for row in ui.MAIN_KEYBOARD["keyboard"] for b in row] == [t for row in ui.MENU for t in row]


def test_market_brief_reads_payload_and_labels_state():
    text, markup = ui.readonly_answer("Nhịp thị trường", CATALOG, payload)
    assert "Điểm nhịp 53,2/100" in text and "1.791,12 điểm (+0,24%)" in text
    assert "Phiên đã kết thúc" in text and "15:05:00, 23/11/2026" in text
    assert "Khối ngoại bán ròng 378,6 tỷ đồng" in text and "Thiếu dữ liệu: Thanh khoản" in text
    assert "thời gian thực" not in text and "realtime" not in text.lower()
    assert markup["inline_keyboard"][0][0]["url"].startswith(ui.BASE)


def test_old_live_data_is_not_called_fresh():
    last = datetime(2026, 11, 23, 10, 0, tzinfo=VN)
    p = payload("fresh", "open", last)
    text = ui.format_market(p, now=(last + timedelta(minutes=10)).timestamp())
    assert "chưa cập nhật trong 10 phút" in text
    assert "vừa cập nhật" in ui.format_market(p, now=(last + timedelta(seconds=30)).timestamp())


def test_source_error_reports_without_numbers():
    def boom():
        raise httpx.ConnectError("down")
    text, _ = ui.readonly_answer("/market", CATALOG, boom)
    assert "Chưa lấy được dữ liệu" in text and not any(ch.isdigit() for ch in text.split("Website")[0])


def test_alert_summary_and_toggle_falls_through():
    text, _ = ui.readonly_answer("/alerts", CATALOG, payload)
    assert "2 mức cao" in text and text.index("VRE") < text.index("BID") and "FPT" not in text
    assert ui.readonly_answer("/alerts on", CATALOG, payload) is None   # bật/tắt thuộc phần đăng ký


def test_company_lookup_valid_invalid_and_plain_text():
    text, markup = ui.readonly_answer("mwg", CATALOG, payload)
    assert "Bán lẻ" in text and markup["inline_keyboard"][0][0]["url"] == ui.BASE + "/doanh-nghiep/MWG"
    assert "Không tìm thấy mã ZZZ" in ui.readonly_answer("/company ZZZ", CATALOG, payload)[0]
    assert ui.readonly_answer("hello", CATALOG, payload) is None
    assert ui.readonly_answer("../etc", CATALOG, payload) is None
    assert "ví dụ" in ui.readonly_answer("Tra doanh nghiệp", CATALOG, payload)[0]


def msg(text):
    return {"message": {"chat": {"type": "private", "id": 7}, "text": text, "date": 100}}


def test_help_and_menu_do_not_subscribe_and_start_names_topics():
    s = {"users": {}}
    assert command(s, msg("/help"), {"MWG"}, 100)[1] == ui.HELP and s["users"] == {}
    assert "chưa đăng ký" in command(s, msg("Mã theo dõi"), {"MWG"}, 100)[1] and s["users"] == {}
    start = command(s, msg("/start news_laws"), {"MWG"}, 100)[1]
    assert "Đang nhận: tin doanh nghiệp, tin chính sách" in start and not s["users"]["7"]["alerts"]
    command(s, msg("/watch MWG"), {"MWG"}, 101)
    assert "Mã theo dõi: MWG" in command(s, msg("Mã theo dõi"), {"MWG"}, 102)[1]
    assert "rổ VN30" in command(s, msg("/all"), {"MWG"}, 103)[1]


def load_webhook():
    path = Path(__file__).resolve().parents[1] / "web/api/telegram.py"
    spec = importlib.util.spec_from_file_location("tg_webhook", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call_webhook(mod, update, monkeypatch, handler):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "hook")
    real = httpx.Client
    monkeypatch.setattr(mod.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler)))
    h = object.__new__(mod.handler)
    body = json.dumps(update).encode()
    h.headers = {"X-Telegram-Bot-Api-Secret-Token": "hook", "Content-Length": str(len(body))}
    h.rfile, h.wfile, out = io.BytesIO(body), io.BytesIO(), {}
    h.send_response = lambda status: out.setdefault("status", status)
    h.send_header = h.end_headers = lambda *a: None
    h.do_POST()
    return out["status"], json.loads(h.wfile.getvalue())


def test_webhook_answers_market_without_touching_subscriptions(monkeypatch):
    serverpkg = Path(__file__).resolve().parents[1] / "web/serverpkg/data/catalog.json"
    if not serverpkg.exists():
        pytest.skip("cần chạy tools/prepare_web_python.py")
    mod = load_webhook()
    seen = []

    def handler(r):
        seen.append(str(r.url))
        if str(r.url) == ui.BASE + "/api/data":
            return httpx.Response(200, json={"payload": payload()})
        raise AssertionError("không được gọi Redis cho câu hỏi chỉ đọc")

    status, body = call_webhook(mod, {"update_id": 1, **msg("Nhịp thị trường")}, monkeypatch, handler)
    assert status == 200 and body["method"] == "sendMessage" and "Điểm nhịp" in body["text"]
    assert seen == [ui.BASE + "/api/data"]
    status, body = call_webhook(mod, {"update_id": 2, **msg("MWG")}, monkeypatch, handler)
    assert body["reply_markup"]["inline_keyboard"][0][0]["url"].endswith("/doanh-nghiep/MWG")
