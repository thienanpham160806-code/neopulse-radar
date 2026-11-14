# Bảo mật

- Không commit `.env`, `data/`, `raw_dump/`, `out/`.
- Token NEO API chỉ nằm trong bộ nhớ tiến trình; không ghi ra đĩa, không in ra log.
- Mã nguồn không chứa và không gọi endpoint đặt/sửa/hủy lệnh (`NeoClient.get` chặn `/trading/orders`).
- Nếu nghi lộ thông tin đăng nhập: đổi mật khẩu VPBankS ngay, thu hồi token Telegram/LLM, xóa khỏi lịch sử git, báo giảng viên.
