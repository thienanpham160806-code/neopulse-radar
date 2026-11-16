from datetime import datetime

import pandas as pd
import pytest

from neopulse.config import Settings
from neopulse.timeutil import VN_TZ


@pytest.fixture
def recv():
    return datetime(2026, 11, 12, 10, 15, 0, tzinfo=VN_TZ)


@pytest.fixture
def settings():
    return Settings(mode="live", neo_username="116C000001", neo_password="s3cret-pw",
                    neo_base_url="https://neo.test/neo-api", neo_auth_url="https://auth.test/auth/token",
                    neo_max_rps=5)


@pytest.fixture
def raw_stock():
    """Bản ghi mẫu theo đúng ví dụ trong tài liệu NEO API mục 4.6 (VPB)."""
    return {"symbol": "VPB", "tradingDate": "15/09/2025", "marketCode": "HOSE", "stockType": "ST",
            "ceilingPrice": 33800, "floorPrice": 29400, "refPrice": 31600,
            "bidPrice3": 31150, "bidVol3": 560800, "bidPrice2": 31200, "bidVol2": 608000,
            "bidPrice1": "31250.0", "bidVol1": 98500, "closePrice": 31250, "closeVol": 5000,
            "priceChange": -350, "percentPriceChange": -1.11,
            "askPrice1": "31300.0", "askVol1": 590900, "askPrice2": 31350, "askVol2": 103600,
            "askPrice3": 31400, "askVol3": 201200, "totalTradingVolume": 33498000,
            "totalTradingValue": 1052566395000, "averagePrice": 31422.0, "openPrice": 31500,
            "highPrice": 32200, "lowPrice": 31100, "foreignBuyVolume": 2924700, "foreignSellVolume": 2334102,
            "foreignBuyValue": 91396875000, "foreignSellValue": 72940687500,
            "foreignRemain": 435283768, "foreignRoom": 2380177080, "totalBidQTTY": None, "openInterest": None}


def quote_row(symbol="AAA", ts="2026-11-12T10:00:00+07:00", **kw):
    base = dict(ts=pd.Timestamp(ts), trading_date="2026-11-12", symbol=symbol, instrument="stock", source="t",
                ceiling=10700.0, floor=9300.0, ref=10000.0, last=10000.0, avg_price=10000.0, pct_change=0.0,
                bid1=9990.0, bid2=9980.0, bid3=9970.0, bid_vol1=1000.0, bid_vol2=1000.0, bid_vol3=1000.0,
                ask1=10010.0, ask2=10020.0, ask3=10030.0, ask_vol1=1000.0, ask_vol2=1000.0, ask_vol3=1000.0,
                total_volume=0.0, total_value=0.0, f_buy_val=0.0, f_sell_val=0.0, f_remain=50.0, f_room=100.0)
    base.update(kw)
    return base


@pytest.fixture
def make_quote():
    return quote_row
