import hashlib

import pandas as pd

from neopulse.analytics import reportdata
from neopulse.data.storage import Storage


def _db(tmp_path, make_quote):
    path = tmp_path / "r.sqlite"
    db = Storage(path)
    rows = []
    for day, start in (("2026-11-19", "10:00"), ("2026-11-20", "09:00")):
        for sym in ("AAA", "BBB"):
            minutes = pd.date_range(f"{day} {start}", f"{day} 11:29", freq="1min", tz="Asia/Ho_Chi_Minh").append(
                pd.date_range(f"{day} 13:00", f"{day} 14:59", freq="1min", tz="Asia/Ho_Chi_Minh"))
            for i, ts in enumerate(minutes):
                rows.append(make_quote(sym, ts=ts, trading_date=day, source="ssi", total_volume=100.0 * (i + 1),
                                      last=10000.0 + i % 3 * 10))
    db.insert_quotes([{**r, "ts": r["ts"].isoformat(timespec="milliseconds")} for r in rows])
    db.insert_index([{"ts": f"2026-11-20T09:0{i}:00+07:00", "trading_date": "2026-11-20", "index_code": "VN30",
                      "source": "ssi", "value": 1900.0, "pct_change": 0.1, "advances": 10, "declines": 15, "no_change": 5,
                      "n_ceiling": 0, "n_floor": 0} for i in range(3)])
    run = db.start_run("2026-11-20T08:58:00+07:00", "ssi")
    db.finish_run(run, "2026-11-20T15:05:00+07:00", n_quotes=10, n_reconnects=2, n_duplicates=5, n_rejected=1)
    db.log_quality([{"ts": "2026-11-19T10:00:00+07:00", "source": "ssi", "kind": "unknown_message", "subject": "", "detail": "x"}])
    db.close()
    return path


def test_report_data_reads_only_and_writes_summary(tmp_path, make_quote):
    path = _db(tmp_path, make_quote)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    summary = reportdata.build(path, "ssi", tmp_path / "out", tests={"pytest": 7, "vitest": None})
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before  # chỉ đọc

    s = pd.read_csv(tmp_path / "out" / "sessions.csv").set_index("phiên")
    assert list(s.index) == ["2026-11-19", "2026-11-20"]
    assert s.loc["2026-11-19", "khoảng trống lớn nhất (phút)"] == 60 and s.loc["2026-11-19", "khoảng trống từ"] == "09:00"
    assert not s.loc["2026-11-19", "đủ"] and s.loc["2026-11-20", "đủ"] and s.loc["2026-11-20", "mã ghi trọn"] == 2
    assert s.loc["2026-11-20", "lần nối lại"] == 2 and s.loc["2026-11-20", "tin lặp"] == 5 and s.loc["2026-11-20", "tin bị loại"] == 1
    assert s.loc["2026-11-19", "tin lạ"] == 1 and s.loc["2026-11-20", "tick chỉ số"] == 3
    for f in ("sessions.csv", "alerts.csv", "validation.csv"):  # không xuất giá/sổ lệnh từng tick
        cols = set(pd.read_csv(tmp_path / "out" / f).columns) if (tmp_path / "out" / f).stat().st_size > 2 else set()
        assert not cols & {"bid1", "ask1", "last", "ts"}

    text = summary.read_text(encoding="utf-8")
    assert "Số phiên: 2 (1 phiên đủ, 1 phiên thiếu)" in text and "Tổng bản ghi giá:" in text
    assert "Python (`pytest --co -q`): 7 ca" in text and "Web (`vitest list`): chưa có ca" in text
    assert "Trong mẫu: 1 phiên (2026-11-19); ngoài mẫu: 1 phiên (2026-11-20)" in text


def test_report_data_counts_pytest_in_quiet_mode():
    assert reportdata._largest_gap([]) == (270.0, 0.0)
    assert reportdata._minute_to_clock(150) == "11:30" and reportdata._minute_to_clock(151) == "13:01"


def _ic_rows(ic, t, net, n=2):
    rows = []
    for k in range(n):
        for mau in ("trong mẫu", "ngoài mẫu"):
            rows.append({"tín hiệu": f"s{k}", "tầm nhìn (thanh)": 1, "mẫu": mau, "ic_mean": ic, "ic_tstat_nw": t,
                         "spread_bps": 5.0, "q5_long_net_bps": net})
    return pd.DataFrame(rows)


def test_ic_conclusion_follows_the_numbers():
    """CX-025: câu định tính đổi theo số; không khẳng định cứng."""
    meta = {"test": ["2026-11-26", "2026-11-27"], "n_symbols": 30}
    good_plac = pd.DataFrame({"kiểu": ["xáo giữa các mã (20 lần)", "tín hiệu cũ t-1"], "ic_mean": [0.001, 0.07]})
    real = " ".join(reportdata.ic_conclusion(_ic_rows(0.2, 20.0, -50.0), good_plac, meta))
    assert "Có liên hệ thống kê ở 2/2 cặp" in real and "cùng chiều dương" in real and "2026-11-26, 2026-11-27" in real
    assert "Sau chi phí không còn dương" in real and "Giả thuyết" in real and "30 mã" in real
    null = " ".join(reportdata.ic_conclusion(_ic_rows(0.0, 0.0, 60.0), pd.DataFrame(
        {"kiểu": ["xáo giữa các mã (20 lần)"], "ic_mean": [0.8]}), meta))
    assert "Không có bằng chứng liên hệ thống kê" in null and "Có liên hệ" not in null
    assert "cần kiểm lại đường tính" in null and "dương ở mọi cặp" in null and "Giả thuyết" not in null
    empty = reportdata.ic_conclusion(_ic_rows(float("nan"), float("nan"), float("nan")), pd.DataFrame(), meta)
    assert "Chưa đủ dữ liệu" in empty[-1]
