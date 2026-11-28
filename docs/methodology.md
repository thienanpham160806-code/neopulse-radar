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
- MAD là median của |x_j − median| với j chạy trong **cùng** cửa sổ 60 thanh trước t, và median cũng là median của cửa sổ đó.
  - Bản trước 28/11/2026 lấy median trượt lần hai của các độ lệch so với những median khác nhau. Cách đó sai công thức và cần gấp đôi số quan sát mới ra z.
  - Đã sửa theo nghiệm thu CX-015, có test đối chiếu tính tay.

## 7. Cảnh báo — `analytics/alerts.py`

| Quy tắc | Điều kiện | Cơ sở |
|---|---|---|
| Khối lượng tăng bất thường | RVOL thanh ≥ 5 (có KL nền cùng khung giờ); không có KL nền thì z_vol ≥ 3,5. Bỏ thanh 09:15 (ATO) và 14:45 (ATC) | ngân sách cảnh báo (RVOL); Iglewicz & Hoaglin (z) |
| Độ chênh giá mua-bán giãn rộng | spread tính bằng **số bước giá HOSE**, đếm trên lưới giá kể cả khi vắt qua mốc 10.000/50.000, ≥ 3 **và vượt** phân vị 95% của chính mã trên các thanh trước trong phiên; chưa đủ 20 thanh trước thì chỉ dùng sàn 3 bước | spread rời rạc theo bước giá, MAD ≈ 0 nên không dùng z |
| Giá biến động đột ngột | \|z_ret\| ≥ 3,5 | thống kê |
| Khối ngoại giao dịch bất thường | trên cửa sổ 3 thanh: NN ròng ≠ 0, chiếm ≥ 30% giá trị khớp, và \|ròng\| ≥ phân vị 99% các cửa sổ có NN trước đó của chính mã; chưa đủ 20 cửa sổ thì không báo | phân phối dồn về 0; room NN về theo cục ~1 lần/phút |
| Mất cân bằng sổ lệnh kéo dài | \|OBI₃\| ≥ 0,6 cùng dấu 5 thanh liền nhau (mất thanh hoặc qua nghỉ trưa thì đếm lại) | 0,6 ⇔ một bên dày gấp 4 lần bên kia; 5 thanh theo ngân sách |
| Sát trần/sàn | \|vị trí biên độ\| ≥ 0,9 | quy tắc biên độ của sàn |

Bước giá cổ phiếu HOSE:
- dưới 10.000 đồng: 10 đồng;
- 10.000–49.950 đồng: 50 đồng;
- từ 50.000 đồng: 100 đồng.

Nguồn: HOSE, *Quy định cần biết khi giao dịch chứng khoán trên HOSE*, T2/2026. Số bước giữa giá mua và giá bán đếm theo từng vùng: 9.990 → 10.050 là 2 bước.

**Mức ưu tiên:**
- **CAO** khi ≥ 2 quy tắc cùng nổ trên một mã trong một thanh, hoặc khi giá trị của quy tắc khối lượng/giá (RVOL hoặc z) ≥ 10.
- Độ chênh giá và khối ngoại đo bằng đơn vị riêng (bước giá, tỷ trọng) nên chỉ CAO khi đi cùng quy tắc khác.
- Sổ lệnh và sát trần/sàn là **THẤP** khi đứng một mình; còn lại **TRUNG BÌNH**.

Thời gian nguội 10 thanh cho mỗi cặp (mã, quy tắc). Khóa chống lặp khi lưu/gửi.

**Hiệu chỉnh ngày 28/11/2026** (chi tiết, kể cả phương án bị loại: [calibration_log.md](calibration_log.md)):
- Chỉ chọn tham số trên 4 phiên trong mẫu (19, 20, 23, 25/11); 26-27/11 chỉ để báo cáo.
- Ngân sách: CAO ≤ 1 và mỗi quy tắc ≤ 2 trên một mã trong một phiên.
- Quy tắc chọn: lấy cấu hình ít chặt nhất đạt ngân sách, với điều kiện độ thu hồi trên sự kiện mô phỏng cài sẵn vẫn ≥ 0,8.
- Kết quả: tổng cảnh báo mỗi phiên giảm từ 96–644 xuống 90–371. CAO trong mẫu 0,90/mã/phiên.
- **Ngoài mẫu CAO là 1,67/mã/phiên, vượt ngân sách.** Hai phiên 26-27/11 sôi động hơn các phiên dùng để chọn.
- Giữ ngưỡng sát trần/sàn 0,9: trong các phiên đầu, |vị trí biên độ| lớn nhất chỉ 0,86, nên quy tắc không báo không phải do lỗi.

## 8. Xếp hạng đa yếu tố — `analytics/ranking.py`

z-score mặt cắt ngang trong rổ, cắt đuôi ±3: động lượng (30%), OBI₃ (25%), NN ròng/tổng (20%), log giá trị khớp (15%), −spread (10%). Mã thiếu một yếu tố được chuẩn hóa lại trọng số. Chỉ có nghĩa tương đối tại thời điểm tính.

## 9. Kiểm chứng — `analytics/validation.py`

**Câu hỏi:** tín hiệu sổ lệnh cuối thanh t có liên hệ với lợi suất giá giữa t → t+h không?

**Chống nhìn trước:**
- Tín hiệu chỉ dùng thông tin đến t; lợi suất tương lai không vượt ranh giới phiên.
- Giá giữa tại t dùng tính lợi suất và các tín hiệu tại t lấy **cùng một ảnh chụp** sổ lệnh: ảnh cuối thanh có sổ lệnh hợp lệ (CX-016). Có test.

**Tính IC:** IC = tương quan hạng Spearman theo mặt cắt ngang từng thanh, lấy trung bình qua các thanh (kiểu Fama–MacBeth, 1973).

**Ba thống kê t**, từ lạc quan nhất đến thận trọng nhất:
- `t` = trung bình/(độ lệch chuẩn/√số thanh). Coi các thanh là độc lập, nên **bị thổi phồng**.
- `t NW`: sai số chuẩn Newey–West (1987), trọng số Bartlett, độ trễ L = max(h, ⌊4(n/100)^(2/9)⌋) (Newey & West, 1994). Tự hiệp phương sai chỉ tính trong cùng phiên.
- `t phiên`: IC trung bình từng phiên là một quan sát, n = số phiên. Với 2–4 phiên, thống kê này rất yếu.

**Chia mẫu:** tách theo thời gian. 60% phiên đầu (19, 20, 23, 25/11) là trong mẫu, phần còn lại (26, 27/11) là ngoài mẫu. Không xáo trộn. Bảng "chỉ phiên đủ" dùng lại đúng cách chia này (CX-017).

**Chi phí:** `Q5−Q1` là chênh lợi suất giá giữa của nhóm 20% tín hiệu cao nhất trừ thấp nhất, **trước chi phí**.
- `Q5−Q1 ròng`: mua Q5 ở giá bán tốt nhất tại t, bán ở giá mua tốt nhất tại t+h; bán khống Q1 ở giá mua, mua lại ở giá bán. Mỗi chiều trừ phí **giả định** 0,15%.
- `Q5 ròng`: benchmark **giả định** chỉ chân mua (không bán khống). Chưa kiểm khả năng khớp ở mức giá 1, tồn kho để bán sau h thanh hay quy định thanh toán, nên không phải bằng chứng một giao dịch thực hiện được.
- Phạm vi: chỉ cổ phiếu trong rổ. HĐTL 41I1GC000 có bước giá và chi phí khác nên không đưa vào mặt cắt kiểm chứng.

**Placebo:** xáo tín hiệu giữa các mã trong cùng thanh (20 lần), và dùng tín hiệu cũ của thanh t−h. IC placebo gần 0 nghĩa là đường tính không tự tạo liên hệ.

**Cách đọc có trách nhiệm.**
- Dưới 5 phiên, kết quả chỉ minh họa.
- Trên dữ liệu mô phỏng, tín hiệu được cài sẵn; kết quả chỉ xác nhận mã tính đúng.
- Kết quả dữ liệu thật và kết luận nằm trong [report/data/SUMMARY.md](../report/data/SUMMARY.md).

## 10. Diễn giải bằng ngôn ngữ — `analytics/explain.py`

Mặc định dùng mẫu câu xác định dựng từ số liệu. Nếu bật mô hình ngôn ngữ: chỉ gửi bảng số liệu; đầu ra bị loại nếu chứa bất kỳ con số nào không có trong bảng, hoặc chứa ngôn ngữ khuyến nghị mua/bán — khi đó quay về mẫu câu. Giao diện luôn ghi nguồn diễn giải.

## Tài liệu tham khảo

*Đã đối chiếu tác giả, năm, tập, số và trang với IDEAS/RePEc, arXiv và danh mục ASQ ngày 25/11/2026; hai bài Newey–West đối chiếu Crossref ngày 28/11/2026.*

- Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*, 5(1), 31–56.
- Chordia, T., Roll, R., & Subrahmanyam, A. (2002). Order imbalance, liquidity, and market returns. *Journal of Financial Economics*, 65(1), 111–130. https://doi.org/10.1016/S0304-405X(02)00136-8
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88. https://doi.org/10.1093/jjfinec/nbt003
- Fama, E. F., & MacBeth, J. D. (1973). Risk, return, and equilibrium: Empirical tests. *Journal of Political Economy*, 81(3), 607–636. https://doi.org/10.1086/260061
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708. https://doi.org/10.2307/1913610
- Newey, W. K., & West, K. D. (1994). Automatic lag selection in covariance matrix estimation. *Review of Economic Studies*, 61(4), 631–653. https://doi.org/10.2307/2297912
- HOSE (2026). *Quy định cần biết khi giao dịch chứng khoán trên HOSE* (T2/2026). https://staticfile.hsx.vn/Uploads/UploadDocuments/2453338/HTGD_Quy%20dinh%20can%20biet%20khi%20GDCK%20tren%20HOSE_T2.2026.pdf
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
