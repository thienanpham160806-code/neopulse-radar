"""Cập nhật mô tả và menu lệnh của bot bằng UTF-8, đọc lại để xác minh, không in token."""
import os

import httpx
from dotenv import load_dotenv

from neopulse.analytics.telegram_ui import COMMANDS  # một nguồn cho danh sách lệnh của bot

DESCRIPTION = (
    "NeoPulse Radar · trợ lý theo dõi thị trường chứng khoán Việt Nam.\n"
    "📊 /thitruong nhịp thị trường · 🚨 /canhbao cảnh báo trong phiên · 🏢 /ma HPG thẻ một mã.\n"
    "⭐ /theodoi mã theo dõi · ⚙️ /caidat bật/tắt từng loại tin · ℹ️ /trangthai · ❓ /huongdan · ⏹ /dung hủy đăng ký.\n"
    "Số liệu lấy từ website NeoPulse. Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."
)
SHORT = "📊 Nhịp thị trường · 🚨 Cảnh báo · 🏢 Thẻ mã · ⭐ Theo dõi. Số liệu khớp website NeoPulse. Không phải lời khuyên đầu tư."


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
