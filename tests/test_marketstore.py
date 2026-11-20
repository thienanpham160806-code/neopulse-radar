import json
from types import SimpleNamespace

import httpx

from neopulse.analytics import marketstore as ms


def test_snapshot_daily_keys_derived_payload_only_and_throttle(monkeypatch):
    def payload(view, _db):
        return {"meta": {"source": view.source, "index_code": view.index_code, "trading_date": view.trading_date}, "pulse": {"score": 55}}

    monkeypatch.setattr(ms.wx, "payload_from_view", payload)
    monkeypatch.setattr(ms.wx, "build_payload", lambda *_a: {"meta": {"trading_date": "2026-11-20"}})
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=[{"result": "OK"}, {"result": "OK"}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        store = ms.MarketSnapshots("https://kv.test", "test-secret", client=client, mono=lambda: 10)
        view = SimpleNamespace(source="ssi", status="ok", index_code="VN30", trading_date="2026-11-20")
        store(view, object())
        store(view, object())
        assert len(calls) == 1
        commands = calls[0]
        assert [r[1] for r in commands] == ["neopulse:market:latest:VN30", "neopulse:market:session:2026-11-20:VN30"]
        assert all(r[0] == "SETEX" and r[2] == ms.TTL for r in commands)
        assert "test-secret" not in str(commands)
        view.source = "sim"
        store.next_write = 0
        store(view, object())
        assert len(calls) == 1
