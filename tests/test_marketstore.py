import json
from concurrent.futures import Future
from types import SimpleNamespace

import httpx

from neopulse.analytics import marketstore as ms


class Deferred:
    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        future = Future()
        self.jobs.append((fn, args, future))
        return future

    def shutdown(self, **_kwargs):
        pass


def test_snapshot_daily_keys_derived_payload_only_and_throttle(monkeypatch):
    def payload(view, _db, **kwargs):
        return {"meta": {"source": view.source, "index_code": view.index_code, "trading_date": view.trading_date}, "pulse": {"score": 55}, **(kwargs.get("extras") or {})}

    monkeypatch.setattr(ms.wx, "payload_from_view", payload)
    monkeypatch.setattr(ms.wx, "build_payload", lambda *_a, **_kw: {"meta": {"trading_date": "2026-11-20"}})
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=[{"result": "OK"}, {"result": "OK"}])

    pool = Deferred()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        store = ms.MarketSnapshots("https://kv.test", "test-secret", client=client, mono=lambda: 10, executor=pool)
        view = SimpleNamespace(source="ssi", status="ok", index_code="VN30", trading_date="2026-11-20")
        store(view, SimpleNamespace(path="test.sqlite"))
        store(view, SimpleNamespace(path="test.sqlite"))
        assert len(calls) == 1
        commands = calls[0]
        assert [r[1] for r in commands] == ["neopulse:market:latest:VN30", "neopulse:market:session:2026-11-20:VN30"]
        assert all(r[0] == "SETEX" and r[2] == ms.TTL for r in commands)
        assert "test-secret" not in str(commands)
        pool.jobs[0][2].set_result({"data_quality": {"n_sessions": 2}})
        store.next_write, view.status = 0, "stale"
        store(view, SimpleNamespace(path="test.sqlite"))
        assert json.loads(calls[-1][0][3])["validation"]["data_quality"]["n_sessions"] == 2
        view.source = "sim"
        store.next_write = 0
        store(view, object())
        assert len(calls) == 2


def test_validation_is_nonblocking_cached_for_ten_minutes_and_scoped_to_session():
    now, pool = [10], Deferred()
    with httpx.Client() as client:
        store = ms.MarketSnapshots("https://kv.test", "secret", client=client, mono=lambda: now[0], executor=pool)
        view = SimpleNamespace(source="ssi", trading_date="2026-11-20")
        db = SimpleNamespace(path="market.sqlite")
        assert store.validation_extras(view, db) is None
        assert len(pool.jobs) == 1 and not pool.jobs[0][2].done()
        block = {"source": "ssi", "data_quality": {"n_sessions": 2}}
        pool.jobs[0][2].set_result(block)
        assert store.validation_extras(view, db) == {"validation": block}
        now[0] = 609
        assert store.validation_extras(view, db) == {"validation": block}
        assert len(pool.jobs) == 1
        now[0] = 610
        assert store.validation_extras(view, db) == {"validation": block}
        pool.jobs[1][2].set_exception(RuntimeError("calculation failed"))
        assert store.validation_extras(view, db) == {"validation": block}
        assert store._validation_due <= 670
        view.trading_date = "2026-11-21"
        assert store.validation_extras(view, db) is None
        assert len(pool.jobs) == 3


def test_telegram_trigger_is_optional_and_sends_secret(monkeypatch):
    calls = []
    monkeypatch.delenv("TELEGRAM_TICK_SECRET", raising=False)
    assert ms.trigger_telegram() is None
    monkeypatch.setenv("TELEGRAM_TICK_SECRET", "s3")
    monkeypatch.setattr(ms.httpx, "post", lambda url, headers, timeout: calls.append((url, headers)))
    ms.trigger_telegram().join(2)
    assert calls == [(ms.TICK_URL, {"Authorization": "Bearer s3"})]

    def boom(*_a, **_k):
        raise ms.httpx.ConnectError("down")
    monkeypatch.setattr(ms.httpx, "post", boom)
    ms.trigger_telegram().join(2)  # lỗi mạng không lan ra bộ phát
