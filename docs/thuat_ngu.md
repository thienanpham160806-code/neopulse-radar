# Thuật ngữ NeoPulse Radar

Mỗi khái niệm có **một** cách gọi duy nhất trên giao diện, bản tin, cảnh báo và tài liệu. Cột "Tên trên giao diện" là cách viết bắt buộc. Cột "Tiếng Anh / viết tắt" chỉ dùng trong ngoặc sau lần xuất hiện đầu tiên trên mỗi màn hình, hoặc trong công thức. Lần đầu xuất hiện trên mỗi màn hình, thuật ngữ có tooltip định nghĩa (biểu tượng ⓘ, nội dung lấy từ `web/src/lib/glossary.ts`).

## Chỉ báo thị trường

| Tên trên giao diện | Tiếng Anh / viết tắt | Định nghĩa |
|---|---|---|
| Điểm nhịp thị trường | Market Pulse Score | Điểm 0–100 tổng hợp năm thành phần: độ rộng, động lượng chỉ số, mất cân bằng sổ lệnh, khối ngoại và thanh khoản; 50 là trung tính. |
| Độ rộng thị trường | Breadth, A/D | Chênh lệch giữa số mã tăng và số mã giảm, chia cho tổng hai nhóm, trong khoảng −1 đến +1. |
| Động lượng chỉ số | Momentum | Mức thay đổi của chỉ số so với độ dao động thường thấy của chính chỉ số đó. |
| Mất cân bằng sổ lệnh | OBI₃ (Order Book Imbalance) | Chênh lệch khối lượng chờ mua và chờ bán trên 3 mức giá tốt nhất, chia cho tổng, trong khoảng −1 đến +1. |
| Mất cân bằng tại mức giá tốt nhất | OBI₁ | Như mất cân bằng sổ lệnh nhưng chỉ dùng mức giá tốt nhất của mỗi phía; chỉ dùng trong phần kiểm chứng. |
| Giá vi mô | Microprice | Giá giữa có trọng số theo khối lượng chờ ở mức giá tốt nhất của hai phía. |
| Giá giữa | Mid price | Trung bình cộng giá mua tốt nhất và giá bán tốt nhất. |
| Độ chênh giá mua-bán | Spread, bps | Khoảng cách giữa giá bán tốt nhất và giá mua tốt nhất, tính theo phần vạn (bps) của giá giữa. |
| Độ sâu 3 mức | Depth | Tổng giá trị lệnh chờ trên 3 mức giá tốt nhất của mỗi phía. |
| Trượt giá | Slippage, bps | Chênh lệch giữa giá khớp bình quân của một lệnh giả định và giá giữa, tính theo bps. |
| Điểm thanh khoản | Liquidity score | Điểm tổng hợp từ giá trị khớp, độ sâu và trượt giá; chỉ so sánh tương đối trong rổ. |
| Khối lượng tương đối | RVOL | Khối lượng khớp chia cho mức thường thấy của chính mã đó ở cùng khung giờ. |
| Giá trị khớp | Matched value | Tổng giá trị giao dịch đã khớp trong phiên, tính bằng đồng. |
| Khối lượng khớp | Matched volume | Tổng số cổ phiếu đã khớp trong phiên. |

## Khối ngoại

| Tên trên giao diện | Tiếng Anh / viết tắt | Định nghĩa |
|---|---|---|
| Khối ngoại mua ròng / bán ròng | Foreign net buy / net sell | Giá trị mua trừ giá trị bán của nhà đầu tư nước ngoài; dương là mua ròng, âm là bán ròng. |
| Tỷ lệ ròng trên tổng | Net/gross | Giá trị ròng chia cho tổng giá trị mua và bán của khối ngoại, trong khoảng −1 đến +1. |
| Tỷ trọng khối ngoại | Foreign participation | Tổng giá trị giao dịch của khối ngoại chia cho giá trị khớp của mã. |
| Room khối ngoại đã dùng | Foreign room used | Tỷ lệ sở hữu nước ngoài hiện tại so với giới hạn sở hữu tối đa. |

## Phái sinh

| Tên trên giao diện | Tiếng Anh / viết tắt | Định nghĩa |
|---|---|---|
| Hợp đồng tương lai VN30 | VN30F; viết tắt HĐTL chỉ dùng trong tiêu đề cột hẹp | Hợp đồng tương lai chỉ số VN30 niêm yết trên HNX. |
| Chênh lệch cơ sở | Basis (F − S) | Giá hợp đồng tương lai trừ giá trị chỉ số cơ sở, tính bằng điểm. |
| Giá trị hợp lý | Fair value | Giá lý thuyết theo mô hình chi phí lưu giữ, với lãi suất và cổ tức giả định. |
| Lệch so với giá trị hợp lý | Mispricing | Giá hợp đồng tương lai trừ giá trị hợp lý, tính bằng điểm. |
| Ngày tới đáo hạn | Days to maturity | Số ngày lịch còn lại đến ngày đáo hạn hợp đồng. |

## Cảnh báo và kiểm chứng

| Tên trên giao diện | Tiếng Anh / viết tắt | Định nghĩa |
|---|---|---|
| Bất thường | Anomaly | Quan sát lệch khỏi mức thường thấy của chính mã đó trong phiên, vượt ngưỡng của quy tắc. |
| Điểm z bền vững | Robust z-score | 0,6745 × (giá trị − trung vị) / MAD, với MAD là độ lệch tuyệt đối trung vị của 60 thanh trước; ít nhạy với giá trị ngoại lai. |
| Mức cảnh báo: Cao, Trung bình, Thấp | Severity | Mức ưu tiên của cảnh báo theo độ lớn của độ lệch; khóa dữ liệu vẫn là `CAO`, `TRUNG BÌNH`, `THẤP`. |
| Sát trần/sàn | Near limit | Giá khớp đã đi từ 90% khoảng cách giữa giá tham chiếu và giá trần (hoặc giá sàn) trở lên. |
| Hệ số thông tin | IC (Information Coefficient) | Tương quan hạng Spearman giữa tín hiệu và lợi suất kế tiếp, tính cho từng thanh rồi lấy trung bình. |
| Trong mẫu / ngoài mẫu | In-sample / out-of-sample | Hai nhóm phiên tách theo thứ tự thời gian: nhóm đầu để quan sát, nhóm sau để kiểm tra lại. |
| Thanh 1 phút | Bar | Khoảng tổng hợp dữ liệu một phút; mọi chỉ báo nội phiên tính trên thanh. |
| Xếp hạng đa yếu tố | Multi-factor ranking | Thứ tự các mã theo tổng có trọng số của điểm z mặt cắt ngang ở năm yếu tố. |

## Dữ liệu và vận hành

| Tên trên giao diện | Tiếng Anh / viết tắt | Định nghĩa |
|---|---|---|
| Rổ theo dõi | Universe | Danh sách mã được ghi sổ lệnh và khối ngoại; mặc định là rổ VN30. |
| Bộ ghi dữ liệu | Recorder | Tiến trình nhận dữ liệu trực tiếp từ nguồn và lưu vào SQLite. |
| Dữ liệu trực tiếp | Live | Số liệu tổng hợp nhận qua kênh trực tiếp trong phiên, độ trễ vài giây. |
| Bản dữ liệu | Snapshot | Bộ số liệu cố định tại một thời điểm, dùng khi không có kênh trực tiếp. |
| Ảnh chụp sổ lệnh | Quote snapshot | Một bản ghi giá và 3 mức sổ lệnh của một mã tại thời điểm nhận. |
| Phiên định kỳ | ATO / ATC | Đợt khớp lệnh mở cửa và đóng cửa; giá mức 1 khi đó không phải giá giới hạn. |
| Mô phỏng | Simulation | Dữ liệu do bộ giả lập sinh ra để kiểm thử; luôn gắn nhãn MÔ PHỎNG. |

## Quy ước trình bày

- Số theo định dạng Việt Nam: dấu chấm phân cách hàng nghìn, dấu phẩy thập phân (1.234,56).
- Đơn vị luôn ghi rõ: điểm, %, bps, đồng, tỷ đồng, cổ phiếu, lần.
- Thời điểm theo giờ Việt Nam, dạng `14:05:32, 19/11/2026`; khi chỉ cần giờ thì `14:05`.
- Mã chứng khoán viết hoa (HPG, VN30F2612); tên chỉ số viết đúng tên chính thức (VN-Index, VN30).
- Dòng miễn trừ trách nhiệm thống nhất: **"Công cụ phân tích học thuật. Không phải lời khuyên đầu tư."**
