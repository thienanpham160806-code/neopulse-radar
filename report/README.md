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
| 7 | Kiểm thử và kết quả | 94 ca kiểm thử; đối chiếu bảng giá; IC ngoài mẫu; tần suất cảnh báo; lỗi đã thử | `docs/test_plan.md`, `neopulse validate` |
| 8 | Hạn chế và sử dụng có trách nhiệm | 3 mức giá, thời điểm nhận, rổ hữu hạn, trọng số thiết kế, không dự báo, bảo mật | README §9–10 |
| 9 | Hướng phát triển | dữ liệu lịch sử từ SSI cho MA20/độ rộng dài hạn; lịch nghỉ lễ; mô hình hóa tác động giá; triển khai máy chủ | `providers/ssi.py` |
| 10 | Kết luận | giá trị tạo ra; bài học kỹ thuật/tài chính | — |
| PL | Phụ lục | từ điển dữ liệu, công thức chi tiết, kết quả `pytest`, hướng dẫn cài đặt, đường dẫn mã/video | `docs/` |

## Phần "Triển khai sản phẩm" (đề cho tự chọn nền tảng triển khai)

Nội dung nên viết (lấy từ `docs/web_architecture.md`):
- **Kiến trúc:** máy tác giả (`record` → SQLite → `neopulse publish`) → Vercel Blob (JSON) → web Next.js trên Vercel. Mọi chỉ báo do Python tính (`build_view`), web chỉ hiển thị.
- **Vì sao không đưa Streamlit lên Vercel:** Vercel chạy hàm serverless ngắn hạn, không giữ tiến trình Python sống lâu và WebSocket hai chiều; SQLite không có chỗ lưu bền. Streamlit vẫn dùng khi chạy cục bộ.
- **Vì sao bộ ghi ở máy tác giả:** giữ kết nối WebSocket SSI nhiều giờ và giữ khóa API; khóa không bao giờ lên đám mây.
- **Giới hạn độ trễ (phải nói thẳng):** không tick-by-tick. Gom lô ≤ 5 s + chu kỳ publish 20 s + cache CDN Blob tối thiểu 60 s + revalidate web 15 s ⇒ ước tính nửa phút đến ~1,5 phút. *Điền số đo thực sau lần chạy thật.*
- **Trạng thái dữ liệu minh bạch:** nguồn, giờ cập nhật, "cách đây X giây", chấm xanh/cam/đỏ, số mã tính/loại, nhãn MÔ PHỎNG, "phiên đã kết thúc" ngoài giờ.
- **Bảo mật:** khóa SSI và `BLOB_READ_WRITE_TOKEN` chỉ ở `.env` máy ghi; Vercel chỉ có `BLOB_READ_URL`, `SITE_PASSWORD`; mật khẩu bằng cookie httpOnly (lưu băm); không đặt mật khẩu thì dữ liệu thật bị khóa; chỉ xuất chỉ báo tổng hợp, không xuất bảng giá/sổ lệnh thô. *Lưu ý trung thực:* URL Blob công khai nên mật khẩu chỉ bảo vệ trang web, không bảo vệ tệp JSON.
- **Ảnh minh họa:** `docs/img/web_*_sim.png` (dữ liệu MÔ PHỎNG — phải ghi rõ trong chú thích); thay bằng ảnh dữ liệu thật khi đã thu.

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
