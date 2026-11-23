from datetime import date

import pandas as pd

from neopulse.analytics import validation
from neopulse.analytics import webexport as wx
from neopulse.data.storage import Storage
from neopulse.finance import microstructure as micro
from neopulse.neo_api.sim import simulate_sessions


def test_session_reduction_matches_full_tick_calculation(monkeypatch, tmp_path):
    db = Storage(tmp_path / "proof.sqlite")
    try:
        simulate_sessions(db, 3, end=date(2026, 11, 20), step_seconds=300)
        bars = micro.make_bars(db.quotes(source="sim"), "1min")
        expected = validation.validate_signals(bars)
        expected_per = validation.per_session_ic(bars)
        original = db.quotes
        calls = []

        def bounded(trading_date=None, *args, **kwargs):
            assert trading_date is not None, "validation must not load all sessions of raw order books"
            calls.append(trading_date)
            return original(trading_date, *args, **kwargs)

        monkeypatch.setattr(db, "quotes", bounded)
        actual = wx.build_validation_block(db, "sim")
        assert calls == db.trading_dates("sim")
        pd.testing.assert_frame_equal(actual["ic"]["table"], expected["table"])
        pd.testing.assert_frame_equal(actual["ic_by_session"], expected_per)
        assert actual["ic"]["train"] == expected["train"] and actual["ic"]["test"] == expected["test"]
    finally:
        db.close()


def test_quality_counts_all_instruments_but_does_not_materialize_the_full_book(monkeypatch, tmp_path):
    db = Storage(tmp_path / "quality.sqlite")
    try:
        rows = [
            {"ts": "2026-11-20T09:00:00+07:00", "trading_date": "2026-11-20", "symbol": "AAA", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-20T09:00:01+07:00", "trading_date": "2026-11-20", "symbol": "FUT", "instrument": "future", "source": "ssi"},
            {"ts": "2026-11-20T09:00:01+07:00", "trading_date": "2026-11-20", "symbol": "BBB", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-20T09:00:02+07:00", "trading_date": "2026-11-20", "symbol": "AAA", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-20T09:00:03+07:00", "trading_date": "2026-11-20", "symbol": "AAA", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-20T09:03:00+07:00", "trading_date": "2026-11-20", "symbol": "AAA", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-20T13:00:00+07:00", "trading_date": "2026-11-20", "symbol": "AAA", "instrument": "stock", "source": "ssi"},
            {"ts": "2026-11-19T09:00:00+07:00", "trading_date": "2026-11-19", "symbol": "OTHER", "instrument": "stock", "source": "neo"},
        ]
        db.insert_quotes(rows)
        original = db.quotes(instrument=None, source="ssi")
        t = original[["trading_date", "ts"]].drop_duplicates().sort_values("ts")
        dt = t.groupby("trading_date")["ts"].diff().dt.total_seconds()
        expected = t.assign(gap_s=dt)
        lunch = (t.ts.dt.hour == 13) & (t.ts.dt.minute < 5)
        expected = expected[(expected.gap_s > max(5 * dt.median(), 60)) & ~lunch]
        monkeypatch.setattr(db, "quotes", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("full book loaded")))
        actual = validation.data_quality_report(db, "ssi")
        assert (actual["n_quotes"], actual["n_sessions"], actual["n_symbols"]) == (7, 1, 3)
        assert len(actual["gaps"]) == 1
        pd.testing.assert_frame_equal(actual["gaps"].reset_index(drop=True), expected.reset_index(drop=True))
        assert validation.data_quality_report(db, "empty")["n_quotes"] == 0
        assert validation.data_quality_report(db)["n_sessions"] == 2
    finally:
        db.close()
