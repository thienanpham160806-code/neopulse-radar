from datetime import datetime

from neopulse.data.normalize import normalize_index, normalize_quote, parse_trading_date, to_float
from neopulse.timeutil import VN_TZ, parse_event_time


def test_to_float_handles_dirty_values():
    assert to_float("31250.0") == 31250.0
    assert to_float(" 1,234 ") == 1234.0
    for bad in (None, "", "ATO", "abc", float("nan"), float("inf"), True):
        assert to_float(bad) is None


def test_documented_example_is_normalized(raw_stock, recv):
    row, issues = normalize_quote(raw_stock, recv, "neo")
    assert issues == []
    assert row["symbol"] == "VPB" and row["instrument"] == "stock"
    assert row["bid1"] == 31250.0 and row["ask1"] == 31300.0  # chuỗi -> số
    assert row["trading_date"] == "2025-09-15"                 # dd/mm/YYYY -> ISO
    assert row["ts"].endswith("+07:00")
    assert row["open_interest"] is None


def test_auction_price_string_is_flagged_not_parsed(raw_stock, recv):
    raw_stock["bidPrice1"] = "ATO"
    row, issues = normalize_quote(raw_stock, recv, "neo")
    assert row["auction_flag"] == "ATO" and row["bid1"] is None
    assert "crossed_book" not in issues


def test_bad_records_are_rejected_or_flagged(raw_stock, recv):
    assert normalize_quote({"closePrice": 1}, recv, "neo") == (None, ["missing_symbol"])
    assert normalize_quote("oops", recv, "neo")[0] is None
    row, issues = normalize_quote({**raw_stock, "bidVol1": -5, "highPrice": "x"}, recv, "neo")
    assert row["bid_vol1"] is None and "negative:bid_vol1" in issues and "bad_type:highPrice" in issues
    _, issues = normalize_quote({**raw_stock, "bidPrice1": "31400", "askPrice1": "31300"}, recv, "neo")
    assert "crossed_book" in issues
    _, issues = normalize_quote({**raw_stock, "closePrice": 99999}, recv, "neo")
    assert "price_outside_band" in issues
    row, issues = normalize_quote({"symbol": "X"}, recv, "neo")
    assert row is None and "no_price" in issues


def test_future_is_detected(recv):
    row, _ = normalize_quote({"symbol": "VN30F2509", "stockType": "FUVN30", "marketCode": "FU", "closePrice": 1862,
                              "refPrice": 1859, "maturityDate": "19/09/2025", "underlyingSymbol": "VN30"}, recv, "neo")
    assert row["instrument"] == "future" and row["maturity_date"] == "2025-09-19" and row["underlying"] == "VN30"


def test_index_uses_event_time_in_vn_timezone(recv):
    raw = {"dateString": "2026-11-12", "indexCode": "vn30", "indexValue": "1940.76", "indexTime": "10:14:50",
           "indexPercentChange": 0.99, "advances": 20, "declines": 8, "noChange": 2}
    row, issues = normalize_index(raw, recv, "neo")
    assert issues == [] and row["index_code"] == "VN30" and row["value"] == 1940.76
    assert row["ts"] == "2026-11-12T10:14:50.000+07:00"


def test_index_rejects_missing_value_and_future_timestamps(recv):
    assert normalize_index({"indexCode": "VN30", "indexValue": None}, recv, "neo")[0] is None
    row, issues = normalize_index({"indexCode": "VN30", "indexValue": 1, "indexTime": "23:59:59",
                                   "dateString": "2026-11-12"}, recv, "neo")
    assert "event_time_in_future" in issues and row["ts"].startswith("2026-11-12T10:15:00")


def test_time_helpers():
    fb = datetime(2026, 11, 12, 9, 0, tzinfo=VN_TZ)
    assert parse_event_time(None, "2025-09-04T15:00:00", fb).isoformat() == "2025-09-04T15:00:00+07:00"
    assert parse_event_time("x", "garbage", fb) == fb
    assert parse_trading_date("garbage", fb) == "2026-11-12"
