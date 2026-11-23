# Tham khảo và quyết định thiết kế trang thị trường

Đối chiếu ngày 23/11/2026. Các nguồn dưới đây được tham khảo về cách tổ chức thông tin và giải thích chỉ số. Giao diện và nội dung tiếng Việt do dự án tự triển khai; không sao chép mã, hình ảnh hay nhận dữ liệu từ các sản phẩm tham khảo.

| Nguồn chính thức | Điều tham khảo | Cách áp dụng tại NeoPulse |
|---|---|---|
| [OpenBB Workspace — Core Widgets](https://docs.openbb.co/workspace/analysts/widgets/core-widgets) | Chia không gian phân tích theo nhóm và giữ ngữ cảnh khi mở thông tin liên quan | Giữ các tab chi tiết; từ năm nhóm bằng chứng mở đúng bảng tương ứng, kèm câu hỏi mà nhóm đó trả lời. Không thêm trình dựng dashboard hoặc nhà cung cấp mới. |
| [TradingView — Floating data tooltip](https://www.tradingview.com/support/solutions/43000759580-how-to-enable-disable-floating-data-tooltip/) | Cho phép xem chi tiết của số liệu ngay trong ngữ cảnh biểu đồ | Nhãn ⓘ mở đúng mục từ, không buộc rời bộ lọc/phiên đang xem. Đây là phần giải thích chỉ số của NeoPulse, không phải tính năng hay dữ liệu của TradingView. |
| [CME Group — What is Equity Index Basis?](https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/what-is-equity-index-basis) | Basis = giá tương lai − chỉ số cơ sở; còn phụ thuộc chi phí vốn và cổ tức | Bỏ diễn giải “basis dương = kỳ vọng tăng”. Nêu giả định mô hình và giới hạn khi đọc dấu basis. |
| [W3C — H102: HTML dialog](https://www.w3.org/WAI/WCAG22/Techniques/html/H102) | Modal bằng phần tử gốc: chuyển/giữ focus, nền inert, Escape và trả focus | Ngăn tra cứu dùng `dialog.showModal()`; toàn màn hình trên điện thoại, ngăn bên phải trên máy tính. |

## Mạch thông tin và hợp đồng nội dung

1. **Phạm vi và độ mới:** chỉ số đang chọn; số mã có dữ liệu sổ lệnh/khối ngoại; mốc bản đầy đủ. Cập nhật nhanh và bảng snapshot được phân biệt.
2. **Đọc nhanh:** biến động giá và số mã tăng/giảm thực có, hai thành phần tác động lớn, phần đang thiếu. Điểm tổng hợp không tự chứng minh độ lan tỏa hay dòng tiền.
3. **Năm nhóm bằng chứng:** câu hỏi, thành phần chuẩn hóa và đơn vị, trọng số gốc, cách đọc, đường mở chi tiết. Phần thiếu vẫn trống.
4. **Cảnh báo:** thời điểm/mã/quy tắc, thông báo gốc, giá trị và ngưỡng nếu payload có. Không suy mức nền từ câu chữ của bản tin live. Số lượt khác số mã; danh sách đã tải khác tổng phiên.
5. **Biểu đồ và ngành:** đặt sự kiện vào chuỗi giá, giải thích MA/EMA và nguồn dữ liệu ngày/nội phiên khác nhau.
6. **Kiểm chứng:** số phiên, số mã, số ảnh chụp, gián đoạn, mốc tính; giải thích trong/ngoài mẫu và giới hạn sau phí. Mốc năm phiên là tối thiểu thu thập, không phải chứng nhận dự báo.

Từ điển dùng chung tại `web/src/lib/glossary.ts`: định nghĩa, cách đọc, ví dụ được gắn nhãn minh họa, vai trò trong đồ án, công thức, giới hạn, nơi sử dụng và nguồn phương pháp. Nhãn bảng và tìm kiếm dùng cùng tập mục từ.

## Các quyết định giữ phạm vi

- Tất cả công thức tài chính vẫn thuộc Python và không đổi trọng số. Web định dạng số, chọn câu giải thích và điều hướng.
- Chưa thêm so sánh “cùng giờ phiên trước” mới: payload chưa công bố đủ giá trị nền và độ phủ để trình bày một phép so sánh mới có thể kiểm tra. Thành phần thanh khoản hiện hữu vẫn giữ yêu cầu tối thiểu ba phiên trước; không lấy lịch sử OHLC thay sổ lệnh.
- Không thêm AI sinh giải thích khi mở trang, dashboard tùy biến, dịch vụ dữ liệu, tài khoản hay hệ thống khuyến nghị giao dịch.
- Cam dark mode chọn `#FF9F43`, chữ trên nền cam dùng `#0C241E`. Giữ màu tăng/giảm/tham chiếu và bảng màu light mode.
- [Phương pháp tài chính của dự án](methodology.md) và mã Python là nguồn xác định công thức thực thi. Tham khảo thiết kế không phải bằng chứng kiểm định tài chính hoặc sự bảo trợ của các sản phẩm trên.
