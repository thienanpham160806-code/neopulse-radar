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
