import numpy as np
import pandas as pd

from neopulse.analytics import alerts
from neopulse.analytics.anomaly import Z_CAP, robust_z, score_bars


def _bars(n=120, symbol="AAA", seed=0, **over):
    rng = np.random.default_rng(seed)
    bar = pd.date_range("2026-11-12 09:15", periods=n, freq="1min", tz="Asia/Ho_Chi_Minh")
    d = pd.DataFrame({"trading_date": "2026-11-12", "symbol": symbol, "bar": bar,
                      "vol": rng.lognormal(8, 0.3, n), "val": rng.lognormal(20, 0.3, n),
                      "spread_bps": 10 + rng.normal(0, 0.3, n), "ret": rng.normal(0, 0.0005, n),
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
    obi[40:42] = 0.8                 # chỉ 2 thanh: chưa đủ
    obi[60:65] = -0.9                # 5 thanh liên tiếp: nổ một lần
    obi[90], obi[91], obi[92] = 0.8, -0.8, 0.8   # đổi dấu liên tục: không nổ
    a = alerts.detect(_bars(obi3=obi), source="t")
    bp = a[a["rule"] == "book_pressure"]
    assert len(bp) == 1 and bp.iloc[0]["ts"].strftime("%H:%M") == "10:17" and bp.iloc[0]["value"] < 0


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
