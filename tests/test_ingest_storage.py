from datetime import timedelta

import pandas as pd

from neopulse.data.ingest import Ingestor
from neopulse.data.storage import Storage


def make_db():
    return Storage(":memory:")


def test_roundtrip_keeps_vietnam_timezone(raw_stock, recv):
    db = make_db()
    ing = Ingestor(db, "neo")
    assert ing.add_quote(raw_stock, recv)
    ing.flush()
    q = db.quotes(source="neo")
    assert len(q) == 1 and str(q["ts"].dt.tz) == "Asia/Ho_Chi_Minh"
    assert q["ts"].iloc[0] == pd.Timestamp(recv) and q["bid1"].iloc[0] == 31250.0
    assert db.trading_dates("neo") == ["2025-09-15"] and db.symbols("stock", "neo") == ["VPB"]


def test_exact_duplicates_are_dropped(raw_stock, recv):
    db = make_db()
    ing = Ingestor(db, "neo")
    assert ing.add_quote(raw_stock, recv)
    assert not ing.add_quote(dict(raw_stock), recv + timedelta(seconds=1))
    assert ing.add_quote({**raw_stock, "bidVol1": 1, "totalTradingVolume": raw_stock["totalTradingVolume"] + 100},
                         recv + timedelta(seconds=2))
    ing.flush()
    assert ing.n_duplicates == 1 and len(db.quotes(source="neo")) == 2


def test_late_message_with_lower_cumulative_volume_is_rejected_and_logged(raw_stock, recv):
    db = make_db()
    ing = Ingestor(db, "neo")
    ing.add_quote(raw_stock, recv)
    late = {**raw_stock, "totalTradingVolume": raw_stock["totalTradingVolume"] - 5000, "closePrice": 31300}
    assert not ing.add_quote(late, recv + timedelta(seconds=3))
    ing.flush()
    log = db.table("quality_log")
    assert ing.n_rejected == 1 and (log["kind"] == "late_or_out_of_order").sum() == 1 and len(db.quotes(source="neo")) == 1


def test_cumulative_volume_may_reset_on_a_new_session(raw_stock, recv):
    ing = Ingestor(make_db(), "neo")
    ing.add_quote(raw_stock, recv)
    assert ing.add_quote({**raw_stock, "tradingDate": "16/09/2025", "totalTradingVolume": 100}, recv + timedelta(days=1))


def test_handle_routes_channels_and_logs_unknown(raw_stock, recv, tmp_path):
    db = make_db()
    ing = Ingestor(db, "neo", raw_dump_dir=str(tmp_path))
    ts = recv.timestamp()
    ing.handle("stockInfo", raw_stock, ts)
    ing.handle("marketInfo", {"indexCode": "VN30", "indexValue": "1900.5", "indexTime": "10:14:59",
                              "dateString": "2026-11-12", "advances": 20, "declines": 5}, ts)
    ing.handle("marketSession", {"marketCode": "HOSE", "marketStatus": "LO"}, ts)
    ing.handle("stockInfo", {"closePrice": 5}, ts)          # thiếu symbol
    ing.handle("unknown", {"mystery": True}, ts)
    ing.flush()
    assert db.counts()["quotes"] == 1 and db.counts()["index_ticks"] == 1
    assert len(db.table("sessions")) == 1
    kinds = set(db.table("quality_log")["kind"])
    assert {"missing_symbol", "unknown_message"} <= kinds
    assert (tmp_path / "unknown_messages.jsonl").read_text().strip() == '{"mystery": true}'


def test_batch_autoflush_and_unique_constraint(raw_stock, recv):
    db = make_db()
    ing = Ingestor(db, "neo", batch_size=2)
    for i in range(3):
        ing.handle("stockInfo", {**raw_stock, "symbol": f"S{i}"}, recv.timestamp())
    assert db.counts()["quotes"] == 2                        # đã tự ghi khi đủ lô
    ing.flush()
    row = db.quotes(source="neo").iloc[0].to_dict()
    row["ts"] = row["ts"].isoformat(timespec="milliseconds")
    assert db.insert_quotes([row]) == 0                      # trùng (symbol, ts, source) => bỏ qua


def test_reset_by_source_and_run_bookkeeping(raw_stock, recv):
    db = make_db()
    for src in ("neo", "sim"):
        ing = Ingestor(db, src)
        ing.add_quote(raw_stock, recv)
        ing.flush()
    run = db.start_run("2026-11-12T09:00:00+07:00", "neo", "test")
    db.finish_run(run, "2026-11-12T15:00:00+07:00", n_quotes=1, n_reconnects=2)
    assert db.table("ingest_runs").iloc[0]["n_reconnects"] == 2
    db.reset("sim")
    assert db.sources() == ["neo"]
    assert db.last_update("sim") is None and db.last_update("neo") is not None


def test_all_null_real_columns_read_back_as_float(tmp_path):
    # 27/11/2026: trước khớp ATO cột total_value toàn NULL, pandas đọc thành object và ranking ném TypeError
    from neopulse.data.storage import Storage
    db = Storage(tmp_path / "n.sqlite")
    db.insert_quotes([{"ts": "2026-11-27T09:05:00.000+07:00", "trading_date": "2026-11-27", "symbol": "AAA",
                       "instrument": "stock", "source": "ssi", "bid1": 10.0}])
    q = db.quotes(source="ssi")
    assert q["total_value"].dtype == float and q["maturity_date"].dtype == object
