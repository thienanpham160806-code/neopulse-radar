"""Xuất JSON cho web + đẩy Vercel Blob: schema, NaN->null, không bí mật, nhãn mô phỏng, dry-run, lỗi mạng."""
import json
import sqlite3
from datetime import date, datetime

import httpx
import numpy as np
import pandas as pd
import pytest

from neopulse.analytics import webexport as wx
from neopulse.analytics import webpublish as wp
from neopulse.cli import main as cli_main
from neopulse.config import Settings
from neopulse.data.storage import Storage
from neopulse.neo_api.sim import simulate_sessions
from neopulse.timeutil import VN_TZ

FAKE_TOKEN = "vercel_blob_rw_STOREID123_SeCrEtPart"
SECRET_WORDS = ("password", "secret", "token", "api_key", "apikey", "authorization", FAKE_TOKEN)


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("web") / "web.sqlite"
    d = Storage(p)
    simulate_sessions(d, 6, end=date(2026, 11, 13), step_seconds=60, symbols=None)
    d.close()
    return p


@pytest.fixture(scope="module")
def ro(db_path):
    return wx.ReadOnlyStorage(db_path)


@pytest.fixture(scope="module")
def payload(ro):
    extras = {"validation": wx.build_validation_block(ro, "sim")}
    return json.loads(wx.dumps(wx.build_payload(ro, "sim", None, "VN30", extras=extras,
                                                now=datetime(2026, 11, 13, 16, 0, tzinfo=VN_TZ))))


# ----------------------------------------------------------------------------- schema & nội dung
def test_schema_blocks_and_version(payload):
    assert payload["meta"]["schema_version"] == wx.SCHEMA_VERSION == 1
    for k in ("meta", "pulse", "index", "breadth", "ranking", "alerts", "book", "foreign", "futures", "validation"):
        assert k in payload
    m = payload["meta"]
    assert m["trading_date"] == "2026-11-13" and m["index_code"] == "VN30" and m["n_sessions"] == 6
    assert m["generated_at"].endswith("+07:00") and m["last_update"].endswith("+07:00")
    assert m["n_symbols_computed"] == 30 and m["n_symbols_excluded"] == 0
    assert "lời khuyên đầu tư" in m["disclaimer"]
    assert payload["pulse"]["score"] is not None and 0 <= payload["pulse"]["score"] <= 100
    assert [c["key"] for c in payload["pulse"]["components"]] == ["breadth", "momentum", "book", "foreign", "liquidity"]
    assert sum(c["weight"] for c in payload["pulse"]["components"]) == pytest.approx(1.0)
    assert payload["futures"]["available"] and payload["futures"]["series"]
    assert payload["alerts"]["total"] == sum(payload["alerts"]["by_severity"].values())


def test_simulated_label_and_status(payload):
    m = payload["meta"]
    assert m["is_simulated"] is True and m["source_label"] == "MÔ PHỎNG"
    assert m["data_status"]["state"] == "fresh" and "MÔ PHỎNG" in m["data_status"]["reason"]
    assert payload["validation"]["simulated_signals_are_planted"] is True


def test_no_raw_ticks_and_bounded_sizes(payload):
    # chỉ chỉ báo tổng hợp: không có cột sổ lệnh thô (giá/KL từng mức) ở bất kỳ đâu
    text = json.dumps(payload)
    for raw in ("bid1", "ask1", "bid_vol", "ask_vol", "bidPrice", "askPrice"):
        assert raw not in text
    assert len(payload["ranking"]) <= wx.MAX_RANK and len(payload["alerts"]["items"]) <= wx.MAX_ALERTS
    assert len(payload["book"]["series"]) <= wx.MAX_SERIES_SYMBOLS
    for cols in payload["book"]["series"].values():
        assert set(cols) == {"t", "mid", "obi3"} and len(cols["t"]) == len(cols["mid"]) == len(cols["obi3"])
        assert len(cols["t"][0]) == 5 and cols["t"][0][2] == ":"


def test_no_secrets_in_output(payload):
    text = wx.dumps(payload).lower()
    for w in SECRET_WORDS:
        assert w.lower() not in text


# ----------------------------------------------------------------------------- làm sạch
def test_clean_nan_inf_and_types():
    out = wx.clean({"a": float("nan"), "b": np.inf, "c": np.float64("-inf"), "d": np.int64(3), "e": np.bool_(True),
                    "f": pd.Timestamp("2026-11-13T10:00:00+07:00"), "g": [np.nan, 1.5], "h": pd.NaT, "i": date(2026, 11, 13)})
    assert out == {"a": None, "b": None, "c": None, "d": 3, "e": True, "f": "2026-11-13T10:00:00.000+07:00",
                   "g": [None, 1.5], "h": None, "i": "2026-11-13"}
    assert isinstance(out["d"], int) and out["e"] is True
    json.loads(wx.dumps({"x": float("nan"), "y": [np.inf]}))     # allow_nan=False: không ném lỗi sau khi làm sạch


# ----------------------------------------------------------------------------- trạng thái dữ liệu
def _view(**kw):
    from neopulse.analytics.view import SessionView
    base = dict(source="ssi", trading_date="2026-11-19", index_code="VN30", status="ok",
                status_message="Đang nhận dữ liệu.", age_seconds=5.0)
    base.update(kw)
    return SessionView(**base)


@pytest.mark.parametrize("hh,mm,weekday_date,phase", [
    (8, 30, (2026, 11, 19), "pre"), (10, 0, (2026, 11, 19), "open"), (12, 0, (2026, 11, 19), "lunch"),
    (14, 59, (2026, 11, 19), "open"), (15, 30, (2026, 11, 19), "closed"), (10, 0, (2026, 11, 21), "closed")])
def test_session_phase(hh, mm, weekday_date, phase):
    assert wx.session_phase(datetime(*weekday_date, hh, mm, tzinfo=VN_TZ)) == phase


def test_data_status_states():
    now_open = datetime(2026, 11, 19, 10, 0, tzinfo=VN_TZ)
    assert wx.data_status(_view(), now_open)["state"] == "fresh"
    assert wx.data_status(_view(status="stale", status_message="cũ", age_seconds=400), now_open)["state"] == "stale"
    assert wx.data_status(_view(status="no_data", status_message="trống"), now_open)["state"] == "error"
    after = wx.data_status(_view(status="stale", age_seconds=9000), datetime(2026, 11, 19, 16, 0, tzinfo=VN_TZ))
    assert after["state"] == "closed" and "kết thúc" in after["reason"]     # ngoài giờ KHÔNG phải lỗi
    lunch = wx.data_status(_view(), datetime(2026, 11, 19, 12, 0, tzinfo=VN_TZ))
    assert lunch["state"] == "closed" and "trưa" in lunch["reason"]
    hist = wx.data_status(_view(trading_date="2026-11-12"), now_open)
    assert hist["state"] == "closed" and "lịch sử" in hist["reason"]


# ----------------------------------------------------------------------------- chỉ đọc
def test_read_only_storage_cannot_write_and_missing_db(db_path, tmp_path):
    ro = wx.ReadOnlyStorage(db_path)
    with pytest.raises(sqlite3.OperationalError):
        ro._con.execute("DELETE FROM quotes")
    assert ro.trading_dates("sim")
    with pytest.raises(FileNotFoundError):
        wx.ReadOnlyStorage(tmp_path / "khong_co.sqlite")


def test_export_to_dir_writes_files_and_index(ro, tmp_path):
    entries = wx.export_to_dir(ro, "sim", tmp_path, index_codes=["VN30", "VNINDEX"], with_validation=False)
    assert (tmp_path / "latest.json").exists() and (tmp_path / "latest_VNINDEX.json").exists()
    idx = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert {s["index_code"] for s in idx["sessions"]} == {"VN30", "VNINDEX"} and len(entries) == 2
    assert all((tmp_path / s["path"]).exists() and s["is_simulated"] for s in idx["sessions"])
    wx.export_to_dir(ro, "sim", tmp_path, trading_date="2026-11-12", index_codes=["VN30"], with_validation=False)
    idx = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert {s["trading_date"] for s in idx["sessions"]} == {"2026-11-13", "2026-11-12"}     # gộp, không ghi đè mất phiên
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["meta"]["trading_date"] == "2026-11-12"


def test_empty_source_gives_error_payload(ro, tmp_path):
    assert wx.export_to_dir(ro, "ssi", tmp_path) == []
    p = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert p["meta"]["data_status"]["state"] == "error" and p["meta"]["is_simulated"] is False


# ----------------------------------------------------------------------------- publish
def _settings(db_path, token=FAKE_TOKEN):
    return Settings(mode="live", source="ssi", db_path=str(db_path), blob_read_write_token=token, blob_prefix="neopulse")


def test_publish_dry_run_writes_locally_without_network(db_path, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("dry-run không được gọi mạng")
    monkeypatch.setattr(httpx.Client, "put", boom)
    st = wp.run_publish(_settings(db_path, token=""), source="sim", dry_run=True, max_cycles=2, work_dir=tmp_path,
                        sleep=lambda s: None, validation_every=1e9)
    assert st.cycles == 2 and st.uploads == 0 and st.failures == 0
    assert (tmp_path / "latest.json").exists() and (tmp_path / "index.json").exists()
    assert list((tmp_path / "sessions").glob("sim_2026-11-13_VN30.json"))


def test_blob_client_request_shape_and_overwrite(tmp_path):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"url": "https://storeid123.public.blob.vercel-storage.com/neopulse/latest.json"})
    c = wp.BlobClient(FAKE_TOKEN, prefix="/neopulse/", transport=httpx.MockTransport(handler))
    url = c.put("latest.json", b"{}")
    r = seen[0]
    assert r.method == "PUT" and r.url.params["pathname"] == "neopulse/latest.json"
    assert r.headers["x-allow-overwrite"] == "1" and r.headers["x-add-random-suffix"] == "0"
    assert r.headers["x-vercel-blob-store-id"] == "STOREID123" and r.headers["authorization"] == f"Bearer {FAKE_TOKEN}"
    assert url.endswith("/neopulse/latest.json")


def test_blob_retries_then_succeeds_and_never_leaks_token():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("mạng rớt")
        return httpx.Response(200, json={"url": "u"}) if calls["n"] == 3 else httpx.Response(503)
    waits = []
    c = wp.BlobClient(FAKE_TOKEN, transport=httpx.MockTransport(handler), sleep=waits.append)
    assert c.put("a.json", b"{}") == "u" and calls["n"] == 3 and waits == [1.0, 2.0]     # lùi dần


def test_blob_gives_up_without_token_in_message_and_auth_error_not_retried():
    c = wp.BlobClient(FAKE_TOKEN, transport=httpx.MockTransport(lambda r: httpx.Response(503)), sleep=lambda s: None,
                      max_retries=2)
    with pytest.raises(wp.BlobPutError) as e:
        c.put("a.json", b"{}")
    assert FAKE_TOKEN not in str(e.value) and "3 lần" in str(e.value)
    n = {"c": 0}

    def deny(req):
        n["c"] += 1
        return httpx.Response(403)
    c2 = wp.BlobClient(FAKE_TOKEN, transport=httpx.MockTransport(deny), sleep=lambda s: None)
    with pytest.raises(wp.BlobPutError, match="từ chối quyền ghi"):
        c2.put("a.json", b"{}")
    assert n["c"] == 1
    with pytest.raises(wp.BlobPutError):
        wp.BlobClient("khong-dung-dinh-dang")


def test_publish_survives_network_outage_and_logs(db_path, tmp_path, caplog):
    def down(req):
        raise httpx.ConnectError("mạng rớt")
    client = wp.BlobClient(FAKE_TOKEN, transport=httpx.MockTransport(down), sleep=lambda s: None, max_retries=1)
    with caplog.at_level("WARNING"):
        st = wp.run_publish(_settings(db_path), source="sim", client=client, max_cycles=3, work_dir=tmp_path,
                            sleep=lambda s: None, validation_every=1e9)
    assert st.cycles == 3 and st.uploads == 0 and st.failures > 0           # không crash dù mạng rớt hoàn toàn
    assert "Không đẩy được" in (st.last_error or "")
    assert FAKE_TOKEN not in caplog.text and (tmp_path / "latest.json").exists()


def test_publish_uploads_each_cycle_and_final_session(db_path, tmp_path):
    puts = []

    def ok(req):
        puts.append(req.url.params["pathname"])
        return httpx.Response(200, json={"url": "u"})
    client = wp.BlobClient(FAKE_TOKEN, prefix="neopulse", transport=httpx.MockTransport(ok))
    st = wp.run_publish(_settings(db_path), source="sim", client=client, max_cycles=2, work_dir=tmp_path,
                        sleep=lambda s: None, validation_every=1e9)
    assert "neopulse/latest.json" in puts and "neopulse/latest_VN30.json" in puts and st.failures == 0
    assert "neopulse/sessions/sim_2026-11-13_VN30.json" in puts and "neopulse/index.json" in puts   # chu kỳ cuối ghi phiên


def test_publish_missing_db_pushes_error_state(tmp_path):
    puts = {}

    def ok(req):
        puts[req.url.params["pathname"]] = req.content
        return httpx.Response(200, json={"url": "u"})
    client = wp.BlobClient(FAKE_TOKEN, transport=httpx.MockTransport(ok))
    st = wp.run_publish(_settings(tmp_path / "nope.sqlite"), source="ssi", client=client, max_cycles=1,
                        work_dir=tmp_path / "w", sleep=lambda s: None, validation_every=1e9)
    body = json.loads(puts["latest.json"])
    assert body["meta"]["data_status"]["state"] == "error" and st.failures == 0


def test_publish_requires_token_unless_dry_run(db_path, tmp_path):
    with pytest.raises(wp.BlobPutError, match="BLOB_READ_WRITE_TOKEN"):
        wp.run_publish(_settings(db_path, token=""), source="sim", max_cycles=1, work_dir=tmp_path)


# ----------------------------------------------------------------------------- CLI
def test_cli_export_web_and_publish_dry_run(db_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("NEOPULSE_DB_PATH", str(db_path))
    monkeypatch.setenv("NEOPULSE_MODE", "sim")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["export-web", "--source", "sim", "--out", "o1", "--no-validation"]) == 0
    assert "MÔ PHỎNG" in capsys.readouterr().out and (tmp_path / "o1" / "latest.json").exists()
    assert cli_main(["publish", "--source", "sim", "--dry-run", "--until", "00:00", "--out", "o2"]) == 0
    assert (tmp_path / "o2" / "latest.json").exists()
    assert cli_main(["export-web", "--source", "sim", "--out", "o3"]) == 0
    assert "validation" in json.loads((tmp_path / "o3" / "latest.json").read_text(encoding="utf-8"))
