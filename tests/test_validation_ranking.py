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


def test_forward_return_uses_mid_of_same_snapshot_as_signal(make_quote):
    """A2: lợi suất t -> t+h tính từ giá giữa của CHÍNH ảnh chụp sinh tín hiệu tại t; thay đổi sau t không đổi tín hiệu t."""
    from neopulse.finance.microstructure import make_bars
    rows = [make_quote(ts="2026-11-12T10:00:20+07:00", bid1=9990.0, ask1=10010.0, bid_vol1=3000.0),
            make_quote(ts="2026-11-12T10:00:50+07:00", bid1=10000.0, ask1=10020.0, bid_vol1=1000.0),  # ảnh cuối thanh 10:00
            make_quote(ts="2026-11-12T10:01:40+07:00", bid1=10040.0, ask1=10060.0)]
    b = validation.add_forward_returns(make_bars(pd.DataFrame(rows)), (1,))
    first = b.iloc[0]
    assert first["mid"] == 10010.0 and first["obi1"] == pytest.approx(0.0)   # cùng ảnh 10:00:50
    assert first["fwd_1"] == pytest.approx((10050.0 / 10010.0 - 1) * 1e4)
    later = rows[:2] + [make_quote(ts="2026-11-12T10:01:40+07:00", bid1=12000.0, ask1=12020.0, bid_vol1=9e6)]
    b2 = validation.add_forward_returns(make_bars(pd.DataFrame(later)), (1,))
    assert b2.iloc[0][["mid", "obi1", "obi3", "micro_dev_bps"]].equals(first[["mid", "obi1", "obi3", "micro_dev_bps"]])


def test_net_returns_cross_the_spread_and_pay_assumed_fee():
    b = synthetic_bars(0.0, n_days=1, n_sym=2, n_bars=3)
    b["bid1"], b["ask1"] = b["mid"] - 5, b["mid"] + 5
    d = validation.add_forward_returns(b, (1,))
    r = d.iloc[0]
    nxt = d.iloc[1]
    assert r["long_1"] == pytest.approx((nxt["bid1"] / r["ask1"] - 1) * 1e4 - 2 * validation.FEE_BPS)
    assert r["short_1"] == pytest.approx((1 - nxt["ask1"] / r["bid1"]) * 1e4 - 2 * validation.FEE_BPS)


def test_newey_west_matches_hand_formula_and_session_t():
    ic = pd.Series([0.1, 0.3, 0.2, 0.4, 0.0, 0.2])
    day = pd.Series(["a", "a", "a", "b", "b", "b"])
    e = ic - ic.mean()
    g0, g1 = (e * e).sum() / 6, (e.iloc[1] * e.iloc[0] + e.iloc[2] * e.iloc[1] + e.iloc[4] * e.iloc[3] + e.iloc[5] * e.iloc[4]) / 6
    want = ic.mean() / np.sqrt((g0 + 2 * 0.5 * g1) / 6)   # lag 1, Bartlett 1 - 1/2; không nối qua ranh giới phiên
    assert validation.newey_west_t(ic, day, 1) == pytest.approx(want)
    assert validation.nw_lag(100, 5) == 5 and validation.nw_lag(1000, 1) == 6
    t = validation.validate_signals(synthetic_bars(0.001, n_days=6), horizons=(1,))["table"].set_index(["tín hiệu", "mẫu"])
    row = t.loc[("obi3", "trong mẫu")]
    assert row["n_sessions"] == 4 and row["ic_tstat_session"] > 0 and row["ic_tstat_nw"] > 0
    assert np.isnan(t.loc[("obi3", "ngoài mẫu"), "ic_tstat_session"])  # 2 phiên: không báo t theo phiên


def test_placebo_ic_is_near_zero_when_signal_is_real():
    p = validation.placebo_table(synthetic_bars(0.001), horizons=(1,)).set_index("kiểu")
    assert p.loc["thật", "ic_mean"] > 0.3
    assert abs(p.filter(like="xáo", axis=0)["ic_mean"].iloc[0]) < 0.05
    assert abs(p.loc["tín hiệu cũ t-1", "ic_mean"]) < 0.05    # obi tổng hợp độc lập theo thời gian


def test_fixed_split_keeps_session_roles():
    b = synthetic_bars(0.001, n_days=4)
    days = sorted(b["trading_date"].unique())
    res = validation.validate_signals(b[b["trading_date"].isin(days[1:])], horizons=(1,), split=(days[:2], days[2:]))
    assert res["train"] == [days[1]] and res["test"] == days[2:]

