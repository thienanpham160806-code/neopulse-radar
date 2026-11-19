"""Hồ sơ doanh nghiệp: tỷ số tính đúng trên số liệu dựng tay, không lộ khuyến nghị, nhóm so sánh có dự phòng."""
import json

import pytest

from neopulse.analytics import company as co

B = 1e9


def _stmt(rows: dict[str, tuple]) -> dict:
    return {"years": ["2024", "2025"], "items": {k: {"2024": v[0], "2025": v[1]} for k, v in rows.items()}}


def _general(sym="AAA", icb="5300"):
    return {
        "symbol": sym, "source": "test",
        "overview": {"organ_name": f"CTCP {sym}", "issue_share": 1e9, "icb_code_lv2": icb, "is_bank": False},
        "income": _stmt({"net_sales": (800 * B, 1000 * B), "cost_of_sales": (-640 * B, -800 * B),
                         "gross_profit": (160 * B, 200 * B), "selling_expenses": (-60 * B, -80 * B),
                         "general_and_admin_expenses": (-20 * B, -20 * B), "interest_expenses": (-10 * B, -10 * B),
                         "net_accounting_profit_loss_before_tax": (90 * B, 110 * B),
                         "net_profit_loss_after_tax": (72 * B, 88 * B), "attributable_to_parent_company": (70 * B, 80 * B)}),
        "balance": _stmt({"total_assets": (400 * B, 600 * B), "owners_equity": (200 * B, 200 * B),
                          "current_assets": (300 * B, 450 * B), "current_liabilities": (150 * B, 300 * B),
                          "inventories_net": (100 * B, 100 * B), "cash_and_cash_equivalents": (50 * B, 60 * B),
                          "short_term_borrowings": (80 * B, 100 * B), "trade_accounts_payable": (40 * B, 40 * B),
                          "accounts_receivable": (50 * B, 50 * B)}),
        "cashflow": _stmt({"net_cash_inflows_outflows_from_operating_activities": (50 * B, 120 * B),
                           "purchases_of_fixed_assets_and_other_long_term_assets": (-30 * B, -20 * B),
                           "depreciation_and_amortization": (10 * B, 10 * B)}),
        "prices": [["2026-11-18", 9.0], ["2026-11-19", 10.0]],  # nghìn đồng
    }


def _bank(sym="BNK"):
    return {
        "symbol": sym, "source": "test", "overview": {"issue_share": 1e9, "icb_code_lv2": "8300", "is_bank": True},
        "income": _stmt({"net_interest_income": (80 * B, 90 * B), "total_operating_income": (100 * B, 120 * B),
                         "general_and_admin_expenses": (-30 * B, -36 * B), "provision_for_credit_losses": (-10 * B, -12 * B),
                         "net_accounting_profit_loss_before_tax": (60 * B, 72 * B),
                         "net_profit_loss_after_tax": (48 * B, 57.6 * B), "attributable_to_parent_company": (48 * B, 57.6 * B)}),
        "balance": _stmt({"total_assets": (1000 * B, 1200 * B), "owners_equity": (100 * B, 120 * B),
                          "loans_and_advances_to_customers": (700 * B, 800 * B), "deposits_from_customers": (800 * B, 1000 * B)}),
        "cashflow": {"years": [], "items": {}},
        "prices": [["2026-11-19", 20.0]],
    }


def test_general_ratios_dupont_and_working_capital():
    rep = co.build_all({"AAA": _general()}, [])["AAA"]
    r = rep["ratios"]["2025"]
    assert rep["kind"] == "general" and rep["years"] == ["2024", "2025"]
    assert r["revenue_growth"] == pytest.approx(0.25)
    assert r["gross_margin"] == pytest.approx(0.2) and r["net_margin"] == pytest.approx(0.08)
    assert r["roe"] == pytest.approx(80 / 200)  # vốn chủ bình quân 200
    assert r["asset_turnover"] == pytest.approx(1000 / 500)
    assert r["leverage"] == pytest.approx(500 / 200)
    assert r["net_margin"] * r["asset_turnover"] * r["leverage"] == pytest.approx(r["roe"])  # DuPont khép kín
    assert r["quick_ratio"] == pytest.approx(350 / 300, abs=0.00005)
    assert r["debt_to_equity"] == pytest.approx(0.5)
    assert r["net_debt"] == pytest.approx(40 * B)
    assert r["inventory_days"] == pytest.approx(100 / 800 * 365, rel=1e-3)
    assert r["fcf"] == pytest.approx(100 * B)
    v = rep["valuation"]  # giá 10 nghìn đồng x 1 tỷ CP = 10.000 tỷ
    assert v["market_cap"] == pytest.approx(10000) and v["pe"] == pytest.approx(125) and v["pb"] == pytest.approx(50)
    assert rep["tables"]["income"][0] == {"label": "Doanh thu thuần", "values": [800.0, 1000.0]}
    assert "Doanh thu thuần năm 2025 đạt 1.000 tỷ đồng (+25,0% so với 2024)" in rep["summary"][0]


def test_bank_uses_bank_ratios():
    rep = co.build_all({"BNK": _bank()}, [])["BNK"]
    r = rep["ratios"]["2025"]
    assert rep["kind"] == "bank"
    assert r["cir"] == pytest.approx(0.3) and r["ldr"] == pytest.approx(0.8)
    assert r["loan_growth"] == pytest.approx(800 / 700 - 1, abs=0.00005)
    assert "revenue_growth" not in r and rep["valuation"]["ev_ebitda"] is None
    assert [t["label"] for t in rep["tables"]["income"]][0] == "Thu nhập lãi thuần"


def test_no_recommendation_or_target_leaks():
    raw = _general()
    raw["overview"].update({"rating": "BUY", "target_price": 77800, "upside_to_target_percent": 0.6})
    # fetch_raw chỉ giữ trường trong _OVERVIEW_KEEP; mô phỏng lại bước lọc rồi kiểm cả đầu ra
    raw["overview"] = {k: raw["overview"].get(k) for k in co._OVERVIEW_KEEP}
    text = json.dumps(co.build_all({"AAA": raw}, [])["AAA"], ensure_ascii=False).lower()
    for bad in ("rating", "target_price", "upside_to_target_percent"):
        assert bad not in text
    assert "buy" not in text and "77800" not in text


def test_peers_only_same_icb():
    raws = {"AAA": _general("AAA", "5300"), "BBB": _general("BBB", "5300"), "CCC": _general("CCC", "5300"),
            "DDD": _general("DDD", "9500"), "BNK": _bank()}
    reps = co.build_all(raws, [])
    assert {r["symbol"] for r in reps["AAA"]["peers"]["rows"]} == {"AAA", "BBB", "CCC"}
    assert reps["AAA"]["peers"]["basis"].startswith("Cùng nhóm ngành")
    # Không lấp thiếu doanh nghiệp cùng ngành bằng doanh nghiệp thuộc ngành khác.
    assert {r["symbol"] for r in reps["DDD"]["peers"]["rows"]} == {"DDD"}
    assert reps["AAA"]["peers"]["median"]["roe"] == pytest.approx(0.4)


def test_price_block_returns_vs_index():
    prices = [[f"d{i:03d}", 10.0 + i * 0.1] for i in range(30)]
    ix = [[f"d{i:03d}", 1000.0] for i in range(30)]
    p = co._price_block(prices, ix)
    assert p["series"][0][1:] == [100.0, 100.0]
    assert p["returns"]["1T"]["index"] == 0 and p["returns"]["1T"]["stock"] == pytest.approx(12.9 / 10.8 - 1, rel=1e-3)
    assert p["last"] == pytest.approx(12900.0)


def test_write_reports_index(tmp_path):
    out = co.write_reports(co.build_all({"AAA": _general()}, []), tmp_path)
    idx = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert idx["symbols"] == [{"symbol": "AAA", "name": "CTCP AAA", "industry": None}]


def test_missing_capex_does_not_become_zero_fcf():
    raw = _general()
    raw["cashflow"]["items"].pop("purchases_of_fixed_assets_and_other_long_term_assets")
    rep = co.build_all({"AAA": raw}, [])["AAA"]
    assert rep["ratios"]["2025"]["fcf"] is None
    assert not rep["dcf"]["cases"]
    assert "Chưa đủ dữ liệu dòng tiền tự do" in " ".join(rep["summary"])


def test_dcf_uses_unlevered_cashflow_and_removes_net_debt_and_minority():
    raw = _general()
    raw["balance"]["items"].update({"long_term_borrowings": {"2024": 0, "2025": 0},
                                     "short_term_investments": {"2024": 0, "2025": 0},
                                     "minority_interests": {"2024": 0, "2025": 0}})
    rep = co.build_all({"AAA": raw}, [])["AAA"]
    # EBIT hoạt động 100 * 80% + D&A 10 - CapEx 20 - delta NWC 0 = 70 tỷ.
    # Loại thu nhập tài chính để không đếm lại tiền mặt khi cộng từ EV sang vốn chủ.
    assert rep["dcf"]["base_fcff"] == 70
    c = rep["dcf"]["cases"][0]
    pv = sum(70e9 / 1.1 ** t for t in range(1, 6))
    terminal = 70e9 * 1.02 / (0.10 - 0.02) / 1.1 ** 5
    assert c["value"] == round((pv + terminal - 40e9) / 1e9)
    assert co.build_all({"BNK": _bank()}, [])["BNK"]["dcf"]["cases"] == []


def test_write_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        co.write_reports({"../escape": {}}, tmp_path)


def test_retail_reference_group_can_include_different_icb():
    raws = {s: _general(s, "5300" if s != "PNJ" else "3700") for s in ("MWG", "FRT", "DGW", "PNJ")}
    rep = co.build_all(raws, [])["MWG"]
    assert {r["symbol"] for r in rep["peers"]["rows"]} == set(raws)
    assert "có khác biệt phân ngành ICB" in rep["peers"]["basis"]
