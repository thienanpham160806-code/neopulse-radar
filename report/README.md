# Báo cáo cuối kỳ — dàn ý theo Mục 12 của đề

Tên tệp nộp: `K244141653_PhamNgocThienAn_BaoCao.pdf` · mã nguồn: `K244141653_PhamNgocThienAn_NEOAPI_FinTech.zip` · video: `K244141653_PhamNgocThienAn_Demo.mp4`.
Khuyến nghị 8–12 trang A4, không tính phụ lục.

Dàn ý dưới đây chỉ ra **lấy nội dung ở đâu trong repo**. Phần chữ, số liệu thật và ảnh chụp phải do bạn viết và thu — đề yêu cầu giải thích được mọi công thức và quyết định thiết kế khi bảo vệ.

| # | Phần | Viết gì | Nguồn trong repo |
|---|---|---|---|
| 1 | Tóm tắt điều hành (½ trang) | vấn đề · người dùng · giải pháp · dữ liệu NEO API · phương pháp · kết quả chính | README §1 |
| 2 | Vấn đề và nhu cầu người dùng | 3 câu hỏi nội phiên; vì sao bảng giá chưa trả lời được; khác gì công cụ sẵn có | README §1 |
| 3 | Thiết kế sản phẩm | sơ đồ kiến trúc tự vẽ; nhiệm vụ từng lớp; lý do chọn SQLite/Streamlit/tách bộ ghi | `docs/architecture.md` |
| 4 | Dữ liệu NEO API | endpoint, kênh, tần suất, quy trình làm sạch, từ điển dữ liệu; số phiên/số bản ghi thật đã thu | `docs/neo_api_notes.md`, `docs/data_dictionary.md`, `ingest_runs` |
| 5 | Phương pháp | công thức, giả định, cơ sở ngưỡng, trọng số và độ nhạy | `docs/methodology.md` |
| 6 | Triển khai | ảnh 8 tab, quy trình sử dụng, trạng thái lỗi/dữ liệu cũ | dashboard + `docs/test_plan.md` §2 |
| 7 | Kiểm thử và kết quả | 243 ca kiểm thử Python và 91 ca kiểm thử web; đối chiếu bảng giá; IC ngoài mẫu; tần suất cảnh báo; lỗi đã thử | `docs/test_plan.md`, `neopulse validate` |
| 8 | Hạn chế và sử dụng có trách nhiệm | 3 mức giá, thời điểm nhận, rổ hữu hạn, trọng số thiết kế, không dự báo, bảo mật | README §9–10 |
| 9 | Hướng phát triển | dữ liệu lịch sử từ SSI cho MA20/độ rộng dài hạn; lịch nghỉ lễ; mô hình hóa tác động giá; triển khai máy chủ | `providers/ssi.py` |
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
- **Ảnh minh họa:** `docs/img/web_*_sim.png` (dữ liệu MÔ PHỎNG — phải ghi rõ trong chú thích); thay bằng ảnh dữ liệu thật khi đã thu.

## Triển khai sản phẩm: bổ sung về giao diện và thời gian thực (19/11/2026)

- **Kiến trúc thời gian thực:** `record` (`--flush-every 1`) ghi SQLite; `live-relay` đọc chỉ-đọc và phát tin tổng hợp lên Ably kênh `neopulse:live` (tick khoảng 1 giây khi có thay đổi, pulse khoảng 10 giây, status); trình duyệt nhận qua SSE với token chỉ subscribe, hạn 15 phút. Snapshot tĩnh là dự phòng khi mất tin quá 60 giây, ngoài giờ giao dịch hoặc khi lỗi.
- **Hạn mức Ably Free:** 6.000.000 tin/tháng, tính cả tin giao tới người xem. Ước tính một phiên ≈ 17.600 tin × (1 + 5 người xem) ≈ 106.000; 22 phiên ≈ 2,3 triệu (≈ 39%). Bộ đếm `out/ably_usage.json` tự giãn nhịp khi vượt 70%.
- **Lý do chọn hướng thiết kế và các phương án đã cân nhắc:** xem `docs/web_architecture.md` mục "Thiết kế giao diện" (bảng điểm ba hướng A/B/C, lý do chọn B kết hợp mobile của C, Lighthouse trước và sau).
- **Thay đổi bảo mật theo quyết định của tác giả:** bỏ mật khẩu trang (commit `1cad109`). Trang và chỉ báo tổng hợp công khai; khóa Ably vẫn chỉ ở máy chủ, token phía trình duyệt chỉ có quyền subscribe. Không xuất sổ lệnh thô.

## Tái sử dụng mã nguồn (ghi trong báo cáo, mục Triển khai hoặc Phụ lục)

Có tái sử dụng có chọn lọc từ dự án cá nhân trước của tác giả (invest-system-phase2): font Be Vietnam Pro (SIL OFL), các hàm định dạng số/tiền/ngày (đã bỏ phần màu khuyến nghị mua/bán), nút sáng/tối, danh sách mã tham chiếu cho phân ngành dự phòng, và cách gọi dự phòng Vietcap qua vnstock. Bảng chi tiết (tệp, nguồn, đã sửa gì) ở README mục "Tái sử dụng từ dự án cũ của tác giả". Không dùng mã của đồ án nhóm Kumo_VN_bot. Tính năng mới dựa trên phần tái sử dụng: **Ngành trong phiên** (độ rộng, % bình quân vốn hóa, đóng góp điểm ước lượng) và **RVOL theo thời điểm** (đầu vào cho cảnh báo khối lượng) - xem docs/methodology.md mục 11-12, kể cả giới hạn (đóng góp lệch do chưa free-float; IC chưa kiểm định lại vì mới một phiên).

## Việc phải có trước khi viết phần 4, 6, 7

- [ ] ≥ 5 phiên dữ liệu **thật** (ưu tiên 10) — theo `docs/live_checklist.md`.
- [ ] Ảnh chụp dashboard với nguồn *NEO API* (không dùng ảnh mô phỏng làm kết quả; nếu có dùng để minh họa giao diện thì ghi rõ "mô phỏng").
- [ ] Bảng IC ngoài mẫu từ dữ liệu thật: `neopulse validate --source neo --out report/ic_table.csv`.
- [ ] Ảnh đối chiếu với bảng giá NEO Invest; ảnh thử lỗi.
- [ ] Kiểm tra lại thư mục tài liệu tham khảo trong `docs/methodology.md`.
- [ ] Ghi rõ việc có dùng công cụ AI hỗ trợ lập trình/biên tập (Mục 13 của đề).

## Gợi ý kịch bản video (5–7 phút)

1. Vấn đề và người dùng (30 giây).
2. `neopulse check` → `neopulse record` đang chạy, log thống kê (1 phút).
3. Dashboard nguồn NEO API: Tổng quan → Sổ lệnh (soi một mã, đổi khối lượng lệnh) → Khối ngoại → Phái sinh → Cảnh báo (2–3 phút).
4. Dừng bộ ghi → trạng thái dữ liệu cũ (30 giây).
5. Tab Kiểm chứng: đọc bảng IC ngoài mẫu và nói rõ giới hạn (1 phút).
6. `pytest` chạy xanh; `.env.example` và việc chặn endpoint giao dịch (30 giây).

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
