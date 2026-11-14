import json

import httpx
import pytest

from neopulse.neo_api.client import NeoClient
from neopulse.neo_api.errors import NeoApiError, NeoAuthError, NeoSafetyError
from neopulse.neo_api.ratelimit import RateLimiter


def ok(data, code="NEOINP000000"):
    return httpx.Response(200, json={"status": 1, "code": code, "message": "ok", "data": data})


def login_ok(token="tok-1"):
    return ok({"access_token": token, "token_type": "Bearer", "expires_in": 10800}, "IABNOT000")


class Server:
    """Máy chủ NEO API giả: ghi lại request, trả lời theo kịch bản."""

    def __init__(self, handler):
        self.requests, self._handler, self.logins = [], handler, 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == "auth.test":
            self.logins += 1
            body = json.loads(request.content)
            if body["password"] != "s3cret-pw":
                return httpx.Response(400, json={"status": 0, "code": "IABNOT001", "message": "Sai tên đăng nhập hoặc mật khẩu"})
            return login_ok(f"tok-{self.logins}")
        return self._handler(request, self)


def make(settings, handler, **kw):
    srv = Server(handler)
    client = NeoClient(settings, transport=httpx.MockTransport(srv), sleep=lambda s: None, **kw)
    return client, srv


def test_login_then_required_headers(settings):
    c, srv = make(settings, lambda r, s: ok([{"marketCode": "HOSE", "marketStatus": "LO"}]))
    assert c.market_status()[0]["marketStatus"] == "LO"
    api = srv.requests[-1]
    assert api.headers["authorization"] == "Bearer tok-1"
    assert api.headers["x-device"] == settings.neo_device_id and api.headers["x-devicetype"] == settings.neo_device_type
    assert api.url.path == "/neo-api/market/marketStatus" and srv.logins == 1
    c.market_status()
    assert srv.logins == 1                                   # token được tái sử dụng


def test_wrong_password_raises_auth_error_without_leaking_secret(settings):
    from dataclasses import replace
    c, _ = make(replace(settings, neo_password="wrong-pw"), lambda r, s: ok([]))
    with pytest.raises(NeoAuthError) as e:
        c.market_status()
    assert "IABNOT001" in str(e.value) and "wrong-pw" not in str(e.value)


def test_missing_credentials_message(settings):
    from dataclasses import replace
    c, _ = make(replace(settings, neo_username="", neo_password=""), lambda r, s: ok([]))
    with pytest.raises(NeoAuthError, match="NEO_USERNAME"):
        c.market_status()


def test_expired_token_triggers_single_relogin(settings):
    def handler(r, s):
        return httpx.Response(401, json={}) if r.headers["authorization"] == "Bearer tok-1" else ok([{"x": 1}])
    c, srv = make(settings, handler)
    assert c.market_status() == [{"x": 1}] and srv.logins == 2


def test_token_refreshes_before_expiry(settings):
    now = [1000.0]
    c, srv = make(settings, lambda r, s: ok([]), clock=lambda: now[0])
    c.market_status()
    now[0] += 10800 - 200                                    # còn 200s < biên an toàn 300s
    c.market_status()
    assert srv.logins == 2


def test_pasted_token_is_used_without_login(settings):
    from dataclasses import replace
    c, srv = make(replace(settings, neo_access_token="pasted", neo_username="", neo_password=""), lambda r, s: ok([]))
    c.market_status()
    assert srv.logins == 0 and srv.requests[-1].headers["authorization"] == "Bearer pasted"


def test_forbidden_ip_is_not_retried(settings):
    c, srv = make(settings, lambda r, s: httpx.Response(403, json={"status": 0, "code": "NEOINP000403", "message": "Forbidden"}))
    with pytest.raises(NeoAuthError, match="IP"):
        c.market_status()
    assert len([r for r in srv.requests if r.url.host == "neo.test"]) == 1


def test_transient_errors_are_retried_then_succeed(settings):
    calls = {"n": 0}

    def handler(r, s):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        if calls["n"] == 2:
            return httpx.Response(200, json={"status": 0, "code": "NEOINP000111", "message": "timeout"})
        return ok([{"ok": True}])
    c, _ = make(settings, handler)
    assert c.market_status() == [{"ok": True}] and calls["n"] == 3


def test_retries_are_bounded(settings):
    c, srv = make(settings, lambda r, s: httpx.Response(500), max_retries=2)
    with pytest.raises(NeoApiError):
        c.market_status()
    assert len([r for r in srv.requests if r.url.host == "neo.test"]) == 3


def test_business_error_is_not_retried_and_empty_is_ok(settings):
    c, srv = make(settings, lambda r, s: httpx.Response(200, json={"status": 0, "code": "NEOINP000134", "message": "bad market"}))
    with pytest.raises(NeoApiError, match="NEOINP000134"):
        c.market_status("XXX")
    assert len([r for r in srv.requests if r.url.host == "neo.test"]) == 1
    c2, _ = make(settings, lambda r, s: httpx.Response(200, json={"status": 0, "code": "NEOINP000004", "message": "empty"}))
    assert c2.market_status() == []


def test_non_json_and_network_errors_are_wrapped(settings):
    c, _ = make(settings, lambda r, s: httpx.Response(200, text="<html>gateway</html>"))
    with pytest.raises(NeoApiError, match="JSON"):
        c.market_status()

    def boom(r, s):
        raise httpx.ConnectError("no route")
    c2, _ = make(settings, boom, max_retries=1)
    with pytest.raises(NeoApiError, match="Lỗi mạng"):
        c2.market_status()


def test_trading_endpoints_are_blocked(settings):
    c, srv = make(settings, lambda r, s: ok([]))
    with pytest.raises(NeoSafetyError):
        c.get("/trading/orders")
    assert srv.requests == []                                # không có request nào rời khỏi máy
    assert not any(hasattr(c, n) for n in ("place_order", "amend_order", "cancel_order", "post", "put", "delete"))


def test_symbols_are_chunked_by_ten(settings):
    seen = []

    def handler(r, s):
        seen.append(r.url.params["symbols"].split(","))
        return ok({"content": [{"symbol": x} for x in seen[-1]], "last": True})
    c, _ = make(settings, handler)
    out = c.stock_detail([f"S{i:02d}" for i in range(23)])
    assert [len(x) for x in seen] == [10, 10, 3] and len(out) == 23


def test_pagination_follows_last_flag(settings):
    def handler(r, s):
        page = int(r.url.params["pageNo"])
        return ok({"content": [{"symbol": f"P{page}"}], "last": page == 3})
    c, srv = make(settings, handler)
    assert [m["symbol"] for m in c.stock_detail_by_index("VN30")] == ["P1", "P2", "P3"]


def test_every_request_passes_through_rate_limiter(settings):
    class Counting(RateLimiter):
        n = 0

        def acquire(self):
            Counting.n += 1
            return 0.0
    c, srv = make(settings, lambda r, s: ok([]), limiter=Counting(5))
    c.market_status()
    c.market_status()
    assert Counting.n == len(srv.requests) == 3              # 1 login + 2 API


def test_rate_limiter_enforces_spacing():
    t = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        t[0] += s
    rl = RateLimiter(5, burst=1, clock=lambda: t[0], sleep=sleep)
    for _ in range(11):
        rl.acquire()
    assert t[0] == pytest.approx(2.0)                        # 10 khoảng cách x 0,2s => đúng 5 req/giây
    with pytest.raises(ValueError):
        RateLimiter(0)
