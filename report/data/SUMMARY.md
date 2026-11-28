# Số liệu báo cáo NeoPulse Radar

Sinh bằng `neopulse report-data --source ssi` lúc 12:15 28/11/2026 từ CSDL SQLite (chỉ đọc). Không chỉnh tay; chạy lại lệnh sau mỗi phiên mới. CSV chi tiết cùng thư mục.

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
| 2026-11-19 | 8 | 35 | 47 | 90 |
| 2026-11-20 | 43 | 66 | 174 | 283 |
| 2026-11-23 | 21 | 36 | 160 | 217 |
| 2026-11-25 | 36 | 85 | 176 | 297 |
| 2026-11-26 | 57 | 95 | 219 | 371 |
| 2026-11-27 | 43 | 70 | 190 | 303 |

Theo quy tắc:

| phiên | book_pressure | foreign_flow | near_limit | price_jump | spread_blowout | volume_spike |
|---|---|---|---|---|---|---|
| 2026-11-19 | 35 | 15 | 0 | 2 | 24 | 14 |
| 2026-11-20 | 68 | 56 | 0 | 22 | 52 | 85 |
| 2026-11-23 | 38 | 65 | 0 | 19 | 37 | 58 |
| 2026-11-25 | 86 | 57 | 0 | 27 | 53 | 74 |
| 2026-11-26 | 97 | 42 | 3 | 47 | 54 | 128 |
| 2026-11-27 | 71 | 52 | 2 | 33 | 52 | 93 |

Nhận xét tự động (chỉ đề xuất, chưa đổi ngưỡng):

- Không quy tắc nào lệch hẳn (không quy tắc nào chiếm >= 50% hoặc bằng 0).

## Kiểm chứng tín hiệu (`validate`)

Cột: `t` coi các thanh độc lập (bị thổi phồng); `t NW` Newey-West, độ trễ L ghi ở cột `L`; `t phiên` lấy IC trung bình từng phiên làm một quan sát (n = số phiên). `Q5-Q1` là chênh lợi suất giá giữa, chưa trừ chi phí. `Q5-Q1 ròng` mua Q5 ở giá bán và bán ở giá mua sau h thanh, bán khống Q1 ở giá mua và mua lại ở giá bán, trừ phí GIẢ ĐỊNH 0,15%/chiều; `Q5 ròng` chỉ chân mua (thị trường cơ sở không cho bán khống trong ngày). Đơn vị bps.

### Mọi phiên

Trong mẫu: 4 phiên (2026-11-19, 2026-11-20, 2026-11-23, 2026-11-25); ngoài mẫu: 2 phiên (2026-11-26, 2026-11-27). Cách chia cố định trên mọi phiên trước khi lọc phiên đủ.

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | t NW | L | t phiên | số phiên | tỷ lệ đúng chiều | Q5-Q1 | Q5-Q1 ròng | Q5 ròng | số thanh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1762 | 23.2178 | 25.7761 | 6 | 17.1939 | 4 | 0.5872 | 5.7506 | -104.2387 | -53.3566 | 654 |
| obi3 | 1 | ngoài mẫu | 0.1747 | 20.2613 | 20.4896 | 5 | chưa có | 2 | 0.5763 | 6.1092 | -106.3873 | -53.9426 | 506 |
| obi3 | 5 | trong mẫu | 0.2056 | 26.4693 | 15.6343 | 6 | 7.9107 | 4 | 0.5596 | 13.1178 | -96.6147 | -48.9975 | 645 |
| obi3 | 5 | ngoài mẫu | 0.2075 | 23.2712 | 13.9426 | 5 | chưa có | 2 | 0.5564 | 14.3381 | -97.7615 | -49.0510 | 501 |
| obi_w | 1 | trong mẫu | 0.2396 | 32.6079 | 32.8908 | 6 | 30.9235 | 4 | 0.6351 | 7.6113 | -102.4680 | -52.3609 | 654 |
| obi_w | 1 | ngoài mẫu | 0.2204 | 26.5664 | 26.7139 | 5 | chưa có | 2 | 0.6081 | 7.8233 | -104.4993 | -53.2012 | 506 |
| obi_w | 5 | trong mẫu | 0.2517 | 34.1062 | 20.9826 | 6 | 12.3087 | 4 | 0.5876 | 14.6779 | -95.1191 | -47.9570 | 645 |
| obi_w | 5 | ngoài mẫu | 0.2428 | 27.4543 | 16.8530 | 5 | chưa có | 2 | 0.5753 | 15.6602 | -96.2590 | -48.4418 | 501 |
| obi1 | 1 | trong mẫu | 0.3205 | 45.9427 | 37.0394 | 6 | 36.7802 | 4 | 0.7109 | 9.7741 | -100.1129 | -50.9190 | 654 |
| obi1 | 1 | ngoài mẫu | 0.2911 | 36.0929 | 30.5736 | 5 | chưa có | 2 | 0.6749 | 9.7667 | -102.8871 | -52.5610 | 506 |
| obi1 | 5 | trong mẫu | 0.2825 | 40.1302 | 25.6871 | 6 | 17.2342 | 4 | 0.6221 | 15.1146 | -94.6379 | -47.6014 | 645 |
| obi1 | 5 | ngoài mẫu | 0.2600 | 30.8614 | 21.1072 | 5 | chưa có | 2 | 0.6042 | 16.3453 | -96.1310 | -48.7733 | 501 |
| micro_dev_bps | 1 | trong mẫu | 0.2860 | 41.8240 | 33.8478 | 6 | 48.8342 | 4 | 0.7109 | 9.1297 | -114.5500 | -61.4453 | 654 |
| micro_dev_bps | 1 | ngoài mẫu | 0.2659 | 33.2393 | 29.8151 | 5 | chưa có | 2 | 0.6749 | 9.2769 | -118.9730 | -62.6802 | 506 |
| micro_dev_bps | 5 | trong mẫu | 0.2620 | 36.2275 | 22.8377 | 6 | 13.0660 | 4 | 0.6221 | 14.3449 | -107.7969 | -57.2162 | 645 |
| micro_dev_bps | 5 | ngoài mẫu | 0.2504 | 30.0360 | 19.9483 | 5 | chưa có | 2 | 0.6042 | 15.2993 | -110.4000 | -57.5126 | 501 |

Độ tin cậy: đủ số phiên tối thiểu.

### Chỉ các phiên đủ

Trong mẫu: 1 phiên (2026-11-25); ngoài mẫu: 2 phiên (2026-11-26, 2026-11-27). Cách chia cố định trên mọi phiên trước khi lọc phiên đủ.

| tín hiệu | tầm nhìn (thanh) | mẫu | IC | t | t NW | L | t phiên | số phiên | tỷ lệ đúng chiều | Q5-Q1 | Q5-Q1 ròng | Q5 ròng | số thanh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| obi3 | 1 | trong mẫu | 0.1632 | 13.4618 | 14.5226 | 4 | chưa có | 1 | 0.5883 | 5.5983 | -103.7379 | -52.2961 | 255 |
| obi3 | 1 | ngoài mẫu | 0.1747 | 20.2613 | 20.4896 | 5 | chưa có | 2 | 0.5763 | 6.1092 | -106.3873 | -53.9426 | 506 |
| obi3 | 5 | trong mẫu | 0.2002 | 15.5187 | 9.1397 | 5 | chưa có | 1 | 0.5506 | 14.0145 | -94.9279 | -49.6999 | 253 |
| obi3 | 5 | ngoài mẫu | 0.2075 | 23.2712 | 13.9426 | 5 | chưa có | 2 | 0.5564 | 14.3381 | -97.7615 | -49.0510 | 501 |
| obi_w | 1 | trong mẫu | 0.2339 | 20.3794 | 20.3568 | 4 | chưa có | 1 | 0.6371 | 7.1690 | -102.4149 | -51.8437 | 255 |
| obi_w | 1 | ngoài mẫu | 0.2204 | 26.5664 | 26.7139 | 5 | chưa có | 2 | 0.6081 | 7.8233 | -104.4993 | -53.2012 | 506 |
| obi_w | 5 | trong mẫu | 0.2630 | 21.7156 | 13.3231 | 5 | chưa có | 1 | 0.5833 | 16.2365 | -92.8969 | -48.5067 | 253 |
| obi_w | 5 | ngoài mẫu | 0.2428 | 27.4543 | 16.8530 | 5 | chưa có | 2 | 0.5753 | 15.6602 | -96.2590 | -48.4418 | 501 |
| obi1 | 1 | trong mẫu | 0.3344 | 31.0723 | 25.5473 | 4 | chưa có | 1 | 0.7170 | 9.7551 | -101.8433 | -51.9475 | 255 |
| obi1 | 1 | ngoài mẫu | 0.2911 | 36.0929 | 30.5736 | 5 | chưa có | 2 | 0.6749 | 9.7667 | -102.8871 | -52.5610 | 506 |
| obi1 | 5 | trong mẫu | 0.3177 | 31.4929 | 23.4160 | 5 | chưa có | 1 | 0.6322 | 17.2203 | -93.8986 | -49.6557 | 253 |
| obi1 | 5 | ngoài mẫu | 0.2600 | 30.8614 | 21.1072 | 5 | chưa có | 2 | 0.6042 | 16.3453 | -96.1310 | -48.7733 | 501 |
| micro_dev_bps | 1 | trong mẫu | 0.2952 | 28.1303 | 24.3608 | 4 | chưa có | 1 | 0.7170 | 8.7734 | -117.1307 | -62.7434 | 255 |
| micro_dev_bps | 1 | ngoài mẫu | 0.2659 | 33.2393 | 29.8151 | 5 | chưa có | 2 | 0.6749 | 9.2769 | -118.9730 | -62.6802 | 506 |
| micro_dev_bps | 5 | trong mẫu | 0.3057 | 29.2940 | 21.6389 | 5 | chưa có | 1 | 0.6322 | 16.5483 | -107.6935 | -59.0680 | 253 |
| micro_dev_bps | 5 | ngoài mẫu | 0.2504 | 30.0360 | 19.9483 | 5 | chưa có | 2 | 0.6042 | 15.2993 | -110.4000 | -57.5126 | 501 |

Độ tin cậy: Mới có 3 phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa.

### Placebo

IC khi phá vỡ liên hệ thật: xáo tín hiệu giữa các mã trong cùng thanh (trung bình và độ lệch chuẩn qua các lần xáo), và dùng tín hiệu cũ của thanh t-h. Mọi phiên.

| tín hiệu | tầm nhìn (thanh) | kiểu | IC | độ lệch qua các lần xáo | t NW |
|---|---|---|---|---|---|
| obi3 | 1 | thật | 0.1755 | chưa có | 32.6597 |
| obi3 | 1 | xáo giữa các mã (20 lần) | -0.0016 | 0.0052 | chưa có |
| obi3 | 1 | tín hiệu cũ t-1 | 0.0748 | chưa có | 12.5148 |
| obi3 | 5 | thật | 0.2065 | chưa có | 20.7624 |
| obi3 | 5 | xáo giữa các mã (20 lần) | -0.0002 | 0.0048 | chưa có |
| obi3 | 5 | tín hiệu cũ t-5 | 0.0566 | chưa có | 5.6129 |
| micro_dev_bps | 1 | thật | 0.2772 | chưa có | 44.3631 |
| micro_dev_bps | 1 | xáo giữa các mã (20 lần) | 0.0006 | 0.0054 | chưa có |
| micro_dev_bps | 1 | tín hiệu cũ t-1 | 0.0854 | chưa có | 13.8965 |
| micro_dev_bps | 5 | thật | 0.2569 | chưa có | 29.9397 |
| micro_dev_bps | 5 | xáo giữa các mã (20 lần) | -0.0014 | 0.0060 | chưa có |
| micro_dev_bps | 5 | tín hiệu cũ t-5 | 0.0395 | chưa có | 4.5960 |

### Kết luận

- **Có liên hệ thống kê.** Ngoài mẫu (26-27/11), 8/8 cặp tín hiệu × tầm nhìn có |t Newey-West| > 2. IC từ 0,17 đến 0,29, t NW từ 13,94 đến 30,57. Chênh IC lớn nhất giữa trong mẫu và ngoài mẫu (cùng tín hiệu, cùng tầm nhìn): 0,03.
- **Placebo xáo giữa các mã:** |IC| lớn nhất là 0,00, tức gần 0. Đường tính không tự tạo ra liên hệ. Tín hiệu cũ t-h vẫn cho IC 0,04–0,09: phù hợp với việc OBI và microprice bền theo thời gian, không phải dấu hiệu rò rỉ (tín hiệu thanh t-h vẫn tương quan với tín hiệu thanh t).
- **Không khai thác được sau chi phí.** Q5-Q1 trước chi phí chỉ 6,11 đến 16,35 bps. Chỉ mua Q5 (thực hiện được) cho -62,68 đến -48,44 bps sau phí giả định; 0/8 cặp dương. Riêng độ chênh giá mua-bán, chưa tính phí, đã làm chân mua còn -32,68 đến -18,44 bps.
- **Vì sao IC cao mà không có lãi.** Lợi suất đo trên giá giữa. Khi một phía sổ lệnh mỏng (OBI, microprice lệch), mức giá tốt nhất phía đó dễ bị ăn hết, nên giá giữa nhảy nửa bước giá về phía đó. Đây là hiệu ứng cơ học của giá giữa và bước giá. Muốn ăn được nửa bước đó phải trả nguyên một bước (vào ở giá bán, ra ở giá mua) cộng phí; một bước giá ở vùng giá 10.000-50.000 là 50 đồng, khoảng 10-50 bps.
- **Giới hạn.** Chỉ có 2 phiên ngoài mẫu, rổ 30 mã. Phí 0,15%/chiều là giả định; chưa tính thuế bán, trượt giá khi lệnh lớn hơn mức 1, và quy định không bán khống.

## Kiểm thử

- Python (`pytest --co -q`): 292 ca
- Web (`vitest list`): 100 ca
