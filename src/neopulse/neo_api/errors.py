"""Ngoại lệ của lớp NEO API và bảng diễn giải mã lỗi thường gặp (tài liệu mục 7.2)."""
from __future__ import annotations


class NeoApiError(Exception):
    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.code:
            parts.append(f"[{self.code}: {ERROR_HINTS.get(self.code, 'xem tài liệu mục 7.2')}]")
        if self.http_status:
            parts.append(f"(HTTP {self.http_status})")
        return " ".join(parts)


class NeoAuthError(NeoApiError):
    """Sai tài khoản/mật khẩu, token hết hạn, chưa được gán quyền hoặc sai IP đăng ký."""


class NeoSafetyError(RuntimeError):
    """Ném ra khi mã nguồn cố gọi một endpoint có thể phát sinh giao dịch thật."""


SUCCESS_CODES = {"NEOINP000000", "IABNOT000"}

ERROR_HINTS = {
    "IABNOT001": "Sai tên đăng nhập hoặc mật khẩu",
    "NEOINP000400": "Yêu cầu không hợp lệ",
    "NEOINP000401": "Chưa xác thực - token thiếu/hết hạn",
    "NEOINP000403": "Bị từ chối - kiểm tra quyền NeoAPI và IP đã đăng ký với VPBankS",
    "NEOINP000404": "Không tìm thấy tài nguyên",
    "NEOINP000500": "Lỗi máy chủ nội bộ",
    "NEOINP000501": "Đã xảy ra lỗi phía máy chủ",
    "NEOINP000111": "Hết thời gian chờ kết nối",
    "NEOINP000003": "Lỗi xác thực dữ liệu đầu vào",
    "NEOINP000004": "Không có bản ghi",
    "NEOINP000021": "Nhập tối đa mười mã cổ phiếu mỗi lần gọi",
    "NEOINP000134": "Không tồn tại mã thị trường",
}

# Mã lỗi nên thử lại (tạm thời) - các mã khác coi là lỗi dứt khoát.
RETRYABLE_CODES = {"NEOINP000500", "NEOINP000501", "NEOINP000111"}
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
