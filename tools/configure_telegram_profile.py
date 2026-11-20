"""Cập nhật mô tả bot bằng UTF-8 và đọc lại để xác minh, không in token."""
import os

import httpx
from dotenv import load_dotenv

DESCRIPTION = (
    "NeoPulse Radar — trợ lý theo dõi thị trường chứng khoán Việt Nam.\n"
    "Nhấn Start hoặc /help để xem hướng dẫn, mở website và chọn nhóm tin: "
    "cảnh báo thị trường, tin doanh nghiệp, chính sách/pháp luật.\n"
    "Đăng ký tự nguyện; /watch để chọn mã, /status xem cài đặt, /stop để hủy.\n"
    "Thông tin tham khảo, không phải khuyến nghị đầu tư."
)
SHORT = "NeoPulse Radar · Cảnh báo, tin doanh nghiệp & chính sách. /start hoặc /help xem hướng dẫn; /web mở website; /stop hủy."


def main():
    load_dotenv()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    with httpx.Client(timeout=20) as client:
        for field, text, setter, getter in [
            ("description", DESCRIPTION, "setMyDescription", "getMyDescription"),
            ("short_description", SHORT, "setMyShortDescription", "getMyShortDescription"),
        ]:
            url = f"https://api.telegram.org/bot{token}/"
            r = client.post(url + setter, json={field: text}).json()
            assert r.get("ok"), "Telegram rejected profile update"
            actual = client.post(url + getter, json={}).json()["result"][field]
            assert actual == text and "?" not in actual, "Profile encoding mismatch"
            print(setter + ": UTF-8 verified")


if __name__ == "__main__":
    main()
