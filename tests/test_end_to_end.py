"""Chạy trọn đường ống trên dữ liệu mô phỏng: sinh -> lưu -> chỉ báo -> cảnh báo -> bản tin -> CLI."""
from datetime import date

import pandas as pd
import pytest

from neopulse.analytics import alerts
from neopulse.analytics.briefing import render_briefing
from neopulse.analytics.formatting import vn_digits
from neopulse.analytics.view import build_view, elapsed_minutes
from neopulse.data.recorder import poll, rest_cycle
from neopulse.data.storage import Storage
from neopulse.neo_api.sim import SimMarket, hose_tick, round_tick, simulate_sessions


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    d = Storage(tmp_path_factory.mktemp("db") / "e2e.sqlite")
    simulate_sessions(d, 6, end=date(2026, 11, 13), step_seconds=60, symbols=None)
    return d


def test_simulation_shape_and_determinism(db):
    assert db.trading_dates("sim") == ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
    assert len(db.symbols("stock", "sim")) == 30 and len(db.symbols("future", "sim")) == 1
    a, b = SimMarket(date(2026, 11, 13), seed=1), SimMarket(date(2026, 11, 13), seed=1)
    for m in (a, b):
        m.step(m.session_times()[0])
    assert a.stock_messages() == b.stock_messages()


def test_simulated_prices_respect_exchange_rules(db):
    q = db.quotes("2026-11-13", source="sim")
    assert ((q["last"] >= q["floor"]) & (q["last"] <= q["ceiling"])).all()
    assert (q["ask1"] > q["bid1"]).all()
    assert q.groupby("symbol")["total_volume"].apply(lambda s: s.is_monotonic_increasing).all()
    assert all(abs(p / hose_tick(p) - round(p / hose_tick(p))) < 1e-9 for p in q["bid1"].head(200))
    assert hose_tick(9990) == 10 and hose_tick(10000) == 50 and hose_tick(50000) == 100
    assert round_tick(31234) == 31250 and round_tick(31234, "down") == 31200
    assert db.table("quality_log").empty                     # dữ liệu sạch không được sinh cảnh báo chất lượng giả


def test_view_is_complete_and_consistent(db):
    v = build_view(db, "sim", index_code="VN30")
    assert v.trading_date == "2026-11-13" and v.status == "ok" and v.is_simulated
    assert v.n_history_sessions == 5 and 0 <= v.pulse.score <= 100 and v.pulse.missing == []
    assert len(v.latest) == 30 and len(v.ranking) == 30 and len(v.liquidity) == 30
    assert v.foreign_summary["net_val"] == pytest.approx(v.foreign["net_val"].sum())
    assert v.breadth_universe["n_up"] == v.index_row["advances"]     # số tự tính khớp số "của sàn"
    assert not v.basis.empty and abs(v.basis_state["basis_pct"]) < 2
    assert v.pulse_series["score"].between(0, 100).all()


def test_view_as_of_never_uses_later_data(db):
    cut = pd.Timestamp("2026-11-13 10:30", tz="Asia/Ho_Chi_Minh")
    v = build_view(db, "sim", as_of=cut)
    assert v.last_update <= cut and v.quotes["ts"].max() <= cut and v.bars["bar"].max() <= cut
    full = build_view(db, "sim")
    early = full.alerts[full.alerts["ts"] < cut - pd.Timedelta(minutes=1)]
    mine = v.alerts[v.alerts["ts"] < cut - pd.Timedelta(minutes=1)]
    assert set(early["dedupe_key"]) == set(mine["dedupe_key"])       # cảnh báo quá khứ không đổi khi có thêm dữ liệu


def test_view_filters_and_empty_states(db, tmp_path):
    v = build_view(db, "sim", symbols=["VPB", "HPG"])
    assert set(v.latest["symbol"]) == {"VPB", "HPG"}
    assert build_view(db, "neo").status == "no_data"
    assert build_view(Storage(tmp_path / "empty.sqlite"), "sim").status == "no_data"
    assert build_view(db, "sim", symbols=["ZZZ"], index_code="NOPE").status == "no_data"


def test_planted_anomalies_are_recovered(db):
    from neopulse.finance.microstructure import make_bars
    bars = make_bars(db.quotes(source="sim"))
    al, truth = alerts.detect(bars, source="sim"), db.table("sim_truth")
    ev = alerts.evaluate_against_truth(al, truth)
    assert ev["n_events"] > 20 and ev["recall"] > 0.6
    for rule in ("spread_blowout", "foreign_flow"):  # quy tắc theo bước giá / tỷ trọng: gần như chỉ nổ ở sự kiện cài
        assert alerts.evaluate_against_truth(al[al["rule"] == rule], truth)["precision"] > 0.9
    # Mô phỏng không có KL nền nên volume_spike chạy nhánh z (|z| >= 3,5, Iglewicz & Hoaglin). Sau khi sửa MAD đúng
    # (CX-015) nhánh này bắt cả đỉnh KL tự nhiên ngoài sự kiện cài, nên không đòi độ chính xác; chỉ giữ ngân sách
    # <= 2 cảnh báo trên một mã một phiên như docs/calibration_log.md.
    per_sym = (al["rule"] == "volume_spike").sum() / bars.groupby(["trading_date", "symbol"]).ngroups
    assert per_sym <= 2


def test_briefing_renders_with_disclaimers(db, tmp_path):
    v = build_view(db, "sim")
    html = render_briefing(v, tmp_path / "b.html")
    assert "DỮ LIỆU MÔ PHỎNG" in html and "Không phải lời khuyên đầu tư" in html and vn_digits(f"{v.pulse.score:,.1f}") in html
    assert "<script" not in html and (tmp_path / "b.html").exists()
    empty = render_briefing(build_view(db, "neo"))
    assert "Chưa có dữ liệu" in empty


def test_elapsed_minutes_skips_lunch():
    ts = pd.Series(pd.to_datetime(["2026-11-13 09:00", "2026-11-13 11:30", "2026-11-13 12:15", "2026-11-13 13:00",
                                   "2026-11-13 14:30"]).tz_localize("Asia/Ho_Chi_Minh"))
    assert elapsed_minutes(ts).tolist() == [0, 150, 150, 150, 240]


class FakeClient:
    """NeoClient giả phát lại thông điệp mô phỏng - kiểm thử bộ ghi REST mà không cần mạng."""

    def __init__(self):
        self.m = SimMarket(date(2026, 11, 13), seed=3)
        self.times = iter(self.m.session_times())
        self.fail_next = False

    def _tick(self):
        self.m.step(next(self.times))

    def stock_detail_by_index(self, index_code):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("HTTP 503")
        self._tick()
        return self.m.stock_messages()

    def fu_stock_detail(self, stock_type="FUVN30", symbols=None):
        return self.m.future_messages()

    def market_index_detail(self, index_code="ALL"):
        return self.m.index_messages()

    def stock_detail(self, symbols, stock_type="ST"):
        return [m for m in self.m.stock_messages() if m["symbol"] in symbols]


def test_rest_polling_survives_api_failure(settings, tmp_path):
    from dataclasses import replace
    s = replace(settings, db_path=str(tmp_path / "poll.sqlite"), indexes=["VN30", "VNINDEX"])
    client = FakeClient()
    client.fail_next = True
    res = poll(s, interval_s=5, max_cycles=4, client=client, sleep=lambda x: None)
    assert res["cycles"] == 4 and res["n_quotes"] >= 3 * 30
    db = Storage(s.db_path)
    assert "poll_failed" in set(db.table("quality_log")["kind"]) and db.sources() == ["neo"]
    assert len(db.table("ingest_runs")) == 1 and db.table("ingest_runs")["ended"].notna().all()
    with pytest.raises(ValueError, match=">= 5"):
        poll(s, interval_s=1, max_cycles=1, client=client)


def test_ws_rest_reconciliation_flags_mismatch(settings):
    from neopulse.data.ingest import Ingestor
    from neopulse.timeutil import now_vn
    db = Storage(":memory:")
    ing = Ingestor(db, "neo")
    client = FakeClient()
    client._tick()
    ws = {m["symbol"]: dict(m) for m in client.m.stock_messages()}
    stocks = sorted(ws)
    assert rest_cycle(client, settings, ing, stocks, ws)["mismatch"] == 0
    ws[stocks[0]]["totalTradingVolume"] *= 2                 # WS "đi trước" REST một cách vô lý
    stats = rest_cycle(client, settings, ing, stocks, ws)
    ing.note(now_vn(), "x")
    ing.flush()
    assert stats["checked"] == 10 and stats["mismatch"] == 1
    assert (db.table("quality_log")["kind"] == "ws_rest_mismatch").sum() == 1


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    from neopulse.cli import main
    monkeypatch.setenv("NEOPULSE_DB_PATH", str(tmp_path / "cli.sqlite"))
    monkeypatch.setenv("NEOPULSE_MODE", "sim")
    monkeypatch.chdir(tmp_path)
    assert main(["simulate", "--sessions", "2", "--step", "120"]) == 0
    assert main(["briefing", "--out", str(tmp_path / "x.html")]) == 0 and (tmp_path / "x.html").exists()
    assert main(["alerts"]) == 0 and main(["validate"]) == 0 and main(["export", "--out-dir", str(tmp_path / "o")]) == 0
    assert main(["check"]) == 0 and main(["record"]) == 2    # không ghi dữ liệu thật khi đang ở chế độ sim
    out = capsys.readouterr().out
    assert "MÔ PHỎNG" in out and "< 5 phiên" in out and "<trống>" in out


def test_view_drops_index_ticks_without_pct_change(tmp_path):
    """19/11/2026: tick chỉ số SSI bị ghi với value = khối lượng, pct/độ rộng trống -> không được lọt vào view."""
    from neopulse.data.storage import Storage as S
    d = S(tmp_path / "bad.sqlite")
    simulate_sessions(d, 1, end=date(2026, 11, 13), step_seconds=300, symbols=None)
    good = d.index_ticks("2026-11-13", "VN30", "sim")
    first = good.iloc[0]
    d.insert_index([{"ts": (first["ts"] - pd.Timedelta(seconds=30)).isoformat(), "trading_date": "2026-11-13",
                     "index_code": "VN30", "source": "sim", "value": 34790395.0}])
    v = build_view(d, "sim", "2026-11-13", "VN30")
    assert v.index["value"].max() < 10_000 and len(v.index) == len(good)
