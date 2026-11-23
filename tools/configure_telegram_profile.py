"""Cập nhật mô tả và menu lệnh của bot bằng UTF-8, đọc lại để xác minh, không in token."""
import os

import httpx
from dotenv import load_dotenv

DESCRIPTION = (
    "NeoPulse Radar — trợ lý theo dõi thị trường chứng khoán Việt Nam.\n"
    "Xem nhanh nhịp thị trường (/market), cảnh báo (/alerts) và hồ sơ doanh nghiệp (gõ mã, ví dụ MWG).\n"
    "Đăng ký tự nguyện bằng /start; /watch để chọn mã, /status xem cài đặt, /stop để hủy.\n"
    "Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."
)
SHORT = "NeoPulse Radar · Nhịp thị trường, cảnh báo, hồ sơ doanh nghiệp và tin theo mã. /help xem hướng dẫn."
COMMANDS = [("market", "Nhịp thị trường VN30"), ("alerts", "Cảnh báo trong phiên"), ("company", "Tra hồ sơ doanh nghiệp, ví dụ /company MWG"),
            ("watchlist", "Mã đang theo dõi"), ("status", "Cài đặt nhận tin"), ("start", "Đăng ký nhận cảnh báo"),
            ("help", "Hướng dẫn"), ("stop", "Hủy và xóa đăng ký")]


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
        commands = [{"command": c, "description": d} for c, d in COMMANDS]
        assert client.post(url + "setMyCommands", json={"commands": commands}).json().get("ok"), "Telegram rejected commands"
        assert client.post(url + "getMyCommands", json={}).json()["result"] == commands, "Command menu mismatch"
        print("setMyCommands: verified")


if __name__ == "__main__":
    main()
