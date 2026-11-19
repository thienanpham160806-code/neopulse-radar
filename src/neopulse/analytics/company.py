"""Hồ sơ doanh nghiệp cho web: tổng quan + phân tích tài chính theo khung báo cáo phân tích cổ phiếu (giới thiệu
doanh nghiệp và ngành, diễn biến giá, kết quả kinh doanh, tỷ số tài chính, DuPont, dòng tiền, so sánh cùng ngành).

Nguồn: BCTC năm hợp nhất, hồ sơ, cổ đông, lãnh đạo, sự kiện và giá ngày qua thư viện vnstock (nguồn Vietcap),
chỉ dữ liệu công khai. Mọi tỷ số do Python tính ở đây; web chỉ hiển thị.

Cố ý KHÔNG đưa: khuyến nghị MUA/BÁN, giá mục tiêu, xếp hạng của công ty chứng khoán (Vietcap trả kèm `rating`,
`target_price`... trong overview: chỉ lấy các trường trong _OVERVIEW_KEEP). DCF chỉ có bảng độ nhạy minh họa,
giữ FCFF nền cố định, công bố rõ giả định; không gọi là giá mục tiêu hay dự phóng riêng doanh nghiệp.

Hai bước tách rời để test được không cần mạng:
  fetch_raw(sym)  -> dict thô (lưu data/company/raw/<MÃ>.json)
  build_report(raw, vnindex, peers) -> dict hiển thị (web/public/data/company/<MÃ>.json)
"""
from __future__ import annotations

import json
import logging
import math
import re
import statistics
import time
from pathlib import Path

from ..timeutil import iso_vn, now_vn
from .explain import vn_digits

log = logging.getLogger(__name__)
SCHEMA = 1
BN = 1e9  # tỷ đồng
PRICE_UNIT = 1000  # quote.history của Vietcap trả giá theo nghìn đồng
RETAIL_PEERS = {"MWG", "FRT", "DGW", "PNJ"}  # nhóm tham khảo trong báo cáo MWG người dùng cung cấp

_OVERVIEW_KEEP = ("organ_name", "organ_short_name", "company_profile", "issue_share", "listing_date", "icb_code_lv2",
                  "icb_code_lv4", "foreigner_percentage", "maximum_foreign_percentage", "state_percentage",
                  "free_float_percentage", "is_bank")

# Bí danh item_id theo loại hình (doanh nghiệp thường, chứng khoán, bảo hiểm dùng tên khác nhau)
_IS = {
    "revenue": ["net_sales", "net_sales_from_insurance_business", "net_revenue_of_insurance_premium"],
    "cogs": ["cost_of_sales", "operating_expense"],
    "gross_profit": ["gross_profit", "gross_insurance_operating_profit"],
    "selling": ["selling_expenses", "selling_cost"],
    "admin": ["general_and_admin_expenses", "general_and_administrative_expenses"],
    "fin_income": ["financial_income", "income_from_financial_activities"],
    "interest": ["interest_expenses", "interests_expenses"],
    "operating_profit": ["operating_profit_loss"],
    "pbt": ["net_accounting_profit_loss_before_tax", "profit_before_tax"],
    "npat": ["net_profit_loss_after_tax", "profit_after_tax"],
    "npat_parent": ["attributable_to_parent_company", "net_profit_attributable_to_shareholders_of_the_group"],
    "eps": ["eps_basic_vnd"],
    # ngân hàng
    "nii": ["net_interest_income"],
    "fee": ["net_fee_and_commission_income"],
    "toi": ["total_operating_income"],
    "provision": ["provision_for_credit_losses"],
}
_BS = {
    "total_assets": ["total_assets"],
    "equity": ["owners_equity", "shareholders_equity"],
    "minority": ["minority_interests", "minority_interest"],
    "current_assets": ["current_assets"],
    "current_liabilities": ["current_liabilities"],
    "cash": ["cash_and_cash_equivalents", "cash_and_precious_metals"],
    "st_invest": ["short_term_investments"],
    "receivables": ["accounts_receivable"],
    "inventory": ["inventories_net"],
    "payables": ["trade_accounts_payable"],
    "st_debt": ["short_term_borrowings"],
    "lt_debt": ["long_term_borrowings", "long_term_borrowings_and_liabilities"],
    "liabilities": ["liabilities", "total_liabilities"],
    "fixed_assets": ["fixed_assets"],
    # ngân hàng
    "loans": ["loans_and_advances_to_customers"],
    "deposits": ["deposits_from_customers"],
}
_CF = {
    "cfo": ["net_cash_inflows_outflows_from_operating_activities", "net_cash_from_operating_activities"],
    "capex": ["purchases_of_fixed_assets_and_other_long_term_assets"],
    "dep": ["depreciation_and_amortization"],
    "dividends": ["dividends_paid"],
    "cfi": ["net_cash_inflows_outflows_from_investing_activities", "net_cash_from_investing_activities"],
    "cff": ["net_cash_inflows_outflows_from_financing_activities"],
}


# ----------------------------------------------------------------------------------------------- lấy dữ liệu thô
def _df_records(df) -> list[dict]:
    df = df.loc[:, ~df.columns.duplicated()]  # overview Vietcap lặp cột issue_share
    return json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))


def _statement(df) -> dict:
    """DataFrame BCTC (item, item_id, các cột năm) -> {'years': [...], 'items': {item_id: {năm: giá trị}}}.
    item_id trùng (VD 'cost' của nhiều nhóm TSCĐ) giữ lần xuất hiện đầu."""
    years = sorted(c for c in df.columns if str(c)[:4].isdigit())
    items: dict[str, dict] = {}
    for _, r in df.iterrows():
        k = r["item_id"]
        if k in items:
            continue
        items[k] = {str(y): (None if r[y] is None or (isinstance(r[y], float) and math.isnan(r[y])) else float(r[y]))
                    for y in years}
    return {"years": [str(y) for y in years], "items": items}


def fetch_raw(symbol: str, *, start: str, end: str, pause: float = 3.5) -> dict:
    """Gọi vnstock (Vietcap). `pause` giữ dưới giới hạn request của bản cộng đồng."""
    try:
        from vnstock import Vnstock  # type: ignore
    except (ImportError, Exception, SystemExit) as e:  # noqa: BLE001 - vnai có thể sys.exit() khi import
        raise RuntimeError(f"không dùng được vnstock: {type(e).__name__}") from e
    st = Vnstock(show_log=False).stock(symbol=symbol, source="VCI")
    out: dict = {"symbol": symbol, "source": "Vietcap (qua vnstock)", "fetched_at": iso_vn(now_vn())}

    def call(name, fn):
        try:
            v = fn()
        except SystemExit as e:  # vnai chạm giới hạn: không để giết tiến trình
            raise RuntimeError("vnstock bị chặn giới hạn") from e
        except Exception as e:  # noqa: BLE001 - thiếu một phần vẫn dựng được báo cáo
            log.warning("%s %s lỗi: %s", symbol, name, str(e)[:120])
            v = None
        time.sleep(pause)
        return v

    ov = call("overview", st.company.overview)
    if ov is not None and len(ov):
        row = _df_records(ov)[0]
        out["overview"] = {k: row.get(k) for k in _OVERVIEW_KEEP}
    sh = call("shareholders", st.company.shareholders)
    out["shareholders"] = [{"name": r["share_holder"], "pct": r["share_own_percent"]} for r in _df_records(sh)[:8]] if sh is not None else []
    of = call("officers", st.company.officers)
    out["officers"] = [{"name": r["officer_name"], "position": r["officer_position"]} for r in _df_records(of)[:8]] if of is not None else []
    ev = call("events", st.company.events)
    out["events"] = [{"date": (r.get("public_date") or "")[:10], "title": r.get("event_title_vi")} for r in _df_records(ev)[:8]] if ev is not None else []
    nw = call("news", st.company.news)
    out["news"] = [{"date": (r.get("public_date") or "")[:10], "title": r.get("news_title")} for r in _df_records(nw)[:6]] if nw is not None else []
    for key, fn in (("income", st.finance.income_statement), ("balance", st.finance.balance_sheet), ("cashflow", st.finance.cash_flow)):
        df = call(key, lambda fn=fn: fn(period="year", lang="vi"))
        out[key] = _statement(df) if df is not None else {"years": [], "items": {}}
    h = call("history", lambda: st.quote.history(start=start, end=end, interval="1D"))
    out["prices"] = [[str(r["time"])[:10], float(r["close"])] for r in _df_records(h)] if h is not None else []
    return out


def fetch_index_prices(code: str, *, start: str, end: str) -> list[list]:
    from vnstock import Vnstock  # type: ignore
    h = Vnstock(show_log=False).stock(symbol=code, source="VCI").quote.history(start=start, end=end, interval="1D")
    return [[str(r["time"])[:10], float(r["close"])] for r in _df_records(h)]


# ------------------------------------------------------------------------------------------------------ tính toán
def _pick(stmt: dict, aliases: dict, key: str, year: str):
    for k in aliases[key]:
        v = stmt.get("items", {}).get(k, {}).get(year)
        if v is not None:
            return v
    return None


def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def _avg(a, b):
    return a if b is None else b if a is None else (a + b) / 2


def _days(balance, flow):
    q = _div(balance, flow)
    return None if q is None else q * 365


def _growth(cur, prev):
    return None if cur is None or prev in (None, 0) or prev < 0 else cur / prev - 1


def _r(x, n=4):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(x, n)


def _years(raw: dict) -> list[str]:
    ys = set(raw.get("income", {}).get("years", [])) & set(raw.get("balance", {}).get("years", []))
    return sorted(ys)


def _series(raw: dict, kind: str) -> dict[str, dict]:
    """Số liệu gốc từng năm (đồng) cho các dòng cần dùng."""
    out = {}
    for y in _years(raw):
        d = {k: _pick(raw["income"], _IS, k, y) for k in _IS}
        d.update({k: _pick(raw["balance"], _BS, k, y) for k in _BS})
        d.update({k: _pick(raw.get("cashflow", {}), _CF, k, y) for k in _CF})
        if d["npat_parent"] is None:
            d["npat_parent"] = d["npat"]
        d["debt"] = (d["st_debt"] or 0) + (d["lt_debt"] or 0) if (d["st_debt"] is not None or d["lt_debt"] is not None) else None
        d["equity_parent"] = None if d["equity"] is None else d["equity"] - (d["minority"] or 0)
        out[y] = d
    return out


def _ratios(s: dict[str, dict], kind: str) -> dict[str, dict]:
    ys = sorted(s)
    out = {}
    for i, y in enumerate(ys):
        c, p = s[y], s[ys[i - 1]] if i else {}
        def avg(k, c=c, p=p):
            return _avg(c.get(k), p.get(k)) if p else c.get(k)
        r = {"npat_growth": _growth(c["npat_parent"], p.get("npat_parent")),
             "net_margin": None, "roe": _div(c["npat_parent"], avg("equity_parent")),
             "roa": _div(c["npat"], avg("total_assets")), "equity_to_assets": _div(c["equity"], c["total_assets"])}
        if kind == "bank":
            r.update({"toi_growth": _growth(c["toi"], p.get("toi")), "loan_growth": _growth(c["loans"], p.get("loans")),
                      "deposit_growth": _growth(c["deposits"], p.get("deposits")),
                      "nii_share": _div(c["nii"], c["toi"]),
                      "cir": _div(-c["admin"] if c["admin"] is not None else None, c["toi"]),
                      "ldr": _div(c["loans"], c["deposits"]),
                      "nii_to_assets": _div(c["nii"], avg("total_assets")),
                      "provision_to_toi": _div(-c["provision"] if c["provision"] is not None else None, c["toi"])})
        else:
            rev, cogs = c["revenue"], c["cogs"]
            cogs_abs = abs(cogs) if cogs is not None else None
            ebit = None if c["pbt"] is None else c["pbt"] + abs(c["interest"] or 0)
            sga = None if c["selling"] is None and c["admin"] is None else abs(c["selling"] or 0) + abs(c["admin"] or 0)
            core = None if c["gross_profit"] is None or sga is None else c["gross_profit"] - sga
            r.update({
                "revenue_growth": _growth(rev, p.get("revenue")),
                "gross_margin": _div(c["gross_profit"], rev), "sga_to_revenue": _div(sga, rev),
                "core_margin": _div(core, rev), "net_margin": _div(c["npat_parent"], rev),
                "ebit_margin": _div(ebit, rev),
                "fin_income_to_pbt": _div(c["fin_income"], c["pbt"]) if (c["pbt"] or 0) > 0 else None,
                "asset_turnover": _div(rev, avg("total_assets")),
                "leverage": _div(avg("total_assets"), avg("equity_parent")),
                "tax_burden": _div(c["npat_parent"], c["pbt"]), "interest_burden": _div(c["pbt"], ebit),
                "current_ratio": _div(c["current_assets"], c["current_liabilities"]),
                "quick_ratio": _div(None if c["current_assets"] is None else c["current_assets"] - (c["inventory"] or 0), c["current_liabilities"]),
                "cash_ratio": _div(None if c["cash"] is None else c["cash"] + (c["st_invest"] or 0), c["current_liabilities"]),
                "debt_to_equity": _div(c["debt"], c["equity"]),
                "net_debt": None if c["debt"] is None else c["debt"] - (c["cash"] or 0) - (c["st_invest"] or 0),
                "interest_cover": _div(ebit, abs(c["interest"])) if c["interest"] else None,
                "inventory_days": _days(avg("inventory"), cogs_abs),
                "receivable_days": _days(avg("receivables"), rev),
                "payable_days": _days(avg("payables"), cogs_abs),
                "cfo": c["cfo"], "capex": c["capex"],
                "fcf": None if c["cfo"] is None or c["capex"] is None else c["cfo"] - abs(c["capex"]),
                "cfo_to_npat": _div(c["cfo"], c["npat"]),
            })
            parts = [r["inventory_days"], r["receivable_days"], r["payable_days"]]
            r["ccc"] = None if any(v is None for v in parts) else parts[0] + parts[1] - parts[2]
            r["ebitda"] = None if ebit is None else ebit + (c["dep"] or 0)
        out[y] = {k: _r(v) for k, v in r.items()}
    return out


def _price_block(prices: list[list], index_prices: list[list]) -> dict:
    if not prices:
        return {"last": None, "date": None, "series": [], "returns": {}, "high_52w": None, "low_52w": None, "n_sessions": 0}
    ip = dict((d, v) for d, v in index_prices)
    closes = [v for _, v in prices]
    common = [(d, v, ip[d]) for d, v in prices if d in ip]
    series = []
    if common:
        b0, i0 = common[0][1], common[0][2]
        series = [[d, round(v / b0 * 100, 2), round(iv / i0 * 100, 2)] for d, v, iv in common]
    ret = {}
    for label, n in (("1T", 21), ("3T", 63), ("6T", 126), ("1N", 250)):
        if len(common) > n:
            ret[label] = {"stock": _r(common[-1][1] / common[-1 - n][1] - 1), "index": _r(common[-1][2] / common[-1 - n][2] - 1)}
    last252 = closes[-250:]
    # giá lịch sử Vietcap tính bằng nghìn đồng -> đổi sang đồng
    return {"last": closes[-1] * PRICE_UNIT, "date": prices[-1][0], "series": series, "returns": ret,
            "high_52w": max(last252) * PRICE_UNIT, "low_52w": min(last252) * PRICE_UNIT, "n_sessions": len(last252)}


def _kind(raw: dict) -> str:
    if (raw.get("overview") or {}).get("is_bank") or "net_interest_income" in raw.get("income", {}).get("items", {}):
        return "bank"
    return "general"


def _valuation(s_last: dict, rat_last: dict, price, shares, kind: str) -> dict:
    mcap = None if price is None or not shares else price * shares
    v = {"market_cap": mcap,
         "pe": _r(_div(mcap, s_last.get("npat_parent")) if (s_last.get("npat_parent") or 0) > 0 else None, 2),
         "pb": _r(_div(mcap, s_last.get("equity_parent")) if (s_last.get("equity_parent") or 0) > 0 else None, 2),
         "ev_ebitda": None}
    if kind != "bank" and mcap is not None and rat_last.get("net_debt") is not None and (rat_last.get("ebitda") or 0) > 0:
        v["ev_ebitda"] = _r((mcap + rat_last["net_debt"]) / rat_last["ebitda"], 2)
    return v


def _bn(x):
    return None if x is None else round(x / BN, 1)


_TABLE_ROWS = {
    "general": {
        "income": [("Doanh thu thuần", "revenue"), ("Lợi nhuận gộp", "gross_profit"), ("Chi phí bán hàng", "selling"),
                   ("Chi phí quản lý doanh nghiệp", "admin"), ("Doanh thu tài chính", "fin_income"),
                   ("Chi phí lãi vay", "interest"), ("Lợi nhuận trước thuế", "pbt"), ("Lợi nhuận sau thuế", "npat"),
                   ("LNST cổ đông công ty mẹ", "npat_parent")],
        "balance": [("Tiền và tương đương tiền", "cash"), ("Đầu tư tài chính ngắn hạn", "st_invest"),
                    ("Phải thu ngắn hạn", "receivables"), ("Hàng tồn kho", "inventory"), ("Tài sản ngắn hạn", "current_assets"),
                    ("Tài sản cố định", "fixed_assets"), ("Tổng tài sản", "total_assets"), ("Nợ ngắn hạn", "current_liabilities"),
                    ("Vay ngắn hạn", "st_debt"), ("Vay dài hạn", "lt_debt"), ("Nợ phải trả", "liabilities"), ("Vốn chủ sở hữu", "equity")],
        "cashflow": [("Dòng tiền kinh doanh (CFO)", "cfo"), ("Chi mua sắm TSCĐ", "capex"), ("Dòng tiền đầu tư", "cfi"),
                     ("Dòng tiền tài chính", "cff"), ("Cổ tức đã trả", "dividends")],
    },
    "bank": {
        "income": [("Thu nhập lãi thuần", "nii"), ("Lãi thuần từ dịch vụ", "fee"), ("Tổng thu nhập hoạt động", "toi"),
                   ("Chi phí hoạt động", "admin"), ("Chi phí dự phòng rủi ro tín dụng", "provision"),
                   ("Lợi nhuận trước thuế", "pbt"), ("LNST cổ đông công ty mẹ", "npat_parent")],
        "balance": [("Cho vay khách hàng", "loans"), ("Tiền gửi của khách hàng", "deposits"),
                    ("Tổng tài sản", "total_assets"), ("Vốn chủ sở hữu", "equity")],
        "cashflow": [("Dòng tiền kinh doanh (CFO)", "cfo"), ("Chi mua sắm TSCĐ", "capex"), ("Cổ tức đã trả", "dividends")],
    },
}


def _pct(x, n=1):
    return "—" if x is None else f"{x * 100:.{n}f}%"


def _summary(sym: str, kind: str, ys: list[str], s: dict, rat: dict, val: dict, peer_med: dict, price: dict) -> list[str]:
    """Nhận định tự động: mỗi câu gắn với số đã tính, không dự báo, không khuyến nghị."""
    if not ys:
        return []
    y, out = ys[-1], []
    c, r = s[y], rat[y]
    head = "Tổng thu nhập hoạt động" if kind == "bank" else "Doanh thu thuần"
    top = c["toi"] if kind == "bank" else c["revenue"]
    g = r.get("toi_growth") if kind == "bank" else r.get("revenue_growth")
    if top is not None:
        out.append(f"{head} năm {y} đạt {top / BN:,.0f} tỷ đồng" + (f" ({'+' if g >= 0 else ''}{g * 100:.1f}% so với {ys[-2]})" if g is not None else "")
                   + (f"; LNST cổ đông công ty mẹ {c['npat_parent'] / BN:,.0f} tỷ đồng" if c["npat_parent"] is not None else "")
                   + (f" ({'+' if r['npat_growth'] >= 0 else ''}{r['npat_growth'] * 100:.1f}%)." if r.get("npat_growth") is not None else "."))
    if kind != "bank" and r.get("gross_margin") is not None and len(ys) >= 2:
        prev = [rat[x]["gross_margin"] for x in ys[:-1] if rat[x].get("gross_margin") is not None]
        if prev:
            m = sum(prev) / len(prev)
            word = "cao hơn" if r["gross_margin"] > m + 0.002 else "thấp hơn" if r["gross_margin"] < m - 0.002 else "ngang"
            out.append(f"Biên lợi nhuận gộp {_pct(r['gross_margin'])}, {word} bình quân các năm trước ({_pct(m)}); biên ròng {_pct(r['net_margin'])}.")
    if r.get("roe") is not None:
        if kind != "bank" and None not in (r.get("net_margin"), r.get("asset_turnover"), r.get("leverage")):
            out.append(f"ROE {_pct(r['roe'])} = biên ròng {_pct(r['net_margin'])} × vòng quay tài sản {r['asset_turnover']:.2f} lần"
                       f" × đòn bẩy {r['leverage']:.2f} lần (DuPont).")
        else:
            out.append(f"ROE {_pct(r['roe'])}, ROA {_pct(r['roa'])}.")
    if kind == "bank":
        if r.get("ldr") is not None:
            out.append(f"Cho vay/tiền gửi khách hàng {_pct(r['ldr'])}; chi phí hoạt động/thu nhập (CIR) {_pct(r['cir'])}.")
    elif r.get("net_debt") is not None:
        nd = r["net_debt"]
        out.append(("Tiền và đầu tư ngắn hạn vượt nợ vay: tiền mặt ròng " if nd < 0 else "Nợ vay ròng ") + f"{abs(nd) / BN:,.0f} tỷ đồng"
                   + (f"; nợ vay/vốn chủ {r['debt_to_equity']:.2f} lần." if r.get("debt_to_equity") is not None else "."))
    if kind != "bank":
        pos = sum(1 for x in ys if (rat[x].get("cfo") or 0) > 0)
        have = sum(rat[x].get("cfo") is not None for x in ys)
        if have:
            out.append(f"Dòng tiền kinh doanh dương {pos}/{have} năm có dữ liệu."
                       + (f" Dòng tiền tự do (CFO trừ chi TSCĐ) năm {y}: {r['fcf'] / BN:,.0f} tỷ đồng."
                          if r.get("fcf") is not None else " Chưa đủ dữ liệu dòng tiền tự do năm gần nhất."))
    if val.get("pe") is not None:
        cmp = f", so với trung vị nhóm so sánh {peer_med['pe']:.1f} lần" if peer_med.get("pe") is not None else ""
        out.append(f"Theo giá {price.get('date') or ''}: P/E {val['pe']:.1f} lần{cmp}; P/B {val['pb']:.2f} lần." if val.get("pb") is not None
                   else f"P/E {val['pe']:.1f} lần{cmp}.")
    one = price.get("returns", {}).get("1N")
    if one and one["stock"] is not None and one["index"] is not None:
        out.append(f"Một năm qua giá {sym} {'+' if one['stock'] >= 0 else ''}{one['stock'] * 100:.1f}%, VN-Index "
                   f"{'+' if one['index'] >= 0 else ''}{one['index'] * 100:.1f}%.")
    return [vn_digits(x) for x in out]


def _dcf(s: dict, raw: dict, shares, kind: str) -> dict:
    """Bảng độ nhạy minh họa, FCFF nền cố định 5 năm, không giả làm dự phóng riêng doanh nghiệp."""
    empty = {"base_fcff": None, "cases": []}
    financial = "financial_assets_at_fair_value_through_profit_or_loss_fvtpl" in raw.get("balance", {}).get("items", {})
    if kind == "bank" or financial or str((raw.get("overview") or {}).get("icb_code_lv2", "")) in {"8300", "8500", "8700"}:
        return {**empty, "reason": "Không áp dụng FCFF giản lược cho ngân hàng, bảo hiểm hoặc công ty tài chính; cần mô hình vốn chủ và giả định ngành riêng."}
    ys = sorted(s)
    if len(ys) < 2 or not shares or shares <= 0:
        return {**empty, "reason": "Cần ít nhất hai năm BCTC liên tiếp và số cổ phiếu để dựng FCFF."}
    c, p = s[ys[-1]], s[ys[-2]]
    keys = ("gross_profit", "selling", "admin", "dep", "capex", "receivables", "inventory", "payables", "cash", "st_invest", "st_debt", "lt_debt", "minority")
    if int(ys[-1]) - int(ys[-2]) != 1 or any(c.get(k) is None for k in keys) or any(p.get(k) is None for k in ("receivables", "inventory", "payables")):
        return {**empty, "reason": "Thiếu khoản mục FCFF, nợ vay, tiền, lợi ích không kiểm soát hoặc hai năm liên tiếp. Không thay dữ liệu thiếu bằng 0 để đưa ra giá trị."}
    def nwc(v):
        return v["receivables"] + v["inventory"] - v["payables"]
    tax = 0.20  # giả định minh họa, không phải kết luận thuế suất hiệu dụng của doanh nghiệp
    core_ebit = c["gross_profit"] - abs(c["selling"]) - abs(c["admin"])
    fcff = core_ebit * (1 - tax) + c["dep"] - abs(c["capex"]) - (nwc(c) - nwc(p))
    if fcff <= 0:
        return {**empty, "base_fcff": _bn(fcff), "reason": "FCFF nền không dương; cần dự phóng chuyển đổi hoạt động thay vì kéo dài dòng tiền hiện tại."}
    net_debt = c["st_debt"] + c["lt_debt"] - c["cash"] - c["st_invest"]
    cases = []
    for wacc in (0.10, 0.12, 0.14):
        pv = sum(fcff / (1 + wacc) ** t for t in range(1, 6))
        for growth in (0.02, 0.03, 0.04):
            terminal = fcff * (1 + growth) / (wacc - growth) / (1 + wacc) ** 5
            equity = pv + terminal - net_debt - c["minority"]
            cases.append({"wacc": wacc, "growth": growth, "value": round(equity / shares) if equity > 0 else None})
    return {"base_fcff": _bn(fcff), "tax_rate": tax, "cases": cases}


def build_report(raw: dict, index_prices: list[list], peers: dict[str, dict], reference: dict | None = None) -> dict:
    """`peers`: {mã: báo cáo đã dựng sơ bộ ('kind','icb','latest'...)} cùng đợt, dùng cho bảng so sánh."""
    sym = raw["symbol"]
    kind = _kind(raw)
    s = _series(raw, kind)
    ys = sorted(s)[-4:]
    rat = _ratios(s, kind)
    ov = raw.get("overview") or {}
    ref = (reference or {}).get(sym, {})
    price = _price_block(raw.get("prices", []), index_prices)
    last = s[ys[-1]] if ys else {}
    val = _valuation(last, rat[ys[-1]] if ys else {}, price["last"], ov.get("issue_share"), kind)

    rows = _TABLE_ROWS["bank" if kind == "bank" else "general"]
    tables = {name: [{"label": lab, "values": [_bn(s[y].get(key)) for y in ys]} for lab, key in spec] for name, spec in rows.items()}
    tables = {k: [r for r in v if any(x is not None for x in r["values"])] for k, v in tables.items()}

    others = {c: p for c, p in peers.items() if c != sym and p.get("peer_row")}
    icb = ov.get("icb_code_lv2")
    peer_rows = [p["peer_row"] for p in others.values() if icb and p.get("icb") == icb]
    basis = "Cùng nhóm ngành ICB cấp 2 trong dữ liệu đã tải"
    if not peer_rows:
        basis = "Chưa có doanh nghiệp khác cùng ngành trong dữ liệu đã tải; không dùng ngành khác làm nhóm so sánh"
    if sym in RETAIL_PEERS:
        peer_rows = [p["peer_row"] for c, p in others.items() if c in RETAIL_PEERS]
        basis = "Nhóm bán lẻ/phân phối tham khảo theo báo cáo MWG: MWG, FRT, DGW, PNJ; có khác biệt phân ngành ICB và mô hình kinh doanh"
    peer_rows.sort(key=lambda r: r["symbol"])
    me = peer_row(sym, kind, ys, rat, val)
    med = {k: (statistics.median(vals) if (vals := [r[k] for r in peer_rows if r.get(k) is not None]) else None)
           for k in ("revenue_growth", "net_margin", "roe", "debt_to_equity", "pe", "pb")}
    rep = {
        "schema": SCHEMA, "symbol": sym, "kind": kind, "generated_at": iso_vn(now_vn()),
        "source": raw.get("source"), "fetched_at": raw.get("fetched_at"),
        "profile": {"name": ov.get("organ_name"), "short_name": ov.get("organ_short_name"),
                    "about": ov.get("company_profile"), "exchange": ref.get("board") or ref.get("exchange"),
                    "industry": ref.get("icb_name"), "listing_date": (ov.get("listing_date") or "")[:10] or None,
                    "shares": ov.get("issue_share"), "foreign_pct": ov.get("foreigner_percentage"),
                    "foreign_room": ov.get("maximum_foreign_percentage"), "state_pct": ov.get("state_percentage"),
                    "free_float_pct": ov.get("free_float_percentage")},
        "shareholders": raw.get("shareholders", []), "officers": raw.get("officers", []),
        "events": raw.get("events", []), "news": raw.get("news", []),
        "price": price, "valuation": {**val, "market_cap": _bn(val["market_cap"])},
        "dcf": _dcf(s, raw, ov.get("issue_share"), kind),
        "years": ys, "tables": tables,
        "ratios": {y: rat[y] for y in ys},
        "peers": {"basis": basis, "rows": [me, *peer_rows], "median": med},
        "summary": _summary(sym, kind, ys, s, rat, val, med, price),
        "notes": ["Số liệu BCTC năm hợp nhất; đơn vị tỷ đồng trừ khi ghi khác.",
                  "Tỷ số dùng bình quân đầu kỳ và cuối kỳ cho các khoản mục bảng cân đối khi có năm trước.",
                  "EBIT ước tính = lợi nhuận trước thuế + chi phí lãi vay; EBITDA = EBIT + khấu hao (từ LCTT).",
                  "P/E và EV/EBITDA dùng kết quả cả năm gần nhất đã tải, không phải số liệu 12 tháng gần nhất.",
                  "DCF nếu có chỉ là bảng độ nhạy theo giả định minh họa, không phải dự phóng hay giá mục tiêu.",
                  "Không có khuyến nghị mua/bán: đây là hồ sơ mô tả, không phải lời khuyên đầu tư."],
    }
    return rep


def peer_row(sym: str, kind: str, ys: list[str], rat: dict, val: dict) -> dict:
    r = rat[ys[-1]] if ys else {}
    return {"symbol": sym, "year": ys[-1] if ys else None,
            "revenue_growth": r.get("toi_growth") if kind == "bank" else r.get("revenue_growth"),
            "net_margin": r.get("net_margin"), "roe": r.get("roe"), "debt_to_equity": r.get("debt_to_equity"),
            "pe": val.get("pe"), "pb": val.get("pb")}


def build_all(raws: dict[str, dict], index_prices: list[list], reference: dict | None = None) -> dict[str, dict]:
    """Hai lượt: lượt 1 dựng dòng so sánh cho mọi mã, lượt 2 dựng báo cáo đầy đủ có nhóm cùng ngành."""
    pre = {}
    for sym, raw in raws.items():
        kind = _kind(raw)
        s = _series(raw, kind)
        ys = sorted(s)[-4:]
        rat = _ratios(s, kind)
        price = _price_block(raw.get("prices", []), [])
        val = _valuation(s[ys[-1]] if ys else {}, rat[ys[-1]] if ys else {}, price["last"], (raw.get("overview") or {}).get("issue_share"), kind)
        pre[sym] = {"icb": (raw.get("overview") or {}).get("icb_code_lv2"), "kind": kind, "peer_row": peer_row(sym, kind, ys, rat, val)}
    return {sym: build_report(raw, index_prices, pre, reference) for sym, raw in raws.items()}


def write_reports(reports: dict[str, dict], out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for sym, rep in reports.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", sym):
            raise ValueError("Mã doanh nghiệp không hợp lệ")
        (out / f"{sym}.json").write_text(json.dumps(rep, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    idx = {"schema": SCHEMA, "generated_at": iso_vn(now_vn()),
           "symbols": [{"symbol": k, "name": reports[k]["profile"].get("short_name") or reports[k]["profile"].get("name"),
             "industry": reports[k]["profile"].get("industry")} for k in sorted(reports)]}
    (out / "index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    return out
