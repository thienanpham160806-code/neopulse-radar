"""Chế độ TRỰC TIẾP: đọc SQLite (chỉ đọc) và phát số liệu TỔNG HỢP lên kênh Ably `neopulse:live`.

Luồng: `neopulse record` -> SQLite -> `neopulse live-relay` -> Ably (REST) -> trình duyệt (token chỉ subscribe).

Ba loại tin (đều có ts giờ VN, source, is_simulated, seq tăng dần):
  tick    ~1 giây, CHỈ khi đổi: các chỉ số (giá trị, thay đổi, %, tăng/giảm/đứng/trần/sàn) + basis HĐTL; < 2 KB
  pulse   ~10-30 giây (đo thời gian build_view thật rồi chọn): điểm nhịp + thành phần, top 5 tăng/giảm, cảnh báo mới
  status  bắt đầu / kết thúc / đổi pha phiên (nghỉ trưa...) / mất dữ liệu (> 60 giây bộ ghi không ghi mới) / có lại
Mọi số do Python tính (build_view, finance/*); không phát lại bảng giá hay sổ lệnh thô.

Hạn mức gói Free của Ably (6.000.000 tin/tháng, TÍNH CẢ tin giao tới người xem): đếm số tin đã gửi trong tháng vào
out/ably_usage.json, ước tính = đã gửi x (1 + số người xem). Vượt 70% thì giãn nhịp (tick x5, pulse x3) và ghi log.
Mạng rớt: thử lại lùi dần, bỏ tin cũ (tick sau thay tick trước), không bao giờ làm chết tiến trình. Khóa không vào log.
"""
from __future__ import annotations

import base64
import json
import logging
import time as _time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import pandas as pd

from ..finance import basis as fbasis
from ..timeutil import iso_vn, now_vn, to_vn
from . import webexport as wx
from .explain import vn_digits
from .view import build_view

log = logging.getLogger(__name__)

CHANNEL = "neopulse:live"
ABLY_REST = "https://rest.ably.io"
FREE_MONTHLY = 6_000_000
SLOW_AT = 0.70
INDEX_CODES = ("VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX")
GAP_AFTER_S = 60.0


class LiveRelayError(Exception):
    """Lỗi cấu hình/quyền (không thử lại được). Thông điệp không chứa khóa."""


# ----------------------------------------------------------------------------- nơi gửi
class AblyPublisher:
    """POST /channels/{kênh}/messages với Basic auth = khóa API (chỉ chạy trên máy tác giả)."""

    def __init__(self, api_key: str, *, channel: str = CHANNEL, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = _time.sleep, max_retries: int = 2):
        if ":" not in api_key or "." not in api_key.split(":", 1)[0]:
            raise LiveRelayError("ABLY_API_KEY không đúng định dạng <appId>.<keyId>:<secret>.")
        self._auth = "Basic " + base64.b64encode(api_key.encode()).decode()
        self._url = f"{ABLY_REST}/channels/{quote(channel, safe='')}/messages"
        self._http = httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0), transport=transport)
        self._sleep, self._max_retries = sleep, max_retries

    def publish(self, name: str, data: dict) -> bool:
        """True nếu Ably nhận. Lỗi tạm thời: thử lại ngắn rồi trả False. Sai khóa/quyền: ném LiveRelayError."""
        body = {"name": name, "data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}
        for attempt in range(self._max_retries + 1):
            try:
                r = self._http.post(self._url, json=body, headers={
                    "Authorization": self._auth,
                    "X-Ably-ClientId": base64.b64encode(b"neopulse-relay").decode(),
                })
            except httpx.HTTPError as e:
                why = f"lỗi mạng {type(e).__name__}"
            else:
                if r.status_code < 300:
                    return True
                if r.status_code in (401, 403):
                    raise LiveRelayError(f"Ably từ chối khóa (HTTP {r.status_code}) - kiểm tra ABLY_API_KEY và quyền publish.")
                why = f"HTTP {r.status_code}"
                if r.status_code < 500 and r.status_code != 429:
                    log.warning("Ably từ chối tin %s (%s) - bỏ tin này", name, why)
                    return False
            if attempt < self._max_retries:
                self._sleep(0.5 * 2 ** attempt)
        log.warning("Không gửi được tin %s (%s)", name, why)
        return False

    def close(self) -> None:
        self._http.close()


class DryRunPublisher:
    """--dry-run: ghi từng tin ra JSONL cục bộ, không gọi mạng."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, name: str, data: dict) -> bool:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name, "data": data}, ensure_ascii=False) + "\n")
        return True

    def close(self) -> None:
        pass


# ----------------------------------------------------------------------------- hạn mức
@dataclass
class UsageGuard:
    """Đếm tin gửi trong tháng; ước tính tin bị tính phí = gửi x (1 + người xem)."""

    path: Path
    viewers: int = 5
    limit: int = FREE_MONTHLY
    month: str = ""
    sent: int = 0
    _slow_logged: bool = field(default=False, repr=False)

    @classmethod
    def load(cls, path: str | Path, viewers: int = 5, *, month: str) -> UsageGuard:
        p = Path(path)
        g = cls(p, viewers, month=month)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("month") == month:
                g.sent = int(d.get("sent", 0))
        except (OSError, ValueError):
            pass
        return g

    @property
    def estimated(self) -> int:
        return self.sent * (1 + self.viewers)

    @property
    def ratio(self) -> float:
        return self.estimated / self.limit

    def factor(self) -> int:
        """1 = bình thường; 5 = đã vượt 70% hạn mức ước tính -> giãn nhịp."""
        if self.ratio < SLOW_AT:
            return 1
        if not self._slow_logged:
            log.warning("Ước tính đã dùng %.0f%% hạn mức Ably tháng %s (%d tin gửi x %d) - GIÃN NHỊP: tick x5, pulse x3",
                        self.ratio * 100, self.month, self.sent, 1 + self.viewers)
            self._slow_logged = True
        return 5

    def count(self, n: int = 1) -> None:
        self.sent += n
        if self.sent % 50 == 0:
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"month": self.month, "sent": self.sent, "viewers_assumed": self.viewers,
                                         "estimated_billable": self.estimated, "limit": self.limit}, ensure_ascii=False),
                             encoding="utf-8")


# ----------------------------------------------------------------------------- dựng tin
def _r(x: Any, nd: int = 2) -> float | None:
    return wx._r(x, nd)


def index_snapshot(db, source: str, day: str, as_of: str | None = None, codes: tuple[str, ...] = INDEX_CODES) -> dict:
    """Bản ghi chỉ số mới nhất (có % thay đổi) của từng chỉ số tới thời điểm `as_of` (ISO) - truy vấn theo chỉ mục."""
    out: dict[str, dict] = {}
    for code in codes:
        sql = ("SELECT value, change, pct_change, advances, declines, no_change, n_ceiling, n_floor, ts FROM index_ticks "
               "WHERE trading_date=? AND index_code=? AND source=? AND pct_change IS NOT NULL"
               + (" AND ts<=?" if as_of else "") + " ORDER BY ts DESC LIMIT 1")
        row = db._con.execute(sql, (day, code, source, as_of) if as_of else (day, code, source)).fetchone()
        if row:
            v, ch, pct, adv, dec, nc, ce, fl, _ = row
            out[code] = {"v": _r(v), "ch": _r(ch), "pct": _r(pct), "adv": _r(adv, 0), "dec": _r(dec, 0),
                         "nc": _r(nc, 0), "ce": _r(ce, 0), "fl": _r(fl, 0)}
    return out


def basis_snapshot(db, source: str, day: str, as_of: str | None = None) -> dict | None:
    """Basis HĐTL gần nhất: dùng finance.basis.basis_series trên điểm mới nhất (không tự viết lại công thức)."""
    cond = " AND ts<=?" if as_of else ""
    args = (day, source, as_of) if as_of else (day, source)
    f = pd.read_sql_query("SELECT ts, trading_date, symbol, last, maturity_date FROM quotes WHERE trading_date=? "
                          f"AND source=? AND instrument='future'{cond} ORDER BY ts DESC LIMIT 1", db._con, params=args)
    if f.empty:
        return None
    # chỉ số VN30 gần nhất KHÔNG muộn hơn tick HĐTL (hai luồng cập nhật độc lập; ghép lùi như basis_series)
    s = pd.read_sql_query("SELECT ts, value FROM index_ticks WHERE trading_date=? AND index_code='VN30' AND source=? "
                          "AND pct_change IS NOT NULL AND ts<=? ORDER BY ts DESC LIMIT 1", db._con,
                          params=(day, source, f["ts"].iloc[0]))
    if s.empty:
        return None
    for d in (f, s):
        d["ts"] = pd.to_datetime(d["ts"], format="ISO8601")
    b = fbasis.basis_series(f, s, tolerance="5min")
    if b.empty:
        return None
    r = b.iloc[-1]
    return {"sym": r["symbol"], "f": _r(r["future"]), "s": _r(r["spot"]), "b": _r(r["basis"]), "bp": _r(r["basis_pct"], 3),
            "dtm": _r(r["dtm"], 0)}


MAX_ALERTS_PER_PULSE = 10


def alert_key(a: dict) -> tuple:
    return (a["t"], a["s"], a["rule"])


def pulse_payload(v, sent_alerts: set[tuple]) -> dict:
    """Điểm nhịp + thành phần, top 5 tăng/giảm trong rổ, tối đa 10 cảnh báo CHƯA gửi (cũ trước).

    KHÔNG đánh dấu đã gửi ở đây: chỉ đánh dấu sau khi Ably nhận gói (LiveRelay.run), để mạng lỗi hay đợt > 10 cảnh báo
    không làm mất cảnh báo - phần còn lại đi ở pulse sau."""
    p = v.pulse
    comps = [{"k": c["key"], "n": c["name"], "w": c["weight"], "v": c["value"]} for c in wx._pulse(v)["components"]]
    lat = v.latest.dropna(subset=["pct_change"]) if len(v.latest) else v.latest
    def movers(asc: bool) -> list[dict]:
        if lat.empty:
            return []
        rows = lat.sort_values("pct_change", ascending=asc).head(5)
        return [{"s": r.symbol, "pct": _r(r.pct_change), "last": _r(r.last, 0)} for r in rows.itertuples()]
    pending = []
    if len(v.alerts):
        for r in v.alerts.sort_values("ts").itertuples():
            a = {"t": r.ts.isoformat(timespec="seconds"), "s": r.symbol, "rule": r.rule, "sev": r.severity, "msg": vn_digits(r.message)}
            if alert_key(a) not in sent_alerts:
                pending.append(a)
    return {"score": _r(p.score, 1) if p else None, "label": p.label if p else "Không đủ dữ liệu", "comps": comps,
            "up": movers(False), "down": movers(True), "alerts": pending[:MAX_ALERTS_PER_PULSE],
            "n_alerts": int(len(v.alerts)), "n_pending": len(pending),
            "sec": [{"n": r["sector"], "p": _r(r["pct_cap"], 2), "c": _r(r["contrib_pts"], 2), "u": int(r["n_up"]),
                     "d": int(r["n_down"])} for r in (v.sectors.to_dict("records") if len(v.sectors) else [])][:12],
            "index_code": v.index_code, "day": v.trading_date}


# ----------------------------------------------------------------------------- vòng lặp
@dataclass
class RelayStats:
    sent: dict[str, int] = field(default_factory=lambda: {"tick": 0, "pulse": 0, "status": 0})
    failed: int = 0
    skipped_unchanged: int = 0
    pulse_every_s: float = 0.0
    build_view_s: float = 0.0


class LiveRelay:
    def __init__(self, db_path: str, source: str, publisher, usage: UsageGuard, *, index_code: str = "VN30",
                 tick_every: float = 1.0, until: time | None = None, replay_speed: float = 0.0,
                 clock: Callable[[], datetime] = now_vn, mono: Callable[[], float] = _time.monotonic,
                 sleep: Callable[[float], None] = _time.sleep, snapshot_publisher=None):
        self.db_path, self.source, self.pub, self.usage = db_path, source, publisher, usage
        self.index_code, self.tick_every, self.until, self.replay_speed = index_code, tick_every, until, replay_speed
        self.clock, self.mono, self.sleep = clock, mono, sleep
        self.seq = 0
        self.stats = RelayStats()
        self._last_tick: dict | None = None
        self._sent_alerts: set[tuple] = set()
        self._phase: str | None = None
        self._gap = False
        self._reported_gap: bool | None = None
        self._fail_streak = 0
        self._next_send_ok = 0.0
        self._replay_t0: float | None = None
        self._replay_base: pd.Timestamp | None = None
        # mã lần chạy: trình duyệt dùng để phân biệt relay khởi động lại với tin đến muộn (CX-009)
        self.run_id = uuid.uuid4().hex
        self.snapshot_publisher = snapshot_publisher

    # -- tin
    def envelope(self, payload: dict) -> dict:
        self.seq += 1
        return {"ts": iso_vn(self.clock()), "source": self.source, "is_simulated": self.source == "sim",
                "run": self.run_id, "seq": self.seq, "data_gap": self._gap, **payload}

    def send(self, name: str, payload: dict) -> bool:
        if self.mono() < self._next_send_ok:
            return False  # đang lùi sau lỗi mạng: bỏ tin tick/pulse cũ, tin sau sẽ thay
        ok = False
        try:
            ok = self.pub.publish(name, self.envelope(payload))
        except LiveRelayError:
            raise
        except Exception as e:  # noqa: BLE001 - không để lỗi bất ngờ giết relay
            log.warning("Gửi %s lỗi: %s", name, type(e).__name__)
        if ok:
            self.stats.sent[name] += 1
            self.usage.count()
            self._fail_streak = 0
        else:
            self.stats.failed += 1
            self._fail_streak += 1
            wait = min(60.0, 2.0 ** min(self._fail_streak, 6))
            self._next_send_ok = self.mono() + wait
            log.warning("Ably chưa nhận được (%d lần liên tiếp) - tạm dừng %.0fs", self._fail_streak, wait)
        return ok

    # -- thời điểm dữ liệu (thật: bây giờ; mô phỏng: phát lại phiên mô phỏng theo tốc độ replay)
    def as_of(self, db, day: str) -> str | None:
        if not self.replay_speed:
            return None
        if self._replay_base is None:
            first = db._con.execute("SELECT MIN(ts) FROM index_ticks WHERE trading_date=? AND source=?",
                                    (day, self.source)).fetchone()[0]
            self._replay_base = pd.Timestamp(first) + pd.Timedelta(minutes=2)  # đủ để mọi chỉ số đã có tick đầu
            self._replay_t0 = self.mono()
        return (self._replay_base + pd.Timedelta(seconds=(self.mono() - self._replay_t0) * self.replay_speed)).isoformat()

    def has_day(self, db, day: str) -> bool:
        return db._con.execute("SELECT 1 FROM index_ticks WHERE trading_date=? AND source=? LIMIT 1",
                               (day, self.source)).fetchone() is not None

    def tick_payload(self, db, day: str, as_of: str | None) -> dict:
        return {"day": day, "ix": index_snapshot(db, self.source, day, as_of), "basis": basis_snapshot(db, self.source, day, as_of)}

    def check_status(self, db, day: str, as_of: str | None) -> None:
        phase = wx.session_phase(self.clock()) if not self.replay_speed else "open"
        if phase != self._phase:
            if self.send("status", {"event": "phase", "phase": phase}):
                self._phase = phase
        if phase != "open":
            return
        last = db._con.execute("SELECT MAX(ts) FROM index_ticks WHERE trading_date=? AND source=?"
                               + (" AND ts<=?" if as_of else ""),
                               (day, self.source, as_of) if as_of else (day, self.source)).fetchone()[0]
        now = pd.Timestamp(as_of) if as_of else pd.Timestamp(self.clock())
        age = (now - pd.Timestamp(last)).total_seconds() if last else None
        gap = age is None or age > GAP_AFTER_S
        self._gap = gap
        if gap != self._reported_gap:
            if self.send("status", {"event": "data_gap" if gap else "data_ok", "age_s": _r(age, 0)}):
                self._reported_gap = gap
            log.log(logging.WARNING if gap else logging.INFO, "Bộ ghi %s (%s)",
                    "KHÔNG ghi mới" if gap else "ghi lại bình thường",
                    "chưa có tick nào hôm nay" if age is None else f"tin mới nhất cách {age:.0f} giây")

    def build_pulse(self, db, day: str, as_of: str | None) -> dict | None:
        t0 = _time.perf_counter()
        try:
            v = build_view(db, self.source, day, self.index_code,
                           as_of=pd.Timestamp(as_of) if as_of else None)
        except Exception as e:  # noqa: BLE001
            log.warning("build_view lỗi: %s", type(e).__name__)
            return None
        self.stats.build_view_s = _time.perf_counter() - t0
        if v.status == "no_data" or v.trading_date != day:
            return None
        if self.snapshot_publisher:
            try:
                self.snapshot_publisher(v, db)
            except Exception as e:  # noqa: BLE001 - cloud bootstrap failure must not stop live ticks
                log.warning("Cập nhật phiên cloud lỗi: %s", type(e).__name__)
        return pulse_payload(v, self._sent_alerts)

    def run(self, max_loops: int | None = None) -> RelayStats:
        loops = 0
        db = None
        try:
            # Bộ ghi có thể chưa tạo CSDL/schema khi relay được khởi động trước lúc mở cửa.
            while db is None:
                try:
                    db = wx.ReadOnlyStorage(self.db_path)
                    if not db._con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='index_ticks'").fetchone():
                        db.close()
                        db = None
                except FileNotFoundError:
                    if self.replay_speed:
                        raise LiveRelayError("Chưa có cơ sở dữ liệu để phát lại.") from None
                if db is None:
                    loops += 1
                    if (self.until and self.clock().time() >= self.until) or (max_loops and loops >= max_loops):
                        return self.stats
                    self.sleep(self.tick_every * 5)
            day = (db._con.execute("SELECT MAX(trading_date) FROM index_ticks WHERE source=?", (self.source,)).fetchone()[0]
                   if self.replay_speed else None)
            if day is None and self.replay_speed:
                raise LiveRelayError(f"Chưa có dữ liệu nguồn '{self.source}'.")
            self.send("status", {"event": "start", "day": day})
            next_pulse = 0.0
            while True:
                t0 = self.mono()
                f = self.usage.factor()
                if not self.replay_speed:
                    # CX-006: relay khởi động 8:55 khi CSDL mới có phiên hôm trước -> chuyển sang phiên hôm nay ngay khi
                    # bộ ghi có dữ liệu (truy vấn theo chỉ mục, rẻ); đổi phiên thì đặt lại mọi trạng thái của phiên cũ
                    today = self.clock().date().isoformat()
                    if day != today and self.has_day(db, today):
                        day = today
                        self._last_tick, self._sent_alerts, self._gap = None, set(), False
                        self._phase, self._reported_gap = None, None
                        next_pulse = 0.0
                        self.send("status", {"event": "start", "day": day})
                if day is None:
                    loops += 1
                    if (self.until and self.clock().time() >= self.until) or (max_loops and loops >= max_loops):
                        break
                    self.sleep(self.tick_every * 5)  # chưa có phiên nào: chờ bộ ghi
                    continue
                as_of = self.as_of(db, day)
                self.check_status(db, day, as_of)
                tick = self.tick_payload(db, day, as_of)
                if tick != self._last_tick and tick["ix"]:
                    if self.send("tick", tick):
                        self._last_tick = tick
                else:
                    self.stats.skipped_unchanged += 1
                if t0 >= next_pulse:
                    pl = self.build_pulse(db, day, as_of)
                    if pl and self.send("pulse", pl):
                        self._sent_alerts.update(alert_key(a) for a in pl["alerts"])  # chỉ khi Ably đã nhận
                    # nhịp pulse = 8 x thời gian build_view thật, kẹp 10-30 giây (x3 khi giãn nhịp)
                    self.stats.pulse_every_s = min(30.0, max(10.0, 8 * self.stats.build_view_s)) * (3 if f > 1 else 1)
                    next_pulse = t0 + self.stats.pulse_every_s
                loops += 1
                if (self.until and self.clock().time() >= self.until) or (max_loops and loops >= max_loops):
                    break
                self.sleep(max(0.0, self.tick_every * f - (self.mono() - t0)))
            self.send("status", {"event": "end"})
        finally:
            self.usage.save()
            if db is not None:
                db.close()
            self.pub.close()
        return self.stats


def run_live_relay(settings, *, source: str, until: time | None, dry_run: bool = False, viewers: int = 5,
                   usage_path: str = "out/ably_usage.json", dry_run_path: str = "out/live_dryrun.jsonl",
                   replay_speed: float = 0.0, max_loops: int | None = None) -> RelayStats:
    if dry_run:
        pub = DryRunPublisher(dry_run_path)
    else:
        if not settings.ably_api_key:
            raise LiveRelayError("Thiếu ABLY_API_KEY trong .env (hoặc dùng --dry-run).")
        pub = AblyPublisher(settings.ably_api_key)
    usage = UsageGuard.load(usage_path, viewers, month=to_vn(now_vn()).strftime("%Y-%m"))
    log.info("live-relay: nguồn=%s · kênh=%s · hạn mức ước tính đã dùng %.1f%%%s", source, CHANNEL, usage.ratio * 100,
             " · DRY-RUN" if dry_run else "")
    from .marketstore import MarketSnapshots
    snapshots = MarketSnapshots.from_env() if source != "sim" and not dry_run and not replay_speed else None
    relay = LiveRelay(settings.db_path, source, pub, usage, until=until, replay_speed=replay_speed, snapshot_publisher=snapshots)
    try:
        st = relay.run(max_loops=max_loops)
    finally:
        if snapshots:
            snapshots.close()
    log.info("live-relay kết thúc: %s · lỗi %d · bỏ qua vì không đổi %d · build_view %.2fs · pulse mỗi %.0fs",
             st.sent, st.failed, st.skipped_unchanged, st.build_view_s, st.pulse_every_s)
    return st
