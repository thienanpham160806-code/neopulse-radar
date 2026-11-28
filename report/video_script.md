# Kịch bản video trình diễn (5–7 phút)

Tệp nộp: `K244141653_PhamNgocThienAn_Demo.mp4`, hoặc đường dẫn video. Số liệu nói trong video lấy từ [report/data/SUMMARY.md](data/SUMMARY.md); nếu sinh lại báo cáo thì đọc lại số trước khi quay.

## Checklist trước khi quay

- [ ] Đóng mọi tab riêng tư: email, ngân hàng, Vercel dashboard, SSI developer portal, Telegram cá nhân khác.
- [ ] **Không mở `.env`** và không mở `out/telegram_tick_secret.txt`. Trong VS Code, đóng mọi tab có token. Không chạy `vercel env pull` hay `env` khi đang quay.
- [ ] Terminal: xóa lịch sử (`Clear-Host`). Không để lộ lệnh có token trong lịch sử. Kiểm tra log định quay không in IP hay khóa (log đã lọc Bearer/JWT, nhưng vẫn xem lướt trước).
- [ ] Ẩn thanh dấu trang và tiện ích trình duyệt. Thu phóng 110–125% để chữ đọc được.
- [ ] Mở sẵn: web production (`/thi-truong?date=2026-11-27`), Telegram với bot `@neopulse_warningbot`, terminal tại gốc repo, VS Code ở `README.md`.
- [ ] Tắt thông báo hệ thống (Focus Assist), tắt chuông điện thoại.
- [ ] Nếu quay trong giờ giao dịch: bộ ghi đang chạy (`Get-ScheduledTaskInfo NeoPulseRecord`). Ngoài giờ: dùng log phiên 27/11 và snapshot cuối phiên.

## Các cảnh

| # | Thời lượng | Màn hình | Lời nói gợi ý |
|---|---|---|---|
| 1 | 0:00–0:40 | Trang chủ web | "NeoPulse Radar là radar nội phiên cho rổ VN30. Người dùng là nhà đầu tư cá nhân và người học tài chính, những người cần biết trong phiên có gì bất thường mà không phải nhìn 30 bảng giá cùng lúc. Hệ thống chỉ phân tích, không đặt lệnh và không khuyến nghị mua bán." |
| 2 | 0:40–1:30 | Terminal: `Get-Content out\record_20261127.log -Tail 8`; Task Scheduler `NeoPulseRecord` | "Dữ liệu là SSI FastConnect thật: sổ lệnh 3 mức, khối ngoại, chỉ số và HĐTL VN30. Bộ ghi chạy theo lịch Windows từ 8 giờ 55, tự nối lại khi mất mạng, khử tin lặp, loại tin đến muộn và ghi vào SQLite. Tôi dùng SSI thay NEO vì NEO yêu cầu IP cố định; giảng viên đã đồng ý." |
| 3 | 1:30–2:20 | Web, tab **Tổng quan** phiên 27/11 | "Điểm nhịp tổng hợp năm nhóm: độ rộng, động lượng, sổ lệnh, khối ngoại, thanh khoản. Trọng số là lựa chọn thiết kế, có phân tích độ nhạy ngay bên dưới. Thanh trạng thái cho biết nguồn, giờ cập nhật cuối và đây là bản cuối phiên." |
| 4 | 2:20–2:50 | Tab **Vì sao?** | "Tab này giải thích điểm nhịp bằng chính số liệu: thành phần nào kéo lên, thành phần nào kéo xuống. Câu chữ dựng từ mẫu cố định, không có con số nào ngoài bảng." |
| 5 | 2:50–3:40 | Tab **Bất thường**: lọc mức CAO, mở một cảnh báo | "Mỗi mã được so với chính nó trong phiên. Spread đo bằng số bước giá, khối ngoại xét theo tỷ trọng trên 3 thanh có dữ liệu gần nhất. Ngưỡng chọn trên 4 phiên đầu theo ngân sách: trung bình không quá 1 cảnh báo CAO trên một mã một phiên. Tôi nói thẳng: ở 2 phiên ngoài mẫu, con số là 1,67, vượt ngân sách." |
| 6 | 3:40–4:10 | Tab **Chi tiết mã**: sổ lệnh 3 mức, trượt giá | "Ở đây là OBI, microprice, độ chênh giá mua-bán và trượt giá ước lượng khi mua 500 triệu đồng bằng cách đi qua 3 mức giá. Đây là cận dưới, vì chỉ có 3 mức." |
| 7 | 4:10–4:40 | Telegram: một tin cảnh báo thật, `/thitruong` | "Bot gửi cảnh báo mức cao và bản tin gộp lúc 8 giờ 30 và 15 giờ. Số trên bot lấy cùng nguồn với web. Cuối mỗi tin luôn có dòng 'Không phải lời khuyên đầu tư'." |
| 8 | 4:40–5:10 | Web khi dữ liệu dừng: thanh trạng thái báo trễ / nhãn "Phiên đã kết thúc"; ảnh tin sức khỏe bộ ghi nếu có | "Khi bộ ghi dừng hoặc mất mạng, web không giả vờ là trực tiếp: nó báo độ trễ và giờ cập nhật cuối. Worker trên cloud nhắn riêng cho tôi nếu 9 giờ 05 chưa có dữ liệu hoặc dữ liệu im lặng quá 5 phút." |
| 9 | 5:10–6:10 | `report/data/SUMMARY.md`, phần Kiểm chứng và Kết luận | "Câu hỏi kiểm chứng: tín hiệu sổ lệnh có liên hệ với biến động giá kế tiếp không? Có, về thống kê. Ngoài mẫu, IC từ 0,17 đến 0,29, t Newey-West trên 13. Placebo xáo giữa các mã cho IC gần 0. Nhưng sau chi phí thì không còn lãi: chỉ mua nhóm Q5 cho âm 48 đến âm 63 điểm cơ bản; riêng độ chênh giá mua-bán đã ăn hết phần chênh. Giả thuyết của tôi là giá giữa nhích nửa bước giá, mà muốn hưởng phần đó phải trả cả một bước. Chỉ có 2 phiên ngoài mẫu nên đây không phải kết luận chắc chắn." |
| 10 | 6:10–6:50 | Terminal `python -m pytest -q` chạy xanh; mở `.env.example`; `src/neopulse/neo_api/client.py` dòng `FORBIDDEN_PATH_PREFIXES` | "Gần 300 ca kiểm thử offline: công thức so với tính tay, không nhìn trước tương lai, dữ liệu bẩn, WebSocket rớt. Bí mật chỉ nằm trong `.env`, repo chỉ có `.env.example`. Endpoint đặt lệnh bị chặn cứng trong client, có test riêng." |
| 11 | 6:50–7:00 | README | "Mã nguồn, hướng dẫn cài và giới hạn đã biết nằm trong README. Cảm ơn thầy đã xem." |

## Gợi ý khi quay

- Nói chậm, mỗi cảnh một ý chính. Nếu quá 7 phút, rút cảnh 4 và 6 trước.
- Cảnh 10: `pytest -q` chạy khoảng 3–4 phút. Quay trước rồi cắt ghép, hoặc chỉ chạy một nhóm: `python -m pytest -q tests/test_anomaly_alerts.py tests/test_validation_ranking.py tests/test_neo_client.py`.
- Không đọc số không có trong SUMMARY. Chưa có ảnh tin Telegram thật thì quay trực tiếp `/thitruong` và `/canhbao`.
