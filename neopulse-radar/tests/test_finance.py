import math

import pandas as pd
import pytest

from neopulse.finance import basis, breadth, foreign, pulse


def test_breadth_ratio_and_divergence():
    ix = pd.DataFrame([{"advances": 300, "declines": 100, "no_change": 100, "n_ceiling": 10, "n_floor": 0}])
    out = breadth.add_breadth(ix).iloc[0]
    assert out["ad_ratio"] == pytest.approx(0.5) and out["pct_advancing"] == pytest.approx(60.0)
    assert out["ext_spread"] == pytest.approx(0.02)
    assert breadth.divergence(0.8, -0.4) and breadth.divergence(-0.8, 0.4)
    assert breadth.divergence(0.8, 0.4) is None and breadth.divergence(0.05, -0.9) is None
    assert breadth.divergence(None, 0.1) is None


def test_breadth_zero_denominator_is_nan():
    out = breadth.add_breadth(pd.DataFrame([{"advances": 0, "declines": 0, "no_change": 0, "n_ceiling": 0, "n_floor": 0}]))
    assert math.isnan(out.iloc[0]["ad_ratio"])


def test_universe_breadth(make_quote):
    latest = pd.DataFrame([make_quote("A", last=10700.0), make_quote("B", last=9900.0), make_quote("C")])
    b = breadth.universe_breadth(latest)
    assert (b["n_up"], b["n_down"], b["n_ceiling"]) == (1, 1, 1) and b["ad_ratio"] == 0.0


def test_foreign_table_and_summary(make_quote):
    latest = pd.DataFrame([make_quote("BUY", f_buy_val=8e9, f_sell_val=2e9, total_value=20e9, f_remain=10.0, f_room=100.0),
                           make_quote("SELL", f_buy_val=1e9, f_sell_val=4e9, total_value=10e9),
                           make_quote("NONE", total_value=5e9)])
    t = foreign.foreign_table(latest)
    assert list(t.index) == ["BUY", "NONE", "SELL"]
    assert t.loc["BUY", "net_ratio"] == pytest.approx(0.6)
    assert t.loc["BUY", "participation"] == pytest.approx(10e9 / 40e9)
    assert t.loc["BUY", "room_used"] == pytest.approx(0.9)
    assert math.isnan(t.loc["NONE", "net_ratio"])          # không giao dịch NN => không xác định, không phải 0
    s = foreign.foreign_summary(t)
    assert s["net_val"] == pytest.approx(3e9) and s["n_net_buy"] == 1 and s["n_net_sell"] == 1


def _fut(ts, last):
    return {"ts": pd.Timestamp(ts), "trading_date": "2026-11-12", "symbol": "VN30F2611", "last": last,
            "maturity_date": "2026-11-19"}


def test_basis_uses_only_past_index_values():
    fut = pd.DataFrame([_fut("2026-11-12T10:00:30+07:00", 1905.0)])
    idx = pd.DataFrame({"ts": pd.to_datetime(["2026-11-12T10:00:00+07:00", "2026-11-12T10:01:00+07:00"]),
                        "value": [1900.0, 2000.0]})
    b = basis.basis_series(fut, idx).iloc[0]
    assert b["spot"] == 1900.0 and b["basis"] == 5.0          # không lấy giá trị 10:01 (tương lai)
    assert b["dtm"] == 7 and b["carry_ann"] == pytest.approx((1905 / 1900 - 1) * 365 / 7)
    assert b["fair_value"] == pytest.approx(1900 * (1 + 0.045 * 7 / 365))


def test_basis_drops_stale_spot_and_handles_empty():
    fut = pd.DataFrame([_fut("2026-11-12T10:30:00+07:00", 1905.0)])
    idx = pd.DataFrame({"ts": pd.to_datetime(["2026-11-12T10:00:00+07:00"]), "value": [1900.0]})
    assert basis.basis_series(fut, idx).empty
    assert basis.basis_state(pd.DataFrame())["label"] == "Không có dữ liệu"


def test_pulse_extremes_neutral_and_labels():
    full = dict.fromkeys(pulse.WEIGHTS, 1.0)
    assert pulse.combine(full).score == 100.0
    assert pulse.combine(dict.fromkeys(pulse.WEIGHTS, -1.0)).score == 0.0
    assert pulse.combine(dict.fromkeys(pulse.WEIGHTS, 0.0)).label == "Trung tính - giằng co"
    assert abs(sum(pulse.WEIGHTS.values()) - 1) < 1e-9
    assert pulse.label_for(65) == "Tích cực lan tỏa" and pulse.label_for(34.9) == "Tiêu cực lan tỏa"


def test_pulse_renormalizes_missing_and_refuses_when_too_little_data():
    p = pulse.combine({"breadth": 1.0, "momentum": 1.0, "book": None, "foreign": None, "liquidity": None})
    assert p.score == 100.0 and set(p.missing) == {"book", "foreign", "liquidity"}
    q = pulse.combine({"liquidity": 1.0, "foreign": 1.0})    # chỉ 25% trọng số có dữ liệu
    assert math.isnan(q.score) and q.label == "Không đủ dữ liệu"


def test_pulse_clips_out_of_range_components():
    assert pulse.combine(dict.fromkeys(pulse.WEIGHTS, 7.0)).score == 100.0


def test_compute_pulse_from_inputs(make_quote):
    latest = pd.DataFrame([make_quote("A", bid_vol1=9000.0, total_value=1e9, f_buy_val=3e9, f_sell_val=1e9)])
    p = pulse.compute_pulse({"advances": 20, "declines": 10, "pct_change": 1.0, "total_value": 2e12}, latest,
                            sigma_pct=1.0, expected_value=1e12)
    assert p.components["breadth"] == pytest.approx(1 / 3)
    assert p.components["momentum"] == pytest.approx(math.tanh(1.0))
    assert p.components["foreign"] == pytest.approx(0.5)
    assert p.components["liquidity"] == pytest.approx(math.tanh(math.log(2)))
    assert p.components["book"] > 0 and p.score > 50


def test_sensitivity_is_bounded():
    s = pulse.sensitivity({"breadth": 0.9, "momentum": 0.8, "book": 0.7, "foreign": 0.9, "liquidity": 0.8})
    assert s["p05"] <= s["base"] <= s["p95"] and s["label_stability"] == 1.0
