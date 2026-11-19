# PRODUCT — NeoPulse Radar

Nguồn: yêu cầu của tác giả (19/11/2026), chi tiết ở `web/DESIGN_CONTEXT.md`. Phần ghi "giả định" là suy ra, chưa được tác giả xác nhận.

## Sản phẩm
Radar nhịp thị trường chứng khoán Việt Nam trong phiên: thị trường khỏe hay yếu, vì sao, có gì bất thường. Đồ án cá nhân môn Gói phần mềm ứng dụng cho tài chính 1 (UEL). Không đặt lệnh, không khuyến nghị.

## Người dùng
Nhà đầu tư cá nhân (điện thoại, trong giờ giao dịch), sinh viên tài chính, giảng viên chấm đồ án (laptop/máy chiếu khi demo).

## Bề mặt
Web Next.js (`web/`), chế độ Operate: bảng điều khiển đọc số trong phiên. Dữ liệu: snapshot tĩnh hoặc luồng trực tiếp qua Ably; luôn hiện trạng thái dữ liệu.

## Cam kết bắt buộc
- Màu bảng giá VN: xanh tăng, đỏ giảm, vàng tham chiếu, tím trần, xanh lơ sàn; không dùng đỏ/xanh cho nghĩa khác; luôn kèm ▲▼■.
- Số tabular, định dạng 1.234,56, đơn vị rõ.
- Trạng thái dữ liệu (trực tiếp / snapshot / MÔ PHỎNG / lỗi) luôn ở trên cùng; có tải, rỗng, lỗi.
- "Không phải lời khuyên đầu tư" luôn hiện.
- Nháy nền 300–600 ms khi số đổi; tắt khi giảm chuyển động. WCAG AA.

## Ràng buộc
Mọi chỉ báo do Python tính; web không tính công thức tài chính. Không xuất sổ lệnh thô. Font Be Vietnam Pro (SIL OFL) tự phục vụ (giả định: giữ cho mọi hướng).


## Bổ sung theo yêu cầu — 19/11/2026
- Đăng ký Telegram hoàn toàn tự nguyện, không bắt buộc dùng website. Người dùng chọn nhóm tin, mã theo dõi và hủy/xóa từ bot. Worker cloud theo đợt khoảng 15 phút, không phụ thuộc laptop; nguồn cảnh báo vẫn phụ thuộc dữ liệu thị trường được cập nhật.
- Có lịch sử đóng cửa ngày, chọn khung thời gian, bật/tắt MA/EMA và tham chiếu. Mọi chỉ báo vẫn tính tại Python, không dựng nến hoặc phiên phút giả từ dữ liệu đóng cửa.
- Tin doanh nghiệp/chính sách kèm nguồn và ngày đăng; không tự suy ra nội dung pháp lý hoặc hiệu lực từ tiêu đề. Dữ liệu đăng ký phải được mã hóa trước khi lưu cloud.
