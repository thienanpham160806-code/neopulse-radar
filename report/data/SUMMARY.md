# Số liệu báo cáo NeoPulse Radar

Sinh bằng `neopulse report-data --source ssi` lúc 16:01 25/11/2026 từ CSDL SQLite (chỉ đọc). Không chỉnh tay; chạy lại lệnh sau mỗi phiên mới. CSV chi tiết cùng thư mục.

## Tổng quan

- Nguồn: `ssi` (SSI FastConnect, dữ liệu thật)
- Số phiên: 4 (0 phiên đủ, 4 phiên thiếu)
- Khoảng thời gian: 2026-11-19 09:58 đến 2026-11-25 14:56
- Tổng bản ghi giá: 966.072
- Tổng tick chỉ số: 22.294

## Từng phiên

Phiên **đủ** khi ít nhất 90% số mã đạt tiêu chí ghi trọn của `finance/rvol.py` (`complete_history`: có dữ liệu trong 5 phút đầu, tới phút cuối phiên, không mất quá 5 phút giao dịch liên tiếp). Khoảng trống tính theo phút giao dịch (bỏ nghỉ trưa), kể cả từ 09:00 tới tin đầu tiên và từ tin cuối tới 15:00.

| phiên | bắt đầu | kết thúc | bản ghi giá | tick chỉ số | số mã | mã ghi trọn | khoảng trống lớn nhất (phút) | khoảng trống từ | lượt chạy bộ ghi | lần nối lại | tin lặp | tin bị loại | tin lạ | ghi chú chất lượng | mã ghi trọn 09:15-14:45 | đủ | đủ 09:15-14:45 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-19 | 09:58:38 | 14:50:18 | 57258 | 1869 | 30 | 0 | 91 | 11:30 | 4 | 19 | 29262 | 0 | 0 | 1 | 0 | thiếu | thiếu |
| 2026-11-20 | 09:31:28 | 14:48:27 | 254064 | 5449 | 30 | 0 | 56 | 13:04 | 2 | 121 | 341255 | 0 | 0 | 0 | 0 | thiếu | thiếu |
| 2026-11-23 | 10:16:03 | 14:57:12 | 275762 | 6243 | 30 | 0 | 76 | 09:00 | 1 | 24 | 755519 | 0 | 0 | 0 | 0 | thiếu | thiếu |
| 2026-11-25 | 08:58:16 | 14:56:19 | 378988 | 8733 | 30 | 0 | 4 | 14:46 | 4 | 39 | 820295 | 0 | 0 | 0 | 30 | thiếu | đủ |

Cột "đủ 09:15-14:45" chỉ để đối chiếu: cùng điều kiện nhưng trong khung có khối lượng khớp (09:15 hết ATO, 14:45 hết ATC). Tiêu chí của `rvol.py` đòi khối lượng từ 09:05 và tới 14:59, trong khi dữ liệu SSI thật chỉ có khối lượng khớp từ 09:15 và sổ lệnh gần như đứng yên sau 14:45, nên không phiên thật nào đạt; khi đó RVOL luôn dùng đường phân bổ đều theo phút. Đây là đề xuất xem lại, chưa sửa trong nhánh này.

## Cảnh báo

Theo mức:

| phiên | CAO | THẤP | TRUNG BÌNH | tổng |
|---|---|---|---|---|
| 2026-11-19 | 24 | 44 | 28 | 96 |
| 2026-11-20 | 223 | 104 | 107 | 434 |
| 2026-11-23 | 220 | 66 | 114 | 400 |
| 2026-11-25 | 266 | 116 | 133 | 515 |

Theo quy tắc:

| phiên | book_pressure | foreign_flow | price_jump | spread_blowout | volume_spike |
|---|---|---|---|---|---|
| 2026-11-19 | 44 | 7 | 2 | 15 | 28 |
| 2026-11-20 | 113 | 76 | 17 | 68 | 160 |
| 2026-11-23 | 67 | 102 | 19 | 69 | 143 |
| 2026-11-25 | 120 | 95 | 20 | 112 | 168 |

Nhận xét tự động (chỉ đề xuất, chưa đổi ngưỡng):

- `near_limit`: không báo lần nào trong 4 phiên (ít bất thường; xem lại ngưỡng hoặc dữ liệu đầu vào).

## Kiểm chứng tín hiệu (`validate`)

### Mọi phiên

Trong mẫu: 2 phiên (2026-11-19, 2026-11-20); ngoài mẫu: 2 phiên (2026-11-23, 2026-11-25).

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | tỷ lệ đúng chiều | Q5-Q1 (bps) | số thanh |
|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1782 | 12.8800 | 0.5612 | 5.6503 | 220 |
| obi3 | 1 | ngoài mẫu | 0.1751 | 19.3699 | 0.6005 | 5.8015 | 434 |
| obi3 | 5 | trong mẫu | 0.1916 | 14.8357 | 0.5194 | 12.5349 | 215 |
| obi3 | 5 | ngoài mẫu | 0.2126 | 21.9383 | 0.5798 | 13.4102 | 430 |
| obi_w | 1 | trong mẫu | 0.2364 | 17.7631 | 0.6045 | 7.8626 | 220 |
| obi_w | 1 | ngoài mẫu | 0.2412 | 27.4415 | 0.6507 | 7.4840 | 434 |
| obi_w | 5 | trong mẫu | 0.2301 | 18.1344 | 0.5505 | 13.0626 | 215 |
| obi_w | 5 | ngoài mẫu | 0.2624 | 29.0476 | 0.6063 | 15.4842 | 430 |
| obi1 | 1 | trong mẫu | 0.3153 | 26.2855 | 0.7021 | 9.7936 | 220 |
| obi1 | 1 | ngoài mẫu | 0.3232 | 37.6511 | 0.7153 | 9.7642 | 434 |
| obi1 | 5 | trong mẫu | 0.2766 | 21.1190 | 0.6139 | 13.5618 | 215 |
| obi1 | 5 | ngoài mẫu | 0.2855 | 34.4284 | 0.6262 | 15.8901 | 430 |
| micro_dev_bps | 1 | trong mẫu | 0.2806 | 23.7782 | 0.7021 | 9.4894 | 220 |
| micro_dev_bps | 1 | ngoài mẫu | 0.2887 | 34.3852 | 0.7153 | 8.9475 | 434 |
| micro_dev_bps | 5 | trong mẫu | 0.2523 | 19.0445 | 0.6139 | 13.6012 | 215 |
| micro_dev_bps | 5 | ngoài mẫu | 0.2668 | 31.0555 | 0.6262 | 14.7186 | 430 |

Độ tin cậy: Mới có 4 phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa. t-stat bị thổi phồng do các thanh liền kề tự tương quan; ít phiên ngoài mẫu nên chưa đủ để kết luận tín hiệu có giá trị dự báo.

### Chỉ các phiên đủ

Trong mẫu: 0 phiên (chưa có); ngoài mẫu: 0 phiên (chưa có).

chưa có

Độ tin cậy: Không có phiên nào trong phạm vi này. t-stat bị thổi phồng do các thanh liền kề tự tương quan; ít phiên ngoài mẫu nên chưa đủ để kết luận tín hiệu có giá trị dự báo.

### Chỉ các phiên đủ 09:15-14:45 (đối chiếu)

Trong mẫu: 1 phiên (2026-11-25); ngoài mẫu: 0 phiên (chưa có).

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | tỷ lệ đúng chiều | Q5-Q1 (bps) | số thanh |
|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1632 | 13.4618 | 0.5883 | 5.5983 | 255 |
| obi3 | 5 | trong mẫu | 0.2002 | 15.5187 | 0.5506 | 14.0145 | 253 |
| obi_w | 1 | trong mẫu | 0.2339 | 20.3794 | 0.6371 | 7.1690 | 255 |
| obi_w | 5 | trong mẫu | 0.2630 | 21.7156 | 0.5833 | 16.2365 | 253 |
| obi1 | 1 | trong mẫu | 0.3344 | 31.0723 | 0.7170 | 9.7551 | 255 |
| obi1 | 5 | trong mẫu | 0.3177 | 31.4929 | 0.6322 | 17.2203 | 253 |
| micro_dev_bps | 1 | trong mẫu | 0.2952 | 28.1303 | 0.7170 | 8.7734 | 255 |
| micro_dev_bps | 5 | trong mẫu | 0.3057 | 29.2940 | 0.6322 | 16.5483 | 253 |

Độ tin cậy: Chỉ có 1 phiên: chưa thể tách ngoài mẫu - cần thu thập thêm phiên. Mới có 1 phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa. t-stat bị thổi phồng do các thanh liền kề tự tương quan; ít phiên ngoài mẫu nên chưa đủ để kết luận tín hiệu có giá trị dự báo.

## Kiểm thử

- Python (`pytest --co -q`): 272 ca
- Web (`vitest list`): 100 ca
