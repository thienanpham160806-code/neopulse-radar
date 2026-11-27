import asyncio
import json
from datetime import datetime

import httpx
import pytest

from neopulse.config import Settings, load_settings
from neopulse.data.ingest import Ingestor
from neopulse.data.recorder_ssi import futures_meta, vn30f_maturity
from neopulse.data.storage import Storage
from neopulse.neo_api.errors import NeoSafetyError
from neopulse.ssi.adapter import SsiAdapter
from neopulse.ssi.client import SsiAuthError, SsiClient
from neopulse.ssi.ws import SsiStream, build_topics
from neopulse.timeutil import VN_TZ


@pytest.fixture
def ssi_settings():
    return Settings(mode="live", source="ssi", ssi_api_key="key-abcdef", ssi_api_secret="sec-xyz",
                    ssi_api_url="https://ssi.test", ssi_max_rps=10)


def frame(topic, **data):
    return {"topic": topic, "data": data}


# ------------------------------------------------------------------- adapter
def test_adapter_merges_partial_frames_into_neo_schema():
    a = SsiAdapter()
    assert a.feed(frame("market.VPB", s="VPB", b="HOSE", ce=33800, fl=29400, ref=31600))[0][0] == "stockInfo"
    a.feed(frame("quote.VPB", s="VPB", bids=[[31250, 98500], [31200, 608000], [31150, 560800]],
                 asks=[[31300, 590900], [31350, 103600], [31400, 201200]]))
    a.feed(frame("room.VPB", s="VPB", tr=2380177080, cr=435283768, bq=2924700, bv=91396875000, sq=2334102, sv=72940687500))
    (ch, b), = a.feed(frame("trade.VPB", s="VPB", p="31250.0", q="5000", v="33498000", o=31500, h=32200, l=31100, a=31422.0))
    assert ch == "stockInfo"
    assert (b["symbol"], b["closePrice"], b["totalTradingVolume"]) == ("VPB", 31250.0, 33498000.0)
    assert (b["bidPrice1"], b["bidVol3"], b["askPrice3"]) == (31250.0, 560800.0, 31400.0)
    assert (b["ceilingPrice"], b["floorPrice"], b["refPrice"]) == (33800.0, 29400.0, 31600.0)
    assert (b["foreignBuyVolume"], b["foreignRoom"], b["foreignRemain"]) == (2924700.0, 2380177080.0, 435283768.0)
    assert b["priceChange"] == pytest.approx(-350.0) and b["percentPriceChange"] == pytest.approx(-1.1076, abs=1e-3)
    assert b["totalTradingValue"] == pytest.approx(31422.0 * 33498000)  # ước lượng = giá TB x KL lũy kế
    assert b["marketCode"] == "HOSE"


def test_adapter_skips_until_price_known_and_ignores_candles_and_acks():
    a = SsiAdapter()
    assert a.feed(frame("quote.AAA", s="AAA", bids=[[1, 1]], asks=[[2, 1]])) == []  # chưa có giá cuối/tham chiếu
    assert a.feed(frame("trade.AAA@1m", s="AAA", p=1)) == [] and a.n_ignored == 1
    assert a.feed({"method": "PING_PONG", "channel": "HEARTBEAT", "status": "ok", "message": "pong"})[0][0] == "control"
    assert a.feed(frame("something.else", x=1))[0][0] == "unknown"
    assert a.feed("text")[0][0] == "unknown"
    assert a.feed(frame("oddlot.AAA", s="AAA")) == []


def test_adapter_auction_word_in_book_and_missing_levels():
    a = SsiAdapter()
    a.feed(frame("market.AAA", s="AAA", ref=10000))
    (_, b), = a.feed(frame("quote.AAA", s="AAA", bids=[["ATO", 5000]], asks=[[10100, 100]]))
    assert b["bidPrice1"] == "ATO" and b["bidPrice2"] is None and b["askPrice1"] == 10100.0
    (_, b2), = a.feed(frame("trade.AAA", s="AAA", p="ATO", q=0, v=0))  # giá chữ không đè giá cuối
    assert "closePrice" not in b2 or b2["closePrice"] is None


def test_adapter_futures_index_and_session_flag():
    a = SsiAdapter(futures_meta=futures_meta(["VN30F2612"]))
    (_, f), = a.feed(frame("trade.VN30F2612", s="VN30F2612", b="DER", p=1859.5, q=2, v=1000))
    assert f["stockType"] == "FU" and f["marketCode"] == "FU"
    assert f["maturityDate"] == "2026-12-17" and f["underlyingSymbol"] == "VN30"
    (ch, ix), = a.feed(frame("indexsummary.HNXUPCOMINDEX", s="HNXUPCOMINDEX", v="125.4", c="0.3", cr="0.24", adv=100, dec=80, nc=20))
    assert ch == "marketInfo" and ix["indexCode"] == "UPCOMINDEX" and ix["indexValue"] == 125.4 and ix["advances"] == 100
    assert a.feed(frame("market.flag", b="HOSE", t="09:00:00", f="ATO")) == [("marketSession", {"marketCode": "HOSE", "marketStatus": "ATO"})]
    assert a.feed(frame("market.flag", b="DER", f="LO"))[0][1]["marketCode"] == "FU"


def test_adapter_price_scale():
    a = SsiAdapter(price_scale=1000)
    (_, b), = a.feed(frame("trade.AAA", s="AAA", p="31.25", q=1, v=1))
    assert b["closePrice"] == 31250.0


def test_vn30f_maturity_third_thursday():
    assert vn30f_maturity("VN30F2512") == "2025-12-18"
    assert vn30f_maturity("vn30f2611") == "2026-11-19"
    assert vn30f_maturity("VN30F2613") is None and vn30f_maturity("HPG") is None
    # mã KRX hiện hành: F=2025, G=2026; tháng A/B/C = 10/11/12
    assert vn30f_maturity("41I1GC000") == "2026-12-17"
    assert vn30f_maturity("41i1gb000") == "2026-11-19"
    assert vn30f_maturity("41I1G9000") == "2026-09-17"
    assert vn30f_maturity("41I1F4000") == "2025-04-17"
    assert vn30f_maturity("41I2GC000") is None  # VN100, không phải VN30
    assert vn30f_maturity("41I1GD000") is None


def test_adapter_output_goes_through_existing_ingestor(tmp_path):
    db = Storage(str(tmp_path / "t.sqlite"))
    ing = Ingestor(db, "ssi")
    a = SsiAdapter()
    recv = datetime(2026, 11, 18, 10, 0, tzinfo=VN_TZ).timestamp()
    for fr in (frame("market.VPB", s="VPB", b="HOSE", ce=33800, fl=29400, ref=31600),
               frame("quote.VPB", s="VPB", bids=[[31250, 1000]], asks=[[31300, 2000]]),
               frame("trade.VPB", s="VPB", p=31250, q=100, v=5000, a=31300),
               frame("indexsummary.VN30", s="VN30", v=1900.5, c=5, cr=0.26, adv=20, dec=8, nc=2)):
        for ch, body in a.feed(fr):
            ing.handle(ch, body, recv)
    ing.flush()
    q = db.quotes(source="ssi")
    # ba khung tin của VPB tới cùng một mili-giây -> gộp thành MỘT hàng đầy đủ (không bỏ rơi bản đến sau)
    assert len(q) == 1 and q.iloc[0]["symbol"] == "VPB" and q.iloc[0]["bid1"] == 31250.0 and q.iloc[0]["total_volume"] == 5000
    assert q.iloc[0]["ceiling"] == 33800.0
    assert db.index_ticks(None, None, "ssi").iloc[0]["index_code"] == "VN30"
    assert ing.n_rejected == 0


# -------------------------------------------------------------------- client
def make_client(settings, handler):
    seen = []

    def transport(request):
        seen.append(request)
        if request.url.path == "/api/v3/auth/token":
            body = json.loads(request.content)
            if body != {"apiKey": "key-abcdef", "apiSecret": "sec-xyz"}:
                return httpx.Response(401, json={"message": "bad key"})
            n = sum(1 for r in seen if r.url.path == "/api/v3/auth/token")
            return httpx.Response(200, json={"tokenType": "Bearer", "accessToken": f"tok-{n}", "refreshToken": "r",
                                             "expiresAt": 4102444800, "refreshExpiresAt": 4102531200})
        return handler(request)
    return SsiClient(settings, transport=httpx.MockTransport(transport), sleep=lambda s: None), seen


def test_client_login_get_and_list_shapes(ssi_settings):
    def handler(req):
        assert req.headers["authorization"] == "Bearer tok-1"
        assert req.url.params["index"] == "VN30"
        return httpx.Response(200, json=[{"symbol": "SSI"}, {"symbol": "HPG"}, "bad"])
    c, seen = make_client(ssi_settings, handler)
    assert [m["symbol"] for m in c.securities_by_index("vn30")] == ["SSI", "HPG"]
    assert c.token_expiry == 4102444800.0 and c.request_count == 1


def test_client_wrapped_rows_and_retry_then_success(ssi_settings):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"data": [{"symbol": "X"}], "pageCount": 1})
    c, _ = make_client(ssi_settings, handler)
    assert c.index_summary("VN30") == [{"symbol": "X"}] and calls["n"] == 2


def test_client_relogin_once_on_401_then_auth_error(ssi_settings):
    def handler(req):
        return httpx.Response(401)
    c, seen = make_client(ssi_settings, handler)
    with pytest.raises(SsiAuthError):
        c.securities_by_index("VN30")
    assert sum(1 for r in seen if r.url.path.endswith("/auth/token")) == 2  # đăng nhập lại đúng một lần


def test_client_blocks_trading_and_account_paths(ssi_settings):
    c, seen = make_client(ssi_settings, lambda r: httpx.Response(200, json=[]))
    for path in ("/api/v3/trading/order", "/api/v3/account/info", "/api/v3/trading/accountBalance"):
        with pytest.raises(NeoSafetyError):
            c.get(path)
    assert seen == []  # không có request nào rời máy


def test_client_missing_credentials_and_bad_key(ssi_settings):
    from dataclasses import replace
    with pytest.raises(SsiAuthError):
        SsiClient(replace(ssi_settings, ssi_api_key="")).login()
    c, _ = make_client(replace(ssi_settings, ssi_api_key="wrong"), lambda r: httpx.Response(200, json=[]))
    with pytest.raises(SsiAuthError):
        c.login()


def test_daily_ohlc_paginates(ssi_settings):
    pages = {"1": [{"close": 1}, {"close": 2}], "2": [{"close": 3}]}

    def handler(req):
        return httpx.Response(200, json={"data": pages[req.url.params["pageIndex"]]})
    c, _ = make_client(ssi_settings, handler)
    assert len(c.daily_ohlc("SSI", "2026/11/01 00:00:00", "2026/11/18 23:59:59", page_size=2)) == 3


# -------------------------------------------------------------------- stream
class FakeWS:
    def __init__(self, script):
        self.sent, self._script = [], list(script)

    async def send(self, m):
        self.sent.append(json.loads(m))

    async def recv(self):
        if not self._script:
            raise ConnectionError("server closed")
        if self._script[0] == "HANG":  # treo thật sự: không nhả dữ liệu, kể cả khi bị hủy rồi gọi lại
            await asyncio.sleep(3600)
        item = self._script.pop(0)
        return item if isinstance(item, str) else json.dumps(item)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def run_stream(scripts, topics=("trade.VPB",), **kw):
    sockets, got = [], []

    def connect(url, additional_headers=None):
        ws = FakeWS(scripts[len(sockets)] if len(sockets) < len(scripts) else [])
        ws.url, ws.headers = url, additional_headers
        sockets.append(ws)
        return ws
    stream = SsiStream("wss://x/ws/v3", lambda: "jwt-abc", list(topics), SsiAdapter(),
                       lambda ch, body, ts: got.append((ch, body)), connect=connect, **kw)
    stream.backoff = lambda attempt: 0.0
    asyncio.run(asyncio.wait_for(stream.run(max_sessions=len(scripts)), timeout=5))
    return stream, sockets, got


def test_stream_sends_bearer_header_subscribes_and_delivers():
    script = [frame("market.VPB", s="VPB", ref=31600), frame("trade.VPB", s="VPB", p=31250, q=1, v=10),
              {"method": "SUBSCRIBE", "channel": "DATA", "status": "ok", "message": "subscribed"}]
    stream, sockets, got = run_stream([script])
    assert sockets[0].headers == {"Authorization": "Bearer jwt-abc"}
    assert sockets[0].sent[0] == {"method": "subscribe", "channel": "DATA", "topics": ["trade.VPB"]}
    assert [c for c, _ in got] == ["stockInfo", "stockInfo"] and got[-1][1]["closePrice"] == 31250.0
    assert stream.stats.per_channel == {"stockInfo": 2, "control": 1} and stream.stats.state == "disconnected"


def test_stream_reconnects_and_chunks_subscriptions():
    many = [f"trade.S{i:03d}" for i in range(120)]
    stream, sockets, got = run_stream([[frame("trade.A", s="A", p=1, q=1, v=1)], []], topics=many)
    assert len(sockets) == 2 and stream.stats.reconnects >= 1
    sent = [m for m in sockets[0].sent if m["method"] == "subscribe"]
    assert [len(m["topics"]) for m in sent] == [50, 50, 20]


def test_stream_detects_stale_connection():
    stream, sockets, got = run_stream([["HANG"]], stale_after_s=0.2, ping_every_s=0.05)
    assert stream.stats.last_error and "treo" in stream.stats.last_error
    assert any(m.get("method") == "ping_pong" for m in sockets[0].sent)


def test_stream_reconnects_before_token_expiry():
    clock = {"t": 1000.0}
    stream, sockets, _ = run_stream([["HANG"], []], expiry_provider=lambda: clock["t"] + 60, clock=lambda: clock["t"],
                                    stale_after_s=100, ping_every_s=100)
    assert len(sockets) == 2  # hạn còn < 120s -> thoát phiên ngay để lấy token mới


def test_build_topics():
    t = build_topics(["VPB"], ["VN30F2612"], ["VN30", "UPCOMINDEX"])
    assert t == ["market.flag", "indexsummary.VN30", "indexsummary.UPCOMINDEX",
                 "trade.VN30F2612", "quote.VN30F2612", "trade.VPB", "quote.VPB", "room.VPB"]
    # rổ VN30 + 4 chỉ số + 1 HĐTL vừa dưới giới hạn 100 chủ đề; vượt thì chỉ số vẫn được giữ
    full = build_topics([f"S{i:02d}" for i in range(30)], ["41I1GC000"], ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"])
    assert len(full) == 97
    big = build_topics([f"S{i:02d}" for i in range(40)], [], ["VN30"])
    assert len(big) == 100 and "indexsummary.VN30" in big


# -------------------------------------------------------------------- config
def test_config_ssi_env(monkeypatch, tmp_path):
    for k in ("NEOPULSE_SOURCE", "SSI_API_KEY", "SSI_API_SECRET", "SSI_CONSUMER_ID", "SSI_CONSUMER_SECRET", "NEOPULSE_MODE"):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text("NEOPULSE_MODE=live\nNEOPULSE_SOURCE=ssi\nSSI_API_KEY=k123456\nSSI_API_SECRET=topsecret\nNEOPULSE_FUTURES=vn30f2612\n")
    s = load_settings(env)
    assert s.source == "ssi" and s.live_source == "ssi" and s.has_ssi_credentials and s.futures == ["VN30F2612"]
    red = s.redacted()
    assert red["ssi_api_secret"] == "<đã điền>" and red["ssi_api_key"] == "k123***"
    assert "topsecret" not in json.dumps(red)
    monkeypatch.setenv("NEOPULSE_SOURCE", "bloomberg")
    with pytest.raises(ValueError):
        load_settings(env)


def test_config_legacy_consumer_vars(monkeypatch, tmp_path):
    for k in ("NEOPULSE_SOURCE", "SSI_API_KEY", "SSI_API_SECRET", "NEOPULSE_MODE"):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text("SSI_CONSUMER_ID=old-id\nSSI_CONSUMER_SECRET=old-secret\n")
    monkeypatch.delenv("SSI_CONSUMER_ID", raising=False)
    monkeypatch.delenv("SSI_CONSUMER_SECRET", raising=False)
    s = load_settings(env)
    assert s.ssi_api_key == "old-id" and s.source == "neo"


def test_real_index_frames_from_live_stream_19_11_2026():
    """Khung tin THẬT ghi lại 19/11/2026: indexsummary mang đủ chỉ số; trade.index chỉ có giá trị + khối lượng.

    Lỗi đã gặp: adapter đọc trade.index và lấy `v` (khối lượng lũy kế 55.506.118) làm giá trị VN30.
    """
    a = SsiAdapter()
    summary = {"s": "VN30", "b": "HOSE", "ss": "C", "t": "2026/11/19 10:39:45", "v": "1791.9", "c": "-14.64",
               "cr": "-0.81", "adv": "3", "dec": "23", "nc": "4", "ce": "0", "fl": "0", "tmv": "1677247419150",
               "tmq": "56290474", "tvp": "802089600", "tqp": "40032", "tq": "56330506", "tv": "1678049508750"}
    (ch, ix), = a.feed({"channel": "DATA", "topic": "indexsummary.VN30", "data": summary})
    assert ch == "marketInfo" and ix["indexCode"] == "VN30"
    assert ix["indexValue"] == 1791.9 and ix["indexChange"] == -14.64 and ix["indexPercentChange"] == -0.81
    assert (ix["advances"], ix["declines"], ix["noChange"], ix["numberOfCe"], ix["numberOfFl"]) == (3, 23, 4, 0, 0)
    assert ix["totalVolume"] == 56330506 and ix["totalValue"] == 1678049508750
    up = dict(summary, s="HNXUPCOMINDEX", b="UPCOM", v="120.5")
    (_, u), = a.feed({"channel": "DATA", "topic": "indexsummary.HNXUPCOMINDEX", "data": up})
    assert u["indexCode"] == "UPCOMINDEX" and u["indexValue"] == 120.5
    trade = {"s": "VN30", "t": "2026/11/19 10:38:30.000", "p": "1791.18", "q": "198038", "a": "29857.8", "si": "",
             "o": "0", "h": "0", "l": "0", "v": "55506118"}
    assert a.feed({"channel": "DATA", "topic": "trade.index.VN30", "data": trade}) == []   # không bao giờ ra marketInfo sai


def test_preload_master_fills_ref_ceiling_floor_from_rest():
    """19/11/2026: market.<mã> không gửi trần/sàn/tham chiếu trong phiên -> nạp từ REST masterdata."""
    a = SsiAdapter(futures_meta=futures_meta(["41I1GC000"]))
    a.watch = {"FPT"}
    rows = [{"board": "HOSE", "symbol": "FPT", "tradingDate": "2026/11/19", "ceiling": 50200, "floor": 43700, "refPrice": 46950},
            {"board": "DERIVATIVES", "symbol": "41I1GC000", "tradingDate": "2026/11/19", "ceiling": 1934.5,
             "floor": 1681.5, "refPrice": 1808},
            {"board": "HOSE", "symbol": "KHONGTHEODOI", "ceiling": 1, "floor": 1, "refPrice": 1}]
    assert a.preload_master(rows) == 2
    (_, b), = a.feed(frame("trade.FPT", s="FPT", p="46700", q="3300", a="47069.88", v="4294000"))
    assert (b["refPrice"], b["ceilingPrice"], b["floorPrice"]) == (46950.0, 50200.0, 43700.0)
    assert b["percentPriceChange"] == pytest.approx((46700 - 46950) / 46950 * 100)
    (_, f), = a.feed(frame("trade.41I1GC000", s="41I1GC000", p="1797.6", q="1", v="100"))
    assert f["refPrice"] == 1808.0 and f["stockType"] == "FU"
    assert "KHONGTHEODOI" not in a._state


def test_client_masterdata_walks_all_pages():
    pages = {1: [{"symbol": "A"}], 2: [{"symbol": "B"}], 3: [{"symbol": "C"}]}

    def handler(req):
        if req.url.path.endswith("/auth/token"):
            return httpx.Response(200, json={"data": {"accessToken": "t", "expiresAt": 9e12}})
        p = int(req.url.params["pageIndex"])
        return httpx.Response(200, json={"code": 200, "pagesCount": 3, "pageIndex": p, "data": pages[p]})
    s = Settings(mode="live", source="ssi", ssi_api_key="k", ssi_api_secret="s", ssi_max_rps=10)
    with SsiClient(s, transport=httpx.MockTransport(handler)) as c:
        assert [r["symbol"] for r in c.masterdata()] == ["A", "B", "C"]
