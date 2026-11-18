"""Nguồn dữ liệu SSI FastConnect (API v3, https://developers.ssi.com.vn).

Chỉ dùng phần DỮ LIỆU THỊ TRƯỜNG: không có hàm nào gọi đặt/sửa/hủy lệnh, và client chặn cứng các
đường dẫn /trading, /account. Khung tin SSI được `adapter.SsiAdapter` đổi về cùng lược đồ thô với
NEO API nên toàn bộ phần chuẩn hóa -> lưu trữ -> chỉ báo -> cảnh báo dùng lại nguyên vẹn.
"""
