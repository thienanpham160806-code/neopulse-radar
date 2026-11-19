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

Trang chủ `/trang-chu` nối sang nhịp thị trường `/` và hồ sơ `/doanh-nghiep`. Header/breadcrumb dùng chung, hỗ trợ quay về cấp cha; breadcrumb thị trường giữ phiên/chỉ số đang chọn. Sáng: xanh băng hà/navy/vàng chanh; tối: xanh rừng/kem/cam. Màu giá chứng khoán vẫn theo quy ước tăng/giảm, độc lập bảng màu trang.

Biểu đồ dùng **TradingView Lightweight Charts 5.3.0** với dữ liệu NeoPulse đã xuất (SSI hoặc Vietcap, tùy trang), không phải nguồn giá TradingView. Có zoom, pan, crosshair, đổi theme và attribution; giấy phép/NOTICE ở public/licenses. Hồ sơ dùng chuỗi so sánh quy về 100, thị trường dùng điểm chỉ số theo phút. Không dựng nến OHLC khi chỉ có giá đóng cửa.

Không dùng iframe Advanced Chart cho HOSE: thử nghiệm MWG trả “This symbol is only available on TradingView”, tức widget không có quyền cung cấp mã đó. Người dùng có link mở mã trên trang TradingView. Xem https://www.tradingview.com/widget-docs/faq/data/ và https://tradingview.github.io/lightweight-charts/docs.


## Telegram tự nguyện & biểu đồ kỹ thuật

`/thong-bao` cho chọn cảnh báo CAO, tin mã cổ phiếu và chính sách; link bot có start payload tương ứng. Đăng ký chỉ tạo khi người dùng nhấn Start trong Telegram. /watch MWG,FPT lọc mã; /all theo VN30; /news on/off, /laws on/off, /alerts on/off; /status; /stop hoặc /delete hủy và xóa đăng ký đang hoạt động.

Workflow `.github/workflows/telegram.yml` chạy khoảng 15 phút/lượt và có thể bị trễ do scheduler, độc lập laptop. Hai GitHub Actions Secrets: TELEGRAM_BOT_TOKEN và TELEGRAM_STATE_KEY (Fernet, giữ ổn định; đổi khóa sẽ không đọc được đăng ký cũ). Chat ID/tùy chọn/dedupe được mã hóa trong artifact telegram-state, giữ 90 ngày, không có plaintext trong Git/log/artifact. Job nối tiếp, phục hồi artifact mới nhất trước xử lý; lỗi khóa hoặc restore phải dừng. Chỉ ghi đã gửi sau Telegram success; gửi lỗi retry lượt sau, 403 xóa đăng ký. Tối đa 10 tin/người và 100 tin/lượt, xoay vòng để tránh bỏ đói người dùng.

Nguồn: snapshot/API NeoPulse cho cảnh báo; RSS CafeF cho tiêu đề chứa mã; Báo Chính phủ home.rss cho tin pháp luật/chính sách. Chỉ gửi tin mới sau thời điểm bật nhóm, không gửi quá 24 giờ và chống lặp 7 ngày. Ngày đăng bài không được coi là ngày ban hành/hiệu lực; link nguồn luôn đi kèm. RSS Công báo cũ đã thử nhưng hiện trống/không phải XML nên không đưa vào nguồn chạy.

Bot không cần máy cá nhân để lấy RSS/đăng ký, nhưng nguồn cảnh báo thị trường vẫn cần bộ ghi/publisher cập nhật. Snapshot đứng yên không tạo cảnh báo mới; worker không tự có SSI realtime trên cloud. Không đưa khóa SSI/Ably lên GitHub. Không sửa webhook hiện có; dùng getUpdates (bot đã kiểm tra không có webhook). Nếu sau này bật webhook, cần chuyển hẳn cơ chế tiếp nhận để tránh xung đột.

`neopulse charts --refresh` lấy lịch sử VN30/VNINDEX và xuất `public/data/charts`; `neopulse charts` chỉ dựng lại cache. `neopulse company` cũng cập nhật charts cho hồ sơ đã lưu. Khung Phiên là số phút đã ghi; 1T/3T/6T/1N tương ứng tối đa 21/63/126/252 phiên ngày. MA/EMA chu kỳ 5/10/20/50/100/200 đều do Python tính trên toàn bộ chuỗi trước khi chọn phần để vẽ. EMA khởi tạo bằng MA n phiên đầu, alpha=2/(n+1); không vẽ trước đủ n điểm. Các đường nội phiên chỉ tới mốc snapshot; dữ liệu phút chưa thu thập không được bịa từ giá ngày. Đường tham chiếu là tham chiếu phiên đang xem, không phải giá tham chiếu riêng của mọi ngày lịch sử.
