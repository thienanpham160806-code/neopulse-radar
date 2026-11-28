# Câu hỏi bảo vệ có thể gặp

Mỗi câu trả lời dẫn tới chỗ trong mã. Số liệu lấy từ [report/data/SUMMARY.md](data/SUMMARY.md), sinh ngày 28/11/2026 từ 6 phiên SSI thật.

## Chỉ báo sổ lệnh

**OBI là gì, vì sao dùng 3 mức?**
- OBI₃ = (ΣKL mua − ΣKL bán) / (ΣKL mua + ΣKL bán) trên 3 mức giá tốt nhất ([finance/microstructure.py](../src/neopulse/finance/microstructure.py), `add_book_metrics`).
- Nằm trong [−1, 1]; dương là bên mua dày hơn. |OBI| = 0,6 nghĩa là một bên dày gấp 4 lần bên kia: (4 − 1)/(4 + 1) = 0,6.
- Dùng 3 mức vì nguồn chỉ có 3 mức. Vì vậy OBI là xấp xỉ, không thấy lệnh ẩn hay lệnh ngoài 3 mức.
- Có thêm OBI₁ (chỉ mức 1) và OBI_w (trọng số 1, 1/2, 1/3) để so sánh trong kiểm chứng.

**Microprice khác giá giữa thế nào?**
- Giá giữa = (mua₁ + bán₁)/2.
- Microprice = (bán₁·KLmua₁ + mua₁·KLbán₁)/(KLmua₁ + KLbán₁) (Stoikov, 2018). Nó nghiêng về phía có khối lượng **mỏng hơn**: bên mua dày thì giá dễ đi lên, nên microprice gần giá bán hơn.
- `micro_dev_bps` = (microprice − giá giữa)/giá giữa × 10⁴.

## Phát hiện bất thường

**Robust z và hằng số 0,6745?**
- z = 0,6745·(x − median)/MAD. Median và MAD tính trên 60 thanh **trước** t của chính mã, tối thiểu 20 thanh ([analytics/anomaly.py](../src/neopulse/analytics/anomaly.py)).
- 0,6745 là phân vị 75% của phân phối chuẩn. Với dữ liệu chuẩn thì MAD ≈ 0,6745σ, nên z quy về thang của z chuẩn.
- Ngưỡng 3,5 theo Iglewicz & Hoaglin (1993).
- MAD tính quanh median của đúng cửa sổ đó. Bản trước 28/11 tính sai, đã sửa và có test đối chiếu tính tay (`test_robust_z_matches_hand_computed_modified_z`).

**Vì sao median/MAD mà không phải trung bình/độ lệch chuẩn?**
- Chính điểm bất thường làm phình độ lệch chuẩn, nên che lấp nhau.
- Median và MAD ít nhạy với ngoại lai hơn nhiều so với trung bình và độ lệch chuẩn. Điểm gãy gần 50% nghĩa là phải làm hỏng gần một nửa số điểm mới kéo được ước lượng đi xa tùy ý. Không có nghĩa ước lượng bất biến khi có ngoại lai, và ở đúng mức 50% thì không còn bảo đảm.

**Sao spread và khối ngoại không dùng z?**
- Trên dữ liệu thật, 79% thanh có spread đúng 1 bước giá, và 42% thanh có khối ngoại ròng bằng 0. Khi đó MAD ≈ 0, z bão hòa ở trần 50 và mất ý nghĩa.
- Spread nay đo bằng **số bước giá HOSE**, đếm trên lưới giá kể cả khi vắt qua mốc 10.000/50.000. Báo khi ≥ 3 bước và vượt phân vị 95% của chính mã.
- Khối ngoại xét trên 3 thanh có dữ liệu gần nhất. Khi mất tin, cửa sổ này có thể dài hơn 3 phút. Lý do: dữ liệu room khối ngoại về theo cục khoảng 1 lần/phút, nên 12% thanh đơn lẻ có giá trị ròng lớn hơn giá trị khớp của chính thanh đó.
- Ngưỡng chọn chỉ trên 4 phiên trong mẫu, theo ngân sách cảnh báo ([docs/calibration_log.md](../docs/calibration_log.md)).

**Chọn ngưỡng như vậy có quá khớp không?**
- Có rủi ro. Cách giảm rủi ro: chọn tham số chỉ trên 19, 20, 23, 25/11; ghi mọi lần thử kể cả phương án bị loại; báo kết quả ngoài mẫu như nó là.
- Ngoài mẫu (26–27/11), CAO là 1,67 cảnh báo trên một mã một phiên, **vượt** ngân sách 1. Không chỉnh lại theo kết quả đó.

## Điểm nhịp

**Điểm nhịp tính thế nào, vì sao trọng số là thiết kế?**
- Điểm = 50 + 50·(Σ wᵢcᵢ)/(Σ wᵢ), cả hai tổng chỉ lấy trên các thành phần có dữ liệu; cᵢ ∈ [−1, 1] ([finance/pulse.py](../src/neopulse/finance/pulse.py)). Đủ 5 thành phần thì mẫu số bằng 1.
- Trọng số gốc: độ rộng 30%, động lượng 25%, sổ lệnh 20%, khối ngoại 15%, thanh khoản 10%.
- Dưới 50% trọng số có dữ liệu thì không kết luận.
- Trọng số **không ước lượng từ dữ liệu**. Với vài phiên mà ước lượng thì chắc chắn quá khớp, và điểm này mô tả hiện trạng chứ không nhằm dự báo.
- `sensitivity()` xáo mỗi trọng số ±50% và báo khoảng điểm cùng tỷ lệ giữ nguyên nhãn, hiển thị trên giao diện.

## Kiểm chứng IC

**IC là gì?**
- Tại mỗi thanh 1 phút, tính tương quan hạng Spearman giữa tín hiệu cuối thanh t và lợi suất giá giữa từ t đến t+h của các mã trong rổ. Sau đó lấy trung bình qua các thanh, kiểu Fama–MacBeth ([analytics/validation.py](../src/neopulse/analytics/validation.py)).

**Vì sao t bị thổi phồng?**
- t thường = trung bình/(độ lệch chuẩn/√n), coi các thanh độc lập. Nhưng IC của các thanh liền kề tự tương quan, và với h = 5 thì lợi suất của các thanh chồng lên nhau.
- Vì vậy có thêm t Newey–West (độ trễ L = max(h, 4(n/100)^(2/9))) và t theo phiên (mỗi phiên là một quan sát, chỉ báo khi có ít nhất 3 phiên).
- NW không phải lúc nào cũng làm |t| giảm. Ví dụ obi3, h = 1, trong mẫu: t thường 23,2, t NW 25,8. Với h = 5, t NW giảm từ 26,5 xuống 15,6.

**IC cao mà sao không khai thác được?**
- Ngoài mẫu, IC từ 0,17 đến 0,29 và t NW từ 13,9 đến 30,6, nhưng Q5−Q1 trước chi phí chỉ 6–16 bps.
- Benchmark giả định chỉ chân mua Q5 (mua ở giá bán, bán ở giá mua sau h thanh, phí giả định 0,15%/chiều) cho −63 đến −48 bps; 0/8 cặp dương. Riêng độ chênh giá mua-bán đã làm còn −33 đến −18 bps.
- Giả thuyết (chưa kiểm riêng): lợi suất đo trên giá giữa. Khi một phía mỏng, mức tốt nhất phía đó bị ăn hết và giá giữa nhích khoảng nửa bước giá. Phần này có thật về thống kê, nhưng muốn hưởng thì phải trả cả độ chênh mua-bán (thường 1 bước) cộng phí.

**Placebo cho thấy gì?**
- Xáo tín hiệu giữa các mã trong cùng thanh (20 lần): |IC| ≤ 0,002. Đường tính không tự tạo ra liên hệ.
- Dùng tín hiệu cũ của thanh t−h: IC 0,04–0,09. Có thể vì OBI bền theo thời gian.
- Placebo không chứng minh loại trừ mọi dạng rò rỉ.

## Chống nhìn trước dữ liệu

**Chống nhìn trước ở đâu?**
- Ngưỡng z: cửa sổ dùng `shift(1)`, chỉ quan sát trước t (`test_robust_z_has_no_lookahead`).
- Phân vị riêng của mã (spread, khối ngoại): chỉ dùng các thanh trước trong phiên (`_prior_quantile`).
- Thanh 1 phút lấy **trạng thái cuối thanh**. Giá giữa và tín hiệu cùng **một ảnh chụp** sổ lệnh (`last_snapshot`, `test_forward_return_uses_mid_of_same_snapshot_as_signal`).
- Lợi suất tương lai không vượt ranh giới phiên.
- Tách mẫu theo thời gian, không xáo trộn. Bảng "chỉ phiên đủ" dùng lại đúng cách chia trên mọi phiên.
- `build_view(as_of=…)`: cảnh báo quá khứ không đổi khi có thêm dữ liệu (test end-to-end).
- RVOL so với khối lượng **các phiên trước** cùng khung giờ.

## Dữ liệu và kết nối

**Xử lý tin lặp, tin muộn, mất kết nối thế nào?** ([data/ingest.py](../src/neopulse/data/ingest.py), [neo_api/ws.py](../src/neopulse/neo_api/ws.py))
- Tin lặp nguyên văn bị bỏ (`n_duplicates`). Khóa duy nhất (mã, ts, nguồn) trong SQLite.
- Tin đến muộn hoặc sai thứ tự: khối lượng lũy kế giảm trong cùng phiên thì bị loại và ghi `late_or_out_of_order` vào `quality_log`.
- Nhiều khung tin cùng mili-giây (trade/quote/room) thì bản sau thay bản trước.
- Mất kết nối: không nhận khung tin quá 60 giây (SSI; lớp NEO là 45 giây) thì coi là treo. Nối lại theo cấp số nhân có nhiễu, tối đa 60 giây.
- `scripts/run_record_session.ps1` (do lịch Windows khởi động) chạy lại tiến trình Python của bộ ghi sau 30 giây nếu nó dừng sớm trong giờ phiên. Task Scheduler không tự khởi động lại chính script này.
- Ngày 20/11 có 121 lần nối lại, 96 trong số đó là lỗi DNS/kết nối từ 12:46 đến 13:58, nghi do mạng cục bộ ([docs/data_quality.md](../docs/data_quality.md)).
- Web báo độ trễ khi dữ liệu dừng. Worker cloud nhắn chủ dự án khi 09:05 chưa có dữ liệu hoặc im lặng quá 5 phút.

**Vì sao đổi NEO sang SSI?**
- NEO đăng nhập `/auth/token` được, nhưng mọi API dữ liệu trả `NEOINP000401` vì cần đăng ký IP cố định. Mạng ký túc xá dùng IP động ([docs/neo_api_notes.md](../docs/neo_api_notes.md)).
- Giảng viên đồng ý dùng SSI FastConnect. Theo hướng dẫn của giảng viên, dùng nguồn nào cũng được miễn đáp ứng đủ yêu cầu của đề.
- `ssi/adapter.py` đổi khung tin SSI về cùng lược đồ với NEO, nên phần còn lại dùng chung. Lớp NEO vẫn có, kiểm thử bằng máy chủ giả.

**Dữ liệu thiếu thì sao?**
- Có 6 phiên, trong đó 3 phiên đủ (25–27/11). Phiên đủ nghĩa là ≥ 90% mã ghi trọn giờ khớp lệnh.
- Kết luận ghi rõ chỉ có 2 phiên ngoài mẫu. Thiếu dữ liệu thì hiện "chưa có", không suy diễn.

## Bảo mật và an toàn

**Bảo mật khóa thế nào?**
- Khóa chỉ trong `.env` (đã `.gitignore`). Token chỉ giữ trong bộ nhớ.
- Log qua `RedactFilter` che JWT, Bearer, mật khẩu ([logging_setup.py](../src/neopulse/logging_setup.py)). `neopulse check` chỉ in đã/chưa điền.
- Khóa SSI/NEO không lên Vercel. Web chỉ nhận JSON chỉ báo tổng hợp, không có giá/sổ lệnh từng tick.
- Bí mật của bot nằm trong biến môi trường Vercel. Đăng ký người dùng mã hóa Fernet trong Redis.

**Có đặt lệnh được không?**
- Không. Client chặn cứng đường dẫn lệnh (`FORBIDDEN_PATH_PREFIXES`, `NeoSafetyError` ở [neo_api/client.py](../src/neopulse/neo_api/client.py) và [ssi/client.py](../src/neopulse/ssi/client.py)), có test.
- Không có khuyến nghị MUA/BÁN. Dữ liệu mô phỏng luôn gắn nhãn MÔ PHỎNG.

**Có dùng mô hình ngôn ngữ không?**
- Tùy chọn, mặc định tắt.
- Nếu bật: chỉ gửi bảng số; đầu ra bị loại nếu có con số không nằm trong bảng hoặc có ngôn ngữ khuyến nghị, khi đó quay về mẫu câu ([analytics/explain.py](../src/neopulse/analytics/explain.py)). Giao diện ghi nguồn diễn giải.
