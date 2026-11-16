# Checklist lần chạy thật đầu tiên

Lớp kết nối được viết theo tài liệu và kiểm thử bằng máy chủ giả. Lần đầu có tài khoản, đi theo thứ tự này và ghi kết quả vào báo cáo (mục 7 — Kiểm thử).

## Trước phiên

- [ ] `.env` có `NEOPULSE_MODE=live`, `NEO_USERNAME`, `NEO_PASSWORD`; `git status` **không** liệt kê `.env`.
- [ ] Máy đang dùng đúng IP đã đăng ký với VPBankS (lỗi `NEOINP000403` nghĩa là sai IP/chưa có quyền).
- [ ] `neopulse check` → in trạng thái phiên và số mã của rổ.
- [ ] Nếu muốn giữ dữ liệu mô phỏng riêng: đặt `NEOPULSE_DB_PATH=data/neopulse_live.sqlite`.

## Trong phiên

- [ ] `neopulse --log-level INFO record` → thấy dòng `WebSocket đã xác thực`.
- [ ] Sau 1–2 phút, dòng thống kê có `tin` tăng dần và `lạ 0`.
  - `lạ > 0` → mở `raw_dump/unknown_messages.jsonl`, xem cấu trúc thật, chỉnh `classify_message` trong `neo_api/ws.py` và thêm ca kiểm thử vào `tests/test_ws.py`.
  - Xác thực thất bại → thử đổi `NEO_WS_MARKET_URL` sang `wss://…`.
  - WebSocket không dùng được → `neopulse poll --interval 15` (vẫn đủ 2 nhóm API theo yêu cầu tối thiểu).
- [ ] Dòng `REST đối chiếu N lệch 0` — nếu `lệch > 0` thường xuyên, xem `quality_log` loại `ws_rest_mismatch`.
- [ ] Mở dashboard → nguồn *NEO API* → trạng thái 🟢 và giờ cập nhật chạy.
- [ ] So 3–5 mã bất kỳ với bảng giá NEO Invest tại cùng thời điểm: giá khớp, 3 mức mua/bán, tổng khối lượng. Chụp màn hình hai bên làm bằng chứng đối chiếu.
- [ ] Thử lỗi có chủ đích và chụp lại: (a) tắt mạng 30 giây → log `Kết nối lại sau …`, dashboard chuyển 🟠; (b) sửa sai mật khẩu → `neopulse check` báo `IABNOT001`; (c) dừng bộ ghi → dashboard báo dữ liệu cũ.

## Sau phiên

- [ ] `neopulse briefing --source neo` và `neopulse alerts --source neo`.
- [ ] Kiểm tra `HĐTL`: tab *Phái sinh* có dữ liệu; nếu không, xem `quality_log` loại `futures_bootstrap_failed`.
- [ ] Sau **≥ 5 phiên** (ưu tiên 10): `neopulse validate --source neo --out report/ic_table.csv` → đưa bảng IC ngoài mẫu vào báo cáo, kể cả khi kết quả yếu hoặc không có ý nghĩa.
- [ ] Sao lưu `data/neopulse_live.sqlite` (không commit).

## Trước khi nộp

- [ ] `pytest` và `ruff check src tests` đều sạch.
- [ ] `git grep -nE "eyJ[A-Za-z0-9_-]{10,}|116C[0-9]{6}"` không ra kết quả nào.
- [ ] Ảnh chụp/video không lộ số tài khoản, token, IP.
- [ ] Cập nhật mục *Giới hạn đã biết* trong README: bỏ dòng "chưa chạy với NEO API thật" **chỉ khi** đã chạy thật, và ghi số phiên đã thu.
