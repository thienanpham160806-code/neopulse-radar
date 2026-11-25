# Quy ước trình bày bot Telegram

Áp dụng cho mọi tin của bot NeoPulse Radar. Hằng số nằm ở một chỗ: `ICON`, `SEV_ICON`, `RULE_TITLE` trong `src/neopulse/analytics/telegram_ui.py`. Thuật ngữ theo [`docs/thuat_ngu.md`](thuat_ngu.md). Mẫu tin thật: [`docs/bot_samples.md`](bot_samples.md).

## Bộ icon

| Icon | Nghĩa | Icon | Nghĩa |
|---|---|---|---|
| 🟢 | Tăng | 📊 | Thị trường |
| 🔴 | Giảm | 🧭 | Điểm nhịp |
| 🟡 | Tham chiếu / đứng giá | 🏦 | Khối ngoại |
| 🟣 | Trần | 📈 | Phái sinh |
| 🔵 | Sàn | 🏢 | Doanh nghiệp |
| 🚨 | Cảnh báo mức cao | 📰 | Bản tin tin tức |
| ⚠️ | Cảnh báo trung bình | ⚖️ | Tin chính sách |
| ℹ️ | Cảnh báo thấp; trạng thái dữ liệu | 🔗 | Liên kết mở website |
|  |  | 🌏 | Tin quốc tế |

Icon cho menu: ⭐ theo dõi · ⚙️ cài đặt · ❓ hướng dẫn · ⏹ hủy đăng ký. Trong màn cài đặt, ✅/▫️ là trạng thái bật/tắt.

Màu tăng/giảm/trần/sàn khớp quy ước bảng giá Việt Nam trên website. Không dùng icon trang trí ngoài bộ này. Luôn kèm ▲▼ và dấu +/− cạnh màu, để người không phân biệt được màu vẫn đọc đúng.

## Cấu trúc một tin

1. **Tiêu đề:** `[icon] <b>Tiêu đề · MÃ</b> · giờ VN`. Dữ liệu mô phỏng có `[MÔ PHỎNG]` ngay đầu tiêu đề.
2. **Dòng chính:** chuyện gì xảy ra và con số then chốt.
3. **`Căn cứ:`** so với mức nào, ngưỡng nào. Điểm z và "gấp N lần mức thường thấy" được diễn giải bằng lời.
4. **`Bối cảnh:`** chỉ số, độ rộng, khối ngoại, ngành, nếu payload có.
5. **Nút 🔗:** mở đúng trang, mã hoặc tab trên website.
6. **Dòng cuối (in nghiêng):** nguồn · trạng thái dữ liệu · "Không phải lời khuyên đầu tư".

Trường nào payload không có thì bỏ cả dòng đó; không thay bằng 0 hay tự suy ra.

## Trạng thái dữ liệu

Trạng thái được tính tại thời điểm bot trả lời, từ `meta.data_status` và `meta.last_update`:

| Trạng thái | Khi nào |
|---|---|
| Trong phiên | Đang giờ giao dịch và dữ liệu mới trong 3 phút |
| Dữ liệu chậm N phút | Đang giờ giao dịch nhưng quá 3 phút chưa có dữ liệu mới |
| Chưa mở cửa / Nghỉ trưa / Phiên đã kết thúc | Ngoài giờ khớp lệnh |
| Dữ liệu MÔ PHỎNG | `meta.is_simulated` |
| Lỗi dữ liệu | Nguồn báo lỗi |

Bot không dùng chữ "thời gian thực" hay "realtime".

## Số và thời gian

- Số kiểu Việt Nam: 1.234,56; số âm dùng dấu −.
- Đơn vị luôn ghi rõ: điểm, %, tỷ đồng, lần.
- Giờ Việt Nam: `14:05` trong một phiên, `14:05, 25/11/2026` khi cần ngày.

## Kỹ thuật

- Gửi bằng `parse_mode=HTML`; mọi chữ lấy từ nguồn ngoài (tên doanh nghiệp, tiêu đề RSS, nhãn) đều được escape.
- Mỗi tin tối đa 4.096 ký tự. Danh sách dài hiện tối đa 15 dòng (10 dòng với cảnh báo gom theo đợt), phần còn lại ghi "… và N mục khác".
- Tin tức không gửi lẻ: gộp thành bản tin đầu phiên (từ 08:30, tin từ 15:00 ngày làm việc trước) và cuối phiên (từ 15:00, tin 08:30–15:00), chia mục 🏢 Doanh nghiệp, 🌏 Quốc tế, ⚖️ Chính sách, pháp luật; tiêu đề bấm được mở bài gốc.
- Nhiều cảnh báo trong cùng một đợt gửi được gom thành một tin. Mỗi cảnh báo, tin và bản tóm tắt chỉ gửi một lần cho mỗi người (ghi nhận theo mã định danh).
- Văn phong mô tả, không khuyến nghị; không có tín hiệu mua/bán, giá mục tiêu hay xếp hạng.
