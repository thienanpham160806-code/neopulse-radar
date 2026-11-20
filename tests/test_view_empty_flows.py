import math

import pandas as pd

from neopulse.analytics.view import pulse_timeseries


def test_opening_session_without_foreign_trades_does_not_divide_by_zero():
    at = pd.Timestamp("2026-11-20T09:01:00+07:00")
    bars = pd.DataFrame({"bar": [at], "total_value": [0.0], "obi3": [0.2], "f_buy_val": [None], "f_sell_val": [None]})
    index = pd.DataFrame({"ts": [at], "advances": [2.0], "declines": [3.0], "no_change": [25.0],
                          "n_ceiling": [0.0], "n_floor": [0.0], "pct_change": [-0.2], "value": [1700.0]})
    result = pulse_timeseries(bars, index, 1)
    assert pd.isna(result.iloc[0]["foreign"])
    assert pd.isna(result.iloc[0]["book"])
    assert math.isfinite(result.iloc[0]["score"])
