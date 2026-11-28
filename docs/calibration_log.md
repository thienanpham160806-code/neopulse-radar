# Nhật ký hiệu chỉnh ngưỡng cảnh báo

Ngày: 28/11/2026. Mã: [src/neopulse/analytics/alerts.py](../src/neopulse/analytics/alerts.py). Tái lập: [tools/calibrate_alerts.py](../tools/calibrate_alerts.py).

Cách tái lập:
- Baseline "trước" chạy chính công cụ trên mã ở commit 4dcfb34, đủ phụ thuộc (RVOL 3, MAD cũ, make_bars cũ), qua `git worktree` và `PYTHONPATH`. Lệnh ghi ở đầu công cụ.
- Chạy lại ngày 28/11 cho đúng từng số với bảng dưới (CX-020).
- Lần 1–9 dùng các nhánh mã trung gian không còn trong mã cuối, ví dụ sàn V của khối ngoại hay so sánh "≥" của spread. Muốn chạy lại các lần đó phải lấy mã ở commit tương ứng (c008081 cho lần 1–9).
- Công cụ hiện tại chỉ tái lập lần 10–11 và bảng cuối.

## Quy tắc chống quá khớp

- Dữ liệu: 6 phiên SSI thật trong `data/neopulse.sqlite`, rổ VN30, thanh 1 phút, cùng đường tính với web (`build_view`, có RVOL).
- **Trong mẫu (được dùng để chọn tham số): 19, 20, 23, 25/11/2026.** Ngoài mẫu: 26, 27/11/2026. Hai phiên này chỉ để báo cáo, không dùng để chọn.
- Mọi số trong tệp này do `tools/calibrate_alerts.py` in ra. Bảng được sinh từ tệp kết quả, không gõ tay.
- Kiểm tra "không làm mù cảnh báo thật": 6 phiên mô phỏng (seed 7, bước 30 giây) có 3 loại sự kiện cài sẵn (`sim_truth`). Độ thu hồi = tỷ lệ sự kiện có cảnh báo đúng loại trong 6 phút. Ở mô phỏng không có KL nền 20 phiên, nên volume_spike chạy nhánh z, **không kiểm được ngưỡng RVOL**.
- Đơn vị đo: số cảnh báo trên một mã trong một phiên, lấy trung bình theo phiên trong mẫu. 19/11 là phiên thiếu (bắt đầu 09:58), nên kéo trung bình xuống một chút.

## Ngân sách cảnh báo và cách chọn

- **CAO ≤ 1 trên một mã trong một phiên.** Đây là mức bot Telegram đẩy đi. Với rổ 30 mã là khoảng 30 tin mỗi phiên, tức 1 tin trên 9 phút: người dùng còn đọc kịp.
- **Mỗi quy tắc ≤ 2 trên một mã trong một phiên**, khoảng 1 lần trên 2 giờ giao dịch. "Bất thường" phải hiếm hơn hẳn trạng thái thường.
- **Độ thu hồi mô phỏng ≥ 0,8** cho loại sự kiện quy tắc đó bắt.
- Cách chọn: trong các cấu hình đạt ngân sách, lấy cấu hình **ít chặt nhất** (nhiều cảnh báo nhất) để giữ độ nhạy tối đa trong ngân sách.
- Chọn theo từng nhóm, nhóm sau giữ kết quả nhóm trước. Riêng CAO_VALUE được kiểm lại sau mỗi lần đổi nhóm khác, vì CAO phụ thuộc việc các quy tắc nổ cùng lúc.

## Hiện trạng trước khi sửa (mã ở commit 4dcfb34)

- spread_blowout: z bền vững của spread_bps ≥ 3,5 và spread ≥ 2 × spread nhỏ nhất đã thấy. Trên 6 phiên, 79% thanh có spread đúng 1 bước giá, nên MAD rất nhỏ và z chạm trần 50 (93% cảnh báo spread ở trần, xem đề xuất 26/11).
- foreign_flow: |z| của giá trị ròng NN ≥ 3,5 và NN ≥ 30% giá trị thanh. Trên 6 phiên, 42% thanh có NN ròng bằng 0 hoặc trống, nên phân phối dồn về 0 và MAD cũng xấp xỉ 0.
- Hai phát hiện mới khi làm lần này:
  - **Room NN về theo cục, khoảng 1 lần mỗi phút** (ví dụ FPT 25/11: `f_sell_val` đổi lúc 10:00:06, 10:01:06, 10:02:06, trong khi `total_value` đổi liên tục). Trong mẫu, 12,4% số thanh 1 phút có |NN ròng| lớn hơn giá trị khớp của chính thanh đó. Cộng 3 thanh còn 5,1%, cộng 5 thanh còn 3,3%.
  - Spread là biến rời rạc. Điều kiện "≥ phân vị riêng" luôn đúng với mã thường trực ở nhiều bước giá, nên phải dùng "**vượt** phân vị riêng".

## Lần thử

### 1. spread_blowout theo số bước giá, so sánh "≥ max(K, phân vị q)" (dạng ban đầu)

Các quy tắc khác vẫn như cũ (khối ngoại cửa sổ 1 thanh, RVOL 3, OBI 3 thanh, CAO_VALUE 6).

| K (bước) | q | spread/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP spread |
|---|---|---|---|---|---|
| 2 | 0,950 | 3,525 | 1,917 | 13,017 | 1 |
| 2 | 0,990 | 2,800 | 1,783 | 12,292 | 1 |
| 3 | 0,950 | 1,600 | 1,617 | 11,092 | 1 |
| 3 | 0,990 | 1,250 | 1,533 | 10,742 | 1 |
| 4 | 0,950 | 1,008 | 1,533 | 10,500 | 1 |
| 4 | 0,990 | 0,842 | 1,483 | 10,333 | 1 |
| 5 | 0,950 | 0,700 | 1,417 | 10,192 | 1 |
| 5 | 0,990 | 0,583 | 1,400 | 10,075 | 1 |

Kết luận: K = 4, q = 0,99 (0,84). Khi đó ngân sách đang đặt là ≤ 1 cho spread. Phương án này **bị thay ở lần 7**, sau khi đổi sang so sánh "vượt" và thống nhất ngân sách mỗi quy tắc ≤ 2.

### 2. foreign_flow, cửa sổ 1 thanh, chỉ xét thanh có NN ròng ≠ 0, phân vị riêng của mã

| W | S | q | NN/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP NN |
|---|---|---|---|---|---|---|
| 1 | 0,200 | 0,900 | 3,333 | 1,600 | 10,933 | 0,974 |
| 1 | 0,200 | 0,950 | 2,775 | 1,517 | 10,375 | 0,974 |
| 1 | 0,200 | 0,990 | 1,617 | 1,433 | 9,217 | 0,947 |
| 1 | 0,300 | 0,900 | 3,308 | 1,567 | 10,908 | 0,974 |
| 1 | 0,300 | 0,950 | 2,733 | 1,483 | 10,333 | 0,974 |
| 1 | 0,300 | 0,990 | 1,600 | 1,417 | 9,200 | 0,947 |
| 1 | 0,500 | 0,900 | 3,225 | 1,550 | 10,825 | 0,974 |
| 1 | 0,500 | 0,950 | 2,633 | 1,467 | 10,233 | 0,974 |
| 1 | 0,500 | 0,990 | 1,550 | 1,417 | 9,150 | 0,947 |

Kết luận: S gần như không có tác dụng (thanh có |ròng| lớn hầu như đều có tỷ trọng lớn), và 21% thanh có NN có tỷ trọng > 100%. Xem lại nhịp dữ liệu, thấy room NN về theo cục, nên chuyển sang cửa sổ nhiều thanh.

### 3. foreign_flow, cửa sổ 5 thanh, thêm sàn giá trị tuyệt đối V

| W | S | q | V (tỷ đồng) | NN/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP NN |
|---|---|---|---|---|---|---|---|
| 5 | 0,300 | 0,950 | 0 | 2,092 | 1,550 | 9,692 | 0,842 |
| 5 | 0,300 | 0,950 | 1 | 1,825 | 1,583 | 9,425 | 0,763 |
| 5 | 0,300 | 0,950 | 2 | 1,350 | 1,517 | 8,950 | 0,684 |
| 5 | 0,300 | 0,950 | 5 | 0,808 | 1,408 | 8,408 | 0,474 |
| 5 | 0,300 | 0,990 | 0 | 1,567 | 1,483 | 9,167 | 0,684 |
| 5 | 0,300 | 0,990 | 1 | 1,383 | 1,500 | 8,983 | 0,658 |
| 5 | 0,300 | 0,990 | 2 | 1,025 | 1,433 | 8,625 | 0,605 |
| 5 | 0,300 | 0,990 | 5 | 0,658 | 1,408 | 8,258 | 0,395 |
| 5 | 0,500 | 0,950 | 0 | 1,700 | 1,433 | 9,300 | 0,342 |
| 5 | 0,500 | 0,950 | 1 | 1,433 | 1,467 | 9,033 | 0,342 |
| 5 | 0,500 | 0,950 | 2 | 1,100 | 1,417 | 8,700 | 0,316 |
| 5 | 0,500 | 0,950 | 5 | 0,675 | 1,375 | 8,275 | 0,211 |
| 5 | 0,500 | 0,990 | 0 | 1,233 | 1,425 | 8,833 | 0,316 |
| 5 | 0,500 | 0,990 | 1 | 1,083 | 1,442 | 8,683 | 0,316 |
| 5 | 0,500 | 0,990 | 2 | 0,833 | 1,408 | 8,433 | 0,289 |
| 5 | 0,500 | 0,990 | 5 | 0,558 | 1,392 | 8,158 | 0,184 |

Kết luận: S = 0,5 và mọi sàn V > 0 đều kéo độ thu hồi mô phỏng xuống dưới 0,8. Nguyên nhân: mô phỏng có |NN ròng| một thanh rất nhỏ (phân vị 50/90/99 = 0,012/0,061/0,439 tỷ đồng), không cùng thang với dữ liệu thật. Sàn tuyệt đối vì vậy không kiểm được trên mô phỏng, nên **loại V**.

### 4. foreign_flow, cửa sổ 1 và 3 thanh

| W | S | q | V (tỷ đồng) | NN/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP NN |
|---|---|---|---|---|---|---|---|
| 1 | 0,300 | 0,950 | 0 | 2,733 | 1,483 | 10,333 | 0,974 |
| 1 | 0,300 | 0,950 | 1 | 1,575 | 1,467 | 9,175 | 0,684 |
| 1 | 0,300 | 0,950 | 2 | 0,958 | 1,417 | 8,558 | 0,526 |
| 1 | 0,300 | 0,990 | 0 | 1,600 | 1,417 | 9,200 | 0,947 |
| 1 | 0,300 | 0,990 | 1 | 1,150 | 1,400 | 8,750 | 0,658 |
| 1 | 0,300 | 0,990 | 2 | 0,808 | 1,367 | 8,408 | 0,500 |
| 3 | 0,300 | 0,950 | 0 | 2,333 | 1,533 | 9,933 | 0,921 |
| 3 | 0,300 | 0,950 | 1 | 1,842 | 1,550 | 9,442 | 0,789 |
| 3 | 0,300 | 0,950 | 2 | 1,325 | 1,492 | 8,925 | 0,684 |
| 3 | 0,300 | 0,990 | 0 | 1,608 | 1,508 | 9,208 | 0,816 |
| 3 | 0,300 | 0,990 | 1 | 1,367 | 1,475 | 8,967 | 0,737 |
| 3 | 0,300 | 0,990 | 2 | 0,975 | 1,425 | 8,575 | 0,658 |

Kết luận: đạt "≤ 2 và thu hồi ≥ 0,8" có W1 q0,99 (1,600; thu hồi 0,947) và W3 q0,99 (1,608; 0,816). Chọn **W = 3, S = 0,30, q = 0,99**. W1 bị loại vì dữ liệu, không phải vì số: 12% thanh đơn lẻ có tỷ trọng NN > 100%, tức tỷ trọng 1 thanh không đo đúng thứ nó định đo. Cửa sổ 5 thanh làm thu hồi rơi còn 0,684.

### 5. CAO_VALUE (lần đầu, spread K4 q0,99, NN W3 q0,99, RVOL 3, OBI 3 thanh)

| CAO_VALUE | CAO/mã/phiên | tổng/mã/phiên | CAO ngoài mẫu (chỉ báo cáo) |
|---|---|---|---|
| 6 | 1,508 | 9,208 | 2,283 |
| 8 | 1,058 | 9,208 | 1,567 |
| 10 | 0,800 | 9,208 | 1,250 |
| 12 | 0,708 | 9,208 | 1,150 |

### 6. volume_spike (RVOL) và book_pressure (OBI, số thanh liên tục)

| RVOL | OBI | số thanh OBI | KL/mã/phiên | sổ lệnh/mã/phiên | CAO/mã/phiên | tổng/mã/phiên |
|---|---|---|---|---|---|---|
| 3 | 0,600 | 3 | 3,408 | 2,867 | 0,800 | 9,208 |
| 3 | 0,600 | 5 | 3,408 | 1,875 | 0,783 | 8,217 |
| 3 | 0,700 | 3 | 3,408 | 1,792 | 0,733 | 8,133 |
| 3 | 0,700 | 5 | 3,408 | 1,075 | 0,767 | 7,417 |
| 3 | 0,800 | 3 | 3,408 | 0,833 | 0,717 | 7,175 |
| 3 | 0,800 | 5 | 3,408 | 0,475 | 0,700 | 6,817 |
| 4 | 0,600 | 3 | 2,533 | 2,867 | 0,825 | 8,333 |
| 4 | 0,600 | 5 | 2,533 | 1,875 | 0,775 | 7,342 |
| 4 | 0,700 | 3 | 2,533 | 1,792 | 0,758 | 7,258 |
| 4 | 0,700 | 5 | 2,533 | 1,075 | 0,775 | 6,542 |
| 4 | 0,800 | 3 | 2,533 | 0,833 | 0,725 | 6,300 |
| 4 | 0,800 | 5 | 2,533 | 0,475 | 0,708 | 5,942 |
| 5 | 0,600 | 3 | 1,925 | 2,867 | 0,858 | 7,725 |
| 5 | 0,600 | 5 | 1,925 | 1,875 | 0,808 | 6,733 |
| 5 | 0,700 | 3 | 1,925 | 1,792 | 0,792 | 6,650 |
| 5 | 0,700 | 5 | 1,925 | 1,075 | 0,808 | 5,933 |
| 5 | 0,800 | 3 | 1,925 | 0,833 | 0,758 | 5,692 |
| 5 | 0,800 | 5 | 1,925 | 0,475 | 0,742 | 5,333 |

Kết luận: chỉ RVOL = 5 đưa KL/mã/phiên xuống ≤ 2 (1,925). Với sổ lệnh, các cấu hình đạt ≤ 2, xếp từ ít chặt đến chặt: (0,6; 5 thanh) 1,875, rồi (0,7; 3 thanh) 1,792. Chọn **OBI 0,6 giữ nguyên, 5 thanh**: chỉ đổi một tham số, và 0,6 vẫn giữ nghĩa "một bên dày gấp 4 lần". Thu hồi mô phỏng không đổi (0,722), vì mô phỏng không có RVOL và book_pressure không có sự kiện cài.

### 7. Kiểm lại CAO_VALUE sau khi đổi RVOL và OBI

| CAO_VALUE | CAO/mã/phiên | tổng/mã/phiên | CAO ngoài mẫu (chỉ báo cáo) |
|---|---|---|---|
| 6 | 1,808 | 6,733 | 3,267 |
| 8 | 1,158 | 6,733 | 1,933 |
| 10 | 0,808 | 6,733 | 1,317 |
| 12 | 0,683 | 6,733 | 1,150 |

### 8. spread_blowout với so sánh "≥ K và VƯỢT phân vị q" (mã cuối)

| K (bước) | q | spread/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP spread |
|---|---|---|---|---|---|
| 2 | 0,950 | 2,575 | 1,042 | 8,467 | 1 |
| 2 | 0,990 | 2,017 | 0,975 | 7,908 | 0,944 |
| 3 | 0,950 | 1,383 | 0,842 | 7,275 | 1 |
| 3 | 0,990 | 1,167 | 0,825 | 7,058 | 0,944 |
| 4 | 0,950 | 0,933 | 0,792 | 6,825 | 1 |
| 4 | 0,990 | 0,808 | 0,775 | 6,700 | 0,944 |
| 5 | 0,950 | 0,642 | 0,767 | 6,533 | 1 |
| 5 | 0,990 | 0,567 | 0,750 | 6,458 | 0,944 |

Kết luận theo ngân sách ≤ 2: cấu hình ít chặt nhất đạt ngân sách là **K = 3, q = 0,95** (1,383; thu hồi 1). K = 2, q = 0,99 vượt ngân sách (2,017).

### 9. CAO_VALUE với bộ tham số cuối

| CAO_VALUE | CAO/mã/phiên | tổng/mã/phiên | CAO ngoài mẫu (chỉ báo cáo) |
|---|---|---|---|
| 6 | 1,825 | 7,275 | 3,483 |
| 8 | 1,183 | 7,275 | 2,200 |
| 10 | 0,842 | 7,275 | 1,600 |
| 12 | 0,717 | 7,275 | 1,433 |

Kết luận: **CAO_VALUE = 10** là mức ít chặt nhất đạt CAO ≤ 1 (0,842). Mức 8 cho 1,183.

### 10. Kiểm lại toàn bộ sau khi sửa MAD (CX-015) và ảnh chụp sổ lệnh (CX-016)

Lần 1-9 chạy trước hai bản sửa này. Hai bản sửa đổi z bền vững (price_jump, nhánh z của volume_spike) và đổi cách lấy sổ lệnh cuối thanh, nên cache lại thanh và chạy lại các lưới với bộ tham số cuối.

| K (bước) | q | spread/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP spread |
|---|---|---|---|---|---|
| 2 | 0,950 | 2,575 | 1,100 | 8,567 | 1 |
| 2 | 0,990 | 2,017 | 1,017 | 8,008 | 0,944 |
| 3 | 0,950 | 1,383 | 0,900 | 7,375 | 1 |
| 3 | 0,990 | 1,167 | 0,867 | 7,158 | 0,944 |
| 4 | 0,950 | 0,933 | 0,850 | 6,925 | 1 |
| 4 | 0,990 | 0,808 | 0,817 | 6,800 | 0,944 |
| 5 | 0,950 | 0,642 | 0,842 | 6,633 | 1 |
| 5 | 0,990 | 0,567 | 0,808 | 6,558 | 0,944 |

| W | q | NN/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP NN |
|---|---|---|---|---|---|
| 1 | 0,950 | 2,733 | 0,858 | 8,500 | 0,974 |
| 1 | 0,990 | 1,600 | 0,842 | 7,367 | 0,947 |
| 3 | 0,950 | 2,333 | 0,917 | 8,100 | 0,921 |
| 3 | 0,990 | 1,608 | 0,900 | 7,375 | 0,816 |

| RVOL | OBI | số thanh OBI | KL/mã/phiên | sổ lệnh/mã/phiên | CAO/mã/phiên | tổng/mã/phiên |
|---|---|---|---|---|---|---|
| 3 | 0,600 | 3 | 3,408 | 2,867 | 0,925 | 9,850 |
| 3 | 0,600 | 5 | 3,408 | 1,875 | 0,875 | 8,858 |
| 3 | 0,700 | 3 | 3,408 | 1,792 | 0,875 | 8,775 |
| 3 | 0,700 | 5 | 3,408 | 1,075 | 0,842 | 8,058 |
| 3 | 0,800 | 3 | 3,408 | 0,833 | 0,825 | 7,817 |
| 3 | 0,800 | 5 | 3,408 | 0,475 | 0,775 | 7,458 |
| 4 | 0,600 | 3 | 2,533 | 2,867 | 0,983 | 8,975 |
| 4 | 0,600 | 5 | 2,533 | 1,875 | 0,900 | 7,983 |
| 4 | 0,700 | 3 | 2,533 | 1,792 | 0,933 | 7,900 |
| 4 | 0,700 | 5 | 2,533 | 1,075 | 0,883 | 7,183 |
| 4 | 0,800 | 3 | 2,533 | 0,833 | 0,867 | 6,942 |
| 4 | 0,800 | 5 | 2,533 | 0,475 | 0,817 | 6,583 |
| 5 | 0,600 | 3 | 1,925 | 2,867 | 0,983 | 8,367 |
| 5 | 0,600 | 5 | 1,925 | 1,875 | 0,900 | 7,375 |
| 5 | 0,700 | 3 | 1,925 | 1,792 | 0,933 | 7,292 |
| 5 | 0,700 | 5 | 1,925 | 1,075 | 0,883 | 6,575 |
| 5 | 0,800 | 3 | 1,925 | 0,833 | 0,867 | 6,333 |
| 5 | 0,800 | 5 | 1,925 | 0,475 | 0,817 | 5,975 |

| CAO_VALUE | CAO/mã/phiên | tổng/mã/phiên | CAO ngoài mẫu (chỉ báo cáo) |
|---|---|---|---|
| 6 | 1,900 | 7,375 | 3,600 |
| 8 | 1,242 | 7,375 | 2,267 |
| 10 | 0,900 | 7,375 | 1,633 |
| 12 | 0,767 | 7,375 | 1,500 |

Kết luận: quy tắc chọn cho **cùng kết quả**:
- spread: 3 bước, q 0,95 (1,383; 2 bước q 0,99 vượt ngân sách với 2,017).
- khối ngoại: W3 q 0,99 (W1 q 0,99 bị loại vì lý do dữ liệu như lần 4).
- RVOL: 5.
- sổ lệnh: 0,6 trong 5 thanh.
- CAO_VALUE: 10 (CAO 0,90; mức 8 cho 1,242).

Độ thu hồi mô phỏng của volume_spike tăng từ 0,722 lên 0,833, vì z đúng công thức nhạy hơn. Đổi lại, độ chính xác chung trên mô phỏng giảm còn 0,588, do nhánh z bắt cả các đỉnh khối lượng tự nhiên không có trong đáp án cài sẵn (xem test `test_planted_anomalies_are_recovered`).

### 11. Đếm bước giá trên lưới (CX-018), chuỗi OBI phải liền thanh (CX-019), giấu ngoài mẫu (CX-020)

- **CX-018.** Spread vắt qua mốc 10.000 hoặc 50.000 trước đây bị chia cho bước giá tại giá mua. Ví dụ 9.990 → 10.050 bị tính 6 bước, đúng ra là 2 bước. Nay đếm trên lưới giá theo từng vùng (`grid_ticks`).
- **CX-019.** Chuỗi OBI cực đoan trước đây vẫn đếm "5 thanh liên tiếp" dù mất dữ liệu giữa chừng. Nay đếm lại khi hai thanh cách nhau quá một thanh, kể cả qua nghỉ trưa.
- **CX-020.** Từ lần này, lưới chỉ in cột trong mẫu. Kết quả ngoài mẫu chỉ in ở bước `final`, sau khi khóa tham số.
  - Ở lần 1–9, công cụ có in CAO ngoài mẫu trong các bảng CAO_VALUE. Quy tắc chọn chỉ dùng cột trong mẫu, nhưng quy trình lúc đó **chưa làm mù** cột ngoài mẫu. Ghi lại ở đây để người đọc tự đánh giá.

| K (bước) | q | spread/mã/phiên | CAO/mã/phiên | tổng/mã/phiên | thu hồi MP spread |
|---|---|---|---|---|---|
| 2 | 0,950 | 2,575 | 1,100 | 8,583 | 1 |
| 2 | 0,990 | 2,017 | 1,017 | 8,025 | 0,944 |
| 3 | 0,950 | 1,383 | 0,900 | 7,392 | 1 |
| 3 | 0,990 | 1,167 | 0,867 | 7,175 | 0,944 |
| 4 | 0,950 | 0,933 | 0,850 | 6,942 | 1 |
| 4 | 0,990 | 0,808 | 0,817 | 6,817 | 0,944 |
| 5 | 0,950 | 0,642 | 0,842 | 6,650 | 1 |
| 5 | 0,990 | 0,567 | 0,808 | 6,575 | 0,944 |

| RVOL | OBI | số thanh OBI | KL/mã/phiên | sổ lệnh/mã/phiên | CAO/mã/phiên | tổng/mã/phiên |
|---|---|---|---|---|---|---|
| 3 | 0,600 | 3 | 3,408 | 2,867 | 0,958 | 9,850 |
| 3 | 0,600 | 5 | 3,408 | 1,892 | 0,875 | 8,875 |
| 3 | 0,700 | 3 | 3,408 | 1,775 | 0,858 | 8,758 |
| 3 | 0,700 | 5 | 3,408 | 1,067 | 0,825 | 8,050 |
| 3 | 0,800 | 3 | 3,408 | 0,817 | 0,808 | 7,800 |
| 3 | 0,800 | 5 | 3,408 | 0,467 | 0,775 | 7,450 |
| 4 | 0,600 | 3 | 2,533 | 2,867 | 1,017 | 8,975 |
| 4 | 0,600 | 5 | 2,533 | 1,892 | 0,900 | 8 |
| 4 | 0,700 | 3 | 2,533 | 1,775 | 0,917 | 7,883 |
| 4 | 0,700 | 5 | 2,533 | 1,067 | 0,867 | 7,175 |
| 4 | 0,800 | 3 | 2,533 | 0,817 | 0,850 | 6,925 |
| 4 | 0,800 | 5 | 2,533 | 0,467 | 0,817 | 6,575 |
| 5 | 0,600 | 3 | 1,925 | 2,867 | 1,017 | 8,367 |
| 5 | 0,600 | 5 | 1,925 | 1,892 | 0,900 | 7,392 |
| 5 | 0,700 | 3 | 1,925 | 1,775 | 0,917 | 7,275 |
| 5 | 0,700 | 5 | 1,925 | 1,067 | 0,867 | 6,567 |
| 5 | 0,800 | 3 | 1,925 | 0,817 | 0,850 | 6,317 |
| 5 | 0,800 | 5 | 1,925 | 0,467 | 0,817 | 5,967 |

| CAO_VALUE | CAO/mã/phiên | tổng/mã/phiên |
|---|---|---|
| 6 | 1,900 | 7,392 |
| 8 | 1,242 | 7,392 |
| 10 | 0,900 | 7,392 |
| 12 | 0,767 | 7,392 |

Kết luận: quy tắc chọn vẫn cho **cùng bộ tham số**.
- spread: 3 bước, q 0,95.
- sổ lệnh: 0,6 trong 5 thanh (1,892). Cấu hình 0,7 trong 3 thanh ít cảnh báo hơn (1,775), nên không phải cấu hình ít chặt nhất.
- CAO_VALUE: 10 (CAO 0,90).

## Tham số cuối

| tham số | trước | sau |
|---|---|---|
| spread_blowout | z ≥ 3,5 và spread ≥ 2 × spread nhỏ nhất | ≥ 3 bước giá HOSE (đếm trên lưới giá) và vượt phân vị 95% của mã (chưa đủ 20 thanh trước: chỉ sàn 3 bước) |
| foreign_flow | \|z\| ≥ 3,5 và NN ≥ 30% GT thanh | cửa sổ 3 thanh: NN ròng ≠ 0, ≥ 30% GT khớp, \|ròng\| ≥ phân vị 99% các cửa sổ có NN trước của mã (chưa đủ 20 cửa sổ: không báo) |
| RVOL_SPIKE | 3 | 5 |
| book_pressure | \|OBI₃\| ≥ 0,6 trong 3 thanh | \|OBI₃\| ≥ 0,6 trong 5 thanh liền nhau |
| CAO theo giá trị (volume_spike, price_jump) | ≥ 6 | ≥ 10 |
| price_jump, near_limit, cooldown 10 thanh, bỏ thanh 09:15/14:45 | | giữ nguyên |

## Trước và sau, theo phiên

Trước: mã ở 4dcfb34 (chạy lại bằng worktree). Sau: mã cuối (gồm CX-015, CX-016, CX-018, CX-019).

| phiên | mẫu | tổng trước | tổng sau | CAO trước | CAO sau | volume_spike trước/sau | spread_blowout trước/sau | price_jump trước/sau | foreign_flow trước/sau | book_pressure trước/sau | near_limit trước/sau |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-19 | trong mẫu | 96 | 90 | 7 | 8 | 28/14 | 15/24 | 2/2 | 7/15 | 44/35 | 0/0 |
| 2026-11-20 | trong mẫu | 404 | 283 | 79 | 43 | 130/85 | 68/52 | 17/22 | 76/56 | 113/68 | 0/0 |
| 2026-11-23 | trong mẫu | 370 | 217 | 53 | 21 | 113/58 | 69/37 | 19/19 | 102/65 | 67/38 | 0/0 |
| 2026-11-25 | trong mẫu | 485 | 297 | 80 | 36 | 138/74 | 112/53 | 20/27 | 95/57 | 120/86 | 0/0 |
| 2026-11-26 | ngoài mẫu | 644 | 371 | 101 | 57 | 196/128 | 119/54 | 43/47 | 135/42 | 148/97 | 3/3 |
| 2026-11-27 | ngoài mẫu | 520 | 303 | 99 | 43 | 143/93 | 122/52 | 25/33 | 106/52 | 122/71 | 2/2 |

| chỉ số | trước | sau |
|---|---|---|
| CAO/mã/phiên trong mẫu | 1,825 | 0,900 |
| tổng/mã/phiên trong mẫu | 11,292 | 7,392 |
| CAO/mã/phiên ngoài mẫu | 3,333 | 1,667 |
| tổng/mã/phiên ngoài mẫu | 19,400 | 11,233 |
| độ chính xác mô phỏng | 0,864 | 0,588 |
| thu hồi mô phỏng foreign_dump | 0,895 | 0,816 |
| thu hồi mô phỏng spread_blowout | 0,806 | 1 |
| thu hồi mô phỏng volume_spike | 0,722 | 0,833 |

## Đọc kết quả (mã cuối)

- **Trong mẫu**, cả hai ngân sách đều đạt: CAO 0,90/mã/phiên, mỗi quy tắc ≤ 1,93.
- **Ngoài mẫu**, CAO là 1,67/mã/phiên, **vượt ngân sách 1**; tổng 11,23/mã/phiên. Hai phiên 26-27/11 sôi động hơn: 26/11 có 484.447 bản ghi giá, nhiều nhất trong 6 phiên. Ngưỡng chọn trên 4 phiên không giữ được ngân sách khi thị trường sôi động hơn. Đây là kết quả ngoài mẫu, ghi nguyên, không chỉnh lại theo nó.
- Độ thu hồi mô phỏng:
  - spread tăng từ 0,806 lên 1.
  - khối ngoại giảm từ 0,895 xuống 0,816, vẫn ≥ 0,8. Cái giá phải trả: một phần sự kiện khối ngoại ngắn (2-4 phút) bị pha loãng khi cộng 3 thanh.
  - khối lượng tăng từ 0,722 lên 0,833, do sửa MAD (CX-015).
- Độ chính xác trên mô phỏng giảm từ 0,864 xuống 0,588, cùng nguyên nhân. Riêng spread và khối ngoại vẫn > 0,9.
- Giới hạn của cách hiệu chỉnh:
  - Chỉ có 4 phiên trong mẫu.
  - Ngân sách là lựa chọn thiết kế, không phải kết quả thống kê.
  - Không có "đáp án đúng" cho dữ liệu thật, nên không đo được độ chính xác trên dữ liệu thật.
  - Mô phỏng không có KL nền, nên không kiểm được ngưỡng RVOL.
