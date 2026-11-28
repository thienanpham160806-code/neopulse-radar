import numpy as np
import pandas as pd
import pytest

from neopulse.analytics import alerts
from neopulse.analytics.anomaly import Z_CAP, robust_z, score_bars


def _bars(n=120, symbol="AAA", seed=0, **over):
    rng = np.random.default_rng(seed)
    bar = pd.date_range("2026-11-12 09:15", periods=n, freq="1min", tz="Asia/Ho_Chi_Minh")
    d = pd.DataFrame({"trading_date": "2026-11-12", "symbol": symbol, "bar": bar,
                      "vol": rng.lognormal(8, 0.3, n), "val": rng.lognormal(20, 0.3, n),
                      "spread_bps": 10 + rng.normal(0, 0.3, n), "ret": rng.normal(0, 0.0005, n),
                      "bid1": 10000.0, "ask1": 10050.0,  # 1 bước giá HOSE ở vùng 10.000-49.950
                      "f_net_val": rng.normal(0, 1e7, n), "obi3": rng.uniform(-0.3, 0.3, n),
                      "band_pos": 0.0, "last": 10000.0, "pct_change": 0.0})
    for k, v in over.items():
        d[k] = v
    return d


def test_robust_z_flags_spike_and_ignores_normal_points():
    x = pd.Series(np.random.default_rng(1).normal(100, 5, 200))
    x.iloc[150] = 400
    z = robust_z(x)
    assert z.iloc[150] > 10 and (z.drop(150).abs().dropna() < 6).all()
    assert z.iloc[:20].isna().all()                      # chưa đủ lịch sử => không kết luận


def test_robust_z_matches_hand_computed_modified_z():
    """CX-015: MAD quanh median của CÙNG cửa sổ x_{t-60..t-1}; đủ 20 quan sát là tính."""
    z = robust_z(pd.Series(np.arange(100, dtype=float)), window=60, min_periods=20)
    assert z[90] == pytest.approx(0.6745 * (90 - 59.5) / 15)   # cửa sổ 30..89: median 59,5, MAD 15
    assert z[20] == pytest.approx(0.6745 * (20 - 9.5) / 5)     # cửa sổ 0..19: median 9,5, MAD 5
    assert np.isnan(z[19])


def test_robust_z_has_no_lookahead():
    x = pd.Series(np.random.default_rng(2).normal(0, 1, 150))
    y = x.copy()
    y.iloc[100:] += 50                                    # thay đổi TƯƠNG LAI
    pd.testing.assert_series_equal(robust_z(x).iloc[:100], robust_z(y).iloc[:100])


def test_robust_z_constant_series_is_nan_and_capped():
    assert robust_z(pd.Series([5.0] * 80)).isna().all()
    x = pd.Series([5.0] * 79 + [5.0001] * 0 + [9.0])
    x.iloc[::2] += 1e-9
    assert robust_z(x).abs().max() <= Z_CAP


def test_volume_spike_alert_and_cooldown():
    b = _bars()
    b.loc[[80, 81, 82], "vol"] = b["vol"].median() * 40
    a = alerts.detect(b, source="t")
    spikes = a[a["rule"] == "volume_spike"]
    assert len(spikes) == 1 and spikes.iloc[0]["ts"] == b.loc[80, "bar"]      # 81, 82 bị cooldown chặn
    assert spikes.iloc[0]["severity"] in {"CAO", "TRUNG BÌNH"}
    assert a["dedupe_key"].is_unique


def test_quiet_market_produces_no_statistical_alerts():
    a = alerts.detect(_bars(seed=5), source="t")
    assert not a["rule"].isin(["volume_spike", "spread_blowout", "foreign_flow"]).any()


def test_book_pressure_requires_persistence_and_same_sign():
    obi = np.zeros(120)
    obi[40:44] = 0.8                 # chỉ 4 thanh: chưa đủ 5
    obi[60:67] = -0.9                # 7 thanh liên tiếp: nổ một lần ở thanh thứ 5
    obi[90], obi[91], obi[92] = 0.8, -0.8, 0.8   # đổi dấu liên tục: không nổ
    a = alerts.detect(_bars(obi3=obi), source="t")
    bp = a[a["rule"] == "book_pressure"]
    assert len(bp) == 1 and bp.iloc[0]["ts"].strftime("%H:%M") == "10:19" and bp.iloc[0]["value"] < 0


def test_near_limit_and_multi_rule_escalation():
    b = _bars()
    b.loc[100, "band_pos"] = 0.95
    b.loc[100, "vol"] = b["vol"].median() * 50
    a = alerts.detect(b, source="t")
    at = a[a["ts"] == b.loc[100, "bar"]]
    assert set(at["rule"]) == {"near_limit", "volume_spike"} and (at["severity"] == "CAO").all()


def test_scores_are_computed_per_symbol():
    b = pd.concat([_bars(symbol="AAA", seed=1), _bars(symbol="BBB", seed=2, vol=1e9)])
    s = score_bars(b)
    assert s[s["symbol"] == "AAA"]["z_vol"].abs().max() < 10   # BBB khổng lồ không làm AAA bất thường


def test_evaluate_against_truth():
    b = _bars()
    b.loc[80, "vol"] = b["vol"].median() * 40
    a = alerts.detect(b, source="sim")
    truth = pd.DataFrame({"ts": [b.loc[80, "bar"], b.loc[30, "bar"]], "symbol": ["AAA", "AAA"],
                          "kind": ["volume_spike", "spread_blowout"]})
    ev = alerts.evaluate_against_truth(a, truth)
    assert ev["by_kind"]["volume_spike"]["recall"] == 1.0 and ev["by_kind"]["spread_blowout"]["recall"] == 0.0
    assert ev["recall"] == 0.5 and ev["precision"] == 1.0
    assert alerts.detect(pd.DataFrame()).empty


def test_auction_bars_skip_volume_rule_and_saturated_z_is_not_high_alone():
    b = _bars(n=340)  # 09:15 -> 14:54; chỉ số 330 là thanh 14:45 (khớp ATC)
    assert b.loc[330, "bar"].strftime("%H:%M") == "14:45"
    b.loc[[200, 330], "vol"] = b["vol"].median() * 40
    b.loc[260, "ask1"] = 10400.0  # 8 bước giá, đứng một mình
    a = alerts.detect(b, source="t")
    spikes = a[a["rule"] == "volume_spike"]
    assert b.loc[200, "bar"] in set(spikes["ts"]) and b.loc[330, "bar"] not in set(spikes["ts"])  # bỏ thanh ATC
    spread = a[a["rule"] == "spread_blowout"]
    assert len(spread) == 1 and spread.iloc[0]["value"] == 8 and spread.iloc[0]["severity"] == "TRUNG BÌNH"


def test_tick_size_follows_hose_price_bands():
    from neopulse.finance.microstructure import tick_size
    assert [tick_size(p) for p in (9990, 10000, 49950, 50000)] == [10, 50, 50, 100]
    assert list(tick_size(pd.Series([9990.0, 49950.0, 120000.0]))) == [10, 50, 100]


def test_spread_rule_uses_ticks_floor_then_symbol_quantile():
    b = _bars()
    b.loc[10, "ask1"] = 10150.0          # 3 bước nhưng chưa đủ 20 thanh trước: chỉ dùng sàn 3 bước -> báo
    b.loc[[30, 50], "ask1"] = 10100.0   # 2 bước < sàn 3 bước -> không báo
    b.loc[70, "ask1"] = 10250.0          # 5 bước, phân vị 95% của mã (chủ yếu 1 bước) thấp hơn -> báo
    a = alerts.detect(b, source="t")
    hits = a[a["rule"] == "spread_blowout"].sort_values("ts")
    assert list(hits["ts"]) == [b.loc[10, "bar"], b.loc[70, "bar"]] and list(hits["value"]) == [3, 5]
    wide = _bars(ask1=10250.0)           # mã thường xuyên 5 bước: phân vị riêng = 5 -> 5 bước không bất thường
    wide.loc[90, "ask1"] = 10300.0
    w = alerts.detect(wide, source="t")
    assert set(w.loc[w["rule"] == "spread_blowout", "ts"]) - {wide.loc[i, "bar"] for i in range(20)} == {wide.loc[90, "bar"]}


def test_foreign_rule_needs_share_and_own_quantile_on_3_bar_window():
    b = _bars(f_net_val=0.0, val=1e9)
    b.loc[range(5, 100, 3), "f_net_val"] = 1e7          # NN lẻ tẻ: tỷ trọng 1%
    b.loc[[100, 101], "f_net_val"] = -4e8               # bán ròng 8e8 / 3e9 = 27% < 30%: không báo
    b.loc[[110, 111], "f_net_val"] = -6e8               # 1,2e9 / 3e9 = 40%: báo, giá trị âm
    a = alerts.detect(b, source="t")
    f = a[a["rule"] == "foreign_flow"]
    assert len(f) == 1 and f.iloc[0]["ts"] == b.loc[111, "bar"] and round(f.iloc[0]["value"], 6) == -0.4
    assert "bán ròng bằng 40%" in f.iloc[0]["message"]


def test_grid_ticks_count_steps_across_price_bands():
    """CX-018: spread vắt qua mốc 10.000 / 50.000 đếm trên lưới giá từng vùng."""
    from neopulse.finance.microstructure import grid_ticks
    assert list(grid_ticks([9990, 49950, 10000, 50000], [10050, 50100, 10150, 50300])) == [2, 2, 3, 3]
    assert np.isnan(grid_ticks([np.nan], [10050])[0])
    b = _bars()
    b["bid1"], b["ask1"] = 9990.0, 10000.0                   # 1 bước
    b.loc[60, "ask1"] = 10050.0                              # 2 bước thật (không phải 6): không báo
    b.loc[80, "bid1"], b.loc[80, "ask1"] = 9970.0, 10050.0   # 3 + 1 = 4 bước: báo
    a = alerts.detect(b, source="t")
    hits = a[a["rule"] == "spread_blowout"]
    assert list(hits["ts"]) == [b.loc[80, "bar"]] and hits.iloc[0]["value"] == 4


def test_book_pressure_run_resets_on_missing_bars():
    """CX-019: 5 thanh cực đoan nhưng mất 10 phút ở giữa thì không phải "5 thanh liên tiếp"."""
    b = _bars(obi3=0.0)
    b.loc[40:44, "obi3"] = 0.8
    gappy = b.drop(index=[42 + i for i in range(0)]).copy()
    gappy.loc[[42, 43, 44], "bar"] = gappy.loc[[42, 43, 44], "bar"] + pd.Timedelta(minutes=10)
    gappy = gappy.drop(index=range(45, 56))                  # bỏ các thanh trùng giờ sau khi dời
    assert alerts.detect(gappy, source="t").query("rule == 'book_pressure'").empty
    assert len(alerts.detect(b, source="t").query("rule == 'book_pressure'")) == 1
