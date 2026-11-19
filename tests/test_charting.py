import pytest

from neopulse.analytics.charting import build_chart


def test_ma_ema_seed_warmup_and_recursive_step():
    rows = [[f"2026-01-{i:02d}", i] for i in range(1, 8)]
    p = build_chart("AAA", rows, source="test")
    assert len(p["studies"]["MA5"]) == 3
    assert p["studies"]["MA5"][0]["value"] == 3
    assert p["studies"]["EMA5"][1]["value"] == pytest.approx(4)
    assert p["studies"]["EMA20"] == []
    shock = build_chart("AAA", [[f"2026-01-{i:02d}", v] for i, v in enumerate([1, 1, 1, 1, 1, 10], 1)], source="test")
    assert shock["studies"]["MA5"][-1]["value"] == pytest.approx(2.8)
    assert shock["studies"]["EMA5"][-1]["value"] == pytest.approx(4)


def test_history_dedup_units_and_invalid_values():
    p = build_chart("AAA", [["2026-01-02", 2], ["2026-01-01", 1], ["2026-01-02", 3], ["x", float("nan")]], source="test", scale=1000)
    assert p["data"] == [{"time": "2026-01-01", "value": 1000}, {"time": "2026-01-02", "value": 3000}]
