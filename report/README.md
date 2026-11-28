# Báo cáo cuối kỳ — tệp nộp và hướng dẫn theo Mục 12 của đề

Tên tệp nộp: `K244141653_PhamNgocThienAn_BaoCao.pdf` · mã nguồn: `K244141653_PhamNgocThienAn_NEOAPI_FinTech.zip` · video: `K244141653_PhamNgocThienAn_Demo.mp4`.
Khuyến nghị 8–12 trang A4, không tính phụ lục.

## Tệp đã chuẩn bị

- [Báo cáo PDF](K244141653_PhamNgocThienAn_BaoCao.pdf) và [bản Word để chỉnh sửa](K244141653_PhamNgocThienAn_BaoCao.docx).
- [Video trình diễn](video/K244141653_PhamNgocThienAn_Demo.mp4), thời lượng 9 phút 26 giây, kèm [phụ đề tiếng Việt](video/K244141653_PhamNgocThienAn_Demo.srt).
- [Số liệu tổng hợp](data/SUMMARY.md), [câu hỏi bảo vệ](defense_qa.md) và [ghi chú video](video/README.md).

Dàn ý dưới đây chỉ ra **lấy nội dung ở đâu trong repo**. Báo cáo đã có số liệu, ảnh và phần công khai việc dùng AI hỗ trợ. Tác giả cần đọc lại, xác nhận thông tin cá nhân và giải thích được mọi công thức, quyết định thiết kế khi bảo vệ. Mục triển khai snapshot ban đầu được giữ như lịch sử; kiến trúc hiện tại có Ably và được mô tả ở phần bổ sung bên dưới cùng `docs/web_architecture.md`.

| # | Phần | Viết gì | Nguồn trong repo |
|---|---|---|---|
| 1 | Tóm tắt điều hành (½ trang) | vấn đề · người dùng · giải pháp · dữ liệu SSI FastConnect (thay NEO API; giảng viên đã đồng ý, đề bài cho phép dùng nguồn nào cũng được miễn đáp ứng đủ yêu cầu) · phương pháp · kết quả chính | README mục "Kết quả chính", `report/data/SUMMARY.md` |
| 2 | Vấn đề và nhu cầu người dùng | 3 câu hỏi nội phiên; vì sao bảng giá chưa trả lời được; khác gì công cụ sẵn có | README phần mở đầu, `PRODUCT.md` |
| 3 | Thiết kế sản phẩm | sơ đồ kiến trúc; nhiệm vụ từng lớp; lý do chọn SQLite, tách bộ ghi, web Next.js + Ably, bot Telegram | `docs/architecture.md`, `docs/web_architecture.md` |
| 4 | Dữ liệu | SSI FastConnect (nguồn chính): endpoint, kênh, tần suất, làm sạch; vì sao không dùng được NEO (IP cố định) và việc được chấp thuận thay thế; số phiên, bản ghi, độ phủ, khoảng trống | `docs/ssi_notes.md`, `docs/neo_api_notes.md`, `docs/data_dictionary.md`, `report/data/SUMMARY.md` (bảng "Từng phiên") |
| 5 | Phương pháp | công thức, giả định, cơ sở ngưỡng, trọng số và độ nhạy | `docs/methodology.md` |
| 6 | Triển khai | bản web 5 tab (ảnh `docs/img/final/`), bot Telegram, dashboard Streamlit cục bộ; trạng thái lỗi/dữ liệu cũ | web production, `docs/test_plan.md` §2 |
| 7 | Kiểm thử và kết quả | số ca pytest/vitest (đếm bằng lệnh); đối chiếu bảng giá; IC trong/ngoài mẫu; tần suất cảnh báo theo mức và quy tắc; lỗi đã thử | `report/data/SUMMARY.md`, `docs/test_plan.md` |
| 8 | Hạn chế và sử dụng có trách nhiệm | ít phiên, phiên ghi thiếu, 3 mức giá, thời điểm nhận, rổ hữu hạn, trọng số thiết kế, không dự báo, bảo mật | README mục "Hạn chế" và "Bảo mật" |
| 9 | Hướng phát triển | lịch nghỉ lễ; bộ ghi chạy trên máy chủ (`deploy/collector/`); mô hình hóa tác động giá; thêm phiên để kiểm chứng | README mục "Hạn chế" |
| 10 | Kết luận | giá trị tạo ra; bài học kỹ thuật/tài chính | — |
| PL | Phụ lục | từ điển dữ liệu, công thức chi tiết, kết quả `pytest`, hướng dẫn cài đặt, đường dẫn mã/video | `docs/` |

## Phần "Triển khai sản phẩm" (đề cho tự chọn nền tảng triển khai)

Nội dung nên viết (lấy từ `docs/web_architecture.md`):
- **Kiến trúc:** máy tác giả (`record` → SQLite → `neopulse publish-static`) → `web/public/data/*.json` → `vercel --prod` → web Next.js trên Vercel. Mọi chỉ báo do Python tính (`build_view`), web chỉ hiển thị.
- **Vì sao không đưa Streamlit lên Vercel:** Vercel chạy hàm serverless ngắn hạn, không giữ tiến trình Python sống lâu và WebSocket hai chiều; SQLite không có chỗ lưu bền. Streamlit vẫn dùng khi chạy cục bộ.
- **Vì sao bộ ghi ở máy tác giả:** giữ kết nối WebSocket SSI nhiều giờ và giữ khóa API; khóa không bao giờ lên đám mây.
- **Vì sao chọn snapshot tĩnh thay cho đẩy liên tục (Vercel Blob):**
  1. *Hạn mức Hobby:* Blob chỉ có 2.000 thao tác nâng cao/tháng; đẩy mỗi 20 giây hết sau 2–3 phiên.
  2. *Bảo mật dữ liệu SSI:* dữ liệu chỉ rời máy khi tác giả chủ động triển khai; không có URL Blob công khai chứa dữ liệu thị trường; tệp thật bị `.gitignore`; web công khai chỉ báo tổng hợp, không cần mật khẩu.
  3. *Độ trễ trung thực:* đồ án là phân tích cuối phiên; web ghi rõ "Snapshot lúc …, cách đây …, không phải thời gian thực" thay vì ra vẻ gần-thời-gian-thực.
  Đường Blob (`neopulse publish`) vẫn còn trong mã như tùy chọn, tốn hạn mức, chưa chạy với Blob thật.
- **Trạng thái dữ liệu minh bạch:** nguồn, giờ snapshot, "cách đây X", chấm màu (snapshot cuối phiên không bị báo đỏ chỉ vì cũ), số mã tính/loại, nhãn MÔ PHỎNG.
- **Bảo mật:** khóa SSI chỉ ở `.env` máy ghi; Vercel giữ ABLY_API_KEY dạng Secret và chỉ cấp token subscribe-only; web không có đăng nhập; chỉ xuất chỉ báo tổng hợp, không xuất bảng giá/sổ lệnh thô.
- **Ảnh minh họa:** bản web cuối dùng dữ liệu thật ở `docs/img/final/`; ảnh trước/sau ở `docs/img/ux/`; ảnh dashboard `docs/img/dashboard_*_sim.png` là MÔ PHỎNG và phải ghi rõ trong chú thích.

## Triển khai sản phẩm: bổ sung về giao diện và thời gian thực (19/11/2026)

- **Kiến trúc thời gian thực:** `record` (`--flush-every 1`) ghi SQLite; `live-relay` đọc chỉ-đọc và phát tin tổng hợp lên Ably kênh `neopulse:live` (tick khoảng 1 giây khi có thay đổi, pulse khoảng 10 giây, status); trình duyệt nhận qua SSE với token chỉ subscribe, hạn 15 phút. Snapshot tĩnh là dự phòng khi mất tin quá 60 giây, ngoài giờ giao dịch hoặc khi lỗi.
- **Hạn mức Ably Free:** 6.000.000 tin/tháng, tính cả tin giao tới người xem. Ước tính một phiên ≈ 17.600 tin × (1 + 5 người xem) ≈ 106.000; 22 phiên ≈ 2,3 triệu (≈ 39%). Bộ đếm `out/ably_usage.json` tự giãn nhịp khi vượt 70%.
- **Lý do chọn hướng thiết kế và các phương án đã cân nhắc:** xem `docs/web_architecture.md` mục "Thiết kế giao diện" (bảng điểm ba hướng A/B/C, lý do chọn B kết hợp mobile của C, Lighthouse trước và sau).
- **Thay đổi bảo mật theo quyết định của tác giả:** bỏ mật khẩu trang (commit `1cad109`). Trang và chỉ báo tổng hợp công khai; khóa Ably vẫn chỉ ở máy chủ, token phía trình duyệt chỉ có quyền subscribe. Không xuất sổ lệnh thô.

## Tái sử dụng mã nguồn (ghi trong báo cáo, mục Triển khai hoặc Phụ lục)

Có tái sử dụng có chọn lọc từ dự án cá nhân trước của tác giả (invest-system-phase2): font Be Vietnam Pro (SIL OFL), các hàm định dạng số/tiền/ngày (đã bỏ phần màu khuyến nghị mua/bán), nút sáng/tối, danh sách mã tham chiếu cho phân ngành dự phòng, và cách gọi dự phòng Vietcap qua vnstock. Bảng chi tiết (tệp, nguồn, đã sửa gì) ở README mục "Tái sử dụng từ dự án cũ của tác giả". Không dùng mã của đồ án nhóm Kumo_VN_bot. Tính năng mới dựa trên phần tái sử dụng: **Ngành trong phiên** (độ rộng, % bình quân vốn hóa, đóng góp điểm ước lượng) và **RVOL theo thời điểm** (đầu vào cho cảnh báo khối lượng) - xem docs/methodology.md mục 11-12, kể cả giới hạn (đóng góp lệch do chưa free-float; RVOL cần ít nhất 3 phiên ghi trọn giờ khớp lệnh mới dùng đường phân bổ thực nghiệm).

## Checklist hoàn thiện trước khi nộp (30/11/2026)

- [x] Ghi thêm phiên 26/11 và 27/11: đã có trong `report/data/SUMMARY.md` (6 phiên, 3 phiên đủ).
- [x] `report/data/SUMMARY.md` sinh lại bằng `neopulse report-data` sau hiệu chỉnh (28/11/2026) và đã commit.
- [ ] Phần 1 và 4 của báo cáo: nêu việc đã xin ý kiến giảng viên dùng SSI thay NEO; điền ngày và hình thức chấp thuận vào chỗ `[ngày]`, `[hình thức]` trong README.
- [x] Ảnh dữ liệu thật cuối ở `docs/img/final/` (desktop và điện thoại, phiên 27/11); ảnh `_sim` chỉ dùng minh họa và ghi rõ "mô phỏng".
- [x] Bảng IC và tần suất cảnh báo trong báo cáo khớp `report/data/SUMMARY.md`; đã nêu số phiên trong/ngoài mẫu và giới hạn.
- [ ] Ảnh đối chiếu 3–5 mã với bảng giá công khai cùng thời điểm; ảnh thử lỗi (dừng bộ ghi, web báo dữ liệu cũ).
- [x] Báo cáo đã ghi việc dùng công cụ AI hỗ trợ lập trình và biên tập (Mục 13 của đề).

## Kịch bản tham khảo (5–7 phút; bản video hiện có dài 9 phút 26 giây)

1. **Vấn đề và người dùng** (30 giây): nhà đầu tư cá nhân cần biết trong phiên thị trường đang thế nào, vì sao, mã nào bất thường.
2. **Dữ liệu** (1 phút): `neopulse check` (chỉ in trạng thái khóa), log `out/record_YYYYMMDD.log` của phiên đang ghi; nói ngắn vì sao dùng SSI thay NEO và đã được chấp thuận.
3. **Bản web** (2–3 phút), https://neopulse-radar.vercel.app/thi-truong: Tổng quan (điểm nhịp, độ rộng, trạng thái dữ liệu), Vì sao? (ngành, khối ngoại, phái sinh), Bất thường (lọc mức, đọc căn cứ một cảnh báo), Chi tiết mã (sổ lệnh, trượt giá), Phương pháp & kiểm chứng. Mở một trang doanh nghiệp.
4. **Bot Telegram** (1 phút): `/thitruong`, `/canhbao`, bấm vào mã để mở thẻ mã, `/caidat` (bản tin 08:30 và 15:00).
5. **Độ tin cậy** (1 phút): bảng từng phiên và IC trong `report/data/SUMMARY.md`; nói rõ ít phiên, phiên ghi thiếu và vì sao IC chỉ mang tính minh họa.
6. **Kiểm thử và an toàn** (30 giây): `python -m pytest -q` và `npm test` chạy xanh; `.env.example`, chặn endpoint giao dịch, web không chứa sổ lệnh thô.

## Kênh thông báo: bot Telegram (25/11/2026)

Bot `@neopulse_warningbot` là kênh đọc nhanh, website vẫn là nơi phân tích chi tiết. Bot chia lệnh thành ba nhóm, mỗi lệnh một việc:
- **Xem ngay:** nhịp thị trường, cảnh báo trong phiên, thẻ một mã.
- **Cá nhân:** mã theo dõi, bật/tắt từng loại tin.
- **Khác:** trạng thái dữ liệu, hướng dẫn, hủy đăng ký.

Số liệu đọc từ cùng payload với website (`/api/data`), nên bot và web luôn khớp. Bot không tính lại chỉ báo.

Mỗi tin theo một khuôn: tiêu đề có icon và giờ VN → dòng chính → căn cứ (ngưỡng, điểm z diễn giải bằng lời) → bối cảnh → nút mở đúng trang web → nguồn, trạng thái dữ liệu và câu "Không phải lời khuyên đầu tư". Dữ liệu mô phỏng gắn nhãn [MÔ PHỎNG].

Về vận hành:
- Tin tự động gửi theo đợt: khoảng mỗi phút trong phiên (bộ phát trực tiếp kích hoạt), mỗi 5 phút ngoài giờ (cron ngoài).
- Nhiều cảnh báo trong một đợt được gom thành một tin; không gửi trùng (khóa Redis, ghi nhận đã gửi).
- Đăng ký là tự nguyện, mã hóa Fernet, không lưu chat ID dạng rõ.
- Lệnh cũ vẫn chạy để không làm gián đoạn người đang dùng.

Nguồn: README mục "Bot Telegram", `docs/bot_style.md`, `docs/bot_samples.md`, `docs/bot_audit.md`. Cách tổ chức mã (tách menu, nút, định dạng tin) tham khảo cấu trúc bot của đồ án nhóm Kumo_VN_bot, không dùng mã của đồ án đó.
