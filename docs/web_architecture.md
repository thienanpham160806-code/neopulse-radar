# Kiến trúc triển khai web (Vercel) — chế độ SNAPSHOT TĨNH

## Sơ đồ

```
MÁY CỦA TÁC GIẢ (giữ khóa SSI/NEO)                                   VERCEL
┌───────────────────────────────────────────────┐              ┌──────────────────────────────────┐
│ neopulse record ──► SQLite (WAL)              │              │  web/ Next.js (App Router)        │
│                        │ đọc, mode=ro         │   vercel     │   public/data/*.json  (tĩnh)      │
│ neopulse publish-static ◄┘                    ├──  --prod ──►│   web công khai · 5 tab          │
│   build_view → webexport → web/public/data/   │  (chủ động)  └───────────────┬──────────────────┘
└───────────────────────────────────────────────┘                              ▼ trình duyệt / điện thoại
```

Luồng: `record` ghi SQLite trong phiên → **sau phiên** (hoặc khi muốn chụp giữa phiên) chạy `neopulse publish-static --source ssi --deploy` → lệnh mở SQLite **chỉ đọc**, gọi `build_view` (cùng hàm Streamlit dùng), ghi JSON vào `web/public/data/` rồi `vercel --prod` trong `web/`. Web đọc các tệp tĩnh đó phía máy chủ. Mọi công thức nằm ở Python; web chỉ hiển thị.

## Vì sao snapshot tĩnh (thay cho đẩy liên tục lên Vercel Blob)

| Lý do | Giải thích |
|---|---|
| **Hạn mức gói Hobby** | Vercel Blob Hobby chỉ có 2.000 thao tác nâng cao mỗi tháng. Đẩy `latest.json` mỗi 20 giây (~1.000 lần/phiên, chưa tính tệp phiên) hết hạn mức sau 2–3 phiên. Snapshot tĩnh tốn **0** thao tác Blob; mỗi lần triển khai chỉ là một deployment. |
| **Truy cập dữ liệu** | Web công khai chỉ báo tổng hợp. Snapshot thật không vào Git; khóa SSI/NEO chỉ ở máy ghi, khóa Ably chỉ ở server. |
| **Độ trễ trung thực** | Đồ án phân tích cuối phiên chứ không phải bảng giá thời gian thực. Thay vì ra vẻ gần-thời-gian-thực với độ trễ 0,5–1,5 phút khó kiểm soát (CDN Blob cache tối thiểu 60 s), web nói thẳng: **snapshot, không phải thời gian thực**, kèm giờ chụp. |
| Đơn giản | Không cần token ghi trên đám mây, không có vòng lặp mạng có thể rớt giữa phiên. |

Vì sao không đưa Streamlit lên Vercel: Vercel chạy hàm serverless ngắn hạn, không giữ tiến trình Python sống lâu và WebSocket hai chiều; SQLite không có chỗ lưu bền. Bộ ghi cũng phải ở máy tác giả vì giữ kết nối WebSocket SSI nhiều giờ và giữ khóa API.

## Quy trình

```bash
neopulse publish-static --source ssi                     # ghi web/public/data/ (chưa triển khai)
neopulse publish-static --source ssi --deploy            # ghi + `vercel --prod` trong web/ + in URL
neopulse publish-static --source ssi --date 2026-11-19 --indexes VN30,VNINDEX --deploy
neopulse publish-static --source ssi --all-dates         # mọi phiên đã lưu (để chọn lại phiên cũ trên web)
```

`web/public/data/` gồm `latest.json`, `latest_<CHỈ SỐ>.json`, `sessions/<nguồn>_<ngày>_<chỉ số>.json`, `index.json`. Mỗi tệp có `meta.snapshot_at`, `meta.snapshot_kind` (`end_of_session` | `intraday`), `meta.snapshot_label` ("Snapshot cuối phiên" / "Snapshot giữa phiên (dừng lúc HH:MM)") và `meta.snapshot_realtime = false`.

Nhiều phiên: chạy `--all-dates` một lần, hoặc chạy từng ngày (`index.json` được gộp, không mất phiên cũ). Dữ liệu cũ trong `public/data/` vẫn nằm đó cho tới khi bạn xóa.

## Hợp đồng dữ liệu (`schema_version = 1`)

| Khối | Nội dung |
|---|---|
| `meta` | nguồn, `is_simulated`, `generated_at`, `last_update`, `snapshot_*`, `trading_date`, `data_status`, số mã tính/loại, số phiên, các ngày có dữ liệu, dòng miễn trừ trách nhiệm |
| `pulse` | điểm 0–100, nhãn, thành phần và trọng số, độ nhạy ±50%, chuỗi theo phút, câu nhận định dựng từ số liệu |
| `index`, `breadth` | chỉ số đang xem + chuỗi; độ rộng của sàn và độ rộng tự tính trên rổ |
| `ranking`, `alerts` | xếp hạng đa yếu tố; cảnh báo (CAO/TRUNG BÌNH/THẤP) |
| `book` | theo mã: OBI₃, spread, độ sâu, trượt giá ước lượng, điểm thanh khoản; chuỗi giá giữa/OBI₃ theo phút cho 20 mã giá trị lớn nhất |
| `foreign`, `futures` | khối ngoại theo mã; basis HĐTL |
| `validation` | IC trong/ngoài mẫu, IC theo phiên, chất lượng dữ liệu |

NaN/∞ → `null` ở bước xuất (`allow_nan=False`). Chỉ có chỉ báo tổng hợp, không có bảng giá/sổ lệnh thô.

## Trạng thái hiển thị của snapshot

Thanh trạng thái luôn hiện: nguồn · "Snapshot lúc HH:MM:SS (giờ VN)" · "cách đây X" · "Không phải thời gian thực" · số mã tính/loại.

| Trường hợp | Chấm | Ghi chú |
|---|---|---|
| Snapshot **cuối phiên** | xanh dương | Không bao giờ đỏ chỉ vì cũ (dữ liệu vốn đứng yên). |
| Snapshot **giữa phiên** | cam | Nhắc rằng thị trường có thể đã thay đổi sau lúc chụp. |
| Dữ liệu **MÔ PHỎNG** | tím | Nhãn MÔ PHỎNG luôn nổi bật. |
| Lỗi (không có dữ liệu, JSON hỏng) | đỏ | Hiện lý do. |

Không có `meta.snapshot_at` (chế độ Blob tùy chọn) thì web dùng logic thời gian thực cũ: xanh < 60 s, cam < 5 phút, đỏ còn lại; ngoài giờ giao dịch là "phiên đã kết thúc".

## Bảo mật

- Khóa SSI/NEO chỉ ở máy ghi; Vercel chỉ giữ ABLY_API_KEY dạng Secret để cấp token subscribe-only.
- `public/data/` nằm trong `.gitignore` (chỉ `public/sample/` — mô phỏng — được commit); `web/.vercelignore` bảo đảm `vercel --prod` vẫn tải thư mục này lên (Vercel CLI mặc định bỏ các tệp trong `.gitignore`). Kiểm thử tự động xác nhận `git check-ignore` đúng và không có tệp `public/data` nào được theo dõi.
- Trang, /api/data và /data/* mở công khai, không kiểm tra mật khẩu/cookie. Không công bố khóa hoặc bảng giá/sổ lệnh thô.
- `publish-static` mở SQLite với `mode=ro`: không thể ghi, chạy song song với `record` an toàn.

**Trước khi triển khai:** kiểm tra snapshot chỉ chứa chỉ báo tổng hợp và khóa không nằm trong bundle client.

## Tùy chọn: đẩy liên tục lên Vercel Blob (`neopulse publish`)

Vẫn còn trong mã nguồn nhưng **không bắt buộc và tốn hạn mức** (Hobby: 2.000 thao tác/tháng). Cần `BLOB_READ_WRITE_TOKEN`/`BLOB_PREFIX` trong `.env` (máy ghi) và `BLOB_READ_URL` trên Vercel; khi `BLOB_READ_URL` được đặt, web ưu tiên đọc Blob rồi mới tới snapshot tĩnh. Giới hạn đã biết: CDN Blob cache tối thiểu 60 s ⇒ độ trễ ước tính nửa phút đến ~1,5 phút (chưa đo thật); Dữ liệu tổng hợp trên Blob cũng được truy cập công khai.

## Triển khai hiện tại

- Dự án Vercel neopulse-radar: https://neopulse-radar.vercel.app — snapshot SSI tổng hợp, realtime qua Ably khi relay hoạt động.
- Web công khai snapshot SSI và token realtime chỉ subscribe; không có bước đăng nhập.

## Chạy khi có dữ liệu thật

Trước phiên (≈ 8:45): `neopulse check` báo `Kết nối REST SSI: OK`; `git status` không liệt kê `.env`; `neopulse publish-static --source ssi` chạy được (nếu chưa có dữ liệu sẽ báo lỗi rõ, không tạo JSON rỗng).

Trong phiên: `neopulse record --until 15:05` (không cần chạy gì thêm).

Sau phiên:
1. `neopulse validate --source ssi` (kiểm tra số phiên, chất lượng dữ liệu).
2. Kiểm tra ABLY_API_KEY production nếu muốn bật realtime.
3. `neopulse publish-static --source ssi --deploy`.
4. Mở URL trên điện thoại, không cần đăng nhập; kiểm tra nguồn SSI và thời điểm snapshot.

## Chế độ TRỰC TIẾP qua Ably (tùy chọn, snapshot vẫn là dự phòng)

```
record (--flush-every 1) ──► SQLite ──(chỉ đọc)──► neopulse live-relay ──REST──► Ably kênh neopulse:live ──SSE──► trình duyệt
                                                                                        ▲ token chỉ subscribe, 15 phút
                                                                       /api/ably-token (Vercel, chỉ subscribe)
```

- `neopulse live-relay --source ssi --until 15:05` gửi `tick` khoảng 1 giây (chỉ khi đổi; tin thật 588 B), `pulse` khoảng 10 giây (8 × thời gian `build_view` đo thật 0,65 s, kẹp 10–30 giây; tin thật 2,9 KB) và `status` (bắt đầu/kết thúc/đổi pha/mất dữ liệu > 60 giây). Mỗi tin có `ts`, `source`, `is_simulated`, `seq`. Chỉ có số liệu tổng hợp.
- Hạn mức Free 6.000.000 tin/tháng tính cả tin giao tới người xem: `out/ably_usage.json` ước tính = đã gửi × (1 + người xem, mặc định 5). Vượt 70% thì giãn nhịp ×5. Ước tính một phiên: khoảng 16.000 tick + 1.600 pulse ≈ 17.600 tin × 6 ≈ 106.000; 22 phiên ≈ 2,3 triệu (khoảng 39%).
- Trình duyệt không dùng SDK: `EventSource` tới `https://realtime.ably.io/sse` với token chỉ subscribe. Gói `ably` 2.30 không qua được SWC của Next 15 (lỗi `'super' keyword outside a method`), nên không dùng. Mất tin > 60 giây, ngoài giờ, lỗi kết nối hoặc relay báo kết thúc thì thanh trạng thái quay về "Snapshot lúc …".
- /api/ably-token công khai, chỉ cấp quyền subscribe neopulse:live, hạn 15 phút; thiếu ABLY_API_KEY trả 503 và web dùng snapshot.
- Đặt khóa trên Vercel (tự chạy, không đặt hộ): `cd web && vercel env add ABLY_API_KEY production` (và `preview` nếu muốn thử bản preview).
- Task Scheduler (`scripts/run_record_session.ps1`) tự chạy `live-relay` song song khi `.env` có `ABLY_API_KEY` (kiểm tra bằng mã thoát, không in giá trị); log ở `out/relay_<ngày>.log`.


### Định danh client Ably

Namespace Ably có thể yêu cầu identified client (lỗi 40161). Relay REST gửi header `X-Ably-ClientId` mã hóa base64 cho `neopulse-relay`; token trình duyệt gắn `clientId=neopulse-web`, vẫn chỉ subscribe `neopulse:live`, hạn 15 phút. Không cần nới rule hoặc capability của tài khoản. Kiểm thử thật 19/11/2026 đã xác nhận gửi/nhận probe sau khi bổ sung định danh; HTTP 200 của SSE riêng lẻ chưa đủ chứng minh nhận tin.

## Thiết kế giao diện: khung "Bản tin", ghép mobile kiểu "Ứng dụng" (chốt 19/11/2026)

**Cách chọn.** Dựng ba hướng khác biệt rõ trên cùng lớp dữ liệu, cùng luồng trực tiếp mô phỏng (route `/preview/a|b|c`, đã gỡ sau khi chọn; ảnh còn trong `docs/img/design_options/`):

| Hướng | Mô tả | Nielsen | Dễ đọc / demo / mobile (1–5) |
|---|---|---|---|
| A "Terminal" | nền tối, mật độ cao | 23/40 | 3 / 2 / 2 |
| B "Bản tin" | nền sáng kiểu báo tài chính, tiêu đề + chú thích | ≈24/40 | 4 / 4 / 3 |
| C "Ứng dụng" | thẻ, ưu tiên điện thoại, chạm để đi sâu | 22/40 | 4 / 2 / 4 |

Chấm bằng `critique` của impeccable: thẩm định thiết kế độc lập cho từng hướng, cộng detector và đo trên trình duyệt (tương phản, tràn ngang, vùng chạm, giảm chuyển động). **Chọn B làm khung** vì hợp nhất với người chấm và gần bản tin mẫu của giảng viên. **Ghép mobile của C**: trên điện thoại, dải chỉ số và cảnh báo lên đầu, có thanh tab đáy (Tổng quan, Cảnh báo, Khối ngoại, Thêm). A giữ làm gợi ý cho một chế độ "theo dõi liên tục" sau này.

**Sửa theo kết quả chấm (áp dụng cho cả 8 tab):**
- Không mượn màu giá cho nghĩa khác: điểm nhịp dùng thang trung tính; trạng thái dữ liệu dùng accent và độ đậm mực; mức cảnh báo dùng ◆◇· thay vì đỏ/vàng; MÔ PHỎNG đổi sang xám đá, không còn lẫn với tím trần.
- Mọi số có dấu đều kèm ▲▼■, kể cả khối ngoại ròng và đóng góp ngành.
- Số trong câu nhận định và thông điệp cảnh báo (do Python sinh) chuyển sang định dạng Việt Nam (1.933,61).
- Biểu đồ chỉ số có đường tham chiếu (Python xuất `index.row.ref`).
- Màn lỗi có giờ của dữ liệu tốt gần nhất, nút "Tải lại" và "Đọc phương pháp".
- `role="tabpanel"` chuyển khỏi thẻ `<main>`.

**Lệnh impeccable đã chạy:** `context` (chưa có PRODUCT.md nên viết `PRODUCT.md` và `web/DESIGN_CONTEXT.md` từ yêu cầu của tác giả), `critique` (ba hướng), `detect` (sạch, mã thoát 0), `polish`/`adapt`/`audit`/`optimize` theo các phát hiện trên. Bỏ bước quay ngẫu nhiên `concept-seed` vì ba hướng do tác giả chỉ định.

**Lighthouse mobile** (trang chính, trung vị 5 lần, cùng máy, dữ liệu mô phỏng):

| | Performance | Accessibility | TBT | LCP | First Load JS |
|---|---|---|---|---|---|
| Trước (giao diện cũ) | 71 | 100 | 667 ms | 4,0 s | 244 kB |
| Sau | 76 | 100 | 599 ms | 3,5 s | 117 kB |

Phần cải thiện chính đến từ việc tải lười Recharts và 7 tab phụ. Số đo dao động mạnh trên máy đang chạy bộ ghi (67–80), vì vậy mới lấy trung vị.
