import importlib.util
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from neopulse.analytics import telegram_cloud as tc
from neopulse.analytics import telegram_ui as ui

VN = timezone(timedelta(hours=7))
CATALOG = {"HPG": {"symbol": "HPG", "name": "Công ty Cổ phần Tập đoàn Hòa Phát", "exchange": "HOSE", "industry": "Tài nguyên cơ bản"},
           "DBC": {"symbol": "DBC", "name": "Dabaco", "exchange": "HOSE", "industry": "Thực phẩm"}}
VALID = set(CATALOG)


def payload(sim=False, state="closed", phase="closed", last=datetime(2026, 11, 23, 15, 5, tzinfo=VN), n_alerts=3):
    items = [{"t": f"2026-11-23T10:{42 - i:02d}:00+07:00", "symbol": "HPG" if i == 0 else f"M{i:02d}", "rule": "volume_spike",
              "rule_name": "Khối lượng tăng bất thường", "severity": "CAO" if i % 3 != 2 else "TRUNG BÌNH",
              "value": 3.4, "threshold": 3.0, "message": "Khối lượng cao gấp 3,4 lần mức thường thấy cùng khung giờ (ngưỡng 3,0)"}
             for i in range(n_alerts)]
    return {
        "meta": {"index_code": "VN30", "source_label": "SSI FastConnect (dữ liệu thật)", "is_simulated": sim,
                 "trading_date": "2026-11-23", "last_update": last.isoformat(),
                 "data_status": {"state": state, "phase": phase, "reason": "Phiên đã kết thúc."}},
        "pulse": {"score": 58.6, "label": "Nghiêng tích cực <test>", "missing": ["liquidity"],
                  "components": [{"key": "breadth", "name": "Độ rộng thị trường", "value": 0.38},
                                 {"key": "momentum", "name": "Động lượng chỉ số", "value": 0.44},
                                 {"key": "book", "name": "Mất cân bằng sổ lệnh", "value": -0.23},
                                 {"key": "liquidity", "name": "Thanh khoản", "value": None}]},
        "index": {"row": {"value": 1967.7, "pct_change": 0.45, "advances": 20, "declines": 9, "no_change": 1, "n_ceiling": 0, "n_floor": 0}},
        "foreign": {"summary": {"net_val": -99.1e9},
                    "rows": [{"symbol": "HPG", "net": 18.8e9, "participation": 0.07}, {"symbol": "BID", "net": -78.1e9, "participation": 0.07}]},
        "book": {"rows": [{"symbol": "HPG", "last": 27350.0, "pct_change": 1.3, "obi3": 0.42, "total_value": 612.4e9}]},
        "sectors": {"rows": [{"sector": "Ngân hàng", "contrib_pts": 6.2}, {"sector": "Thép", "contrib_pts": -1.0}]},
        "futures": {"available": True, "state": {"symbol": "VN30F2612", "basis": -1.2, "dtm": 24}},
        "alerts": {"total": n_alerts, "by_severity": {"CAO": sum(a["severity"] == "CAO" for a in items), "TRUNG BÌNH": sum(a["severity"] != "CAO" for a in items), "THẤP": 0},
                   "items": items},
    }


def buttons(markup):
    return [b for row in (markup or {}).get("inline_keyboard", []) for b in row]


# ------------------------------------------------------------------------------------------------ lệnh, bí danh
def test_menu_and_aliases_map_to_one_command_each():
    assert ui.normalize("📊 Thị trường") == "/thitruong" and ui.normalize("Nhịp thị trường") == "/thitruong"  # nhãn cũ
    assert ui.split_command("/market") == ("/thitruong", "", "/market")
    assert ui.split_command("/alerts") == ("/canhbao", "", "/alerts")
    assert ui.split_command("/alerts on") == ("/alerts", "on", None)       # bật/tắt giữ nguyên, chuyển /caidat
    assert ui.split_command("/company hpg") == ("/ma", "hpg", "/company")
    assert len({c for _, c in ui.BUTTON_COMMANDS.items()}) == 7
    assert [c for c, _ in ui.COMMANDS] == ["thitruong", "canhbao", "ma", "theodoi", "caidat", "trangthai", "huongdan", "dung"]


def test_old_command_answers_with_new_name_note():
    text, _ = ui.readonly_answer("/market", CATALOG, payload)
    assert "Lệnh mới: /thitruong" in text
    assert "Lệnh mới" not in ui.readonly_answer("/thitruong", CATALOG, payload)[0]


# ------------------------------------------------------------------------------------------------ mẫu tin
def test_market_message_structure_icons_and_escape():
    text, markup = ui.readonly_answer("📊 Thị trường", CATALOG, payload)
    assert text.startswith("📊 <b>Nhịp thị trường · VN30</b> · 15:05, 23/11/2026")
    assert "🧭 Điểm nhịp <b>58,6/100</b>" in text and "&lt;test&gt;" in text and "<test>" not in text
    assert "VN30 1.967,70 🟢 ▲ +0,45% · 20 mã tăng / 9 mã giảm / 1 đứng giá" in text
    assert "<b>Căn cứ:</b> Động lượng chỉ số +0,44 và Độ rộng thị trường +0,38 kéo điểm lên; Mất cân bằng sổ lệnh −0,23 kéo xuống" in text
    assert "🏦 Khối ngoại bán ròng 99,1 tỷ đồng" in text and "Ngân hàng +6,2 điểm" in text
    assert text.endswith("<i>SSI FastConnect · Phiên đã kết thúc · Không phải lời khuyên đầu tư</i>")
    assert [b.get("callback_data") or b["url"] for b in buttons(markup)] == ["v:canhbao", ui.BASE + "/?tab=tong-quan"]


def test_simulated_and_missing_fields_are_labelled_not_invented():
    p = payload(sim=True)
    for k in ("index", "foreign", "sectors"):
        p.pop(k)
    text = ui.format_market(p)
    assert "[MÔ PHỎNG]" in text and "Bộ mô phỏng · Dữ liệu MÔ PHỎNG" in text
    assert "Bối cảnh" not in text and "VN30 1." not in text and "None" not in text
    p["pulse"]["score"] = None
    assert "Chưa đủ dữ liệu" in ui.format_market(p)


def test_stale_live_data_is_not_called_in_session():
    last = datetime(2026, 11, 23, 10, 0, tzinfo=VN)
    p = payload(state="fresh", phase="open", last=last)
    assert "Dữ liệu chậm 10 phút" in ui.format_market(p, now=(last + timedelta(minutes=10)).timestamp())
    assert "· Trong phiên ·" in ui.format_market(p, now=(last + timedelta(seconds=30)).timestamp())


def test_alert_list_scope_and_length_limit():
    p = payload(n_alerts=300)
    p["alerts"]["items"][0]["message"] = "x" * 300
    text, markup = ui.readonly_answer("/canhbao", CATALOG, lambda: p)
    assert len(text) <= 4096 and "cảnh báo khác." in text and "⚠️" not in text.split("Mức cao gần nhất:")[1].split("…")[0]
    assert {b.get("callback_data") for b in buttons(markup)} >= {"cl:CAO", "cl:TB"}
    kind, wide, _ = ui.readonly_callback("cl:TB", CATALOG, lambda: payload())
    assert kind == "edit" and "⚠️" in wide and "Từ trung bình trở lên" in wide


def test_single_alert_push_matches_target_layout():
    p = payload()
    text = ui.format_alert_push([p["alerts"]["items"][0]], p)
    lines = text.split("\n")
    assert lines[0] == "🚨 <b>Khối lượng bất thường · HPG</b> · 10:42"
    assert lines[1] == "HPG khớp lệnh gấp 3,4 lần mức thường thấy cùng khung giờ; giá 27.350 🟢 ▲ +1,30%."
    assert lines[2] == "<b>Căn cứ:</b> vượt ngưỡng cảnh báo 3,0 lần mức thường thấy; sổ lệnh nghiêng về bên mua (OBI₃ +0,42)."
    assert lines[3].startswith("<b>Bối cảnh:</b> VN30 1.967,70 🟢 ▲ +0,45%")
    assert lines[-1].endswith("Không phải lời khuyên đầu tư</i>")
    urls = [b.get("url") for b in buttons(ui.alert_push_keyboard([p["alerts"]["items"][0]]))]
    assert ui.BASE + "/doanh-nghiep/HPG" in urls


def test_many_alerts_in_one_round_become_one_message():
    p = payload(n_alerts=5)
    cao = [a for a in p["alerts"]["items"] if a["severity"] == "CAO"]
    text = ui.format_alert_push(cao, p)
    assert text.startswith(f"🚨 <b>{len(cao)} cảnh báo mức cao mới</b>") and text.count("🚨 10:") == len(cao)


def test_card_in_basket_and_outside_basket():
    text, markup = ui.readonly_answer("hpg", CATALOG, payload)
    assert "Giá 27.350 🟢 ▲ +1,30%" in text and "🏦 Khối ngoại mua ròng 18,8 tỷ đồng (tỷ trọng 7,0% giá trị khớp)" in text
    assert "1 cảnh báo trong phiên" in text
    assert [b.get("callback_data") or b["url"] for b in buttons(markup)] == ["c:HPG", ui.BASE + "/doanh-nghiep/HPG"]
    outside, _ = ui.readonly_answer("/ma DBC", CATALOG, payload)
    assert "chỉ có cho các mã thuộc rổ VN30" in outside and "Giá 2" not in outside and "Khối ngoại" not in outside
    assert "Không tìm thấy mã ZZZ" in ui.readonly_answer("/ma ZZZ", CATALOG, payload)[0]
    assert ui.readonly_answer("hello", CATALOG, payload) is None


def test_source_error_reports_without_numbers():
    def boom():
        raise httpx.ConnectError("down")
    text, _ = ui.readonly_answer("/thitruong", CATALOG, boom)
    assert "Chưa lấy được dữ liệu" in text and not any(ch.isdigit() for ch in text)
    assert "Chưa lấy được dữ liệu" in ui.readonly_answer("/trangthai", CATALOG, boom)[0]


def test_close_digest_and_news_message():
    text = ui.format_close_digest(payload())
    assert text.startswith("📊 <b>Tổng kết phiên 23/11/2026 · VN30</b>")
    assert "🟣 0 trần · 🔵 0 sàn" in text and "📈 VN30F2612: chênh lệch cơ sở −1,20 điểm, còn 24 ngày tới đáo hạn" in text
    assert "mua ròng nhiều nhất HPG, bán ròng nhiều nhất BID" in text
    news = ui.format_news("laws", "baochinhphu.vn", "Nghị định <mới> & thuế", "https://baochinhphu.vn/a.htm", 0, [])
    assert news.startswith("⚖️ <b>Tin chính sách</b>") and "Nghị định &lt;mới&gt; &amp; thuế" in news and "dự thảo" in news


# ------------------------------------------------------------------------------------------------ đăng ký
def msg(text, cid=7):
    return {"message": {"chat": {"type": "private", "id": cid}, "text": text, "date": 100}}


def test_help_and_menu_do_not_subscribe_unknown_text_gets_reply():
    s = {"users": {}}
    assert tc.command(s, msg("/huongdan"), VALID, 100)[1] == ui.HELP and s["users"] == {}
    text, markup = tc.command(s, msg("⚙️ Cài đặt"), VALID, 100)[1:]
    assert "chưa đăng ký" in text and buttons(markup)[0]["callback_data"] == "sub" and s["users"] == {}
    assert "Chưa hiểu yêu cầu" in tc.command(s, msg("xin chào"), VALID, 100)[1]


def test_start_settings_watch_and_old_commands():
    s = {"users": {}}
    start = tc.command(s, msg("/start news_laws"), VALID, 100)[1]
    assert "Đang nhận: tin doanh nghiệp, tin chính sách" in start and not s["users"]["7"]["alerts"]
    text, markup = tc.command(s, msg("/alerts on"), VALID, 101)[1:]
    assert s["users"]["7"]["alerts"] and "Lệnh mới: /caidat" in text and buttons(markup)[0]["callback_data"] == "t:alerts"
    tc.command(s, msg("/theodoi HPG"), VALID, 102)
    assert s["users"]["7"]["symbols"] == ["HPG"]
    assert "Lệnh mới: /theodoi" in tc.command(s, msg("/all"), VALID, 103)[1] and s["users"]["7"]["symbols"] == []
    assert "Lệnh mới: /dung" in tc.command(s, msg("/stop"), VALID, 104)[1] and not s["users"]


def test_callbacks_toggle_watch_and_stop_and_read_old_records():
    old = {"since": 0, "alerts": True, "news": False, "laws": False, "symbols": [], "delivered": {}}  # bản ghi trước bản này
    s = {"users": {"7": old}}
    assert "▫️ Tóm tắt đầu phiên" in ui.settings_text(old)
    r = tc.callback(s, "7", "t:digest_open", VALID, 500)
    assert old["digest_open"] and old["enabled_since"]["digest_open"] == 500 and "✅ Tóm tắt đầu phiên" in r["edit"][0]
    assert "Đã thêm HPG" in tc.callback(s, "7", "c:HPG", VALID, 501)["toast"] and old["symbols"] == ["HPG"]
    assert "Đã bỏ HPG" in tc.callback(s, "7", "c:HPG", VALID, 502)["toast"] and old["symbols"] == []
    assert tc.callback(s, "7", "c:ZZZ", VALID, 503)["toast"] == "Nút này không còn hiệu lực."
    tc.callback(s, "7", "stop", VALID, 504)
    assert not s["users"] and "chưa đăng ký" in tc.callback(s, "7", "t:news", VALID, 505)["toast"]


def test_outbox_groups_alerts_and_skips_delivered():
    p = payload(n_alerts=4)
    user = {"since": 0, "alerts": True, "news": True, "laws": False, "symbols": [], "delivered": {}}
    now = datetime(2026, 11, 23, 10, 45, tzinfo=VN).timestamp()
    events = [{"id": f"a{i}", "category": "alerts", "at": now - 60, "symbols": [a["symbol"]], "alert": a}
              for i, a in enumerate(p["alerts"]["items"]) if a["severity"] == "CAO"]
    events.append({"id": "n1", "category": "news", "at": now - 30, "symbols": ["HPG"], "text": "📰 x", "markup": None})
    basket = {a["symbol"] for a in p["alerts"]["items"]} | {"HPG"}
    out = tc.outbox(user, events, basket, p, now)
    assert len(out) == 2 and out[0]["ids"] == [e["id"] for e in events if e["category"] == "alerts"]
    user["delivered"] = {i: now for i in out[0]["ids"]}
    assert [m["ids"] for m in tc.outbox(user, events, basket, p, now)] == [["n1"]]


def test_digest_events_once_per_day_at_right_time():
    now = datetime(2026, 11, 23, 15, 10, tzinfo=VN).timestamp()
    p = payload(last=datetime(2026, 11, 23, 15, 5, tzinfo=VN))
    assert [e["id"] for e in tc.digest_events(p, now)] == ["digest_close|2026-11-23"]
    p_open = payload(state="fresh", phase="open", last=datetime(2026, 11, 23, 9, 20, tzinfo=VN))
    assert [e["id"] for e in tc.digest_events(p_open, datetime(2026, 11, 23, 9, 21, tzinfo=VN).timestamp())] == ["digest_open|2026-11-23"]
    assert tc.digest_events(payload(sim=True), now) == []
    assert tc.digest_events(p, now + 86400) == []          # dữ liệu hôm qua không tạo tổng kết hôm nay


# ------------------------------------------------------------------------------------------------ webhook
def load_webhook():
    path = Path(__file__).resolve().parents[1] / "web/api/telegram.py"
    if not (path.parent.parent / "serverpkg/data/catalog.json").exists():
        pytest.skip("cần chạy tools/prepare_web_python.py")
    spec = importlib.util.spec_from_file_location("tg_webhook", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call_webhook(mod, update, monkeypatch, handler):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "hook")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
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


def readonly_site(r):
    if str(r.url) == ui.BASE + "/api/data":
        return httpx.Response(200, json={"payload": payload()})
    raise AssertionError("không được gọi Redis cho yêu cầu chỉ đọc")


def test_webhook_message_uses_html_and_never_touches_subscriptions(monkeypatch):
    mod = load_webhook()
    status, body = call_webhook(mod, {"update_id": 1, **msg("📊 Thị trường")}, monkeypatch, readonly_site)
    assert status == 200 and body["method"] == "sendMessage" and body["parse_mode"] == "HTML" and "Điểm nhịp" in body["text"]
    status, body = call_webhook(mod, {"update_id": 2, **msg("HPG")}, monkeypatch, readonly_site)
    assert ui.BASE + "/doanh-nghiep/HPG" in [b.get("url") for b in buttons(body["reply_markup"])]


def test_webhook_readonly_callback_edits_and_foreign_chat_is_ignored(monkeypatch):
    mod = load_webhook()
    query = {"id": "q1", "from": {"id": 7}, "data": "cl:TB", "message": {"message_id": 5, "chat": {"type": "private", "id": 7}}}
    status, body = call_webhook(mod, {"update_id": 3, "callback_query": query}, monkeypatch, readonly_site)
    assert body["method"] == "editMessageText" and body["message_id"] == 5 and "Từ trung bình" in body["text"]
    query = {**query, "from": {"id": 8}}
    status, body = call_webhook(mod, {"update_id": 4, "callback_query": query}, monkeypatch, readonly_site)
    assert body == {"method": "answerCallbackQuery", "callback_query_id": "q1"}
