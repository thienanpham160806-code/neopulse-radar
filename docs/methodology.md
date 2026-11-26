# Phương pháp tài chính và phân tích

Ký hiệu: b_i, a_i — giá mua/bán mức i (i = 1..3); Bv_i, Av_i — khối lượng chờ; S — chỉ số cơ sở; F — giá HĐTL.

## 1. Vi cấu trúc sổ lệnh — `finance/microstructure.py`

| Chỉ báo | Công thức | Diễn giải |
|---|---|---|
| Giá giữa | mid = (a₁ + b₁)/2 | giá tham chiếu không lệch về phía nào |
| Spread | (a₁ − b₁)/mid × 10⁴ (bps) | chi phí khứ hồi tức thời của lệnh nhỏ |
| OBI_k | (ΣBv_i − ΣAv_i)/(ΣBv_i + ΣAv_i), i ≤ k | ∈ [−1, 1]; > 0: bên mua dày hơn |
| OBI_w | như trên, trọng số 1, ½, ⅓ | coi trọng mức giá gần |
| Microprice | (a₁·Bv₁ + b₁·Av₁)/(Bv₁ + Av₁) | giá giữa nghiêng về phía mỏng hơn — nơi giá dễ dịch tới |
| Áp lực | ΣAv_i / ΣBv_i | > 1: chào bán dày hơn |
| Vị trí biên độ | (giá − tham chiếu)/(trần − tham chiếu) | +1 = trần, −1 = sàn |

**Vì sao chọn.** Mất cân bằng giữa hai phía sổ lệnh là biến trạng thái ngắn hạn được nghiên cứu nhiều nhất trong vi cấu trúc: Cont, Kukanov & Stoikov (2014) cho thấy mất cân bằng dòng lệnh ở mức giá tốt nhất giải thích phần lớn biến động giá ngắn hạn; Stoikov (2018) đề xuất microprice như ước lượng giá tương lai gần tốt hơn giá giữa. NEO API cung cấp đúng 3 mức giá nên OBI₃ là chỉ báo đầy đủ nhất tính được.

**Giả định và giới hạn.** Chỉ thấy 3 mức; không thấy lệnh ẩn, lệnh ATO/ATC, hay việc đặt-hủy nhanh. Trong phiên định kỳ, mức 1 mang nhãn ATO/ATC → mọi chỉ báo sổ lệnh để trống thay vì suy diễn.

### Trượt giá ước lượng (`walk_book`)
Với lệnh mua Q cổ phiếu: khớp lần lượt tại a₁, a₂, a₃ cho tới khi đủ Q hoặc hết 3 mức.
trượt giá (bps) = (giá bình quân − mid)/mid × 10⁴; phần không khớp được báo riêng.
Đây là **cận dưới**: sổ lệnh giả định đứng yên, không tính tác động thị trường ngoài 3 mức.

### Amihud nội phiên
trung vị theo thanh của |lợi suất thanh, bps| / giá trị khớp thanh (tỷ đồng) — phỏng theo Amihud (2002), vốn định nghĩa ở tần suất ngày. Dùng để so sánh tương đối giữa các mã trong rổ.

### Điểm thanh khoản
Trung bình hạng phân vị trong rổ của: spread (thấp = tốt), độ sâu 3 mức, giá trị khớp, Amihud (thấp = tốt) → thang 0–100. Là xếp hạng tương đối, không phải thước đo tuyệt đối.

## 2. Độ rộng thị trường — `finance/breadth.py`

A/D = (số mã tăng − số mã giảm)/(số mã tăng + số mã giảm). Độ rộng đo mức lan tỏa độc lập với vốn hóa. **Phân kỳ** được gắn cờ khi chỉ số đổi > 0,15% mà A/D ngược dấu với độ lớn > 0,15 (vùng đệm để bỏ dao động quanh 0): chỉ số được kéo/đè bởi ít mã lớn.

Độ rộng tự tính trên rổ (từ giá từng mã) được hiển thị song song với số của sàn để đối chiếu.

## 3. Dòng tiền nước ngoài — `finance/foreign.py`

| Chỉ báo | Công thức |
|---|---|
| Ròng | mua − bán (đồng) |
| Ròng/tổng | (mua − bán)/(mua + bán) ∈ [−1, 1] |
| Tỷ trọng | (mua + bán)/(2 × tổng giá trị khớp) |
| Room đã dùng | 1 − room còn lại/tổng room |

Tách *chiều* (ròng/tổng) khỏi *quy mô* (tỷ trọng): mua ròng 5 tỷ trên 6 tỷ giao dịch NN nhưng chỉ chiếm 1% thanh khoản mã là tín hiệu yếu. Mã không có giao dịch NN nhận giá trị trống, không phải 0.

## 4. Basis phái sinh — `finance/basis.py`

basis = F − S; basis% = (F − S)/S; lãi suất hàm ý quy năm = (F/S − 1) × 365/số ngày tới đáo hạn.
Giá trị hợp lý theo chi phí lưu giữ: F* = S × (1 + (r − q)·T), mặc định r = 4,5%/năm, q = 0 — **giả định, cần cập nhật theo lãi suất thực tế**.
Mỗi ảnh chụp HĐTL ghép với giá trị chỉ số gần nhất *trước đó* (không quá 2 phút) — không dùng giá trị tương lai, bỏ cặp ghép khi chỉ số bị trễ.
Basis âm không tự động là cơ hội arbitrage: bán khống cơ sở bị hạn chế ở Việt Nam.

## 5. Điểm nhịp thị trường — `finance/pulse.py`

score = 50 + 50 × Σ wᵢ·cᵢ, cᵢ ∈ [−1, 1]

| Thành phần | cᵢ | wᵢ | Lý do |
|---|---|---|---|
| Độ rộng | A/D | 0,30 | lan tỏa là đặc trưng bền nhất của trạng thái thị trường |
| Động lượng | tanh(% thay đổi chỉ số / σ) | 0,25 | biên độ so với mức dao động thường ngày |
| Sổ lệnh | OBI₃ bình quân trọng số giá trị khớp | 0,20 | áp lực đang chờ |
| Khối ngoại | Σròng/Σ(mua + bán) | 0,15 | nhóm nhà đầu tư có thông tin/kỷ luật riêng |
| Thanh khoản | tanh(ln(GTGD hiện tại / GTGD kỳ vọng)) | 0,10 | xác nhận bằng dòng tiền |

- σ = độ lệch chuẩn % thay đổi cuối phiên của các phiên đã lưu (cần ≥ 5 phiên, mặc định 1,0).
- GTGD kỳ vọng = trung vị GTGD lũy kế các phiên trước tại cùng số phút giao dịch đã trôi qua (cần ≥ 3 phiên).
- Thành phần thiếu dữ liệu bị loại và trọng số được chuẩn hóa lại; dưới 50% trọng số có dữ liệu → **không kết luận**.
- Nhãn: ≥ 65 tích cực lan tỏa · 55–65 nghiêng tích cực · 45–55 trung tính · 35–45 nghiêng tiêu cực · < 35 tiêu cực lan tỏa.

**Trung thực về trọng số.** Trọng số là lựa chọn thiết kế, không ước lượng từ dữ liệu (số phiên thu được quá ít để ước lượng mà không quá khớp). `sensitivity()` xáo trộn mỗi trọng số ±50% và báo khoảng điểm cùng tỷ lệ giữ nguyên nhãn — hiển thị ngay trên dashboard. Điểm mô tả hiện trạng, **không dự báo**.

## 6. Phát hiện bất thường — `analytics/anomaly.py`

z_t = 0,6745 × (x_t − median)/MAD, median và MAD lấy trên 60 thanh **trước** t của chính mã đó trong phiên (tối thiểu 20 thanh).

- Median/MAD thay cho trung bình/độ lệch chuẩn: chính điểm bất thường làm phình độ lệch chuẩn và che lấp nhau.
- 0,6745 đưa z về thang chuẩn tắc; ngưỡng |z| ≥ 3,5 theo Iglewicz & Hoaglin (1993).
- Khối lượng lấy log(1 + x) vì lệch phải mạnh. MAD = 0 → không kết luận. |z| chặn ở 50 để dễ đọc.

## 7. Cảnh báo — `analytics/alerts.py`

| Quy tắc | Điều kiện | Cơ sở |
|---|---|---|
| Khối lượng tăng bất thường | z_vol ≥ 3,5 | thống kê |
| Độ chênh giá mua-bán giãn rộng | z_spread ≥ 3,5 **và** spread ≥ 2 × spread nhỏ nhất đã thấy trong phiên | thống kê + loại nhiễu một bước giá |
| Giá biến động đột ngột | \|z_ret\| ≥ 3,5 | thống kê |
| Khối ngoại giao dịch bất thường | \|z_fnet\| ≥ 3,5 **và** khối ngoại ≥ 30% giá trị thanh | thống kê + điều kiện trọng yếu |
| Mất cân bằng sổ lệnh kéo dài | \|OBI₃\| ≥ 0,6 cùng dấu 3 thanh liên tiếp | 0,6 ⇔ một bên dày gấp 4 lần bên kia; 3 thanh để loại nhiễu đặt-hủy |
| Sát trần/sàn | \|vị trí biên độ\| ≥ 0,9 | quy tắc biên độ của sàn |

Mức ưu tiên: **CAO** khi ≥ 2 quy tắc cùng nổ trên một mã trong một thanh, hoặc |giá trị| ≥ 6 (z, hoặc RVOL với quy tắc khối lượng); hai quy tắc cuối là **THẤP** khi đứng một mình; còn lại **TRUNG BÌNH**. Thời gian nguội 10 thanh cho mỗi cặp (mã, quy tắc). Khóa chống lặp khi lưu/gửi.

**Điều chỉnh sau khi đối chiếu 4 phiên SSI thật (duyệt 26/11/2026):**
- Độ chênh giá và khối ngoại **chỉ CAO khi đi cùng quy tắc khác**. Spread thường đúng 1 bước giá và khối ngoại thường bằng 0, nên MAD ≈ 0 và |z| bão hòa: 93% cảnh báo độ chênh giá chạm trần 50, 258/264 lượt bị xếp CAO, nên mốc "|z| ≥ 6" không còn phân biệt được.
- Quy tắc khối lượng **bỏ thanh 09:15 (khớp ATO) và 14:45 (khớp ATC)**: khối lượng đấu giá lớn do cấu trúc phiên, không phải bất thường; 90/499 cảnh báo khối lượng rơi vào thanh 14:45.
- Giữ ngưỡng sát trần/sàn 0,9: quy tắc không báo lần nào vì trong 4 phiên |vị trí biên độ| lớn nhất chỉ 0,86, không phải do lỗi.

Ngưỡng 30%, 3 thanh, 10 thanh là quy tắc nghiệp vụ do tác giả đặt — nên rà lại bằng dữ liệu thật (tần suất cảnh báo mỗi phiên) trước khi coi là cuối cùng.

## 8. Xếp hạng đa yếu tố — `analytics/ranking.py`

z-score mặt cắt ngang trong rổ, cắt đuôi ±3: động lượng (30%), OBI₃ (25%), NN ròng/tổng (20%), log giá trị khớp (15%), −spread (10%). Mã thiếu một yếu tố được chuẩn hóa lại trọng số. Chỉ có nghĩa tương đối tại thời điểm tính.

## 9. Kiểm chứng — `analytics/validation.py`

**Câu hỏi:** tín hiệu sổ lệnh cuối thanh t có liên hệ với lợi suất giá giữa t → t+h không?

- Tín hiệu chỉ dùng thông tin đến t; lợi suất tương lai không vượt ranh giới phiên.
- IC = tương quan hạng Spearman theo mặt cắt ngang từng thanh, lấy trung bình qua các thanh (kiểu Fama–MacBeth, 1973); t = trung bình/(độ lệch chuẩn/√n).
- **Tách theo thời gian**: 60% phiên đầu là trong mẫu, phần còn lại là ngoài mẫu; không xáo trộn.
- Báo thêm tỷ lệ đúng chiều và chênh lệch lợi suất nhóm 20% tín hiệu cao nhất − thấp nhất.

**Cách đọc có trách nhiệm.** t-stat bị thổi phồng do thanh liền kề tự tương quan. Q5−Q1 chưa trừ spread và phí: với spread VN30 thường 5–20 bps, một tín hiệu vài bps **không** là lợi nhuận khả thi. Dưới 5 phiên, kết quả chỉ minh họa. Trên dữ liệu mô phỏng, tín hiệu được cài sẵn — kết quả chỉ xác nhận mã tính đúng.

## 10. Diễn giải bằng ngôn ngữ — `analytics/explain.py`

Mặc định dùng mẫu câu xác định dựng từ số liệu. Nếu bật mô hình ngôn ngữ: chỉ gửi bảng số liệu; đầu ra bị loại nếu chứa bất kỳ con số nào không có trong bảng, hoặc chứa ngôn ngữ khuyến nghị mua/bán — khi đó quay về mẫu câu. Giao diện luôn ghi nguồn diễn giải.

## Tài liệu tham khảo

*Đã đối chiếu tác giả, năm, tập, số và trang với IDEAS/RePEc, arXiv và danh mục ASQ ngày 25/11/2026.*

- Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*, 5(1), 31–56.
- Chordia, T., Roll, R., & Subrahmanyam, A. (2002). Order imbalance, liquidity, and market returns. *Journal of Financial Economics*, 65(1), 111–130. https://doi.org/10.1016/S0304-405X(02)00136-8
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88. https://doi.org/10.1093/jjfinec/nbt003
- Fama, E. F., & MacBeth, J. D. (1973). Risk, return, and equilibrium: Empirical tests. *Journal of Political Economy*, 81(3), 607–636. https://doi.org/10.1086/260061
- Iglewicz, B., & Hoaglin, D. C. (1993). *How to Detect and Handle Outliers* (ASQC Basic References in Quality Control: Statistical Techniques, Vol. 16). Milwaukee: ASQC Quality Press.
- Stoikov, S. (2018). The micro-price: a high-frequency estimator of future prices. *Quantitative Finance*, 18(12), 1959–1966.
- VPBankS. *NeoAPI Docs* v1.0.0. https://neoinvest.vpbanks.com.vn/neo-openapi/docs/overview (truy cập 14/11/2026; kiểm tra lại 25/11/2026: trang công khai, tiêu đề "Overview - NeoAPI Docs", phiên bản v1.0.0).
- SSI. *FastConnect Data API v3*. https://developers.ssi.com.vn (nguồn dữ liệu đang dùng; truy cập 19–25/11/2026).

## 11. Ngành trong phiên — `finance/sectors.py`

Phân ngành theo mã ICB 4 chữ số (chuẩn cũ) do SSI trả trong `securitiesByBoard`, gom về nhóm cấp 1; tài chính tách thành Ngân hàng / Bảo hiểm / Bất động sản / Dịch vụ tài chính. Không có mã ICB thì dùng danh sách tham chiếu (tái sử dụng từ invest-system-phase2).

- % ngành = Σ vốn hóaᵢ·%ᵢ / Σ vốn hóaᵢ, với vốn hóaᵢ = số CP niêm yếtᵢ × giá tham chiếuᵢ.
- Đóng góp (điểm) = vốn hóaᵢ / Σ vốn hóa rổ × %ᵢ/100 × chỉ số phiên trước.

**Giới hạn:** vốn hóa chưa điều chỉnh free-float và giới hạn tỷ trọng của VN30, nên đóng góp là **ước lượng**. Ví dụ phiên 19/11/2026 lúc 11:29: tổng ước lượng −19,0 điểm so với thay đổi thật −16,3; nhóm Bất động sản (họ Vingroup) bị phóng đại nhiều nhất.

## 12. Khối lượng tương đối theo thời điểm (RVOL) — `finance/rvol.py`

Lịch sử dùng cho profile và KL ngày dự phòng được lọc theo từng mã/phiên theo **giờ khớp lệnh**: có khối lượng khớp trong 5 phút sau 09:15 (hết ATO), tới ít nhất 14:44 (ATC kết thúc 14:45), khối lượng ngày dương và không có khoảng trống quá 5 phút giao dịch liên tiếp trong khoảng đó; giao dịch thỏa thuận lác đác sau 14:45 không được tính. Đây là tiêu chí độ phủ bảo thủ, không phải xác nhận dữ liệu của sàn đã đầy đủ. Cần ít nhất 3 phiên đạt tiêu chí cho mỗi mã; nếu không đủ thì không dùng các đoạn ghi dở như KL cả ngày. Độ dài thanh RVOL được tính bằng phút giao dịch, loại thời gian nghỉ trưa.

RVOL thanh = KL khớp trong thanh / (KL TB 20 phiên × (f(m₁) − f(m₀))), với f(m) là tỷ lệ khối lượng cả ngày thường đã khớp tới phút giao dịch thứ m. Nhờ vậy so với **cùng thời điểm** của các phiên trước, không so với cả ngày. KL TB 20 phiên lấy từ REST ngày của SSI (`neopulse refdata --refresh`, dự phòng Vietcap qua vnstock). f(m) dùng đường thực nghiệm khi đã có ít nhất 3 phiên ghi trọn, nếu không thì **giả định phân bổ đều theo phút** (bỏ qua hình chữ U và khối lượng ATC: biết là thô).

Cảnh báo "Khối lượng tăng bất thường" dùng RVOL thanh ≥ 3 (CAO khi ≥ 6) khi có KL TB 20 phiên; nếu không có thì quay về z bền vững của log khối lượng trong phiên. Lý do: z trong phiên cần ít nhất 20 thanh lịch sử và không biết mức "bình thường" của chính mã đó. Trên dữ liệu thật 19/11/2026 (10:59–11:29, 929 thanh, 30 mã), quy tắc z cũ cho 0 cảnh báo khối lượng, quy tắc RVOL cho 12 (1,29% số thanh, 2 mức CAO). IC và tần suất cảnh báo trên các phiên thật: xem [`report/data/SUMMARY.md`](../report/data/SUMMARY.md) (sinh bằng `neopulse report-data`).

**Thay đổi 25/11/2026:** trước đây tiêu chí là "có dữ liệu trong 5 phút đầu (09:05), tới 14:59". Đối chiếu dữ liệu SSI thật cho thấy khối lượng khớp chỉ có từ 09:15 và sổ lệnh gần như đứng yên sau 14:45, nên không phiên thật nào đạt và RVOL luôn rơi về đường phân bổ đều. Mốc được đổi thành 09:15–14:45 (`MATCH_START_MIN`, `MATCH_END_MIN` trong `finance/rvol.py`); công thức RVOL không đổi.
