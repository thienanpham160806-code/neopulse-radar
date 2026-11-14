import asyncio
import json

import pytest

from neopulse.neo_api.ws import MarketStream, classify_message


def test_classify_documented_payloads():
    stock = {"symbol": "HPG", "refPrice": 29850, "bidPrice1": "29750.0"}
    info = {"indexCode": "VNXALL", "indexValue": "2940.76", "advances": 229, "indexPercentChange": 0.99}
    vol = {"indexCode": "HNX30", "indexValue": "644.39", "totalVolume": 1, "volume": 2}
    sess = {"marketCode": "HOSE", "rawMarketCode": "HOSE", "marketStatus": "C", "rawMarketStatus": "K"}
    assert classify_message(stock) == [("stockInfo", stock)]
    assert classify_message(info)[0][0] == "marketInfo"
    assert classify_message(vol)[0][0] == "marketVolume"
    assert classify_message(sess)[0][0] == "marketSession"
    assert classify_message({"type": "auth", "status": "success"})[0][0] == "auth"


def test_classify_tolerates_envelopes_lists_and_garbage():
    stock = {"symbol": "HPG", "closePrice": 1}
    assert classify_message({"channel": "stockInfo", "data": stock}) == [("stockInfo", stock)]
    assert classify_message({"type": "stockInfo", "data": [stock, stock]}) == [("stockInfo", stock)] * 2
    assert classify_message([stock, {"indexCode": "VN30", "advances": 1}])[1][0] == "marketInfo"
    assert classify_message({"hello": "world"})[0][0] == "unknown"
    assert classify_message("text")[0][0] == "unknown"
    assert classify_message({"type": "sub", "status": "ok"})[0][0] == "control"


class FakeWS:
    def __init__(self, script):
        self.sent, self._script = [], list(script)

    async def send(self, m):
        self.sent.append(json.loads(m))

    async def recv(self):
        if not self._script:
            raise ConnectionError("server closed")
        item = self._script.pop(0)
        if item == "HANG":
            await asyncio.sleep(3600)
        return item if isinstance(item, str) else json.dumps(item)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def run_stream(scripts, **kw):
    sockets, got = [], []

    def connect(url):
        ws = FakeWS(scripts[len(sockets)] if len(sockets) < len(scripts) else [])
        sockets.append(ws)
        return ws
    stream = MarketStream("ws://x", lambda: "jwt-abc", {"stockInfo": ["VPB", "HPG"], "marketInfo": ["VN30"], "empty": []},
                          lambda ch, body, ts: got.append((ch, body)), connect=connect, **kw)
    stream.backoff = lambda attempt: 0.0
    asyncio.run(stream.run(max_sessions=len(scripts)))
    return stream, sockets, got


AUTH_OK = {"type": "auth", "status": "success", "data": {"username": "u"}}


def test_auth_then_subscribe_then_dispatch():
    stream, sockets, got = run_stream([[AUTH_OK, {"symbol": "VPB", "closePrice": 31250}, "not json", {"weird": 1}]])
    sent = sockets[0].sent
    assert sent[0] == {"action": "auth", "data": "jwt-abc"}
    assert {"type": "sub", "channel": "stockInfo", "listId": ["VPB", "HPG"]} in sent
    assert {"type": "sub", "channel": "marketInfo", "listId": ["VN30"]} in sent
    assert len(sent) == 3                                    # kênh rỗng không được đăng ký
    assert [g[0] for g in got] == ["stockInfo", "unknown"]
    assert stream.stats.parse_errors == 1 and stream.stats.unknown == 1 and stream.stats.messages == 2


def test_data_before_auth_is_ignored_and_auth_failure_is_reported():
    stream, sockets, got = run_stream([[{"symbol": "VPB", "closePrice": 1}, {"type": "auth", "status": "error", "data": "Invalid JWT token"}]])
    assert got == [] and "Invalid JWT token" in stream.stats.last_error
    assert len(sockets[0].sent) == 1                         # không đăng ký kênh khi chưa xác thực


def test_reconnects_and_resubscribes_after_drop():
    msg = {"symbol": "VPB", "closePrice": 1}
    stream, sockets, got = run_stream([[AUTH_OK, msg], [AUTH_OK, msg, msg]])
    assert stream.stats.connects == 2 and stream.stats.reconnects >= 1 and len(got) == 3
    assert all(s.sent[0]["action"] == "auth" and len(s.sent) == 3 for s in sockets)


def test_silent_connection_is_treated_as_stale():
    stream, _, _ = run_stream([[AUTH_OK, "HANG"]], stale_after_s=0.05)
    assert "treo" in stream.stats.last_error


def test_backoff_is_bounded_with_jitter():
    s = MarketStream("ws://x", lambda: "t", {}, lambda *a: None, max_backoff_s=30)
    vals = [s.backoff(a) for a in range(0, 15)]
    assert all(0.5 <= v <= 30 for v in vals) and vals[0] <= 1.0 and max(vals) > 10


def test_stop_ends_run():
    async def go():
        stream = MarketStream("ws://x", lambda: "t", {}, lambda *a: None, connect=lambda url: FakeWS([AUTH_OK, "HANG"]),
                              stale_after_s=5)
        task = asyncio.create_task(stream.run())
        await asyncio.sleep(0.05)
        stream.stop()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return stream
    assert asyncio.run(go()).stats.connects == 1
