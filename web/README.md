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
