"""live-relay: định dạng tin, chỉ gửi khi đổi, giãn nhịp theo hạn mức, lỗi mạng giả lập, không lộ khóa."""
import json
from datetime import date, datetime

import httpx
import pytest

from neopulse.analytics import liverelay as lr
from neopulse.cli import main as cli_main
from neopulse.data.storage import Storage
from neopulse.neo_api.sim import simulate_sessions
from neopulse.timeutil import VN_TZ

FAKE_KEY = "appId.keyId:SeCrEtValue123"


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("live") / "l.sqlite"
    d = Storage(p)
    simulate_sessions(d, 2, end=date(2026, 11, 13), step_seconds=60, symbols=None)
    d.close()
    return p


class Mem:
    def __init__(self, ok=True):
        self.msgs, self.ok = [], ok

    def publish(self, name, data):
        self.msgs.append((name, data))
        return self.ok

    def close(self):
        pass


class Clock:
    """Đồng hồ giả: mono tăng theo sleep; giờ VN cố định trong giờ giao dịch."""

    def __init__(self):
        self.t = 0.0

    def mono(self):
        return self.t

    def sleep(self, s):
        self.t += max(s, 0.001)

    def now(self):
        return datetime(2026, 11, 13, 10, 0, tzinfo=VN_TZ)


def make(db_path, tmp_path, pub, *, speed=60.0, viewers=5, sent=0):
    c = Clock()
    usage = lr.UsageGuard(tmp_path / "u.json", viewers, month="2026-11", sent=sent)
    r = lr.LiveRelay(str(db_path), "sim", pub, usage, replay_speed=speed, clock=c.now, mono=c.mono, sleep=c.sleep)
    return r, c


# ----------------------------------------------------------------------------- định dạng
def test_message_envelope_and_sizes(db_path, tmp_path):
    pub = Mem()
    r, _ = make(db_path, tmp_path, pub)
    r.run(max_loops=30)
    names = [n for n, _ in pub.msgs]
    assert names[0] == "status" and names[-1] == "status" and "tick" in names and "pulse" in names
    seqs = [d["seq"] for _, d in pub.msgs]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)            # seq tăng dần, không trùng
    for name, d in pub.msgs:
        assert d["ts"].endswith("+07:00") and d["source"] == "sim" and d["is_simulated"] is True
        text = json.dumps(d, ensure_ascii=False)
        if name == "tick":
            assert len(text.encode()) < 2048                                 # tick < 2 KB
            assert set(d["ix"]) <= set(lr.INDEX_CODES) and "VN30" in d["ix"]
            assert set(d["ix"]["VN30"]) == {"v", "ch", "pct", "adv", "dec", "nc", "ce", "fl"}
        for raw in ("bid1", "ask1", "bid_vol", "ask_vol"):
            assert raw not in text                                           # không phát sổ lệnh thô
    pulse = next(d for n, d in pub.msgs if n == "pulse")
    assert 0 <= pulse["score"] <= 100 and len(pulse["comps"]) == 5 and len(pulse["up"]) <= 5 and len(pulse["down"]) <= 5
    events = [d["event"] for n, d in pub.msgs if n == "status"]
    assert events[0] == "start" and events[-1] == "end"


def test_tick_only_sent_when_changed(db_path, tmp_path):
    pub = Mem()
    r, _ = make(db_path, tmp_path, pub, speed=0.0)                           # không phát lại -> dữ liệu đứng yên
    r.run(max_loops=8)
    assert [n for n, _ in pub.msgs].count("tick") == 1 and r.stats.skipped_unchanged == 7


def test_new_alerts_are_sent_once(db_path, tmp_path):
    pub = Mem()
    r, c = make(db_path, tmp_path, pub, speed=600.0)
    r.run(max_loops=400)
    keys = [(a["t"], a["s"], a["rule"]) for n, d in pub.msgs if n == "pulse" for a in d["alerts"]]
    assert keys and len(keys) == len(set(keys))


# ----------------------------------------------------------------------------- hạn mức
def test_usage_estimate_and_slowdown(db_path, tmp_path, caplog):
    g = lr.UsageGuard(tmp_path / "u.json", viewers=5, month="2026-11", sent=699_000)
    assert g.estimated == 699_000 * 6 and g.factor() == 1
    g.sent = 700_001                                                         # 700.001 x 6 > 70% của 6.000.000
    with caplog.at_level("WARNING"):
        assert g.factor() == 5
    assert "GIÃN NHỊP" in caplog.text
    pub = Mem()
    r, c = make(db_path, tmp_path, pub, sent=800_000)
    r.run(max_loops=3)
    assert c.t >= 2 * 5 * 0.99                                               # mỗi vòng ngủ 5 x 1 giây
    assert r.stats.pulse_every_s >= 30


def test_usage_file_persists_and_resets_each_month(tmp_path):
    g = lr.UsageGuard(tmp_path / "u.json", 5, month="2026-11", sent=123)
    g.save()
    assert lr.UsageGuard.load(tmp_path / "u.json", 5, month="2026-11").sent == 123
    assert lr.UsageGuard.load(tmp_path / "u.json", 5, month="2026-12").sent == 0
    assert lr.UsageGuard.load(tmp_path / "khong_co.json", 5, month="2026-11").sent == 0


# ----------------------------------------------------------------------------- mạng
def test_ably_publisher_request_shape_and_no_key_leak(caplog):
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(201, json={})
    p = lr.AblyPublisher(FAKE_KEY, transport=httpx.MockTransport(handler), sleep=lambda s: None)
    assert p.publish("tick", {"a": 1})
    req = seen[0]
    assert req.method == "POST" and req.url.raw_path == b"/channels/neopulse%3Alive/messages"
    assert req.headers["authorization"].startswith("Basic ")
    body = json.loads(req.content)
    assert body["name"] == "tick" and json.loads(body["data"]) == {"a": 1}
    assert FAKE_KEY not in caplog.text and "SeCrEt" not in caplog.text


def test_ably_retries_then_gives_up_without_crash(caplog):
    calls = {"n": 0}

    def down(req):
        calls["n"] += 1
        raise httpx.ConnectError("mạng rớt")
    waits = []
    p = lr.AblyPublisher(FAKE_KEY, transport=httpx.MockTransport(down), sleep=waits.append, max_retries=2)
    with caplog.at_level("WARNING"):
        assert p.publish("tick", {}) is False
    assert calls["n"] == 3 and waits == [0.5, 1.0] and "SeCrEt" not in caplog.text


def test_ably_auth_error_is_fatal_and_bad_key_rejected():
    p = lr.AblyPublisher(FAKE_KEY, transport=httpx.MockTransport(lambda r: httpx.Response(401)), sleep=lambda s: None)
    with pytest.raises(lr.LiveRelayError) as e:
        p.publish("tick", {})
    assert "SeCrEt" not in str(e.value)
    with pytest.raises(lr.LiveRelayError):
        lr.AblyPublisher("khong-dung-dinh-dang")


def test_relay_survives_network_outage_with_backoff(db_path, tmp_path):
    pub = Mem(ok=False)
    r, _ = make(db_path, tmp_path, pub)
    st = r.run(max_loops=20)
    assert st.failed > 0 and sum(st.sent.values()) == 0
    ticks_tried = [n for n, _ in pub.msgs].count("tick")
    assert ticks_tried < 20                                                  # lùi dần: không dội 20 lần liên tiếp


def test_data_gap_status(db_path, tmp_path):
    pub = Mem()
    r, c = make(db_path, tmp_path, pub, speed=0.0)
    r.clock = lambda: datetime(2026, 11, 13, 10, 0, tzinfo=VN_TZ)
    r.replay_speed = 0.0
    r.run(max_loops=2)
    # dữ liệu mô phỏng ngày 13/11 nhưng "bây giờ" là 10:00 -> bản ghi cuối (14:30) ở TƯƠNG LAI: không phải mất dữ liệu
    assert all(d.get("event") != "data_gap" for n, d in pub.msgs if n == "status")
    pub2 = Mem()
    r2, _ = make(db_path, tmp_path, pub2, speed=0.0)
    r2.clock = lambda: datetime(2026, 11, 13, 14, 50, tzinfo=VN_TZ)
    r2.run(max_loops=2)
    assert any(d.get("event") == "data_gap" for n, d in pub2.msgs if n == "status")


# ----------------------------------------------------------------------------- CLI
def test_cli_dry_run_and_missing_key(db_path, tmp_path, monkeypatch):
    monkeypatch.setenv("NEOPULSE_DB_PATH", str(db_path))
    monkeypatch.setenv("NEOPULSE_MODE", "sim")
    monkeypatch.delenv("ABLY_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["live-relay", "--source", "sim", "--until", "00:00", "--dry-run"]) == 0
    lines = (tmp_path / "out" / "live_dryrun.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["name"] == "status" and (tmp_path / "out" / "ably_usage.json").exists()
    assert cli_main(["live-relay", "--source", "sim", "--until", "00:00"]) == 2


def test_replay_first_loop_has_ticks_and_no_false_gap(db_path, tmp_path):
    pub = Mem()
    r, _ = make(db_path, tmp_path, pub, speed=10.0)
    r.run(max_loops=1)
    names = [n for n, _ in pub.msgs]
    assert "tick" in names and all(d.get("event") != "data_gap" for n, d in pub.msgs if n == "status")


def _view_with_alerts(n):
    """SessionView giả có n cảnh báo CAO khác nhau."""
    import pandas as pd

    from neopulse.analytics.view import SessionView
    from neopulse.finance.pulse import combine
    v = SessionView("sim", "2026-11-13", "VN30", status="ok")
    v.pulse = combine({"breadth": 0.1, "momentum": 0.1, "book": 0.0, "foreign": 0.0})
    ts = pd.Timestamp("2026-11-13T10:00:00+07:00")
    v.alerts = pd.DataFrame({"ts": [ts + pd.Timedelta(minutes=i) for i in range(n)], "symbol": [f"M{i:02d}" for i in range(n)],
                             "rule": "volume_spike", "severity": "CAO", "message": "m", "value": 5.0, "threshold": 3.5})
    return v


def test_cx003_alerts_beyond_10_are_sent_in_next_pulse_not_lost():
    v = _view_with_alerts(12)
    sent = set()
    p1 = lr.pulse_payload(v, sent)
    assert len(p1["alerts"]) == 10 and p1["n_pending"] == 12 and not sent       # dựng gói không đánh dấu
    sent.update(lr.alert_key(a) for a in p1["alerts"])                          # Ably đã nhận gói 1
    p2 = lr.pulse_payload(v, sent)
    assert [a["s"] for a in p2["alerts"]] == ["M10", "M11"]                     # 2 cảnh báo còn lại không bị mất


def test_cx003_failed_send_keeps_alerts_for_retry(db_path, tmp_path):
    pub = Mem(ok=False)
    r, c = make(db_path, tmp_path, pub, speed=600.0)
    r.run(max_loops=200)
    assert not r._sent_alerts                                                   # gửi lỗi -> không cảnh báo nào bị coi đã gửi
    pub.ok = True
    r2 = r
    r2._next_send_ok = 0.0
    r2.run(max_loops=200)
    assert r2._sent_alerts                                                      # mạng có lại -> cảnh báo được gửi
    keys = [lr.alert_key(a) for n, d in pub.msgs if n == "pulse" for a in d["alerts"]]
    assert keys


def test_cx004_basis_pairs_index_tick_not_later_than_future(tmp_path):
    d = Storage(tmp_path / "b.sqlite")
    rows = [{"ts": f"2026-11-19T10:00:0{s}.000+07:00", "trading_date": "2026-11-19", "index_code": "VN30", "source": "sim",
             "value": 1800.0, "pct_change": 0.1} for s in (0, 5)]
    d.insert_index(rows)
    d.insert_quotes([{"ts": "2026-11-19T10:00:02.000+07:00", "trading_date": "2026-11-19", "symbol": "41I1GC000",
                      "instrument": "future", "source": "sim", "last": 1805.0, "maturity_date": "2026-12-17"}])
    d.close()
    from neopulse.analytics.webexport import ReadOnlyStorage
    b = lr.basis_snapshot(ReadOnlyStorage(tmp_path / "b.sqlite"), "sim", "2026-11-19")
    assert b is not None and b["b"] == 5.0 and b["s"] == 1800.0
