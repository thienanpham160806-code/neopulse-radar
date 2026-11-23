"""Run the existing SSI recorder/relay on one persistent cloud instance, on a Vietnam weekday schedule."""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime
from datetime import time as daytime
from pathlib import Path
from threading import Event

from ..config import load_settings
from ..timeutil import now_vn, to_vn

log = logging.getLogger(__name__)
START = daytime(8, 50)
ENDS = {"record": daytime(15, 5), "live-relay": daytime(15, 10)}


def in_session_window(now: datetime, holidays: set[str]) -> bool:
    now = to_vn(now)
    return now.weekday() < 5 and now.date().isoformat() not in holidays and START <= now.time() < ENDS["live-relay"]


def backup_database(db_path: Path) -> None:
    """SQLite backup API includes committed WAL pages; replace the previous backup only after integrity verification."""
    if not db_path.is_file():
        return
    output = db_path.parent / "backups" / "latest.sqlite"
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".tmp")
    try:
        with closing(sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(temp)) as target:
                source.backup(target)
                if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)


class Supervisor:
    def __init__(self, db_path: Path, holidays: set[str]):
        self.db_path, self.holidays = db_path, holidays
        self.children: dict[str, subprocess.Popen] = {}
        self.retry_at: dict[str, float] = {}
        self.failures: dict[str, int] = {}
        self.day: str | None = None

    def stop(self, name: str | None = None) -> None:
        # Stop the writer first, allowing its SIGTERM handler to flush committed data.
        for key in ([name] if name else list(ENDS)):
            child = self.children.get(key)
            if child is not None:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=10)
                self.children.pop(key, None)

    def step(self, now: datetime, elapsed: float) -> None:
        now = to_vn(now)
        if not in_session_window(now, self.holidays):
            self.stop()
            if self.day:
                backup_database(self.db_path)
                log.info("Session stopped; local volume backup verified")
                self.day = None
            return
        day = now.date().isoformat()
        if self.day != day:
            self.stop()
            self.retry_at.clear()
            self.failures.clear()
            self.day = day
        for name, end in ENDS.items():
            if now.time() >= end:
                self.stop(name)
                continue
            child = self.children.get(name)
            if child is not None:
                code = child.poll()
                if code is None:
                    continue
                self.children.pop(name)
                self.failures[name] = self.failures.get(name, 0) + 1
                wait = min(60, 5 * 2 ** min(self.failures[name] - 1, 4))
                self.retry_at[name] = elapsed + wait
                log.warning("%s exited (%s); retry in %ss", name, code, wait)
            if elapsed < self.retry_at.get(name, 0):
                continue
            command = [sys.executable, "-m", "neopulse.cli", "--log-level", "WARNING", name, "--until", end.strftime("%H:%M")]
            command += ["--flush-every", "1"] if name == "record" else ["--source", "ssi"]
            self.children[name] = subprocess.Popen(command)
            log.info("Started %s for %s", name, day)


def preflight() -> Path:
    settings = load_settings()
    if settings.mode != "live" or settings.source != "ssi":
        raise ValueError("Cloud recorder requires NEOPULSE_MODE=live and NEOPULSE_SOURCE=ssi")
    required = {"SSI_API_KEY/SSI_API_SECRET": settings.has_ssi_credentials, "ABLY_API_KEY": bool(settings.ably_api_key),
                "KV_REST_API_URL": bool(os.environ.get("KV_REST_API_URL")), "KV_REST_API_TOKEN": bool(os.environ.get("KV_REST_API_TOKEN"))}
    missing = [key for key, exists in required.items() if not exists]
    if missing:
        raise ValueError("Missing runtime secrets: " + ", ".join(missing))
    db = Path(settings.db_path)
    if not db.is_absolute() or os.environ.get("NEOPULSE_PERSISTENCE_CONFIRMED") != "1":
        raise ValueError("Mount persistent storage, use an absolute NEOPULSE_DB_PATH and confirm persistence before enabling")
    db.parent.mkdir(parents=True, exist_ok=True)
    return db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check local runtime settings without contacting SSI or starting children")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        db = preflight()
    except ValueError as error:
        log.error("%s", error)
        return 2
    if args.check:
        log.info("Runtime configuration present; network connectivity and persisted restart still require verification")
        return 0
    # Linux cloud containers: flock prevents two supervisors sharing one volume from recording twice.
    import fcntl
    with (db.parent / "collector.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.error("Another collector owns this volume")
            return 2
        stopped = Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stopped.set())
        holidays = {day.strip() for day in os.environ.get("NEOPULSE_MARKET_HOLIDAYS", "").split(",") if day.strip()}
        runner = Supervisor(db, holidays)
        try:
            while not stopped.is_set():
                runner.step(now_vn(), time.monotonic())
                stopped.wait(5)
        finally:
            runner.stop()
            backup_database(db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
