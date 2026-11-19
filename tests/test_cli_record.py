"""`neopulse record --flush-every`: truyền đúng nhịp ghi lô xuống bộ ghi, kiểm tra miền giá trị."""
import pytest

from neopulse import cli


def _capture(monkeypatch):
    seen = {}

    async def fake_record_ssi(settings, *, until=None, flush_every_s=5.0, raw_dump_dir="raw_dump"):
        seen["flush"] = flush_every_s
        return {}
    monkeypatch.setattr("neopulse.data.recorder_ssi.record_ssi", fake_record_ssi)
    monkeypatch.setenv("NEOPULSE_MODE", "live")
    monkeypatch.setenv("NEOPULSE_SOURCE", "ssi")
    monkeypatch.setenv("SSI_API_KEY", "k")
    monkeypatch.setenv("SSI_API_SECRET", "s")
    return seen


def test_flush_every_default_is_5(monkeypatch, tmp_path):
    seen = _capture(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["record", "--until", "00:00"]) == 0
    assert seen["flush"] == 5.0


def test_flush_every_passed_through(monkeypatch, tmp_path):
    seen = _capture(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["record", "--until", "00:00", "--flush-every", "1"]) == 0
    assert seen["flush"] == 1.0


@pytest.mark.parametrize("bad", ["0", "-1", "61", "abc"])
def test_flush_every_rejects_out_of_range(bad, monkeypatch, tmp_path):
    _capture(monkeypatch)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["record", "--flush-every", bad])
