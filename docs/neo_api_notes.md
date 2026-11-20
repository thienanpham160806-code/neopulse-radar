# Ghi chú kỹ thuật NEO API

Nguồn: <https://neoinvest.vpbanks.com.vn/neo-openapi/docs/overview> — phiên bản tài liệu v1.0.0, đọc ngày 14/11/2026.
VPBankS có thể cập nhật; **kiểm tra lại tại thời điểm triển khai.**

## Môi trường

| Mục | Giá trị |
|---|---|
| Đăng nhập | `POST https://external.vpbanks.com.vn/auth/token` — body `{"username", "password"}` |
| REST production | `https://neoapi.vpbanks.com.vn/neo-api` |
| WebSocket thị trường | `ws://neoapi.vpbanks.com.vn/stock-stream/broker` |
| Header bắt buộc | `Authorization: Bearer <jwt>`, `x-device`, `x-devicetype` |
| Token | `expires_in` = 10800 giây (3 giờ) |
| Giới hạn | 5 request/giây mỗi client; chỉ dùng được từ IP đã đăng ký |
| Envelope | `{status: 1|0, code, message, timestamp, data}`; thành công `NEOINP000000` |
| Phân trang | `pageNo` (từ 1), `pageSize` (mặc định 1000); `data.content`, `data.last` |

Đề đồ án nêu NEO API **không có môi trường thử cho khách hàng** và lệnh qua API là lệnh thật → sản phẩm không dùng nhóm `/trading/*` và không dùng host UAT.

## Endpoint được dùng

| Hàm trong `NeoClient` | Endpoint | Tham số |
|---|---|---|
| `login` | `POST /auth/token` | username, password |
| `market_status` | `GET /market/marketStatus` | marketCode |
| `market_index_detail` | `GET /market/marketIndexDetail` | indexCode (`ALL`, `VNINDEX`, `VN30`…) |
| `intraday_market_index` | `GET /market/intradayMarketIndex` | indexCode |
| `index_list` | `GET /market/indexList` | exchangeCode |
| `stock_list` | `GET /stock/stockList` | marketCode |
| `stock_detail` | `GET /stock/stockDetail` | symbols (tự chia lô 10 mã), stockType |
| `stock_detail_by_index` | `GET /stock/stockDetailByIndex` | indexCode |
| `fu_stock_detail` | `GET /stock/fuStockDetail` | stockType=`FUVN30`, symbols |

## WebSocket

```
→ {"action": "auth", "data": "<jwt>"}
← {"type": "auth", "status": "success", "data": {...}}
→ {"type": "sub", "channel": "stockInfo",     "listId": ["VPB", "HPG", ...]}
→ {"type": "sub", "channel": "marketInfo",    "listId": ["VNINDEX", "VN30", ...]}
→ {"type": "sub", "channel": "marketSession", "listId": ["HOSE", "HNX", "UPCOM", "FU"]}
```

Kênh `marketVolume` không đăng ký vì khối lượng lũy kế đã có trong `marketInfo`.

## Điểm dữ liệu cần lưu ý (đã xử lý trong `data/normalize.py`)

- `bidPrice1`, `askPrice1` là **chuỗi** (`"31250.0"`) và có thể là `"ATO"`/`"ATC"`; các mức 2–3 là số.
- `indexValue` trên WebSocket là chuỗi; trên REST là số.
- `tradingDate`, `maturityDate` dạng `dd/mm/YYYY`; `indexTime` dạng `HH:MM:SS` (WS) hoặc ISO (REST).
- `stockInfo` **không có dấu thời gian** → lưu thời điểm nhận theo giờ VN.
- Nhiều trường `null` hoặc chuỗi rỗng (`totalBidQTTY`, `openInterest`, `exerciseRatio`…).
- Ví dụ trong tài liệu có `indexColor: "green"` trong khi mô tả ghi `Up/Down/Nochange` → không dùng trường này.
- Mã lỗi `NEOINP000021`: tối đa 10 mã mỗi lần gọi → client tự chia lô.

## Lần thử kết nối thật (20/11/2026)

Dùng tài khoản VPBankS thật của tác giả, chỉ gọi endpoint đọc `GET /market/marketStatus`, không gọi nhóm `/trading/*`.

| Bước | Kết quả |
|---|---|
| `POST https://external.vpbanks.com.vn/auth/token` | 200, `IABNOT000`, nhận JWT `token_type: Bearer`, `scope: profile email`; `expires_in` thực tế 28800 giây (tài liệu ghi 10800) |
| `GET https://neoapi.vpbanks.com.vn/neo-api/market/marketStatus` với `Authorization`, `x-device`, `x-devicetype` | 401, `NEOINP000401` (thử cả giá trị mẫu `my-app`/`chrome` của tài liệu) |
| Cùng request nhưng bỏ `x-device` | 400, `NEOINP000003 Missing required header: x-device` - cổng API nhận đúng định dạng header |

Endpoint, base URL và bộ header khớp từng chữ với tài liệu v1.0.0 (trang *Xác thực*, *Quy ước chung*, *4.4 Trạng thái thị trường*). Trang *Xác thực* ghi **"IP Whitelist: Bắt buộc - chỉ IP đã đăng ký"**: máy chủ đăng nhập không kiểm IP nên vẫn cấp token, còn cổng dữ liệu từ chối IP chưa đăng ký.

Tác giả ở ký túc xá, mạng dùng IP động và không đăng ký được IP tĩnh; IP 4G thay đổi liên tục và dùng chung nhiều thuê bao. Vì vậy đồ án dùng **SSI FastConnect** làm nguồn dữ liệu thật (cùng lược đồ thô, xem `docs/ssi_notes.md`). Lớp `neo_api/` giữ nguyên, đã kiểm thử bằng máy chủ giả, và chạy được ngay khi có IP được whitelist: chỉ cần `NEOPULSE_SOURCE=neo`.

## Chưa xác minh được từ tài liệu

Tài liệu không nói rõ các điểm sau; mã nguồn xử lý theo hướng chịu lỗi và ghi nhận để hiệu chỉnh:

1. **Phong bì của thông điệp đẩy về qua WebSocket** — thân trần hay bọc trong `{channel, data}`. `classify_message` chấp nhận cả hai.
2. **`stockInfo` có nhận mã HĐTL (`VN30F…`) hay không** — nếu không, HĐTL vẫn được lấy bằng REST mỗi 60 giây.
3. **Cơ chế ping/pong** — hiện dựa vào ping mặc định của thư viện `websockets` và ngưỡng im lặng 45 giây.
4. **Cách làm mới token bằng `refresh_token`** — chưa có endpoint trong tài liệu → đăng nhập lại.
5. **`ws://` hay `wss://`** — tài liệu ghi `ws://` (trang tổng quan ghi `http://`); đổi được qua `NEO_WS_MARKET_URL`.
6. **Đơn vị giá HĐTL và `totalTradingValue` của HĐTL** — basis chỉ dùng `closePrice` (điểm chỉ số).
