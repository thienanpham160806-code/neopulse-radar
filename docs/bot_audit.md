# Rà soát bot Telegram NeoPulse Radar và đề xuất cấu trúc mới

Ngày rà soát: 25/11/2026 · Nhánh: `bot/ux` · Trạng thái: chờ duyệt, chưa sửa mã.

Phạm vi: `src/neopulse/analytics/telegram_ui.py`, `telegram_cloud.py`, `telegram_store.py`, `notify.py`, `web/api/telegram.py`, `web/api/telegram_tick.py`, `web/src/app/thong-bao`, `tools/configure_telegram_profile.py`.

Tham khảo cấu trúc bot `Kumo_VN_bot` (đồ án nhóm, chỉ đọc): tách `handlers/` theo nhu cầu, một tệp `keyboards.py` cho menu và nút theo mã, một tệp `formatters.py` cho trình bày. Không chép mã, không import, không mang sang tín hiệu MACD/RSI/Ichimoku, khuyến nghị hay khai phá BCTC.

## 1. Hiện trạng

### 1.1 Lệnh và nút menu

| Lệnh / nút | Việc đang làm | Dữ liệu | Cần đăng ký? | Vấn đề |
|---|---|---|---|---|
| `/start [alerts_news_laws]` | Tạo đăng ký (mặc định chỉ cảnh báo mức cao), in hướng dẫn | Redis | Tạo mới | Vừa đăng ký vừa in toàn bộ hướng dẫn: tin dài |
| `/help`, nút "Hướng dẫn" | In hướng dẫn | Tĩnh | Không | Trùng vai trò giới thiệu với `/web` |
| `/web`, `/website` | In 3 đường dẫn web | Tĩnh | Không | Trùng `/help`; không có trong menu |
| `/market`, nút "Nhịp thị trường" | Bản tin nhịp thị trường VN30 | `/api/data` | Không | Ổn; chưa có icon, chưa có màu tăng/giảm |
| `/alerts` (không tham số), nút "Cảnh báo" | Tóm tắt cảnh báo trong phiên | `/api/data` | Không | **Cùng tên với `/alerts on/off`**: một lệnh hai việc |
| `/alerts on/off`, `/news on/off`, `/laws on/off` | Bật/tắt từng loại tin | Redis | Có | Người dùng phải nhớ cú pháp; không có nút |
| `/company <MÃ>`, gõ mã, nút "Tra doanh nghiệp" | Thẻ tên, sàn, ngành, link hồ sơ | catalog | Không | Thẻ chưa có giá, cảnh báo, khối ngoại của mã dù payload có |
| `/watch MÃ,MÃ` | Đặt danh sách mã (ghi đè) | Redis | Có | Không thêm/bớt từng mã được; ghi đè cả danh sách |
| `/all` | Xóa danh sách mã = theo cả rổ VN30 | Redis | Có | Chồng với `/watch`; tên không tự giải thích |
| `/watchlist`, nút "Mã theo dõi" | In cài đặt (giống `/status`) | Redis | Có | **Trùng `/status`** |
| `/status`, nút "Cài đặt nhận tin" | In cài đặt | Redis | Có | Nút tên "Cài đặt" nhưng chỉ xem, không chỉnh được |
| `/stop`, `/delete` | Hủy và xóa đăng ký | Redis | Có | Ổn |
| Văn bản thường không phải mã | Người đã đăng ký nhận lại hướng dẫn; người chưa đăng ký không được trả lời | — | — | Người mới gõ sai không nhận phản hồi |

### 1.2 Tin tự động (worker `telegram_cloud.run`, kích hoạt bởi `/api/telegram_tick`, relay và GitHub)

| Loại | Điều kiện gửi | Dạng tin | Vấn đề |
|---|---|---|---|
| Cảnh báo | Chỉ mức CAO, mã trong rổ VN30 hoặc danh sách theo dõi, phát sinh sau lúc bật | Một tin mỗi cảnh báo: `[Cảnh báo mức cao] MÃ · thời điểm ISO` + câu mô tả + link | Nhiều cảnh báo cùng đợt thành nhiều tin; thời điểm dạng ISO khó đọc; không có giá, bối cảnh; không chọn được mức |
| Tin doanh nghiệp | RSS CafeF, tiêu đề có mã trong catalog | `[cafef.vn] tiêu đề` + ngày đăng RFC + link | Ngày đăng dạng tiếng Anh; không có icon |
| Tin chính sách | RSS Báo Chính phủ, lọc từ khóa | Tương tự + ghi chú hiệu lực | Tương tự |
| `notify.py` | Gửi cảnh báo qua chat cố định khi chạy `neopulse alerts --notify` (dòng lệnh) | Văn bản thuần | Kênh cũ cho một chat, tách khỏi bot đăng ký |

Giới hạn mỗi lượt: tối đa 10 tin mỗi người, 100 tin mỗi lượt, khóa Redis chống chạy song song, ghi nhận đã gửi để không gửi lại.

### 1.3 Kỹ thuật cần lưu ý

- Webhook hiện chỉ xử lý `message`. Nút inline có `callback_data` (thêm/bớt mã, bật/tắt loại tin) cần xử lý thêm `callback_query`: kiểm tra người bấm, chống lặp, trả `answerCallbackQuery` và sửa tin cũ. Webhook chỉ trả được một method trong HTTP response, nên một trong hai lời gọi phải gọi API trực tiếp bằng token đã có trên Vercel.
- Payload `/api/data` có: `book.rows` (giá, % thay đổi, OBI₃, độ chênh, thanh khoản) và `foreign.rows` **chỉ cho các mã trong rổ đang ghi (VN30)**; `alerts.items` theo mã; `index.row`, `pulse`, `sectors`, `futures`. Không có giá trần/sàn từng mã, nên 🟣/🔵 chỉ dùng được khi có cảnh báo sát trần/sàn hoặc số mã trần/sàn của chỉ số.
- Mã ngoài rổ VN30: thẻ mã chỉ có tên, sàn, ngành và link hồ sơ (không có giá trong payload).
- Tin hiện gửi dạng văn bản thuần, chưa dùng `parse_mode`.

## 2. Đề xuất cấu trúc mới

Mỗi lệnh một việc, chia ba nhóm. Tên lệnh tiếng Việt không dấu theo đề xuất; Telegram chỉ cho chữ thường a–z, số và `_` trong tên lệnh.

| Nhóm | Lệnh | Một việc | Cần đăng ký? |
|---|---|---|---|
| Xem ngay | 📊 `/thitruong` | Bản tin nhịp thị trường VN30 | Không |
| | 🚨 `/canhbao` | Danh sách cảnh báo trong phiên, lọc theo mức bằng nút | Không |
| | 🏢 `/ma <MÃ>` (hoặc gõ mã) | Thẻ một mã: giá, cảnh báo của mã, khối ngoại, nút mở hồ sơ | Không |
| Cá nhân | ⭐ `/theodoi` | Xem danh sách mã; nút thêm/bớt từng mã; lựa chọn "Theo dõi cả rổ VN30" | Có (tự đăng ký nếu chưa có, sau khi người dùng bấm xác nhận) |
| | ⚙️ `/caidat` | Bật/tắt từng loại tin bằng nút: cảnh báo theo mức (Cao / Từ Trung bình), tin doanh nghiệp, tin chính sách, tóm tắt đầu phiên, tổng kết cuối phiên | Có |
| Khác | ℹ️ `/trangthai` | Dữ liệu đang trong phiên / bản dữ liệu / MÔ PHỎNG, cập nhật lúc nào, nhịp gửi tin | Không |
| | ❓ `/huongdan` | Bot làm gì, ba nhóm lệnh, website, miễn trừ | Không |
| | ⏹ `/dung` | Hủy và xóa đăng ký (có nút xác nhận) | Có |

`/start` giữ vai trò đăng ký (Telegram luôn gửi `/start` khi mở bot qua link): tạo đăng ký mặc định rồi trả một tin ngắn "Đã bật: … · Đổi trong ⚙️ Cài đặt", kèm menu.

Bí danh lệnh cũ (vẫn chạy, kèm một dòng "Lệnh mới: …"):

| Lệnh cũ | Chuyển sang |
|---|---|
| `/market` | `/thitruong` |
| `/alerts` (không tham số) | `/canhbao` |
| `/alerts on/off`, `/news on/off`, `/laws on/off` | Thực hiện như cũ, gợi ý `/caidat` |
| `/company <MÃ>` | `/ma <MÃ>` |
| `/watch MÃ,MÃ`, `/all`, `/watchlist` | Thực hiện như cũ, gợi ý `/theodoi` |
| `/status` | `/caidat` |
| `/help`, `/web`, `/website` | `/huongdan` |
| `/stop`, `/delete` | `/dung` |

### 2.1 Menu chính (bàn phím 3 hàng)

```text
[📊 Thị trường] [🚨 Cảnh báo]  [🏢 Tra mã]
[⭐ Theo dõi]   [⚙️ Cài đặt]
[ℹ️ Trạng thái] [❓ Hướng dẫn]
```

`/dung` không đặt trên menu để tránh bấm nhầm; có trong `/caidat` và `/huongdan`.

### 2.2 Nút bước tiếp theo

| Sau tin | Nút inline |
|---|---|
| `/thitruong` | [🚨 Xem cảnh báo] [🔗 Mở trên web] |
| `/canhbao` | [🚨 Chỉ mức cao] [⚠️ Từ trung bình] [🔗 Mở trên web] |
| `/ma MÃ` | [⭐ Theo dõi MÃ] hoặc [Bỏ theo dõi MÃ] · [🔗 Hồ sơ MÃ] |
| Cảnh báo tự động | [🏢 Thẻ MÃ] [🔗 Xem MÃ trên NeoPulse] |
| `/caidat` | Mỗi loại tin một nút bật/tắt, [⏹ Hủy đăng ký] |
| `/theodoi` | Mỗi mã một nút bỏ, [Theo dõi cả rổ VN30], hướng dẫn "gõ /ma MÃ để thêm" |

## 3. Năm mẫu tin (dữ liệu MÔ PHỎNG, chỉ để duyệt bố cục)

Số liệu dưới đây là minh họa, không phải dữ liệu thị trường.

### 3.1 Nhịp thị trường

```text
📊 [MÔ PHỎNG] Nhịp thị trường · VN30 · 10:45, 25/11/2026
🧭 Điểm nhịp 58,6/100: Nghiêng tích cực.
VN30 1.967,70 🟢 ▲ +0,45% · 20 mã tăng / 9 mã giảm / 1 đứng giá.
Căn cứ: Động lượng chỉ số +0,44 và Độ rộng thị trường +0,38 kéo điểm lên; Mất cân bằng sổ lệnh −0,23 kéo xuống.
Bối cảnh: 🏦 Khối ngoại bán ròng 99,1 tỷ đồng trong rổ · Ngành đóng góp nhiều nhất: Ngân hàng +6,2 điểm.
Thiếu dữ liệu: Thanh khoản (điểm tính trên phần còn lại).
[🚨 Xem cảnh báo] [🔗 Mở trên web]
Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư
```

### 3.2 Danh sách cảnh báo

```text
🚨 [MÔ PHỎNG] Cảnh báo trong phiên · VN30 · 10:45
31 lượt: 🚨 7 mức cao · ⚠️ 14 trung bình · ℹ️ 10 thấp.
Mức cao gần nhất:
🚨 10:42 HPG · Khối lượng gấp 3,4 lần mức thường thấy cùng khung giờ
🚨 10:31 VIB · Độ chênh giá mua-bán giãn rộng, lệch rất xa mức thường thấy trong phiên
🚨 10:13 SHB · Khối ngoại bán ròng cao bất thường
… và 4 cảnh báo khác.
Cảnh báo là quan sát cần xem lại, chưa cho biết nguyên nhân hay hướng giá.
[🚨 Chỉ mức cao] [⚠️ Từ trung bình] [🔗 Mở trên web]
Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư
```

### 3.3 Một cảnh báo tự động (gom theo đợt)

Một đợt có một cảnh báo:

```text
🚨 [MÔ PHỎNG] Khối lượng bất thường · HPG · 10:42
HPG khớp lệnh gấp 3,4 lần mức thường thấy cùng khung giờ; giá 27.350 🟢 ▲ +1,30%.
Căn cứ: vượt ngưỡng cảnh báo 3,0 lần; sổ lệnh nghiêng về bên mua (OBI₃ +0,42).
Bối cảnh: VN30 🟢 ▲ +0,52% · 18 mã tăng / 9 mã giảm.
[🏢 Thẻ HPG] [🔗 Xem HPG trên NeoPulse]
Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư
```

Một đợt có nhiều cảnh báo: một tin, mỗi cảnh báo một dòng như mẫu 3.2, tối đa 10 dòng rồi "… và N cảnh báo khác".

### 3.4 Thẻ mã

```text
🏢 [MÔ PHỎNG] HPG · Công ty Cổ phần Tập đoàn Hòa Phát
HOSE · Tài nguyên cơ bản · Trong rổ VN30
Giá 27.350 🟢 ▲ +1,30% · Giá trị khớp 612,4 tỷ đồng
🏦 Khối ngoại mua ròng 18,8 tỷ đồng (tỷ trọng 7,0% giá trị khớp)
Mất cân bằng sổ lệnh +0,42: bên mua dày hơn trên 3 mức giá tốt nhất.
🚨 2 cảnh báo trong phiên, gần nhất 10:42: khối lượng gấp 3,4 lần mức thường thấy.
[⭐ Theo dõi HPG] [🔗 Hồ sơ HPG]
Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư
```

Mã ngoài rổ đang ghi (ví dụ DBC): chỉ có tên, sàn, ngành và nút hồ sơ, kèm câu "Giá trong phiên chỉ có cho các mã thuộc rổ VN30 đang theo dõi."

### 3.5 Tổng kết cuối phiên

```text
📊 [MÔ PHỎNG] Tổng kết phiên 25/11/2026 · VN30
VN30 đóng 1.967,70 🟢 ▲ +8,82 điểm (+0,45%) · 20 tăng / 9 giảm / 1 đứng giá · 🟣 0 trần · 🔵 0 sàn.
🧭 Điểm nhịp cuối phiên 58,6/100: Nghiêng tích cực.
🏦 Khối ngoại bán ròng 99,1 tỷ đồng; mua ròng nhiều nhất TCB, bán ròng nhiều nhất BID.
📈 VN30F2612: chênh lệch cơ sở −1,20 điểm, còn 24 ngày tới đáo hạn.
🚨 31 cảnh báo (7 mức cao), nhiều nhất ở VIB, TPB, CTG.
[🔗 Xem bản tin phiên trên web]
Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư
```

## 4. Bộ icon (đề xuất, ghi vào `docs/bot_style.md` ở bước 2)

🟢 tăng · 🔴 giảm · 🟡 tham chiếu/đứng giá · 🟣 trần · 🔵 sàn · 🚨 mức cao · ⚠️ trung bình · ℹ️ thấp · 📊 thị trường · 🧭 điểm nhịp · 🏦 khối ngoại · 📈 phái sinh · 🏢 doanh nghiệp · 📰 tin tức · ⚖️ chính sách. Thêm cho menu: ⭐ theo dõi · ⚙️ cài đặt · ❓ hướng dẫn · ⏹ dừng · 🔗 liên kết. Luôn kèm ▲▼ và dấu +/− để không phụ thuộc màu.

## 5. Điểm cần duyệt trước khi làm

1. **Gửi tin theo đợt (đụng logic worker).** Ba việc bắt buộc phải sửa `telegram_cloud.run`, dù không đổi cơ chế kích hoạt (`/api/telegram_tick`, relay, GitHub):
   - gom nhiều cảnh báo trong một đợt thành một tin;
   - cho chọn mức cảnh báo (Cao hoặc Từ trung bình);
   - thêm hai loại tin mới: tóm tắt đầu phiên và tổng kết cuối phiên. Hai loại này gửi một lần mỗi ngày, khi lượt chạy đầu tiên sau 09:15 và sau 15:05 thấy dữ liệu của ngày đó. Ghi nhận đã gửi theo ngày, nên không gửi trùng.
2. **Nút inline có `callback_data`** cho `/theodoi`, `/caidat`, lọc mức trong `/canhbao`: cần thêm xử lý `callback_query` ở webhook, như mục 1.3.
3. **Dữ liệu đăng ký.** Thêm trường mới có giá trị mặc định khi đọc:
   - `alert_level` mặc định `"CAO"`, đúng hành vi hiện tại;
   - `digest_open` và `digest_close` mặc định tắt.

   Không đổi khóa Redis hay mã hóa, nên bản ghi cũ đọc được như cũ.
4. **`notify.py`** (kênh một chat cũ qua dòng lệnh): đề xuất chỉ đổi định dạng cho khớp mẫu mới, không bỏ.
5. **Tên lệnh** tiếng Việt không dấu như đề xuất (`/thitruong`, `/canhbao`, `/ma`, `/theodoi`, `/caidat`, `/trangthai`, `/huongdan`, `/dung`).

## 6. Quyết định đã duyệt (25/11/2026)

1. Đồng ý: gom cảnh báo theo đợt; thêm tóm tắt đầu phiên và tổng kết cuối phiên.
2. Đồng ý: nút bấm có `callback_query`.
3. Không thêm chọn mức cảnh báo: tin tự động giữ chỉ mức cao. Thêm `digest_open`, `digest_close` (mặc định tắt); bản ghi cũ đọc được như cũ.
4. Đồng ý: `notify.py` chỉ đổi định dạng.
5. Đồng ý tên lệnh tiếng Việt không dấu.
