"""publish-static: snapshot tĩnh cho web (không thời gian thực, không Blob, dữ liệu thật không vào git)."""
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from neopulse.analytics import webexport as wx
from neopulse.analytics import webstatic as ws
from neopulse.cli import main as cli_main
from neopulse.data.storage import Storage
from neopulse.neo_api.sim import simulate_sessions

REPO = Path(__file__).resolve().parents[1]
SECRET_WORDS = ("password", "secret", "token", "api_key", "apikey", "authorization", "blob_read_write")


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("static") / "s.sqlite"
    d = Storage(p)
    simulate_sessions(d, 3, end=date(2026, 11, 13), step_seconds=120, symbols=None)
    d.close()
    return p


def _reject_constant(c: str):
    raise AssertionError(f"có hằng {c} không hợp lệ trong JSON")


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_publish_static_writes_files_with_snapshot_meta(db_path, tmp_path):
    res = ws.publish_static(db_path, "sim", out_dir=tmp_path, index_codes=["VN30", "VNINDEX"], with_validation=False)
    assert (tmp_path / "latest.json").exists() and (tmp_path / "latest_VNINDEX.json").exists()
    assert (tmp_path / "index.json").exists() and len(res.entries) == 2 and res.url is None
    m = _read(tmp_path / "latest.json")["meta"]
    assert m["trading_date"] == "2026-11-13" and m["is_simulated"] is True and m["source_label"] == "MÔ PHỎNG"
    assert m["snapshot_at"].endswith("+07:00") and m["snapshot_realtime"] is False
    assert m["snapshot_kind"] == "end_of_session" and m["snapshot_label"] == "Snapshot cuối phiên"   # phiên 13/11 đã qua
    idx = _read(tmp_path / "index.json")
    assert {s["index_code"] for s in idx["sessions"]} == {"VN30", "VNINDEX"}
    assert all((tmp_path / s["path"]).exists() and s["snapshot_kind"] == "end_of_session" for s in idx["sessions"])


def test_output_has_no_secrets_and_no_raw_ticks(db_path, tmp_path):
    ws.publish_static(db_path, "sim", out_dir=tmp_path)
    for f in tmp_path.rglob("*.json"):
        text = f.read_text(encoding="utf-8").lower()
        assert not any(w in text for w in SECRET_WORDS), f
        assert not any(w in text for w in ("bid1", "ask1", "bid_vol", "ask_vol")), f
        json.loads(text, parse_constant=_reject_constant)   # JSON hợp lệ nghiêm ngặt: không NaN/Infinity


def test_specific_date_all_dates_and_unknown_date(db_path, tmp_path):
    ws.publish_static(db_path, "sim", trading_date="2026-11-12", out_dir=tmp_path / "a", with_validation=False)
    assert _read(tmp_path / "a" / "latest.json")["meta"]["trading_date"] == "2026-11-12"
    res = ws.publish_static(db_path, "sim", out_dir=tmp_path / "b", all_dates=True, with_validation=False)
    assert {e["trading_date"] for e in res.entries} == {"2026-11-11", "2026-11-12", "2026-11-13"}
    with pytest.raises(ws.StaticPublishError, match="Không có phiên 2026-01-01"):
        ws.publish_static(db_path, "sim", trading_date="2026-01-01", out_dir=tmp_path / "c")
    with pytest.raises(ws.StaticPublishError, match="Chưa có dữ liệu cho nguồn 'ssi'"):
        ws.publish_static(db_path, "ssi", out_dir=tmp_path / "d")
    with pytest.raises(ws.StaticPublishError, match="Không thấy cơ sở dữ liệu"):
        ws.publish_static(tmp_path / "khong_co.sqlite", "sim", out_dir=tmp_path / "e")


def test_snapshot_kind_intraday_vs_end_of_session():
    from datetime import datetime

    from neopulse.timeutil import VN_TZ
    mid = wx.snapshot_meta("2026-11-19", datetime(2026, 11, 19, 10, 30, tzinfo=VN_TZ))
    assert mid["snapshot_kind"] == "intraday" and "10:30" in mid["snapshot_label"] and "giữa phiên" in mid["snapshot_label"]
    eod = wx.snapshot_meta("2026-11-19", datetime(2026, 11, 19, 15, 30, tzinfo=VN_TZ))
    assert eod["snapshot_kind"] == "end_of_session"
    old = wx.snapshot_meta("2026-11-18", datetime(2026, 11, 19, 10, 30, tzinfo=VN_TZ))
    assert old["snapshot_kind"] == "end_of_session"                     # phiên của ngày trước luôn là cuối phiên
    assert mid["snapshot_realtime"] is False


def test_source_db_is_not_modified(db_path, tmp_path):
    before = db_path.stat().st_mtime_ns, db_path.stat().st_size
    ws.publish_static(db_path, "sim", out_dir=tmp_path, with_validation=False)
    assert (db_path.stat().st_mtime_ns, db_path.stat().st_size) == before


# ----------------------------------------------------------------------------- triển khai
class _Done:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def _web(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_deploy_runs_vercel_prod_in_web_dir_and_prints_alias_url(tmp_path):
    seen = {}

    def runner(cmd, **kw):
        seen.update(cmd=cmd, cwd=kw["cwd"])
        return _Done(0, "Production: https://neopulse-radar-abc123-x.vercel.app [3s]\n",
                     "Aliased: https://neopulse-radar.vercel.app [3s]\n")
    url = ws.deploy_web(_web(tmp_path), runner=runner, which=lambda n: "/bin/vercel")
    assert url == "https://neopulse-radar.vercel.app"
    assert seen["cmd"] == ["/bin/vercel", "--prod", "--yes"] and seen["cwd"] == str(tmp_path)


def test_deploy_errors_are_clear(tmp_path):
    with pytest.raises(ws.StaticPublishError, match="Không tìm thấy lệnh `vercel`"):
        ws.deploy_web(_web(tmp_path), which=lambda n: None)
    with pytest.raises(ws.StaticPublishError, match="Thư mục web không hợp lệ"):
        ws.deploy_web(tmp_path / "khong_co", which=lambda n: "/bin/vercel")
    with pytest.raises(ws.StaticPublishError, match="thất bại"):
        ws.deploy_web(_web(tmp_path), runner=lambda c, **k: _Done(1, "", "Error: not logged in"), which=lambda n: "/bin/vercel")


def test_publish_static_deploy_flag_calls_deployer_after_export(db_path, tmp_path):
    calls = []
    res = ws.publish_static(db_path, "sim", out_dir=tmp_path / "o", with_validation=False, deploy=True,
                            web_dir="WEB", deployer=lambda d: calls.append(d) or "https://x.vercel.app")
    assert calls == ["WEB"] and res.url == "https://x.vercel.app" and (tmp_path / "o" / "latest.json").exists()
    ws.publish_static(db_path, "sim", out_dir=tmp_path / "o2", with_validation=False,
                      deployer=lambda d: pytest.fail("không được triển khai khi thiếu --deploy"))


# ----------------------------------------------------------------------------- CLI
def test_cli_publish_static(db_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("NEOPULSE_DB_PATH", str(db_path))
    monkeypatch.setenv("NEOPULSE_MODE", "sim")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["publish-static", "--source", "sim", "--out", "o", "--no-validation"]) == 0
    out = capsys.readouterr().out
    assert "MÔ PHỎNG" in out and "Chưa triển khai" in out and (tmp_path / "o" / "latest.json").exists()
    assert cli_main(["publish-static", "--source", "ssi", "--out", "o2"]) == 1
    assert "LỖI" in capsys.readouterr().out
    assert cli_main(["publish-static", "--source", "sim", "--date", "2026-11-12", "--out", "o3", "--no-validation"]) == 0


# ----------------------------------------------------------------------------- dữ liệu thật không vào git
@pytest.mark.skipif(shutil.which("git") is None or not (REPO / ".git").exists(), reason="cần git và thư mục .git")
def test_real_snapshot_dir_is_gitignored_but_sample_is_not():
    def ignored(path: str) -> bool:
        r = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO)
        return r.returncode == 0
    for p in ("web/public/data/latest.json", "web/public/data/index.json", "web/public/data/sessions/ssi_2026-11-19_VN30.json"):
        assert ignored(p), f"{p} phải bị .gitignore (dữ liệu thật không được vào git)"
    assert not ignored("web/public/sample/latest.json")
    assert not ignored("web/public/sample/sessions/sim_2026-11-18_VN30.json")


def test_no_real_data_tracked_in_git():
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("cần git")
    files = subprocess.run(["git", "ls-files", "web/public"], cwd=REPO, capture_output=True, text=True).stdout.split()
    assert files, "web/public/sample phải được commit"
    assert all(f.startswith("web/public/sample/") or not f.startswith("web/public/data/") for f in files)
    for f in files:
        if f.endswith(".json") and not f.endswith("index.json"):
            doc = json.loads((REPO / f).read_text(encoding="utf-8"))
            if "messages" in doc:  # luồng phát lại cho bản xem trước: mọi tin phải là mô phỏng
                assert doc["messages"] and all(m["data"]["is_simulated"] is True for m in doc["messages"]), f
            else:
                assert doc["meta"]["is_simulated"] is True, f"{f} không phải dữ liệu mô phỏng"


def test_primary_index_other_than_vn30_maps_files_by_code(db_path, tmp_path):
    """CX-001: chỉ số chính VNINDEX (đảo thứ tự --indexes) -> mỗi chỉ số vẫn có latest_<MÃ>.json đúng nội dung."""
    ws.publish_static(db_path, "sim", out_dir=tmp_path, index_codes=["VNINDEX", "VN30"], with_validation=False)
    assert _read(tmp_path / "latest.json")["meta"]["index_code"] == "VNINDEX"
    assert _read(tmp_path / "latest_VNINDEX.json")["meta"]["index_code"] == "VNINDEX"
    assert _read(tmp_path / "latest_VN30.json")["meta"]["index_code"] == "VN30"
