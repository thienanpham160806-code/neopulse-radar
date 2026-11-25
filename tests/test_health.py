from datetime import datetime

import pytest

from neopulse.analytics import health
from neopulse.timeutil import VN_TZ


def at(d, h, m):
    return datetime(2026, 11, d, h, m, tzinfo=VN_TZ).timestamp()


def payload(last):
    return {"meta": {"last_update": last.isoformat(), "is_simulated": False}}


class FakeStore:
    def __init__(self):
        self.keys = {}
        self.ttls = {}

    def call(self, *args):
        if args[0] == "SET":
            assert "NX" in args
            if args[1] in self.keys:
                return None
            self.keys[args[1]] = args[2]
            self.ttls[args[1]] = int(args[-1])
            return "OK"
        assert args[0] == "EVAL" and args[2] == 1
        key, claim, outcome = args[3:]
        if self.keys.get(key) != claim:
            return 0
        if outcome == "sent":
            self.keys[key], self.ttls[key] = "sent", 86400
            return "OK"
        del self.keys[key]
        self.ttls.pop(key)
        return 1


def test_no_data_by_0905_and_only_on_weekdays_in_session():
    old = payload(datetime(2026, 11, 25, 14, 56, tzinfo=VN_TZ))
    assert health.recorder_issue(old, at(26, 9, 4)) is None  # chưa tới 09:05
    marker, text = health.recorder_issue(old, at(26, 9, 5))
    assert marker == "no_data|2026-11-26" and "chưa ghi dữ liệu phiên 26/11" in text
    assert health.recorder_issue(None, at(26, 9, 30))[0] == "no_data|2026-11-26"
    assert health.recorder_issue({"meta": {"last_update": "2026-11-26T09:30:00+07:00", "is_simulated": True}},
                                 at(26, 9, 31))[0] == "no_data|2026-11-26"  # dữ liệu mô phỏng không tính
    assert health.recorder_issue(old, at(28, 10, 0)) is None  # thứ Bảy
    assert health.recorder_issue(old, at(26, 12, 0)) is None and health.recorder_issue(old, at(26, 14, 50)) is None


def test_silence_counts_trading_minutes_not_lunch():
    fresh = payload(datetime(2026, 11, 26, 10, 0, tzinfo=VN_TZ))
    assert health.recorder_issue(fresh, at(26, 10, 5)) is None
    marker, text = health.recorder_issue(fresh, at(26, 10, 6))
    assert marker == "silent|2026-11-26T10:00:00+07:00" and "im lặng 6 phút" in text and "10:00" in text
    before_lunch = payload(datetime(2026, 11, 26, 11, 30, tzinfo=VN_TZ))
    assert health.recorder_issue(before_lunch, at(26, 13, 5)) is None  # nghỉ trưa không tính là im lặng
    assert health.recorder_issue(before_lunch, at(26, 13, 6))[0].startswith("silent|")


def test_notify_owner_once_per_incident_and_needs_chat(monkeypatch):
    sent, store = [], FakeStore()
    old = payload(datetime(2026, 11, 25, 14, 56, tzinfo=VN_TZ))
    monkeypatch.delenv("TELEGRAM_OWNER_CHAT_ID", raising=False)
    assert not health.notify_owner(old, at(26, 9, 10), store, lambda c, t: sent.append(c))
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    assert health.notify_owner(old, at(26, 9, 10), store, lambda c, t: sent.append(c))
    assert not health.notify_owner(old, at(26, 9, 15), store, lambda c, t: sent.append(c))
    assert sent == ["42"]


def test_failed_delivery_can_retry_and_only_success_gets_daily_dedup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    store = FakeStore()
    old = payload(datetime(2026, 11, 25, 14, 56, tzinfo=VN_TZ))

    def fail(_chat, _text):
        assert list(store.ttls.values()) == [120]
        raise RuntimeError("Telegram unavailable")

    with pytest.raises(RuntimeError, match="Telegram unavailable"):
        health.notify_owner(old, at(26, 9, 10), store, fail)
    assert not store.keys
    assert health.notify_owner(old, at(26, 9, 11), store, lambda *_: {"message_id": 1})
    assert list(store.ttls.values()) == [86400]
    assert not health.notify_owner(old, at(26, 9, 12), store, fail)


def test_blocked_owner_is_not_reported_as_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    store = FakeStore()
    assert not health.notify_owner(None, at(26, 9, 10), store, lambda *_: {"blocked": True})
    assert not store.keys


def test_expired_claim_does_not_remove_another_senders_claim(monkeypatch):
    monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "42")
    store = FakeStore()

    def fail_after_claim_replaced(*_):
        key = next(iter(store.keys))
        store.keys[key] = "another-sender"
        raise RuntimeError("slow failed send")

    with pytest.raises(RuntimeError, match="slow failed send"):
        health.notify_owner(None, at(26, 9, 10), store, fail_after_claim_replaced)
    assert list(store.keys.values()) == ["another-sender"]
