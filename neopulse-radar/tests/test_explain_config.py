import logging
from dataclasses import replace

import httpx
import pytest

from neopulse.analytics import explain
from neopulse.analytics.notify import format_alert, send_telegram
from neopulse.config import load_settings
from neopulse.logging_setup import RedactFilter, redact

FACTS = {"điểm_nhịp": 64.1, "thay_đổi_pct": 0.68, "số_mã_tăng": 18, "gtgd_tỷ": 22510, "nn_ròng_tỷ": -85.7}


def test_numbers_grounded_accepts_facts_in_vn_and_en_formats():
    ok, bad = explain.numbers_grounded("Điểm nhịp 64,1/100; VN30 +0,68%; 18 mã tăng; GTGD 22.510 tỷ; NN bán ròng 85,7 tỷ.", FACTS)
    assert ok and bad == []
    assert explain.numbers_grounded("Điểm 64.1, tăng 0.68%", FACTS)[0]


def test_numbers_grounded_rejects_invented_numbers():
    ok, bad = explain.numbers_grounded("VN30 tăng 2,35% lên 1.999 điểm.", FACTS)
    assert not ok and len(bad) == 2


def test_advice_filter():
    assert explain.contains_advice("Nhà đầu tư nên mua VPB ở vùng giá này.")
    assert explain.contains_advice("Khuyến nghị bán khi thủng hỗ trợ")
    assert not explain.contains_advice("Khối ngoại mua ròng 85,7 tỷ trong rổ theo dõi.")


class V:  # SessionView tối giản cho bộ diễn giải
    def __init__(self):
        import pandas as pd

        from neopulse.finance.pulse import combine
        self.status, self.source, self.is_simulated, self.trading_date, self.index_code = "ok", "sim", True, "2026-11-13", "VN30"
        self.index_row = {"value": 1981.02, "pct_change": 0.68, "advances": 18, "declines": 10, "n_ceiling": 0,
                          "n_floor": 0, "total_value": 22.51e12}
        self.pulse = combine({"breadth": 0.29, "momentum": 0.69, "book": 0.14, "foreign": -0.03, "liquidity": -0.01})
        self.foreign_summary = {"net_val": -85.7e9, "n_net_buy": 13, "n_net_sell": 17}
        self.foreign = pd.DataFrame({"net_val": [1.0, -1.0]}, index=["TCB", "BID"])
        self.basis_state, self.alerts, self.divergence = {}, pd.DataFrame(), None


def llm_transport(text, status=200):
    return httpx.MockTransport(lambda r: httpx.Response(status, json={"content": [{"type": "text", "text": text}]}))


def test_template_summary_is_grounded_in_its_own_facts():
    v = V()
    text = " ".join(explain.template_summary(v))
    assert "64.1" in text and "TCB" in text and "BID" in text
    assert explain.numbers_grounded(text, {**explain.build_facts(v), "raw": [1981.02, 22.5, 22510, 85.7, 13, 17, 100]})[0]
    assert not explain.contains_advice(text)


def test_llm_disabled_without_key(settings):
    assert explain.llm_summary(V(), settings)["engine"] == "template"


def test_llm_output_is_used_only_when_grounded_and_advice_free(settings):
    s = replace(settings, llm_api_key="k", llm_model="some-model")
    good = explain.llm_summary(V(), s, transport=llm_transport("Dữ liệu mô phỏng. VN30 tăng 0,68%, điểm nhịp 64,1."))
    assert good["engine"] == "llm:some-model" and good["rejected_reason"] is None
    invented = explain.llm_summary(V(), s, transport=llm_transport("VN30 tăng 5,55% nhờ tin vĩ mô."))
    assert invented["engine"] == "template" and "số không có" in invented["rejected_reason"]
    advice = explain.llm_summary(V(), s, transport=llm_transport("Điểm nhịp 64,1 - nên mua mạnh."))
    assert advice["engine"] == "template" and "khuyến nghị" in advice["rejected_reason"]
    failed = explain.llm_summary(V(), s, transport=llm_transport("x", status=500))
    assert failed["engine"] == "template" and failed["text"]


def test_settings_load_validate_and_redact(tmp_path, monkeypatch):
    for k in ("NEOPULSE_MODE", "NEO_USERNAME", "NEO_PASSWORD", "NEO_ACCESS_TOKEN", "NEO_MAX_RPS", "NEOPULSE_EXTRA_SYMBOLS"):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text("NEOPULSE_MODE=live\nNEO_USERNAME=116C123456\nNEO_PASSWORD=hunter2\nNEOPULSE_EXTRA_SYMBOLS= fpt , hpg\n")
    s = load_settings(env)
    assert s.is_live and s.has_neo_credentials and s.extra_symbols == ["FPT", "HPG"]
    red = str(s.redacted())
    assert "hunter2" not in red and "116C123456" not in red and "<đã điền>" in red
    monkeypatch.setenv("NEO_MAX_RPS", "9")
    with pytest.raises(ValueError, match="5"):
        load_settings(env)
    monkeypatch.setenv("NEO_MAX_RPS", "4")
    monkeypatch.setenv("NEOPULSE_MODE", "prod")
    with pytest.raises(ValueError):
        load_settings(env)


def test_log_redaction():
    jwt = "eyJhbGciOiJSUzI1NiIs.eyJzdWIiOiIxMjM0NTY3ODkw.SflKxwRJSMeKKF2QT4"
    assert jwt not in redact(f"token={jwt}") and "abcdefghijklmnop" not in redact("Authorization: Bearer abcdefghijklmnop")
    assert "hunter2" not in redact('{"username": "u", "password": "hunter2"}')
    rec = logging.LogRecord("x", logging.INFO, "", 0, "auth %s", (jwt,), None)
    RedactFilter().filter(rec)
    assert jwt not in rec.getMessage()


def test_telegram_is_optional_and_never_raises(settings):
    assert send_telegram(settings, "hi") is False
    s = replace(settings, telegram_bot_token="123:ABC", telegram_chat_id="1")
    assert send_telegram(s, "hi", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True})))

    def boom(r):
        raise httpx.ConnectError("down")
    assert send_telegram(s, "hi", transport=httpx.MockTransport(boom)) is False
    msg = format_alert({"ts": "2026-11-13T10:00:00+07:00", "severity": "CAO", "symbol": "VPB", "message": "m"}, simulated=True)
    assert msg.startswith("[MÔ PHỎNG]") and "không phải khuyến nghị" in msg
