# NeoPulse Radar — bản web (Next.js trên Vercel)

Web **chỉ hiển thị** chỉ báo do Python tính (`neopulse export-web`). Không có công thức tài chính nào bằng JavaScript, không có khóa SSI/NEO, không có SQLite. Kiến trúc và giới hạn: [`../docs/web_architecture.md`](../docs/web_architecture.md).

## Chạy thử cục bộ (dữ liệu MÔ PHỎNG đi kèm)

```bash
cd web
npm install
npm run dev          # http://localhost:3000  (dùng web/public/sample/*.json, có nhãn MÔ PHỎNG)
npm run lint && npm test && npm run build
```

Sinh lại dữ liệu mẫu từ Python (dùng CSDL mô phỏng riêng để không đụng dữ liệu thật):

```bash
NEOPULSE_MODE=sim NEOPULSE_DB_PATH=out/web_sim.sqlite neopulse simulate --sessions 6 --reset
for d in 2026-11-16 2026-11-17 2026-11-18; do
  NEOPULSE_MODE=sim NEOPULSE_DB_PATH=out/web_sim.sqlite neopulse export-web --source sim --date $d --indexes VN30,VNINDEX --out web/public/sample
done
```

## Biến môi trường (trên Vercel)

| Biến | Ý nghĩa |
|---|---|
| `BLOB_READ_URL` | Địa chỉ đọc thư mục Blob chứa JSON, không có `/` cuối, VD `https://<storeid>.public.blob.vercel-storage.com/neopulse`. Không đặt ⇒ dùng dữ liệu mẫu MÔ PHỎNG. |
| `SITE_PASSWORD` | Mật khẩu trang. Không đặt ⇒ chỉ xem được dữ liệu MÔ PHỎNG (dữ liệu thật bị khóa). |

**Không** đặt khóa SSI/NEO hay `BLOB_READ_WRITE_TOKEN` trên Vercel; các khóa đó chỉ nằm trong `.env` trên máy ghi dữ liệu.

## Triển khai

Dự án Vercel `neopulse-radar`, Root Directory = `web` (khi triển khai từ Git); từ máy: `cd web && vercel --prod`. Đặt biến:

```bash
vercel env add SITE_PASSWORD production      # tự nhập mật khẩu khi được hỏi
vercel env add BLOB_READ_URL production
vercel --prod
```

## Cấu trúc

```
src/app/            page.tsx (đọc dữ liệu phía máy chủ) · api/data (làm mới) · api/login · login/
src/middleware.ts   chặn khi đã đặt SITE_PASSWORD mà chưa có cookie httpOnly hợp lệ
src/lib/            types (hợp đồng JSON) · status (tươi/cũ) · parse · data (Blob/mẫu) · auth · format
src/components/     StatusBar · Dashboard (bộ lọc, 8 tab) · tabs · ui
tests/              vitest: trạng thái tươi/cũ, phân tích JSON, cổng dữ liệu, xác thực, định dạng
```
