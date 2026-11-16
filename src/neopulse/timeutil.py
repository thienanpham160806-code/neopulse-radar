"""Tiện ích thời gian: mọi dấu thời gian trong hệ thống đều theo Asia/Ho_Chi_Minh (UTC+7)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Khung giờ khớp lệnh liên tục + định kỳ của HOSE (dùng để lọc dữ liệu ngoài phiên).
SESSION_OPEN = time(9, 0)
LUNCH_START = time(11, 30)
LUNCH_END = time(13, 0)
SESSION_CLOSE = time(15, 0)


def now_vn() -> datetime:
    return datetime.now(VN_TZ)


def to_vn(dt: datetime) -> datetime:
    """Chuyển về giờ VN. Datetime 'naive' được hiểu là giờ VN (quy ước của NEO API)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ)


def iso_vn(dt: datetime) -> str:
    """Chuỗi ISO 8601 có offset +07:00, độ phân giải mili-giây - định dạng lưu trữ chuẩn."""
    return to_vn(dt).isoformat(timespec="milliseconds")


def parse_event_time(date_str: str | None, time_str: str | None, fallback: datetime) -> datetime:
    """Ghép `dateString` (YYYY-MM-DD) và `indexTime` (HH:MM:SS hoặc ISO) của NEO API.

    Trả về `fallback` (thời điểm nhận) nếu không phân tích được - không bao giờ ném lỗi.
    """
    fb = to_vn(fallback)
    if not time_str:
        return fb
    s = str(time_str).strip()
    try:
        if "T" in s or (len(s) > 10 and "-" in s):
            return to_vn(datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T")))
        t = time.fromisoformat(s)
        d = date.fromisoformat(date_str) if date_str else fb.date()
        return datetime.combine(d, t, tzinfo=VN_TZ)
    except (ValueError, TypeError):
        return fb


def in_trading_hours(dt: datetime) -> bool:
    d = to_vn(dt)
    if d.weekday() >= 5:
        return False
    t = d.time()
    return (SESSION_OPEN <= t < LUNCH_START) or (LUNCH_END <= t <= SESSION_CLOSE)


def trading_minutes_elapsed(dt: datetime) -> float:
    """Số phút giao dịch đã trôi qua trong phiên (bỏ giờ nghỉ trưa), tối đa 270."""
    d = to_vn(dt)
    mins = lambda t: t.hour * 60 + t.minute + t.second / 60  # noqa: E731
    m = mins(d.time())
    am = max(0.0, min(m, mins(LUNCH_START)) - mins(SESSION_OPEN))
    pm = max(0.0, min(m, mins(SESSION_CLOSE)) - mins(LUNCH_END))
    return am + pm


def previous_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d
