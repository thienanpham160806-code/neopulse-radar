# Số liệu báo cáo NeoPulse Radar

Sinh bằng `neopulse report-data --source ssi` lúc 15:10 27/11/2026 từ CSDL SQLite (chỉ đọc). Không chỉnh tay; chạy lại lệnh sau mỗi phiên mới. CSV chi tiết cùng thư mục.

## Tổng quan

- Nguồn: `ssi` (SSI FastConnect, dữ liệu thật)
- Số phiên: 6 (3 phiên đủ, 3 phiên thiếu)
- Khoảng thời gian: 2026-11-19 09:58 đến 2026-11-27 14:47
- Tổng bản ghi giá: 1.766.339
- Tổng tick chỉ số: 38.016

## Từng phiên

Phiên **đủ** khi ít nhất 90% số mã đạt tiêu chí ghi trọn của `finance/rvol.py` (`complete_history`: có khối lượng khớp trong 5 phút sau 09:15, tới 14:44, không mất quá 5 phút giao dịch liên tiếp trong giờ khớp lệnh). Khoảng trống tính theo phút giao dịch (bỏ nghỉ trưa), kể cả từ 09:00 tới tin đầu tiên và từ tin cuối tới 15:00.

| phiên | bắt đầu | kết thúc | bản ghi giá | tick chỉ số | số mã | mã ghi trọn | khoảng trống lớn nhất (phút) | khoảng trống từ | lượt chạy bộ ghi | lần nối lại | tin lặp | tin bị loại | tin lạ | ghi chú chất lượng | đủ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-19 | 09:58:38 | 14:50:18 | 57258 | 1869 | 30 | 0 | 91 | 11:30 | 4 | 19 | 29262 | 0 | 0 | 1 | thiếu |
| 2026-11-20 | 09:31:28 | 14:48:27 | 254064 | 5449 | 30 | 0 | 56 | 13:04 | 2 | 121 | 341255 | 0 | 0 | 0 | thiếu |
| 2026-11-23 | 10:16:03 | 14:57:12 | 275762 | 6243 | 30 | 0 | 76 | 09:00 | 1 | 24 | 755519 | 0 | 0 | 0 | thiếu |
| 2026-11-25 | 08:58:16 | 14:56:19 | 378988 | 8733 | 30 | 30 | 4 | 14:46 | 4 | 39 | 820295 | 0 | 0 | 0 | đủ |
| 2026-11-26 | 08:55:18 | 14:50:11 | 484447 | 8184 | 30 | 30 | 10 | 14:50 | 1 | 53 | 1069004 | 0 | 0 | 0 | đủ |
| 2026-11-27 | 09:00:04 | 14:47:28 | 315820 | 7538 | 30 | 29 | 13 | 14:47 | 2 | 60 | 856905 | 0 | 0 | 0 | đủ |

## Cảnh báo

Theo mức:

| phiên | CAO | THẤP | TRUNG BÌNH | tổng |
|---|---|---|---|---|
| 2026-11-19 | 7 | 44 | 45 | 96 |
| 2026-11-20 | 79 | 107 | 218 | 404 |
| 2026-11-23 | 53 | 67 | 250 | 370 |
| 2026-11-25 | 80 | 118 | 287 | 485 |
| 2026-11-26 | 101 | 145 | 398 | 644 |
| 2026-11-27 | 99 | 120 | 301 | 520 |

Theo quy tắc:

| phiên | book_pressure | foreign_flow | near_limit | price_jump | spread_blowout | volume_spike |
|---|---|---|---|---|---|---|
| 2026-11-19 | 44 | 7 | 0 | 2 | 15 | 28 |
| 2026-11-20 | 113 | 76 | 0 | 17 | 68 | 130 |
| 2026-11-23 | 67 | 102 | 0 | 19 | 69 | 113 |
| 2026-11-25 | 120 | 95 | 0 | 20 | 112 | 138 |
| 2026-11-26 | 148 | 135 | 3 | 43 | 119 | 196 |
| 2026-11-27 | 122 | 106 | 2 | 25 | 122 | 143 |

Nhận xét tự động (chỉ đề xuất, chưa đổi ngưỡng):

- Không quy tắc nào lệch hẳn (không quy tắc nào chiếm >= 50% hoặc bằng 0).

## Kiểm chứng tín hiệu (`validate`)

### Mọi phiên

Trong mẫu: 4 phiên (2026-11-19, 2026-11-20, 2026-11-23, 2026-11-25); ngoài mẫu: 2 phiên (2026-11-26, 2026-11-27).

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | tỷ lệ đúng chiều | Q5-Q1 (bps) | số thanh |
|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1762 | 23.2178 | 0.5872 | 5.7506 | 654 |
| obi3 | 1 | ngoài mẫu | 0.1747 | 20.2613 | 0.5763 | 6.1092 | 506 |
| obi3 | 5 | trong mẫu | 0.2056 | 26.4693 | 0.5596 | 13.1178 | 645 |
| obi3 | 5 | ngoài mẫu | 0.2075 | 23.2712 | 0.5564 | 14.3381 | 501 |
| obi_w | 1 | trong mẫu | 0.2396 | 32.6079 | 0.6351 | 7.6113 | 654 |
| obi_w | 1 | ngoài mẫu | 0.2204 | 26.5664 | 0.6081 | 7.8233 | 506 |
| obi_w | 5 | trong mẫu | 0.2517 | 34.1062 | 0.5876 | 14.6779 | 645 |
| obi_w | 5 | ngoài mẫu | 0.2428 | 27.4543 | 0.5753 | 15.6602 | 501 |
| obi1 | 1 | trong mẫu | 0.3205 | 45.9427 | 0.7109 | 9.7741 | 654 |
| obi1 | 1 | ngoài mẫu | 0.2911 | 36.0929 | 0.6749 | 9.7667 | 506 |
| obi1 | 5 | trong mẫu | 0.2825 | 40.1302 | 0.6221 | 15.1146 | 645 |
| obi1 | 5 | ngoài mẫu | 0.2600 | 30.8614 | 0.6042 | 16.3453 | 501 |
| micro_dev_bps | 1 | trong mẫu | 0.2860 | 41.8240 | 0.7109 | 9.1297 | 654 |
| micro_dev_bps | 1 | ngoài mẫu | 0.2659 | 33.2393 | 0.6749 | 9.2769 | 506 |
| micro_dev_bps | 5 | trong mẫu | 0.2620 | 36.2275 | 0.6221 | 14.3449 | 645 |
| micro_dev_bps | 5 | ngoài mẫu | 0.2504 | 30.0360 | 0.6042 | 15.2993 | 501 |

Độ tin cậy: đủ số phiên tối thiểu. t-stat bị thổi phồng do các thanh liền kề tự tương quan; ít phiên ngoài mẫu nên chưa đủ để kết luận tín hiệu có giá trị dự báo.

### Chỉ các phiên đủ

Trong mẫu: 2 phiên (2026-11-25, 2026-11-26); ngoài mẫu: 1 phiên (2026-11-27).

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | tỷ lệ đúng chiều | Q5-Q1 (bps) | số thanh |
|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1711 | 19.8674 | 0.5691 | 6.0845 | 506 |
| obi3 | 1 | ngoài mẫu | 0.1705 | 14.0015 | 0.6033 | 5.6006 | 255 |
| obi3 | 5 | trong mẫu | 0.2048 | 22.7975 | 0.5312 | 14.4984 | 502 |
| obi3 | 5 | ngoài mẫu | 0.2057 | 16.1558 | 0.6023 | 13.5217 | 252 |
| obi_w | 1 | trong mẫu | 0.2280 | 27.5161 | 0.6069 | 7.8353 | 506 |
| obi_w | 1 | ngoài mẫu | 0.2188 | 18.9993 | 0.6389 | 7.0893 | 255 |
| obi_w | 5 | trong mẫu | 0.2512 | 28.9117 | 0.5561 | 16.1536 | 502 |
| obi_w | 5 | ngoài mẫu | 0.2464 | 19.5704 | 0.6222 | 15.0817 | 252 |
| obi1 | 1 | trong mẫu | 0.3085 | 38.2335 | 0.6818 | 9.7476 | 506 |
| obi1 | 1 | ngoài mẫu | 0.2999 | 27.3398 | 0.7015 | 9.7619 | 255 |
| obi1 | 5 | trong mẫu | 0.2774 | 34.2852 | 0.6020 | 15.7908 | 502 |
| obi1 | 5 | ngoài mẫu | 0.2832 | 24.6428 | 0.6358 | 18.2183 | 252 |
| micro_dev_bps | 1 | trong mẫu | 0.2794 | 35.2832 | 0.6818 | 9.0308 | 506 |
| micro_dev_bps | 1 | ngoài mẫu | 0.2686 | 24.7998 | 0.7015 | 9.2258 | 255 |
| micro_dev_bps | 5 | trong mẫu | 0.2693 | 32.5586 | 0.6020 | 15.4923 | 502 |
| micro_dev_bps | 5 | ngoài mẫu | 0.2682 | 24.3773 | 0.6358 | 16.0315 | 252 |

Độ tin cậy: Mới có 3 phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa. t-stat bị thổi phồng do các thanh liền kề tự tương quan; ít phiên ngoài mẫu nên chưa đủ để kết luận tín hiệu có giá trị dự báo.

## Kiểm thử

- Python (`pytest --co -q`): 279 ca
- Web (`vitest list`): 100 ca
