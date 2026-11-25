import json
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.fernet import Fernet

from neopulse.analytics import telegram_cloud as tc
from neopulse.analytics.telegram_cloud import (
    Telegram,
    command,
    load_state,
    rss_items,
    save_state,
    should_send,
)


def state():
    return {"users": {}, "offset": 0}


def update(text, kind="private"):
    return {"message": {"chat": {"type": kind, "id": 123}, "text": text}}


def test_explicit_optin_preferences_stop_and_group_rejected():
    s = state()
    command(s, update("/news on"), {"MWG"}, 100)
    assert s["users"] == {}
    command(s, update("/start", "group"), {"MWG"}, 100)
    assert s["users"] == {}
    command(s, update("/start"), {"MWG"}, 100)
    assert s["users"]["123"]["alerts"] and not s["users"]["123"]["news"]
    command(s, update("/watch ../bad"), {"MWG"}, 100)
    assert s["users"]["123"]["symbols"] == []
    command(s, update("/watch MWG"), {"MWG"}, 100)
    command(s, update("/news on"), {"MWG"}, 100)
    assert s["users"]["123"]["symbols"] == ["MWG"]
    command(s, update("/stop"), {"MWG"}, 100)
    assert not s["users"]


def test_no_old_news_dedup_and_watch_filter():
    u = {"since": 100, "news": True, "symbols": ["MWG"], "delivered": {}}
    e = {"id": "a", "category": "news", "at": 101, "symbols": ["MWG"]}
    assert should_send(u, e, 110)
    assert not should_send(u, {**e, "at": 99}, 110)
    assert not should_send(u, {**e, "symbols": ["FPT"]}, 110)
    u["delivered"]["a"] = 110
    assert not should_send(u, e, 111)


def test_encrypted_state_and_wrong_key_fail_closed(tmp_path):
    crypto = pytest.importorskip("cryptography.fernet")
    key = crypto.Fernet.generate_key().decode()
    p = tmp_path / "state.enc"
    s = state()
    command(s, update("/start"), {"MWG"}, 100)
    save_state(p, key, s)
    assert b'"123"' not in p.read_bytes()
    assert load_state(p, key) == s
    with pytest.raises(crypto.InvalidToken):
        load_state(p, crypto.Fernet.generate_key().decode())


def rss(*titles):
    items = "".join(f'<item><title>{t}</title><link>https://cafef.vn/{i}.chn</link><pubDate>Thu, 19 Nov 2026 10:00:00 +0700</pubDate></item>'
                    for i, t in enumerate(titles))
    return f"<rss><channel>{items}</channel></rss>".encode()


def test_rss_cites_source_does_not_invent_effective_date():
    xml = rss("MWG earnings")
    events = rss_items(xml, "news", "cafef.vn", {"MWG"})
    assert events[0]["symbols"] == ["MWG"] and events[0]["link"] == "https://cafef.vn/0.chn" and events[0]["host"] == "cafef.vn"
    assert events[0]["at"] == datetime(2026, 11, 19, 3, tzinfo=timezone.utc).timestamp()
    assert not rss_items(xml, "news", "baochinhphu.vn", {"MWG"})
    with pytest.raises(ValueError):
        rss_items(b'<!DOCTYPE test><rss/>', "news", "cafef.vn", set())


def test_telegram_errors_never_include_token_or_recipient():
    transport = httpx.MockTransport(lambda r: httpx.Response(500, json={"ok": False}))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(RuntimeError) as e:
            Telegram("TEST_SECRET_TOKEN", client).send("PRIVATE_CHAT", "hello")
    assert "TEST_SECRET_TOKEN" not in str(e.value) and "PRIVATE_CHAT" not in str(e.value)


def test_delivery_ack_is_only_added_after_send_succeeds(tmp_path):
    crypto = pytest.importorskip("cryptography.fernet")
    from neopulse.analytics.telegram_cloud import BASE, run
    key = crypto.Fernet.generate_key().decode()
    p = tmp_path / "telegram.enc"
    s = {"offset": 1, "users": {"123": {"since": 0, "alerts": True, "news": False, "laws": False, "symbols": [], "delivered": {}}}}
    save_state(p, key, s)
    def handler(r):
        if "getUpdates" in str(r.url):
            return httpx.Response(200, json={"ok": True, "result": []})
        if "sendMessage" in str(r.url):
            return httpx.Response(500, json={"ok": False})
        if str(r.url) == BASE + "/data/company/index.json":
            return httpx.Response(200, json={"symbols": [{"symbol": "MWG"}]})
        if str(r.url) == BASE + "/data/latest_VN30.json":
            return httpx.Response(200, json={"book": {"rows": [{"symbol": "MWG"}]}})
        if str(r.url) == BASE + "/api/data":
            return httpx.Response(200, json={"payload": {"meta": {"is_simulated": False}, "alerts": {"items": [{"t": "1970-01-01T00:01:40+00:00", "severity": "CAO", "symbol": "MWG", "rule": "x", "message": "test"}]}}})
        return httpx.Response(200, content=b'<rss><channel/></rss>')
    with httpx.Client(transport=httpx.MockTransport(handler)) as c, pytest.raises(RuntimeError):
        run(p, "TEST", key, client=c, now=110)
    assert not load_state(p, key)["users"]["123"]["delivered"]
    assert "PRIVATE" not in json.dumps(load_state(p, key))


def test_redis_lock_skips_concurrent_run(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("KV_REST_API_URL", "https://redis.test")
    monkeypatch.setenv("KV_REST_API_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_STATE_KEY", Fernet.generate_key().decode())
    seen = []

    def redis(request):
        cmd = json.loads(request.content)
        seen.append(cmd[0])
        return httpx.Response(200, json={"result": None})  # SET NX thất bại: lượt khác giữ khóa

    with httpx.Client(transport=httpx.MockTransport(redis)) as c:
        tc.run(tmp_path / "s.enc", "tok", Fernet.generate_key().decode(), client=c)
    assert seen == ["SET"] and "bỏ qua" in capsys.readouterr().out


def test_rss_keeps_only_notable_items():
    symbols = {"MWG", "CEO", "HAI"}
    news = rss_items(rss("MWG lãi kỷ lục", "CEO chia sẻ bí quyết", "Hai doanh nghiệp bắt tay", "Chuyện hậu trường"), "news", "cafef.vn", symbols)
    assert [n["symbols"] for n in news] == [["MWG"]]  # viết tắt CEO và chữ thường "Hai" không bị nhận là mã
    world = rss_items(rss("Fed giữ nguyên lãi suất", "Phát hiện kho báu dưới lòng đất"), "world", "cafef.vn", symbols)
    assert [n["title"] for n in world] == ["Fed giữ nguyên lãi suất"]
    laws = rss_items(rss("Nghị định mới về thuế thu nhập", "Từ năm 2028 không dùng điểm cộng"), "laws", "cafef.vn", symbols)
    assert [n["title"] for n in laws] == ["Nghị định mới về thuế thu nhập"]
