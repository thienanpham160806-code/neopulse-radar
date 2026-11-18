# Ghi chú kỹ thuật: nguồn SSI FastConnect (API v3)

Nguồn: cổng nhà phát triển https://developers.ssi.com.vn (truy cập 18/11/2026) và mã nguồn SDK chính thức
`ssi-sdk` 3.3.2 trên PyPI (đọc để lấy giao thức streaming mà tài liệu web không mô tả). Không có dòng nào của SDK
được sao chép vào repo; chỉ dùng tên trường và quy ước giao thức.

## Kết nối

| Thành phần | Giá trị |
|---|---|
| REST | `https://api.ssi.com.vn` |
| Token | `POST /api/v3/auth/token` với `{apiKey, apiSecret}` → `accessToken`, `expiresAt` (epoch giây). Không gửi `otp` ⇒ chỉ đọc được dữ liệu thị trường |
| Dữ liệu REST dùng | `GET /api/v3/data/securitiesByBoard?index=VN30`, `indexList`, `indexSummary`, `ohlc`, `securitiesSummary` |
| WebSocket | `wss://stream.ssi.com.vn/ws/v3`, header `Authorization: Bearer <token>` khi bắt tay |
| Đăng ký | `{"method":"subscribe","channel":"DATA","topics":[...]}`; giữ nhịp `{"method":"ping_pong","channel":"HEARTBEAT"}` |
| Chủ đề dùng | `trade.<MÃ>`, `quote.<MÃ>`, `room.<MÃ>`, `market.<MÃ>`, `market.flag`, `trade.index.<MÃ>` |

Máy chủ chỉ kiểm tra token lúc kết nối, nên `SsiStream` chủ động nối lại khi token còn dưới 120 giây.

## Ánh xạ về lược đồ NEO (`ssi/adapter.py`)

| Trường nội bộ (kiểu NEO) | Nguồn SSI |
|---|---|
| `closePrice`, `closeVol`, `totalTradingVolume`, `openPrice`, `highPrice`, `lowPrice`, `averagePrice` | `trade.*`: `p`, `q`, `v`, `o`, `h`, `l`, `a` |
| `bidPrice1..3`, `bidVol1..3`, `askPrice1..3`, `askVol1..3` | `quote.*`: `bids`/`asks` = `[[giá, KL], ...]`, tốt nhất trước |
| `foreignRoom`, `foreignRemain`, `foreignBuy/SellVolume`, `foreignBuy/SellValue` | `room.*`: `tr`, `cr`, `bq`, `sq`, `bv`, `sv` |
| `ceilingPrice`, `floorPrice`, `refPrice` | `market.<MÃ>`: `ce`, `fl`, `ref` |
| `priceChange`, `percentPriceChange` | **tính** từ giá cuối và giá tham chiếu |
| `totalTradingValue` | **ước lượng** = giá trung bình × khối lượng lũy kế (SSI không gửi giá trị lũy kế) |
| Chỉ số (`marketInfo`) | `trade.index.*`: `v`, `c`, `cr`, `adv`, `dec`, `nc`, `ce`, `fl`, `tq`/`tmq`, `tv`/`tmv` |
| `marketSession` | `market.flag`: `b` (sàn), `f` (cờ: ATO, LO, ATC…) |

SSI tách mỗi loại tin thành chủ đề riêng, mỗi tin chỉ mang một phần dữ liệu. Adapter giữ trạng thái gộp theo mã và phát một bản ghi đầy
đủ sau mỗi tin. Vì nhiều tin của một mã có thể tới trong cùng một mili-giây mà khóa duy nhất là (mã, ts), `Ingestor` gộp chúng thành một hàng
(bản đến sau thay bản đến trước) thay vì bỏ rơi.

## Khác biệt so với NEO ảnh hưởng tới kết quả

- **Không có HĐTL tự động**: REST dữ liệu không liệt kê sàn phái sinh. Phải điền `NEOPULSE_FUTURES`; ngày đáo hạn suy ra từ mã `VN30FYYMM` = thứ Năm thứ ba của tháng. Không điền ⇒ tab Phái sinh/basis trống.
- **Giá trị giao dịch lũy kế là ước lượng** nên chỉ báo thanh khoản theo giá trị (Amihud, quy mô lệnh) kém chính xác hơn bản NEO.
- **Không có polling REST**: không có endpoint REST giá/sổ lệnh thời gian thực, nên `neopulse poll` không dùng được với SSI.
- Thời điểm sự kiện: khung SSI có trường thời gian `t` nhưng định dạng chưa rõ ⇒ dùng thời điểm nhận (giờ VN), như NEO.

## Điểm CHƯA kiểm chứng trên luồng thật

1. Đơn vị giá (đồng hay nghìn đồng) → `SSI_PRICE_SCALE`.
2. Số mức giá trong `quote.*` (hệ thống chỉ dùng 3 mức đầu).
3. Ý nghĩa các trường chỉ số (`adv`, `dec`, `nc`, `ce`, `fl`, `tq`, `tv`): SDK ghi rõ là suy từ chữ viết tắt.
4. `bv`/`sv` là giá trị (đồng) hay đơn vị khác; `bq`/`sq` có lũy kế trong ngày không.
5. Tên tham số REST `index` của `securitiesByBoard` (suy từ SDK), giới hạn tần suất (tài liệu không nêu; mặc định 5 req/s).
6. Giới hạn số chủ đề mỗi yêu cầu đăng ký (chia lô 50 cho an toàn) và số kết nối đồng thời (SDK ghi tối đa 10 mỗi client).
7. Quyền dữ liệu thời gian thực của tài khoản/khóa cá nhân (tài liệu không nói rõ điều kiện, phí).

Mọi khung tin không nhận diện được đi vào kênh `unknown` và được ghi vào `raw_dump/unknown_messages.jsonl` để hiệu chỉnh.

## Quan sát trên dữ liệu thật (18/11/2026, ngoài giờ giao dịch)

Đã kiểm chứng bằng cuộc gọi REST thật (chỉ dữ liệu thị trường) và một lần đăng ký WebSocket ngắn:

- `GET /api/v3/data/securitiesByBoard?index=VN30` trả mảng trần 30 phần tử ⇒ tên tham số `index` đúng. `?board=HOSE|HNX|UPCOM` cũng chạy: HOSE 926, HNX 421, UPCOM 846 bản ghi; `board` khác (DER, HNXDER...) trả HTTP 400.
- Trường mỗi bản ghi: `symbol`, `board`, `lotSize`, `listedShare`, `icbCode`, `stockType`, `maturityDate`, `cwUnderlyingSymbol`... `stockType` phân biệt được loại chứng khoán: HOSE gồm `Stock` 410, `CW Product` 461, `ETF Product` 21, `Investment Fund` 3, `None` 31; HNX gồm `Stock` 299, `Bond` 104, `Future` 14, `None` 4; UPCOM gồm `Stock` 808, `None` 38. (Bản ghi `None` chưa rõ bản chất.)
- HĐTL nằm trong bản ghi của sàn HNX với `stockType=Future`, và mã là mã nội bộ chứ không phải dạng `VN30F2612`: `41I1GB000` (VN30, đáo hạn 19/11/2026), `41I1GC000` (VN30, 17/12/2026), `41I1H3000` (03/2027), `41I1H6000` (06/2027). Mã `VN30F...` có phải chủ đề streaming hợp lệ không CHƯA biết; máy chủ trả "Subscribed to N topic(s)" cho mọi chủ đề (kể cả mã chưa kiểm chứng), nên xác nhận ack **không** chứng minh chủ đề tồn tại. Chỉ biết có dữ liệu hay không khi chạy trong phiên.
- Token: `expiresAt` cho thời hạn ~899 giây (~15 phút), không phải vài giờ ⇒ luồng WebSocket phải nối lại gần 15 phút một lần (`SsiStream` đã chủ động nối lại khi còn dưới 120 giây).
- Windows: console mặc định cp1252 làm `neopulse check` lỗi `UnicodeEncodeError`; đã ép stdout/stderr UTF-8 trong `cli.main`.
