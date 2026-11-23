## Cập nhật trang thị trường — 23/11/2026

Theo kế hoạch được chủ dự án duyệt: phạm vi/độ mới → đọc nhanh → năm nhóm bằng chứng → cảnh báo → biểu đồ/ngành → kiểm chứng. Giữ tab chi tiết và bộ lọc khi tra cứu. Từ điển dùng chung có tìm không dấu/viết tắt, ví dụ, công thức, giới hạn và vai trò trong đồ án; desktop dùng ngăn bên phải, mobile toàn màn hình. Dark mode dùng cam #FF9F43, chữ tối trên nền cam. Công thức/trọng số tài chính giữ nguyên. Xem [nguồn tham khảo và quyết định](../docs/market-design-references.md). Thứ tự ưu tiên cũ bên dưới chỉ là lịch sử; thay đổi mới này được ưu tiên.

## Cập nhật theo yêu cầu người dùng — 19/11/2026

Ưu tiên bản thiết kế mới: giảm đường kẻ đậm; phân lớp bằng khoảng cách, nền mềm và hero có màu. Light xanh băng hà + navy + vàng chanh; dark xanh rừng + kem + cam. Giá tăng/giảm giữ màu chứng khoán riêng. Header và breadcrumb dùng chung cho Trang chủ > Nhịp thị trường > Tab, và Trang chủ > Doanh nghiệp > Mã. Trang chủ tại /trang-chu; giữ / cho thị trường để bảo toàn URL cũ. TradingView Lightweight Charts hiển thị dữ liệu NeoPulse và ghi nguồn rõ; iframe HOSE không được phép cung cấp MWG nên đã loại khỏi bản cuối.

Bối cảnh thiết kế trước đây ở dưới được giữ làm lịch sử.

# Bối cảnh thiết kế — NeoPulse Radar (web)

Viết cho: người làm giao diện (người hoặc agent) trước khi chỉnh bất kỳ màn hình nào. Nguồn: yêu cầu của tác giả ngày 19/11/2026. Mục ghi "giả định" là chỗ tác giả chưa nói rõ.

## Sản phẩm

Radar nhịp thị trường chứng khoán Việt Nam trong phiên. Trả lời nhanh ba câu: **thị trường đang khỏe hay yếu, vì sao, có gì bất thường**. Mọi con số do Python tính (`build_view`); web chỉ hiển thị.

## Người dùng và bối cảnh

| Ai | Ở đâu, khi nào | Cần gì |
|---|---|---|
| Nhà đầu tư cá nhân | Điện thoại, trong giờ giao dịch, liếc nhanh giữa việc khác | Trạng thái chung, cảnh báo, không phải đọc bảng dài |
| Sinh viên tài chính | Laptop, học/ôn | Hiểu vì sao điểm nhịp như vậy, xem phương pháp |
| Giảng viên chấm đồ án | Laptop/máy chiếu khi demo | Thấy rõ nguồn dữ liệu, trạng thái thật/mô phỏng, giới hạn |

## Thứ tự ưu tiên thông tin (bắt buộc)

1. Trạng thái dữ liệu: trực tiếp / snapshot / MÔ PHỎNG / lỗi
2. Điểm nhịp và chỉ số
3. Cảnh báo
4. Độ rộng, ngành, khối ngoại, phái sinh
5. Chi tiết, phương pháp, giới hạn

## Quy ước màu bảng giá Việt Nam (bắt buộc)

Xanh lá = tăng · đỏ = giảm · vàng = tham chiếu/đứng giá · tím = trần · xanh lơ = sàn. **Không dùng đỏ/xanh cho ý nghĩa khác** (lỗi hệ thống dùng chữ và biểu tượng, không dùng đỏ trơn như giá giảm). Không phụ thuộc màu: luôn có ▲ ▼ ■ (▲▲ trần, ▼▼ sàn). Tương phản WCAG AA ở cả nền sáng và tối.

## Số liệu

Font số đều nhau (`tabular-nums`), định dạng Việt Nam (1.234,56), đơn vị rõ: điểm, tỷ đồng, %, bps.

## Bắt buộc theo đề

Trạng thái dữ liệu minh bạch (nguồn, giờ, tươi/cũ/lỗi, nhãn MÔ PHỎNG); trạng thái đang tải, rỗng, lỗi; điều hướng hợp lý; dòng "Không phải lời khuyên đầu tư".

## Chuyển động

Số trực tiếp đổi thì nháy nền 300–600 ms, tinh tế; tắt hoàn toàn khi `prefers-reduced-motion`.

## Tham khảo

Bản tin mẫu của giảng viên `daily_briefing_trial.html`: nền sáng slate `#f8fafc`, thẻ trắng viền mảnh, chữ Inter, accent xanh `#2563eb`, pill "live" có chấm xanh, tab dạng viên thuốc. Dùng như mức chuẩn về độ sạch sẽ, không sao chép.

## Ba hướng đề xuất để chọn (preview)

- **A "Terminal"**: nền tối, mật độ cao, nhiều số trên một màn hình, cho người theo dõi liên tục.
- **B "Bản tin"**: nền sáng, kiểu báo tài chính, kể chuyện bằng tiêu đề và chú thích, hợp demo và đọc trên điện thoại.
- **C "Ứng dụng"**: dạng thẻ, ưu tiên điện thoại, ít số mỗi màn hình, chạm để đi sâu.

## Giả định

- Font: Be Vietnam Pro (đã có, tái sử dụng) cho cả ba hướng; không dùng font mono làm "trang phục kỹ thuật".
- Điện thoại mục tiêu 390 px; laptop 1440 px; máy chiếu demo coi như laptop.
