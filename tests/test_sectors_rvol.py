"""Ngành trong phiên và RVOL: kiểm bằng số tính tay."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from neopulse.analytics import alerts as al
from neopulse.analytics import refdata as rd
from neopulse.finance import rvol, sectors


# ----------------------------------------------------------------------------- phân ngành
@pytest.mark.parametrize("sym,code,want", [
    ("VCB", "8355", "Ngân hàng"), ("BVH", "8575", "Bảo hiểm"), ("VHM", "8633", "Bất động sản"),
    ("SSI", "8777", "Dịch vụ tài chính"), ("FPT", "9537", "Công nghệ"), ("HPG", "1757", "Nguyên vật liệu"),
    ("PLX", "0533", "Dầu khí"), ("GAS", "7573", "Tiện ích"), ("VNM", "3577", "Hàng tiêu dùng"),
    ("VJC", "5751", "Dịch vụ tiêu dùng"),
    ("MBB", None, "Ngân hàng"), ("VND", "", "Dịch vụ tài chính"), ("ZZZ", None, sectors.UNKNOWN),   # dự phòng tĩnh
])
def test_sector_of(sym, code, want):
    assert sectors.sector_of(sym, code) == want


def test_bundled_reference_covers_vn30_with_shares():
    ref = sectors.bundled_reference()
    assert {"VCB", "FPT", "VHM", "HPG"} <= set(ref) and ref["VCB"]["icb_code"] == "8355" and ref["VPB"]["listed_share"] > 0


def test_sector_table_hand_computed():
    """3 mã: A, B (ngân hàng), C (công nghệ). Tham chiếu 10.000; chỉ số phiên trước 1.000 điểm.

    A: 100 CP, +2%  -> vốn hóa 1.000.000 ; B: 300 CP, -1% -> 3.000.000 ; C: 100 CP, +5% -> 1.000.000 ; tổng 5.000.000
    Ngân hàng: % = (1e6*2 + 3e6*(-1))/4e6 = -0,25% ; đóng góp = (1e6/5e6*2% + 3e6/5e6*(-1%)) x 1000 = (0,4 - 0,6) = -2 điểm
    Công nghệ: % = 5% ; đóng góp = 1e6/5e6 x 5% x 1000 = 10 điểm ; tỷ trọng 0,2
    """
    latest = pd.DataFrame({"symbol": ["A", "B", "C"], "ref": [10000.0] * 3, "last": [10200.0, 9900.0, 10500.0],
                           "pct_change": [2.0, -1.0, 5.0]})
    ref = {"A": {"icb_code": "8355", "listed_share": 100}, "B": {"icb_code": "8355", "listed_share": 300},
           "C": {"icb_code": "9537", "listed_share": 100}}
    t = sectors.sector_table(latest, ref, index_prev=1000.0).set_index("sector")
    assert t.loc["Ngân hàng", "pct_cap"] == pytest.approx(-0.25)
    assert t.loc["Ngân hàng", "contrib_pts"] == pytest.approx(-2.0)
    assert (t.loc["Ngân hàng", "n_up"], t.loc["Ngân hàng", "n_down"], t.loc["Ngân hàng", "n"]) == (1, 1, 2)
    assert t.loc["Công nghệ", "pct_cap"] == pytest.approx(5.0) and t.loc["Công nghệ", "contrib_pts"] == pytest.approx(10.0)
    assert t.loc["Công nghệ", "weight"] == pytest.approx(0.2)
    assert t.index[0] == "Công nghệ"                                       # sắp theo đóng góp giảm dần


def test_sector_table_missing_shares_still_counts_breadth():
    latest = pd.DataFrame({"symbol": ["A", "X"], "ref": [100.0, 100.0], "last": [101.0, 99.0], "pct_change": [1.0, -1.0]})
    t = sectors.sector_table(latest, {"A": {"icb_code": "8355", "listed_share": 10}}, 1000.0).set_index("sector")
    assert np.isnan(t.loc[sectors.UNKNOWN, "contrib_pts"]) and t.loc[sectors.UNKNOWN, "n_down"] == 1
    assert sectors.sector_table(pd.DataFrame(), {}).empty


# ----------------------------------------------------------------------------- RVOL
def _bars(times, vols, cum):
    ts = [pd.Timestamp(f"2026-11-19T{t}:00+07:00") for t in times]
    return pd.DataFrame({"trading_date": "2026-11-19", "symbol": "AAA", "bar": ts, "vol": vols, "total_volume": cum})


def test_add_rvol_hand_computed_linear_profile():
    """KL TB 20 phiên 270.000 => kỳ vọng 1.000 CP/phút (phân bổ đều 270 phút).

    10:00 = phút 60: lũy kế 120.000 so với kỳ vọng 60.000 -> RVOL lũy kế 2,0
    thanh 10:00-10:01: 5.000 CP so với kỳ vọng 1.000 -> RVOL thanh 5,0
    13:30 = phút 180 (150 phút sáng + 30, bỏ nghỉ trưa): lũy kế 180.000 / 180.000 = 1,0
    """
    b = _bars(["10:00", "10:01", "13:30"], [np.nan, 5000.0, 1000.0], [120000.0, 125000.0, 180000.0])
    out = rvol.add_rvol(b, {"AAA": 270000.0})
    assert out["rvol_cum"].iloc[0] == pytest.approx(2.0)
    assert out["rvol_bar"].iloc[1] == pytest.approx(5.0)
    assert out["rvol_cum"].iloc[2] == pytest.approx(1.0)
    assert rvol.add_rvol(b, {})["rvol_bar"].isna().all()                  # không có KL TB -> không đoán


def test_empirical_profile_needs_three_sessions_and_is_monotone():
    rows = []
    for d in ("2026-11-10", "2026-11-11", "2026-11-12"):
        for t in pd.date_range(f"{d}T09:00:00+07:00", f"{d}T14:59:00+07:00", freq="1min"):
            if t.hour == 12 or (t.hour == 11 and t.minute >= 30):
                continue
            m = rvol.trading_minutes_elapsed(t.to_pydatetime())
            cum = np.interp(m, [0, 30, 120, 269], [0, 200, 500, 1000])
            rows.append({"trading_date": d, "symbol": "AAA", "bar": t, "total_volume": cum})
    h = pd.DataFrame(rows)
    assert rvol.empirical_profile(h[h.trading_date < "2026-11-12"]) is None
    f = rvol.empirical_profile(h)
    assert f(30) == pytest.approx(0.2) and f(120) == pytest.approx(0.5) and f(270) == pytest.approx(1.0)
    assert np.all(np.diff(f(np.arange(0, 271, 10))) >= 0)
    assert rvol.avg_volume_from_history(h) == {"AAA": 1000.0}


def test_rvol_bar_excludes_lunch_break():
    b = _bars(["11:29", "13:00"], [1000.0, 9000.0], [149000.0, 158000.0])
    assert rvol.add_rvol(b, {"AAA": 270000.0})["rvol_bar"].iloc[-1] == pytest.approx(9.0)


def test_partial_sessions_do_not_supply_profile_or_daily_average():
    rows = []
    for d in ("2026-11-10", "2026-11-11", "2026-11-12"):
        for t, cum in (("09:30", 30000.0), ("10:00", 60000.0)):
            rows.append({"trading_date": d, "symbol": "AAA", "bar": pd.Timestamp(f"{d}T{t}:00+07:00"), "total_volume": cum})
    h = pd.DataFrame(rows)
    assert rvol.empirical_profile(h) is None
    assert rvol.avg_volume_from_history(h) == {}


def test_history_with_large_internal_gap_is_not_complete():
    h = _bars(["09:00", "10:00", "14:59"], [0, 1000, 1000], [0, 1000, 2000])
    assert rvol.complete_history(h).empty


def test_volume_alert_uses_rvol_when_available():
    """Thanh có RVOL 4 (>= 3) phải báo dù z khối lượng thô không đủ cửa sổ; RVOL 2 thì không báo."""
    n = 6
    ts = [pd.Timestamp("2026-11-19T10:00:00+07:00") + pd.Timedelta(minutes=i) for i in range(n)]
    b = pd.DataFrame({"trading_date": "2026-11-19", "symbol": "AAA", "bar": ts, "vol": 1000.0, "val": 1e7,
                      "spread_bps": 10.0, "ret": 0.0, "f_net_val": 0.0, "obi3": 0.0, "band_pos": 0.0, "last": 10.0,
                      "pct_change": 0.0, "rvol_bar": [1, 1, 4.0, 1, 2.0, 1]})
    a = al.detect(b)
    vs = a[a.rule == "volume_spike"]
    assert len(vs) == 1 and vs.iloc[0]["value"] == pytest.approx(4.0) and vs.iloc[0]["threshold"] == rvol.RVOL_SPIKE
    assert "RVOL = 4.0" in vs.iloc[0]["message"]
    assert al.detect(b.drop(columns=["rvol_bar"])).query("rule == 'volume_spike'").empty   # z thô: chưa đủ cửa sổ


# ----------------------------------------------------------------------------- refdata
class FakeClient:
    def __init__(self, fail_ohlc=False):
        self.fail = fail_ohlc

    def securities_by_board(self, b):
        return [{"symbol": "AAA", "board": b, "icbCode": "8355", "icbName": "Ngân hàng", "listedShare": "1000"}] if b == "HOSE" else []

    def daily_ohlc(self, s, f, t):
        if self.fail:
            raise RuntimeError("down")
        return [{"tradingDate": f"2026/10/{d:02d}", "volume": str(d * 100)} for d in range(1, 26)]


def test_fetch_refdata_uses_last_20_sessions_and_vietcap_fallback():
    d = rd.fetch_refdata(FakeClient(), ["AAA"], today=date(2026, 11, 19))
    assert d["reference"]["AAA"]["icb_code"] == "8355" and d["reference"]["AAA"]["listed_share"] == 1000.0
    assert d["avg_volume"]["AAA"] == {"avg": sum(range(6, 26)) * 100 / 20, "n": 20, "source": "ssi"}   # 20 phiên cuối
    f = rd.fetch_refdata(FakeClient(fail_ohlc=True), ["AAA"], today=date(2026, 11, 19),
                         vnstock_fallback=lambda s, a, b: [100.0, 300.0])
    assert f["avg_volume"]["AAA"] == {"avg": 200.0, "n": 2, "source": "vietcap"}
    g = rd.fetch_refdata(FakeClient(fail_ohlc=True), ["AAA"], vnstock_fallback=lambda *a: (_ for _ in ()).throw(RuntimeError("x")))
    assert g["avg_volume"] == {}                                            # cả hai nguồn lỗi: không đoán, không crash


def test_refdata_roundtrip_and_bundled_fallback(tmp_path):
    db = tmp_path / "x.sqlite"
    assert rd.load_refdata(db)["avg_volume"] == {} and "VCB" in rd.load_refdata(db)["reference"]
    rd.save_refdata(db, {"generated_at": "t", "reference": {"AAA": {"icb_code": "9537"}},
                         "avg_volume": {"AAA": {"avg": 5.0, "n": 1, "source": "ssi"}}})
    d = rd.load_refdata(db)
    assert d["avg_volume"] == {"AAA": 5.0} and d["reference"]["AAA"]["icb_code"] == "9537" and "VCB" in d["reference"]
