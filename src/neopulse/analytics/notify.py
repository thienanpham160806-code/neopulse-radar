"""Gửi cảnh báo qua Telegram (tùy chọn). Không có token => bỏ qua trong im lặng có ghi log."""
from __future__ import annotations

import logging

import httpx
import pandas as pd

from ..config import Settings
from .formatting import vn_digits

log = logging.getLogger(__name__)
DISCLAIMER = "Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."


def format_alert(row: dict | pd.Series, simulated: bool = False) -> str:
    ts = pd.Timestamp(row["ts"]).strftime("%H:%M %d/%m")
    tag = "[MÔ PHỎNG] " if simulated else ""
    level = {"CAO": "Mức cao", "TRUNG BÌNH": "Mức trung bình", "THẤP": "Mức thấp"}.get(row["severity"], row["severity"])
    return f"{tag}[{level}] {row['symbol']} · {ts}\n{vn_digits(row['message'])}\n{DISCLAIMER}"


def send_telegram(settings: Settings, text: str, *, transport: httpx.BaseTransport | None = None) -> bool:
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        log.debug("Chưa cấu hình Telegram - bỏ qua gửi.")
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        with httpx.Client(timeout=10, transport=transport) as c:
            r = c.post(url, json={"chat_id": settings.telegram_chat_id, "text": text})
        if r.status_code != 200:
            log.warning("Telegram trả HTTP %s", r.status_code)  # không log URL vì chứa token
        return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("Không gửi được Telegram: %s", type(e).__name__)
        return False


def push_new_alerts(settings: Settings, storage, alerts: pd.DataFrame, min_severity: str = "CAO") -> int:
    """Lưu cảnh báo (khóa dedupe chặn lặp) và chỉ gửi những cảnh báo MỚI đạt mức ưu tiên."""
    from .alerts import to_rows
    if alerts.empty:
        return 0
    existing = set(storage.alerts()["dedupe_key"]) if len(storage.alerts()) else set()
    new = alerts[~alerts["dedupe_key"].isin(existing)]
    storage.insert_alerts(to_rows(new))
    order = {"THẤP": 0, "TRUNG BÌNH": 1, "CAO": 2}
    sent = 0
    for _, r in new[new["severity"].map(order) >= order[min_severity]].iterrows():
        sent += send_telegram(settings, format_alert(r, simulated=r["source"] == "sim"))
    return sent
