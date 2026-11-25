# Mẫu tin bot Telegram

Sinh bằng `tools/render_bot_samples.py` từ payload **MÔ PHỎNG** (bộ mô phỏng `neopulse simulate`, xuất bằng mã hiện tại); số liệu không phải dữ liệu thị trường. Tin thật gửi dạng HTML (`parse_mode=HTML`); dưới đây giữ nguyên thẻ `<b>`, `<i>`. Dòng `[…]` cuối mỗi mẫu là các nút bấm đi kèm.

## Nhịp thị trường (/thitruong)

```text
📊 <b>[MÔ PHỎNG] Nhịp thị trường · VN30</b> · 14:30, 23/11/2026
🧭 Điểm nhịp <b>58,6/100</b>: Nghiêng tích cực.
VN30 1.967,70 🟢 ▲ +0,45% · 20 mã tăng / 9 mã giảm / 1 đứng giá
<b>Căn cứ:</b> Động lượng chỉ số +0,44 và Độ rộng thị trường +0,38 kéo điểm lên; Mất cân bằng sổ lệnh −0,23 và Khối ngoại −0,03 kéo xuống. Thành phần chuẩn hóa từ −1 đến +1, 0 là trung tính.
<b>Bối cảnh:</b> 🏦 Khối ngoại bán ròng 99,1 tỷ đồng trong rổ · ngành đóng góp nhiều nhất: Ngân hàng +5,2 điểm (ước lượng).
<i>Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư</i>
[🚨 Xem cảnh báo]  [🔗 Mở trên web]
```

## Danh sách cảnh báo (/canhbao)

```text
🚨 <b>[MÔ PHỎNG] Cảnh báo trong phiên · VN30</b> · 14:30
31 lượt: 🚨 7 mức cao · ⚠️ 4 trung bình · ℹ️ 20 thấp.
Mức cao gần nhất:
🚨 14:28 <b>VIB</b> · độ chênh giá mua-bán giãn rộng bất thường
🚨 14:09 <b>TPB</b> · độ chênh giá mua-bán giãn rộng bất thường
🚨 13:44 <b>CTG</b> · khối ngoại bán ròng cao bất thường
🚨 11:09 <b>HPG</b> · khối ngoại bán ròng cao bất thường
🚨 10:54 <b>BID</b> · độ chênh giá mua-bán giãn rộng bất thường
🚨 10:46 <b>VJC</b> · độ chênh giá mua-bán giãn rộng bất thường
🚨 10:13 <b>SHB</b> · độ chênh giá mua-bán giãn rộng bất thường
Cảnh báo là quan sát cần xem lại, chưa cho biết nguyên nhân hay hướng giá.
<i>Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư</i>
[✓ 🚨 Chỉ mức cao]  [⚠️ Từ trung bình]  [🔗 Mở trên web]
```

## Một cảnh báo tự động

```text
🚨 <b>[MÔ PHỎNG] Độ chênh giá mua-bán giãn rộng · VIB</b> · 14:28
VIB: độ chênh giá mua-bán giãn rộng bất thường; giá 41.600 🔴 ▼ −0,95%.
<b>Căn cứ:</b> điểm z bền vững vượt 50 (ngưỡng 3,5): lệch rất xa so với mức thường thấy trong phiên.
<b>Bối cảnh:</b> VN30 1.967,70 🟢 ▲ +0,45% · 20 mã tăng / 9 mã giảm / 1 đứng giá.
<i>Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư</i>
[🏢 Thẻ VIB]  [🔗 Xem VIB trên NeoPulse]
```

## Thẻ mã (/ma VIB)

```text
🏢 <b>[MÔ PHỎNG] VIB · Ngân hàng Thương mại Cổ phần Quốc tế Việt Nam</b>
HOSE · Ngân hàng · Trong rổ VN30
Giá 41.600 🔴 ▼ −0,95% · Giá trị khớp 421,1 tỷ đồng · lúc 14:30
🏦 Khối ngoại bán ròng 5,0 tỷ đồng (tỷ trọng 7,5% giá trị khớp)
Mất cân bằng sổ lệnh −0,06: bên bán dày hơn trên 3 mức giá tốt nhất.
🚨 1 cảnh báo trong phiên, gần nhất 14:28: độ chênh giá mua-bán giãn rộng bất thường.
<i>Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư</i>
[⭐ Theo dõi / bỏ theo dõi VIB]  [🔗 Hồ sơ VIB]
```

## Tổng kết cuối phiên

```text
📊 <b>[MÔ PHỎNG] Tổng kết phiên 23/11/2026 · VN30</b> · 14:30, 23/11/2026
VN30 1.967,70 🟢 ▲ +0,45% · 20 mã tăng / 9 mã giảm / 1 đứng giá · 🟣 0 trần · 🔵 0 sàn
🧭 Điểm nhịp 58,6/100: Nghiêng tích cực.
🏦 Khối ngoại bán ròng 99,1 tỷ đồng trong rổ; mua ròng nhiều nhất TCB, bán ròng nhiều nhất BID.
📈 VN30F2612: chênh lệch cơ sở −1,20 điểm, còn 24 ngày tới đáo hạn.
🚨 31 cảnh báo (7 mức cao), nhiều nhất ở VIB, TPB, CTG.
<i>Bộ mô phỏng · Dữ liệu MÔ PHỎNG · Không phải lời khuyên đầu tư</i>
[🔗 Xem bản tin phiên trên web]
```
