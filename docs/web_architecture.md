# Kiến trúc triển khai web (Vercel)

## Sơ đồ

```
MÁY CỦA TÁC GIẢ (giữ khóa SSI/NEO)                          VERCEL
┌────────────────────────────────────────────────┐        ┌───────────────────────────────┐
│ neopulse record ──► SQLite (WAL)               │        │  Vercel Blob (JSON, public)   │
│                        │ đọc, mode=ro          │  PUT   │   latest.json  (ghi đè 20 s)  │
│ neopulse publish ◄─────┘                       ├───────►│   sessions/…json · index.json │
│   build_view → webexport (JSON) → HTTP PUT     │        └──────────────┬────────────────┘
└────────────────────────────────────────────────┘                       │ fetch, revalidate 15 s
                                                          ┌──────────────▼────────────────┐
                                                          │  web/ Next.js (App Router)     │
                                                          │  middleware mật khẩu · 8 tab   │
                                                          └──────────────┬────────────────┘
                                                                         ▼  trình duyệt / điện thoại
```

Luồng một chu kỳ: `record` ghi SQLite → `publish` mở SQLite **chỉ đọc**, gọi `build_view` (cùng hàm Streamlit dùng) → `analytics/webexport.py` biến kết quả thành JSON → `PUT` lên Vercel Blob → web đọc JSON phía máy chủ rồi dựng giao diện. Mọi công thức nằm ở Python; web chỉ hiển thị (không có công thức tài chính nào bằng JavaScript).

## Vì sao thiết kế như vậy

| Câu hỏi | Trả lời |
|---|---|
| Vì sao không đưa Streamlit lên Vercel? | Vercel chạy hàm serverless ngắn hạn, không giữ tiến trình dài. Streamlit cần một tiến trình Python sống lâu và kết nối WebSocket hai chiều tới trình duyệt; không chạy được trên mô hình này. |
| Vì sao bộ ghi phải ở máy tác giả? | Bộ ghi giữ kết nối WebSocket SSI nhiều giờ liên tục và giữ khóa API. Vercel không giữ được kết nối dài; đặt khóa lên đám mây cũng mở rộng bề mặt rò rỉ. Khóa chỉ nằm trong `.env` trên máy tác giả. |
| Vì sao không đưa SQLite lên Vercel? | Hệ tệp của hàm serverless chỉ đọc/tạm thời; SQLite ghi bền vững không có chỗ lưu. |
| Vì sao chọn Vercel Blob? | Cùng hệ sinh thái Vercel, không cần dựng cơ sở dữ liệu hay máy chủ; chỉ cần một HTTP `PUT` có token và một URL đọc cố định. Mô hình "đẩy JSON tĩnh" tách hẳn nguồn dữ liệu khỏi web: web sập không ảnh hưởng bộ ghi, bộ ghi dừng thì web chỉ thấy dữ liệu cũ đi và báo rõ. |
| Vì sao gửi chỉ báo tổng hợp, không gửi bảng giá thô? | Giảm dung lượng, giảm rủi ro tái phân phối dữ liệu thị trường của nhà cung cấp, và đúng mục tiêu sản phẩm (diễn giải, không phải bảng giá). |

## Hợp đồng dữ liệu (`schema_version = 1`)

`latest.json` · `latest_<CHỈ SỐ>.json` · `sessions/<nguồn>_<ngày>_<chỉ số>.json` · `index.json` (danh sách phiên đã xuất).

| Khối | Nội dung |
|---|---|
| `meta` | nguồn, `is_simulated`, `generated_at` (+07:00), `last_update`, `trading_date`, `data_status`, số mã tính/bị loại, số phiên, các ngày có dữ liệu, dòng cảnh báo miễn trừ trách nhiệm |
| `pulse` | điểm 0–100, nhãn, thành phần và trọng số, độ nhạy ±50%, chuỗi theo phút, câu nhận định dựng từ số liệu |
| `index`, `breadth` | chỉ số đang xem + chuỗi; độ rộng của sàn và độ rộng tự tính trên rổ |
| `ranking`, `alerts` | xếp hạng đa yếu tố; cảnh báo (CAO/TRUNG BÌNH/THẤP) |
| `book` | theo mã: OBI₃, spread, độ sâu, trượt giá ước lượng, điểm thanh khoản; chuỗi giá giữa/OBI₃ theo phút cho 20 mã giá trị lớn nhất |
| `foreign`, `futures` | khối ngoại theo mã; basis HĐTL |
| `validation` | IC trong/ngoài mẫu, IC theo phiên, chất lượng dữ liệu (tính thưa, mỗi ~10 phút) |

`data_status.state` ∈ `fresh` · `stale` · `error` · `closed`. `closed` (ngoài giờ giao dịch, nghỉ trưa, phiên lịch sử) **không phải lỗi**; web hiển thị "phiên đã kết thúc". Web tự tính lại độ tươi từ `last_update` và đồng hồ trình duyệt/máy chủ (xanh < 60 s, cam < 5 phút, đỏ còn lại) vì JSON chỉ là ảnh chụp tại `generated_at`.

NaN/∞ được đổi thành `null` ở bước xuất; JSON được ghi với `allow_nan=False`.

## Giới hạn (nói thẳng)

- **Độ trễ không phải tick-by-tick.** Chuỗi trễ cộng dồn: bộ ghi gom lô ≤ 5 s + chu kỳ `publish` 20 s + cache CDN của Vercel Blob (đặt `x-cache-control-max-age` = 60 s, **mức tối thiểu** Vercel cho phép) + `revalidate` 15 s của web. Ước tính trung thực: **nửa phút đến ~1,5 phút** từ khi tin về máy tới khi hiện trên màn hình. Con số thực đo được sẽ ghi ở mục "Đo độ trễ" bên dưới sau lần chạy thật.
- Blob URL **công khai**: ai biết đường dẫn đều đọc được JSON, mật khẩu chỉ bảo vệ trang web. Vì vậy chỉ xuất chỉ báo tổng hợp; muốn khóa hẳn cần chuyển sang Blob riêng tư (cần đưa token đọc lên Vercel).
- Web chỉ phản ánh những gì `publish` đã đẩy; máy tác giả tắt hoặc mất mạng thì dữ liệu cũ đi (đỏ), không có dữ liệu "tự bịa".

## Bảo mật

- Khóa SSI/NEO và `BLOB_READ_WRITE_TOKEN` chỉ ở `.env` trên máy tác giả. Trên Vercel chỉ đặt `BLOB_READ_URL` (địa chỉ đọc) và `SITE_PASSWORD`.
- `publish` mở SQLite với `mode=ro` + `PRAGMA query_only`: không thể ghi, nên chạy song song với `record` an toàn.
- Log che token; thông báo lỗi Blob không chứa token.
- Middleware yêu cầu mật khẩu (`SITE_PASSWORD`, cookie `httpOnly`); nếu không đặt, trang chỉ cho xem khi dữ liệu là **mô phỏng**.

## Chạy khi có dữ liệu thật

Chuẩn bị một lần: tạo Blob store trên Vercel, đặt `BLOB_READ_WRITE_TOKEN` và `BLOB_PREFIX=neopulse` trong `.env` (máy ghi), đặt `BLOB_READ_URL`, `SITE_PASSWORD` trên Vercel (xem `web/README.md`).

Trước phiên (≈ 8:45):
- [ ] `neopulse check` báo `Kết nối REST SSI: OK`; `git status` không liệt kê `.env`.
- [ ] `neopulse export-web --source ssi --no-validation --out out/web_try` chạy được (kể cả khi chưa có dữ liệu: ra JSON trạng thái `error` rõ ràng, không crash).
- [ ] `neopulse publish --source ssi --dry-run --until 00:00` ghi được `out/web/latest.json`.

Trong phiên, **hai cửa sổ terminal**:

```bash
neopulse --log-level INFO record --until 15:05            # cửa sổ 1: ghi dữ liệu
neopulse --log-level INFO publish --every 20 --until 15:05   # cửa sổ 2: đẩy lên web
```

Kiểm tra trên điện thoại: mở URL production → nhập mật khẩu → thanh trạng thái hiện *SSI FastConnect (dữ liệu thật)*, chấm xanh, "cách đây" < 60–90 s; bật chế độ máy bay 30 giây rồi bật lại để thấy chấm chuyển cam/đỏ rồi xanh lại; sau 15:05 thanh trạng thái chuyển "phiên đã kết thúc".

Cuối phiên `publish` tự ghi thêm `sessions/…json` và cập nhật `index.json` để chọn lại phiên cũ trên web.
