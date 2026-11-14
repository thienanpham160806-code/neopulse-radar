import math

import numpy as np
import pandas as pd
import pytest

from neopulse.finance.microstructure import add_book_metrics, liquidity_table, make_bars, walk_book


def test_book_metrics_known_values(make_quote):
    df = pd.DataFrame([make_quote(bid_vol1=3000.0, ask_vol1=1000.0)])
    m = add_book_metrics(df).iloc[0]
    assert m["mid"] == 10000.0
    assert m["spread_bps"] == pytest.approx(20.0)
    assert m["obi1"] == pytest.approx(0.5)                       # (3000-1000)/4000
    assert m["obi3"] == pytest.approx((5000 - 3000) / 8000)
    assert m["microprice"] == pytest.approx((10010 * 3000 + 9990 * 1000) / 4000)  # nghiêng về phía bán khi mua dày
    assert m["micro_dev_bps"] > 0
    assert m["pressure"] == pytest.approx(3000 / 5000)
    assert m["band_pos"] == 0.0


def test_obi_bounds_and_symmetry(make_quote):
    a = add_book_metrics(pd.DataFrame([make_quote(bid_vol1=5000.0)])).iloc[0]
    b = add_book_metrics(pd.DataFrame([make_quote(ask_vol1=5000.0)])).iloc[0]
    assert a["obi3"] == pytest.approx(-b["obi3"]) and -1 <= b["obi_w"] <= 1


def test_one_sided_or_crossed_book_gives_nan_not_guess(make_quote):
    df = pd.DataFrame([make_quote(ask1=np.nan), make_quote(bid1=10020.0)])
    m = add_book_metrics(df)
    assert m[["mid", "spread_bps", "obi3", "microprice"]].isna().all().all()


def test_empty_frame_keeps_columns():
    assert "obi3" in add_book_metrics(pd.DataFrame(columns=["bid1", "ask1"])).columns


def test_walk_book_buy_and_sell(make_quote):
    row = make_quote()
    w = walk_book(row, 1500, "buy")                      # 1000 @10010 + 500 @10020
    assert w["avg_price"] == pytest.approx((1000 * 10010 + 500 * 10020) / 1500)
    assert w["slippage_bps"] == pytest.approx((w["avg_price"] - 10000) / 10000 * 1e4)
    assert w["fill_ratio"] == 1.0
    s = walk_book(row, 1000, "sell")
    assert s["avg_price"] == 9990 and s["slippage_bps"] == pytest.approx(10.0)


def test_walk_book_partial_fill_and_missing_side(make_quote):
    w = walk_book(make_quote(), 10_000, "buy")
    assert w["filled"] == 3000 and w["unfilled"] == 7000 and w["fill_ratio"] == pytest.approx(0.3)
    assert math.isnan(walk_book(make_quote(ask1=np.nan), 100)["slippage_bps"])
    assert walk_book(make_quote(), 0)["filled"] == 0


def test_bars_take_last_state_and_diff_cumulative(make_quote):
    rows = [make_quote(ts="2026-11-12T10:00:10+07:00", total_volume=100.0, total_value=1e6),
            make_quote(ts="2026-11-12T10:00:50+07:00", total_volume=300.0, total_value=3e6, bid_vol1=9000.0),
            make_quote(ts="2026-11-12T10:01:30+07:00", total_volume=700.0, total_value=7e6, bid1=10000.0, ask1=10020.0)]
    bars = make_bars(pd.DataFrame(rows))
    assert len(bars) == 2
    assert bars.loc[0, "obi1"] == pytest.approx(0.8)    # trạng thái CUỐI thanh đầu
    assert math.isnan(bars.loc[0, "vol"]) and bars.loc[1, "vol"] == 400.0
    assert bars.loc[1, "ret"] == pytest.approx(10010 / 10000 - 1)


def test_bars_do_not_diff_across_sessions(make_quote):
    rows = [make_quote(ts="2026-11-11T14:29:00+07:00", total_volume=9000.0) | {"trading_date": "2026-11-11"},
            make_quote(ts="2026-11-12T09:15:00+07:00", total_volume=50.0)]
    bars = make_bars(pd.DataFrame(rows))
    assert bars["vol"].isna().all() and bars["ret"].isna().all()


def test_liquidity_table_ranks_tight_deep_book_higher(make_quote):
    latest = pd.DataFrame([make_quote("LIQ", total_value=5e9, bid_vol1=5e5, ask_vol1=5e5),
                           make_quote("ILL", total_value=1e8, bid1=9900.0, ask1=10100.0, bid_vol1=100.0, ask_vol1=100.0)])
    t = liquidity_table(latest, order_value=50e6)
    assert t.index[0] == "LIQ" and t.loc["LIQ", "liq_score"] > t.loc["ILL", "liq_score"]
    assert t.loc["ILL", "slippage_bps"] > t.loc["LIQ", "slippage_bps"]
