"""Tải báo cáo công khai theo yêu cầu, dùng lại đúng bộ tính Python của hồ sơ đã xuất."""
from __future__ import annotations

import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx

from ..timeutil import VN_TZ, iso_vn, now_vn
from .charting import build_chart
from .company import _OVERVIEW_KEEP, build_report

BASE = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company"


def statement(data: dict, metrics: list, aliases: dict) -> dict:
    rows = sorted(data.get("years", []), key=lambda r: int(r.get("yearReport", 0)), reverse=True)[:5]
    years = sorted({str(r["yearReport"]) for r in rows})
    items = {}
    for metric in metrics:
        key = aliases.get(metric.get("titleEn", ""))
        field = metric.get("field")
        if not key or not field or key in items:
            continue
        items[key] = {str(r["yearReport"]): r.get(field) for r in rows}
    return {"years": years, "items": items}


def fetch_report(symbol: str, entry: dict, aliases: dict, client: httpx.Client, index_prices: list | None = None) -> dict:
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", symbol):
        raise ValueError("Mã không hợp lệ")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://trading.vietcap.com.vn/"}

    def read(path):
        r = client.get(BASE + path, headers=headers)
        r.raise_for_status()
        data = r.json().get("data")
        if data is None:
            raise ValueError("Nguồn chưa có dữ liệu")
        return data

    paths = [f"/details?ticker={symbol}", f"/{symbol}/financial-statement/metrics"] + [
        f"/{symbol}/financial-statement?section={s}" for s in ("INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW")]
    with ThreadPoolExecutor(max_workers=3) as pool:
        detail, metrics, income, balance, cashflow = list(pool.map(read, paths))
    ov = {"organ_name": detail.get("viOrganName") or entry.get("name"), "organ_short_name": detail.get("viOrganShortName"),
          "company_profile": " ".join(html.unescape(re.sub(r"<[^>]+>", " ", detail.get("profile") or "")).split()),
          "issue_share": detail.get("issueShare") or detail.get("numberOfSharesMktCap"),
          "listing_date": detail.get("listingDate"), "is_bank": detail.get("comTypeCode") == "NH",
          "icb_code_lv2": entry.get("icb_code"), "foreigner_percentage": detail.get("foreignerPercentage"),
          "maximum_foreign_percentage": detail.get("maximumForeignPercentage"), "state_percentage": detail.get("statePercentage")}
    raw = {"symbol": symbol, "source": "Vietcap · tải theo yêu cầu", "fetched_at": iso_vn(now_vn()),
           "overview": {k: ov.get(k) for k in _OVERVIEW_KEEP}, "prices": [],
           "income": statement(income, metrics.get("INCOME_STATEMENT", []), aliases),
           "balance": statement(balance, metrics.get("BALANCE_SHEET", []), aliases),
           "cashflow": statement(cashflow, metrics.get("CASH_FLOW", []), aliases)}
    if not raw["income"]["years"] or not raw["balance"]["years"]:
        raise ValueError("Chưa đủ BCTC năm từ nguồn")
    report = build_report(raw, index_prices or [], {}, {symbol: {"board": entry.get("exchange"), "icb_name": entry.get("industry")}})
    try:
        response = client.post("https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart", headers=headers,
                               json={"timeFrame": "ONE_DAY", "symbols": [symbol], "to": int(time.time()), "countBack": 300})
        response.raise_for_status()
        prices = response.json()
        if isinstance(prices, dict):
            prices = prices.get("data", [])
        row = prices[0] if prices else {}
        raw["prices"] = [[datetime.fromtimestamp(float(t), VN_TZ).date().isoformat(), float(v) / 1000] for t, v in zip(row.get("t", []), row.get("c", []), strict=False)]
        if raw["prices"]:
            report = build_report(raw, index_prices or [], {}, {symbol: {"board": entry.get("exchange"), "icb_name": entry.get("industry")}})
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
        pass  # BCTC vẫn có ích khi nguồn giá tạm lỗi.
    # Overview cung cấp giá tham khảo nhưng không có ngày giá: không gán ngày tải thành ngày giao dịch.
    report["technical"] = build_chart(symbol, raw["prices"], source="Vietcap · giá đóng cửa ngày", unit="đồng/CP", scale=1000)
    report["profile"]["about"] = report["profile"]["about"] or entry.get("name")
    report["notes"].append("Hồ sơ tải theo yêu cầu: chưa có cổ đông, lãnh đạo hoặc tin/sự kiện trong lần tải này; không thay dữ liệu thiếu bằng 0.")
    return report
