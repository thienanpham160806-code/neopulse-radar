import sqlite3
from datetime import datetime, timezone

import pytest

from neopulse.analytics import cloud_recorder as cloud
from neopulse.timeutil import VN_TZ


def at(day="2026-11-23", hour=9, minute=0):
    return datetime.fromisoformat(f"{day}T{hour:02}:{minute:02}:00").replace(tzinfo=VN_TZ)


@pytest.mark.parametrize("now,holidays,expected", [
    (at(hour=8, minute=49), set(), False), (at(hour=8, minute=50), set(), True),
    (at(hour=12), set(), True), (at(hour=15, minute=10), set(), False),
    (at(day="2026-11-28"), set(), False), (at(), {"2026-11-23"}, False),
    (datetime(2026, 11, 23, 1, 50, tzinfo=timezone.utc), set(), True),
])
def test_window_is_in_vietnam_time(now, holidays, expected):
    assert cloud.in_session_window(now, holidays) is expected


class Child:
    def __init__(self, command):
        self.command, self.code, self.terminated = command, None, False

    def poll(self):
        return self.code

    def terminate(self):
        self.terminated, self.code = True, 0

    def wait(self, timeout):
        return self.code


def test_supervisor_avoids_duplicates_and_leaves_time_for_final_publication(monkeypatch, tmp_path):
    launched, backups = [], []

    def launch(command):
        child = Child(command)
        launched.append(child)
        return child

    monkeypatch.setattr(cloud.subprocess, "Popen", launch)
    monkeypatch.setattr(cloud, "backup_database", backups.append)
    runner = cloud.Supervisor(tmp_path / "record.sqlite", set())
    runner.step(at(), 0)
    runner.step(at(), 5)
    assert len(launched) == 2
    assert "15:05" in launched[0].command and "15:10" in launched[1].command
    runner.step(at(hour=15, minute=5), 100)
    assert launched[0].terminated and not launched[1].terminated
    runner.step(at(hour=15, minute=10), 400)
    runner.step(at(hour=16), 500)
    assert launched[1].terminated and len(backups) == 1
    runner.step(at(day="2026-11-24"), 1000)
    assert len(launched) == 4


def test_failed_child_is_retried_with_backoff_not_per_poll(monkeypatch, tmp_path):
    launched = []

    def launch(command):
        child = Child(command)
        launched.append(child)
        return child

    monkeypatch.setattr(cloud.subprocess, "Popen", launch)
    runner = cloud.Supervisor(tmp_path / "record.sqlite", set())
    runner.step(at(), 0)
    launched[0].code = 1
    runner.step(at(), 5)
    runner.step(at(), 9)
    assert len(launched) == 2
    runner.step(at(), 10)
    assert len(launched) == 3 and runner.children["live-relay"] is launched[1]
    runner.stop()


def test_backup_includes_wal_and_keeps_previous_when_source_is_corrupt(tmp_path):
    db = tmp_path / "record.sqlite"
    source = sqlite3.connect(db)
    source.execute("PRAGMA journal_mode=WAL")
    source.execute("CREATE TABLE proof (value INTEGER)")
    source.execute("INSERT INTO proof VALUES (42)")
    source.commit()
    cloud.backup_database(db)
    output = tmp_path / "backups/latest.sqlite"
    with sqlite3.connect(output) as saved:
        assert saved.execute("SELECT value FROM proof").fetchone() == (42,)
    source.close()
    previous = output.read_bytes()
    db.write_bytes(b"broken sqlite input")
    with pytest.raises(sqlite3.DatabaseError):
        cloud.backup_database(db)
    assert output.read_bytes() == previous
    assert not output.with_suffix(".tmp").exists()


def test_preflight_refuses_unconfirmed_storage_without_exposing_keys(monkeypatch, tmp_path):
    from neopulse.config import Settings
    settings = Settings(mode="live", source="ssi", db_path=str(tmp_path / "live.sqlite"),
                        ssi_api_key="test-key", ssi_api_secret="test-secret", ably_api_key="test-ably")
    monkeypatch.setattr(cloud, "load_settings", lambda: settings)
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.test")
    monkeypatch.setenv("KV_REST_API_TOKEN", "test-kv")
    monkeypatch.delenv("NEOPULSE_PERSISTENCE_CONFIRMED", raising=False)
    with pytest.raises(ValueError, match="persistent storage"):
        cloud.preflight()
    monkeypatch.setenv("NEOPULSE_PERSISTENCE_CONFIRMED", "1")
    assert cloud.preflight() == tmp_path / "live.sqlite"
    monkeypatch.delenv("KV_REST_API_TOKEN")
    with pytest.raises(ValueError, match="KV_REST_API_TOKEN") as error:
        cloud.preflight()
    assert "test-secret" not in str(error.value) and "test-key" not in str(error.value)
