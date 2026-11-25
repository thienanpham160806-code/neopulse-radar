"""Kiểm tra sức khỏe bộ ghi, báo riêng cho chủ dự án qua bot Telegram.

Chạy trong worker cloud (`/api/telegram_tick`, cron ngoài mỗi 5 phút), nên vẫn báo được khi máy ghi tắt hẳn.
Đọc `meta.last_update` của payload `/api/data` (dữ liệu bộ phát trực tiếp đẩy lên Redis):
  * từ 09:05 ngày thứ Hai–thứ Sáu mà chưa có dữ liệu của hôm nay -> "chưa ghi gì";
  * trong giờ khớp lệnh mà dữ liệu đứng yên quá 5 phút giao dịch -> "im lặng".
Mỗi sự cố báo một lần (khóa Redis). Chưa có lịch nghỉ lễ: ngày lễ trong tuần sẽ nhận một tin "chưa ghi gì".
Chat nhận tin: biến môi trường TELEGRAM_OWNER_CHAT_ID (không lưu trong mã).
"""
from __future__ import annotations

import os
from datetime import datetime

from ..timeutil import VN_TZ, trading_minutes_elapsed

SILENT_MIN = 5.0
KEY = "neopulse:health:"


def _last_update(payload: dict | None) -> datetime | None:
    meta = (payload or {}).get("meta") or {}
    if meta.get("is_simulated"):
        return None
    try:
        return datetime.fromisoformat(meta["last_update"]).astimezone(VN_TZ)
    except (KeyError, TypeError, ValueError):
        return None


def recorder_issue(payload: dict | None, now: float) -> tuple[str, str] | None:
    """-> (mã sự cố để chống báo trùng, nội dung HTML) hoặc None nếu bình thường / ngoài giờ kiểm tra."""
    t = datetime.fromtimestamp(now, VN_TZ)
    hm = t.strftime("%H:%M")
    if t.weekday() >= 5 or not ("09:05" <= hm < "11:30" or "13:05" <= hm < "14:45"):
        return None  # chỉ kiểm trong giờ khớp lệnh liên tục; 5 phút đầu mỗi buổi để bộ ghi kịp khởi động
    today = t.date().isoformat()
    last = _last_update(payload)
    if last is None or last.date().isoformat() != today:
        return (f"no_data|{today}",
                f"⚠️ <b>Bộ ghi NeoPulse chưa ghi dữ liệu phiên {t.strftime('%d/%m')}</b>\n"
                f"Đến {hm} web vẫn chưa nhận dữ liệu của hôm nay. Kiểm tra máy ghi: máy có bật và cắm sạc, "
                "tác vụ NeoPulseRecord, mạng, log out/record_*.log.\n<i>Nếu hôm nay nghỉ lễ, bỏ qua tin này.</i>")
    silent = trading_minutes_elapsed(t) - trading_minutes_elapsed(last)
    if silent > SILENT_MIN:
        return (f"silent|{last.isoformat()}",
                f"⚠️ <b>Dữ liệu NeoPulse im lặng {silent:.0f} phút</b>\n"
                f"Cập nhật cuối lúc {last.strftime('%H:%M')}, bây giờ {hm}. Bộ ghi hoặc bộ phát trực tiếp có thể đã dừng "
                "hoặc mất mạng; kiểm tra log out/record_*.log và out/relay_*.log trên máy ghi.")
    return None


def notify_owner(payload: dict | None, now: float, store, send) -> bool:
    """Gửi cảnh báo sức khỏe nếu có sự cố mới. store: RedisUsers (cần .call); send(chat, text). -> đã gửi hay chưa."""
    chat = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "").strip()
    issue = recorder_issue(payload, now) if chat and store else None
    if not issue:
        return False
    marker, text = issue
    if not store.call("SET", KEY + marker, "1", "NX", "EX", "86400"):
        return False  # đã báo sự cố này
    send(chat, text)
    return True
