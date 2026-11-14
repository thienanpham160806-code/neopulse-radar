import numpy as np
import pandas as pd
import pytest

from neopulse.analytics import validation
from neopulse.analytics.ranking import rank_universe, zscore_cs


def synthetic_bars(strength: float, n_days=4, n_sym=12, n_bars=80, seed=0):
    """Giá giữa mà lợi suất kỳ sau = strength * obi + nhiễu."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_days):
        day = f"2026-11-{10 + d:02d}"
        bar = pd.date_range(f"{day} 09:15", periods=n_bars, freq="1min", tz="Asia/Ho_Chi_Minh")
        for s in range(n_sym):
            obi = rng.uniform(-1, 1, n_bars)
            ret = strength * obi + rng.normal(0, 0.001, n_bars)
            mid = 10000 * np.cumprod(1 + np.r_[0, ret[:-1]])          # obi[t] quyết định ret t -> t+1
            rows.append(pd.DataFrame({"trading_date": day, "symbol": f"S{s}", "bar": bar, "mid": mid, "obi3": obi,
                                      "obi_w": obi, "obi1": obi, "micro_dev_bps": obi}))
    return pd.concat(rows, ignore_index=True)


def test_time_split_is_chronological_and_leaves_holdout():
    days = ["2026-11-12", "2026-11-10", "2026-11-11", "2026-11-13", "2026-11-14"]
    train, test = validation.time_split(days)
    assert train == sorted(days)[:3] and test == sorted(days)[3:] and max(train) < min(test)
    assert validation.time_split(["a"]) == (["a"], [])
    assert validation.time_split(["a", "b"]) == (["a"], ["b"])


def test_forward_returns_stop_at_session_boundary():
    d = validation.add_forward_returns(synthetic_bars(0.001, n_days=2, n_sym=1, n_bars=10), (1, 5))
    last = d.groupby("trading_date").tail(1)
    assert last["fwd_1"].isna().all() and d.groupby("trading_date")["fwd_5"].apply(lambda s: s.isna().sum()).eq(5).all()


def test_ic_detects_planted_signal_and_is_zero_for_noise():
    res = validation.validate_signals(synthetic_bars(0.001), horizons=(1,))
    t = res["table"].set_index(["tín hiệu", "mẫu"])
    assert t.loc[("obi3", "ngoài mẫu"), "ic_mean"] > 0.3 and t.loc[("obi3", "ngoài mẫu"), "hit_rate"] > 0.6
    assert t.loc[("obi3", "ngoài mẫu"), "spread_bps"] > 0
    noise = validation.validate_signals(synthetic_bars(0.0, seed=3), horizons=(1,))["table"].set_index(["tín hiệu", "mẫu"])
    assert abs(noise.loc[("obi3", "ngoài mẫu"), "ic_mean"]) < 0.05


def test_ic_matches_scipy_spearman():
    stats = pytest.importorskip("scipy.stats")
    d = validation.add_forward_returns(synthetic_bars(0.0005, n_days=1, n_bars=30), (1,))
    ic = validation._ic_per_bar(d, "obi3", "fwd_1")
    bar = ic.index[5]
    x = d[d["bar"] == bar].dropna(subset=["fwd_1"])
    assert ic.loc[bar] == pytest.approx(stats.spearmanr(x["obi3"], x["fwd_1"]).statistic)


def test_small_samples_report_nan_and_notes():
    res = validation.validate_signals(synthetic_bars(0.001, n_days=1, n_sym=3, n_bars=6), horizons=(1,))
    assert res["test"] == [] and "1 phiên" in res["note"] and "< 5 phiên" in res["note"]
    assert res["table"]["ic_mean"].isna().all()
    assert validation.validate_signals(pd.DataFrame())["table"].empty


def test_zscore_and_ranking(make_quote):
    assert zscore_cs(pd.Series([1.0, 1.0, 1.0])).eq(0).all()
    assert zscore_cs(pd.Series([0.0] * 20 + [1000.0])).max() == 3.0
    latest = pd.DataFrame([
        make_quote("BEST", pct_change=3.0, bid_vol1=9000.0, f_buy_val=5e9, f_sell_val=1e9, total_value=9e9),
        make_quote("MID", pct_change=0.0, total_value=3e9, f_buy_val=1e9, f_sell_val=1e9),
        make_quote("WORST", pct_change=-3.0, ask_vol1=9000.0, f_buy_val=1e9, f_sell_val=5e9, total_value=1e9,
                   bid1=9950.0, ask1=10050.0),
        make_quote("NOFOREIGN", pct_change=0.5, total_value=2e9)])
    r = rank_universe(latest)
    assert r.index[0] == "BEST" and r.index[-1] == "WORST" and list(r["rank"]) == [1, 2, 3, 4]
    assert r.loc["NOFOREIGN", "n_factors"] == 4 and not np.isnan(r.loc["NOFOREIGN", "score"])
