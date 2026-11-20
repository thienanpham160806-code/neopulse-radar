# NeoPulse Radar — bản web (Next.js trên Vercel)

Web **chỉ hiển thị** chỉ báo do Python tính (`neopulse export-web`). Không có công thức tài chính nào bằng JavaScript, không có khóa SSI/NEO, không có SQLite. Kiến trúc và giới hạn: [`../docs/web_architecture.md`](../docs/web_architecture.md).

## Chạy thử cục bộ (dữ liệu MÔ PHỎNG đi kèm)

```bash
cd web
npm install
npm run dev          # http://localhost:3000  (dùng public/data nếu có, không thì public/sample có nhãn MÔ PHỎNG)
npm run lint && npm test && npm run build
```

Sinh lại dữ liệu mẫu từ Python (dùng CSDL mô phỏng riêng để không đụng dữ liệu thật):

```bash
NEOPULSE_MODE=sim NEOPULSE_DB_PATH=out/web_sim.sqlite neopulse simulate --sessions 6 --reset
for d in 2026-11-16 2026-11-17 2026-11-18; do
  NEOPULSE_MODE=sim NEOPULSE_DB_PATH=out/web_sim.sqlite neopulse export-web --source sim --date $d --indexes VN30,VNINDEX --out web/public/sample
done
```

## Dữ liệu thật: snapshot tĩnh

```bash
neopulse publish-static --source ssi --deploy     # chạy ở thư mục gốc repo: ghi web/public/data/ rồi vercel --prod
```

Web đọc theo thứ tự: `BLOB_READ_URL` (tùy chọn) → `web/public/data/` (snapshot thật, **bị .gitignore**) → `web/public/sample/` (mô phỏng, được commit). Mọi tệp thật chỉ rời máy khi bạn chạy `--deploy`. Không phải thời gian thực.

## Biến môi trường (trên Vercel)

| Biến | Ý nghĩa |
|---|---|
| `ABLY_API_KEY` | Khóa Ably chỉ ở server, cấp token chỉ subscribe kênh neopulse:live. Không cấu hình thì dùng snapshot. |
| `BLOB_READ_URL` | *Tùy chọn, tốn hạn mức*: địa chỉ đọc Blob nếu dùng `neopulse publish`. Bỏ trống = snapshot tĩnh. |

**Không** đặt khóa SSI/NEO hay `BLOB_READ_WRITE_TOKEN` trên Vercel.

## Cấu trúc

```
src/app/            page.tsx (đọc dữ liệu phía máy chủ) · api/data (làm mới) · api/ably-token
src/lib/            types (hợp đồng JSON) · status (tươi/cũ/snapshot) · parse · data (Blob tùy chọn/tĩnh/mẫu) · auth (quyết định truy cập) · format
src/components/     StatusBar · Dashboard (bộ lọc, 8 tab) · tabs · ui
tests/              vitest: trạng thái tươi/cũ, phân tích JSON, cổng dữ liệu, xác thực, định dạng
```

Web công khai, không cần đăng nhập. Snapshot và API chỉ cung cấp chỉ báo tổng hợp; khóa gốc không được gửi xuống trình duyệt. /login cũ chuyển về trang chủ.

## Hồ sơ doanh nghiệp

`/doanh-nghiep` tìm theo mã, tên hoặc ngành. `/doanh-nghiep/MWG` gồm bốn phần: doanh nghiệp/ngành, tài chính/kinh doanh, tóm tắt/rủi ro, định giá/giả định. Các mã trong cảnh báo, bảng thanh khoản, khối ngoại, xếp hạng và danh sách ngành dẫn đến hồ sơ. Bố cục tham khảo phần chính của báo cáo MWG; không đưa phụ lục vào giao diện.

```bash
neopulse company --refresh --symbols MWG,FRT,DGW,PNJ
neopulse company                          # dựng lại toàn bộ hồ sơ từ cache, không gọi mạng
```

Dữ liệu công khai tải qua vnstock/Vietcap, cache tại `data/company/raw/`; JSON hiển thị tại `web/public/data/company/`, cả hai bị Git bỏ qua. Khi triển khai, phải kèm thư mục JSON này; không tự tải dữ liệu doanh nghiệp trên trình duyệt. Mỗi hồ sơ ghi ngày giá, năm BCTC và thời điểm lấy dữ liệu. Mã thiếu hiện thông báo chưa có hồ sơ.

Python tính tỷ số, DuPont, so sánh cùng ICB và bảng độ nhạy DCF. Bội số dùng kết quả năm gần nhất đã tải, không phải TTM. DCF giữ FCFF hoạt động nền cố định 5 năm, WACC 10/12/14%, g 2/3/4%, thuế giả định 20%; đây là minh họa, không phải dự phóng riêng hay giá mục tiêu. Không áp dụng mô hình này cho ngân hàng, bảo hiểm, chứng khoán hoặc khi thiếu đầu vào. Các phân tích chiến lược/thị phần chưa có dữ liệu được ghi rõ, không tạo nội dung thay thế.


## Giao diện & biểu đồ

Phiên mới nhất ưu tiên payload tổng hợp trong Redis (`neopulse:market:latest:<index>`). Bộ relay SSI ghi nền VN30/VNINDEX khoảng mỗi phút, dùng lại kết quả Python; Ably gửi tick khi chỉ số đổi và điểm nhịp khoảng 10–30 giây. Web kiểm tra nền mỗi 20 giây, kể cả khi trước đó chỉ có snapshot tĩnh, và làm mới khi nhận ngày giao dịch mới. Phiên lịch sử dùng khóa riêng theo ngày (giữ 7 ngày trên cloud) hoặc snapshot đã xuất, không trộn với tin live. Không đọc được cloud thì hiện dữ liệu đã lưu kèm thông báo; mất nguồn không được gắn nhãn trực tiếp.

Bộ ghi/relay SSI hiện vẫn chạy trên máy đã cài lịch Windows; máy ngủ hoặc mất mạng thì dữ liệu mới dừng. Redis/Ably không tự lấy dữ liệu SSI. Bot Telegram vẫn chạy trên cloud độc lập.

Trang chủ `/trang-chu` nối sang nhịp thị trường `/` và hồ sơ `/doanh-nghiep`. Header/breadcrumb dùng chung, hỗ trợ quay về cấp cha; breadcrumb thị trường giữ phiên/chỉ số đang chọn. Sáng: xanh băng hà/navy/vàng chanh; tối: xanh rừng/kem/cam. Màu giá chứng khoán vẫn theo quy ước tăng/giảm, độc lập bảng màu trang.

Biểu đồ dùng **TradingView Lightweight Charts 5.3.0** với dữ liệu NeoPulse đã xuất (SSI hoặc Vietcap, tùy trang), không phải nguồn giá TradingView. Có zoom, pan, crosshair, đổi theme và attribution; giấy phép/NOTICE ở public/licenses. Hồ sơ dùng chuỗi so sánh quy về 100, thị trường dùng điểm chỉ số theo phút. Không dựng nến OHLC khi chỉ có giá đóng cửa.

Không dùng iframe Advanced Chart cho HOSE: thử nghiệm MWG trả “This symbol is only available on TradingView”, tức widget không có quyền cung cấp mã đó. Người dùng có link mở mã trên trang TradingView. Xem https://www.tradingview.com/widget-docs/faq/data/ và https://tradingview.github.io/lightweight-charts/docs.


## Telegram tự nguyện & biểu đồ kỹ thuật

`/thong-bao` cho chọn cảnh báo CAO, tin mã cổ phiếu và chính sách; link bot có start payload tương ứng. Đăng ký chỉ tạo khi người dùng nhấn Start trong Telegram. /watch MWG,FPT lọc mã; /all theo VN30; /news on/off, /laws on/off, /alerts on/off; /status; /stop hoặc /delete hủy và xóa đăng ký đang hoạt động.

`api/telegram.py` nhận webhook Telegram, xác thực `TELEGRAM_WEBHOOK_SECRET` và trả lời Start/Help/Web cùng nút mở website. Redis Upstash Free (không tự nâng gói) lưu từng đăng ký mã hóa Fernet, khóa tra cứu HMAC; CAS chống webhook/worker ghi đè, update ID chống lệnh lặp. `/stop` xóa đăng ký và ID, giữ dấu phiên bản mã hóa 7 ngày chống phát lại. `TELEGRAM_STATE_KEY` phải giữ ổn định. Vercel chỉ cần khóa trạng thái/webhook và KV_REST_API_URL/KV_REST_API_TOKEN; không cần bot token.

Workflow `.github/workflows/telegram.yml` chỉ gửi nội dung mới theo đợt khoảng 15 phút (scheduler có thể trễ), đọc đăng ký Redis thay vì gọi getUpdates khi KV đã cấu hình. GitHub Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_STATE_KEY, KV_REST_API_URL, KV_REST_API_TOKEN. Artifact telegram-state mã hóa vẫn dùng để sao lưu, giữ 90 ngày; không có ID plaintext trong Git/log/artifact. Worker kiểm tra lại tùy chọn trước mỗi tin, chỉ ghi đã gửi sau Telegram success; 403 xóa đăng ký. Tối đa 10 tin/người và 100 tin/lượt, xoay vòng để tránh bỏ đói người dùng.

Nguồn: snapshot/API NeoPulse cho cảnh báo; RSS CafeF cho tiêu đề chứa mã; Báo Chính phủ home.rss cho tin pháp luật/chính sách. Chỉ gửi tin mới sau thời điểm bật nhóm, không gửi quá 24 giờ và chống lặp 7 ngày. Ngày đăng bài không được coi là ngày ban hành/hiệu lực; link nguồn luôn đi kèm. RSS Công báo cũ đã thử nhưng hiện trống/không phải XML nên không đưa vào nguồn chạy.

Bot không cần máy cá nhân để lấy RSS/đăng ký, nhưng nguồn cảnh báo thị trường vẫn cần bộ ghi/publisher cập nhật. Snapshot đứng yên không tạo cảnh báo mới; worker không tự có SSI realtime trên cloud. Không đưa khóa SSI/Ably lên GitHub. Không chạy getUpdates song song với webhook. Trước deploy từ repo, chạy `python tools/prepare_web_python.py` để đóng gói đúng mô-đun dùng chung; `web/serverpkg` không chứa Secret.

Danh mục `/doanh-nghiep` dùng `public/data/company/catalog.json` (cổ phiếu HOSE/HNX/UPCoM, không gồm mọi doanh nghiệp tư nhân). Bộ lọc tách toàn thị trường, VN30 và báo cáo đã lưu. `api/company.py` tải BCTC công khai theo yêu cầu cho mã ngoài cache, dùng chung bộ tính Python; cache Redis 6 giờ, khóa chống tải trùng. Thiếu nguồn thì vẫn hiện tên/sàn/ngành và cho thử lại; không tạo số liệu thay thế. Chuỗi giá ngày từ Vietcap được đổi đúng đơn vị trước tính định giá và MA/EMA.

`neopulse charts --refresh` lấy lịch sử VN30/VNINDEX và xuất `public/data/charts`; `neopulse charts` chỉ dựng lại cache. `neopulse company` cũng cập nhật charts cho hồ sơ đã lưu. Khung Phiên là số phút đã ghi; 1T/3T/6T/1N tương ứng tối đa 21/63/126/252 phiên ngày. MA/EMA chu kỳ 5/10/20/50/100/200 đều do Python tính trên toàn bộ chuỗi trước khi chọn phần để vẽ. EMA khởi tạo bằng MA n phiên đầu, alpha=2/(n+1); không vẽ trước đủ n điểm. Các đường nội phiên chỉ tới mốc snapshot; dữ liệu phút chưa thu thập không được bịa từ giá ngày. Đường tham chiếu là tham chiếu phiên đang xem, không phải giá tham chiếu riêng của mọi ngày lịch sử.
