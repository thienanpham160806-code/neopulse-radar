# Kế hoạch kiểm thử và kiểm chứng

## 1. Kiểm thử tự động (`pytest`, 94 ca, không cần mạng)

| Tệp | Kiểm tra | Vì sao quan trọng |
|---|---|---|
| `test_normalize.py` | Ví dụ gốc trong tài liệu NEO API; giá dạng chuỗi; `ATO`/`ATC`; số âm; sai kiểu; sổ lệnh chéo; giá ngoài biên độ; ngày dd/mm/YYYY; dấu thời gian tương lai | Dữ liệu bẩn không được làm sập hay làm sai chỉ báo |
| `test_microstructure.py` | OBI, microprice, spread với số tính tay; đối xứng; sổ lệnh một phía → trống; trượt giá khớp đủ/khớp thiếu; thanh lấy trạng thái cuối; không lấy hiệu qua ranh giới phiên | Tính đúng công thức |
| `test_finance.py` | A/D, phân kỳ, khối ngoại, basis không dùng chỉ số tương lai, bỏ chỉ số trễ, điểm nhịp ở cực trị, chuẩn hóa lại khi thiếu thành phần, từ chối kết luận khi thiếu dữ liệu | Logic tài chính |
| `test_anomaly_alerts.py` | z bền vững bắt đột biến; **đổi dữ liệu tương lai không đổi z quá khứ**; chuỗi đứng yên → trống; cooldown; OBI phải kéo dài và cùng dấu; nâng mức khi nhiều quy tắc; tính riêng từng mã | Không nhìn trước, không báo động giả |
| `test_neo_client.py` | Header bắt buộc; đăng nhập lại đúng một lần khi 401; làm mới token trước hạn; 403 không thử lại; 5xx thử lại có giới hạn; lỗi nghiệp vụ không thử lại; phản hồi không phải JSON; lỗi mạng; **chặn `/trading/orders`**; chia lô 10 mã; phân trang; mọi request qua bộ giới hạn; đúng 5 req/giây; mật khẩu không lọt vào thông báo lỗi | Sử dụng API đúng và có trách nhiệm |
| `test_ws.py` | Phân loại 4 kênh theo ví dụ tài liệu; chịu được phong bì/mảng/rác; thứ tự auth → sub; bỏ dữ liệu trước khi xác thực; sai token; rớt kết nối → nối lại và đăng ký lại; im lặng → coi là treo; lùi dần có giới hạn | Mất kết nối, thông điệp bất thường |
| `test_ingest_storage.py` | Múi giờ VN giữ nguyên qua lưu/đọc; khử lặp; loại tin đến muộn; cho phép đặt lại lũy kế sang phiên mới; ghi log thông điệp lạ; tự ghi theo lô; ràng buộc duy nhất; xóa theo nguồn | Lặp, muộn, thời gian |
| `test_validation_ranking.py` | Tách theo thời gian; lợi suất tương lai dừng ở cuối phiên; IC bắt được tín hiệu cài và ≈ 0 với nhiễu; IC khớp `scipy.stats.spearmanr`; mẫu nhỏ → trống kèm ghi chú | Kiểm chứng không tự lừa mình |
| `test_explain_config.py` | Số bịa bị loại; ngôn ngữ khuyến nghị bị loại; lỗi gọi mô hình → mẫu câu; cấu hình che bí mật; log che JWT/mật khẩu; Telegram tùy chọn, không ném lỗi | Mục 13 của đề và bảo mật |
| `test_end_to_end.py` | Sinh → lưu → chỉ báo → cảnh báo → bản tin → CLI; mô phỏng tuân thủ bước giá/biên độ; `as_of` không dùng dữ liệu sau đó và **cảnh báo quá khứ không đổi khi có thêm dữ liệu**; trạng thái rỗng; polling sống sót khi API lỗi; đối chiếu WS–REST bắt lệch | Toàn chuỗi |

## 2. Tình huống lỗi trên giao diện

| Tình huống | Hành vi mong đợi | Cách tái hiện |
|---|---|---|
| CSDL trống | Thanh bên hiện nút tạo dữ liệu mô phỏng + lệnh chạy bộ ghi | xóa `data/neopulse.sqlite` |
| Bộ ghi dừng/mất kết nối | Trạng thái 🟠, băng đỏ "dữ liệu đã cũ N phút", số liệu giữ nguyên | dừng `neopulse record` |
| Bộ lọc không có dữ liệu | Thông báo rõ, không biểu đồ rỗng | chọn mã không có trong phiên |
| Thiếu thành phần điểm nhịp | Ghi rõ thành phần thiếu; < 50% trọng số → không hiện điểm | phiên đầu tiên (chưa có lịch sử thanh khoản) |
| Không có HĐTL | Tab Phái sinh giải thích lý do | chọn chỉ số khác VN30 |
| Lỗi khi tính | Hộp lỗi nêu loại lỗi; các phần khác vẫn dùng được | — |
| Dữ liệu mô phỏng | Băng vàng trên mọi trang, nhãn trong bản tin và tin Telegram | nguồn *Mô phỏng* |

## 2b. Kiểm thử bản web (`web/`, Python + vitest)

| Ca | Kiểm bằng | Kỳ vọng |
|---|---|---|
| Schema JSON đủ khối, `schema_version`=1, thời gian có +07:00 | `tests/test_webexport.py` | meta, pulse, index, breadth, ranking, alerts, book, foreign, futures, validation |
| NaN/inf -> null, kiểu numpy -> Python | pytest + `allow_nan=False` | JSON hợp lệ nghiêm ngặt |
| Nhãn MÔ PHỎNG và trạng thái | pytest, vitest | `is_simulated`, `source_label`="MÔ PHỎNG", web luôn hiện nhãn |
| Không bí mật, không sổ lệnh thô trong JSON | pytest, vitest (quét chuỗi) | không có password/secret/token/bid1/ask1... |
| Trạng thái fresh/stale/error/closed; ngoài giờ không phải lỗi | pytest + vitest (40 ca) | ngưỡng xanh <60 s, cam <5 phút, đỏ; "phiên đã kết thúc" |
| SQLite mở chỉ đọc | pytest | thử `DELETE` báo `OperationalError`; thiếu CSDL ném `FileNotFoundError` |
| `publish-static` sinh đúng tệp (latest, sessions, index) với `snapshot_at/kind/label`, `snapshot_realtime=false` | `tests/test_webstatic.py` | cuối phiên khi phiên đã đóng, giữa phiên khi đang mở |
| JSON snapshot không bí mật, không sổ lệnh thô, không NaN; không sửa CSDL nguồn | pytest | quét chuỗi, `parse_constant`, so mtime/size |
| `--deploy` chạy `vercel --prod --yes` trong `web/`, in URL alias; lỗi báo rõ | pytest (runner giả) | thiếu vercel / thư mục sai / mã thoát khác 0 |
| Dữ liệu thật không vào git | pytest (`git check-ignore`, `git ls-files`) | `web/public/data/**` bị ignore; `web/public/sample/**` được theo dõi và đều `is_simulated` |
| Trạng thái snapshot: cuối phiên không bao giờ đỏ, giữa phiên cam, MÔ PHỎNG/lỗi giữ nguyên | vitest (`snapshot.test.ts`) | 11 ca |
| Web/API/snapshot công khai, không cần cookie | vitest + HTTP production | 200 |
| `publish --dry-run` (Blob, tùy chọn) không gọi mạng | pytest (chặn `httpx.Client.put`) | ghi `latest.json`, `index.json` cục bộ |
| Blob: ghi đè cùng đường dẫn, header đúng giao thức | pytest (MockTransport) | `x-allow-overwrite=1`, `x-add-random-suffix=0` |
| Mạng rớt: thử lại lùi dần, không crash, log không lộ token | pytest | chờ 1 s, 2 s...; `failures>0` nhưng vòng lặp vẫn chạy đủ chu kỳ |
| CSDL thiếu: đẩy trạng thái `error` để web hiện rõ | pytest | `latest.json` có `data_status.state="error"` |
| Token Ably công khai vẫn chỉ subscribe, TTL ngắn và không lộ khóa | vitest + HTTP production | 200, capability chỉ subscribe; thiếu key:503 |
| Bố cục di động 390 px, không tràn ngang, 8 tab, sáng/tối | puppeteer chụp từng tab | `scrollWidth` = 390; ảnh trong `docs/img/web_*_sim.png` |

## 3. Kiểm chứng với dữ liệu thật — **việc còn phải làm**

| Việc | Bằng chứng đưa vào báo cáo |
|---|---|
| Đối chiếu 3–5 mã với bảng giá NEO Invest cùng thời điểm | ảnh chụp hai bên |
| Đối chiếu WebSocket với REST | số dòng `reconcile` và `ws_rest_mismatch` trong `quality_log` |
| Độ ổn định kết nối một phiên | `ingest_runs`: số tin, số lần nối lại, số bị loại/lặp |
| Khoảng trống dữ liệu | `neopulse validate` mục [1] |
| IC ngoài mẫu sau ≥ 5 phiên | bảng `neopulse validate --source neo` — báo cả khi yếu |
| Tần suất cảnh báo mỗi phiên theo quy tắc | mục [4]; nếu quá dày, điều chỉnh ngưỡng và ghi lại lý do |
| Thử lỗi có chủ đích (rút mạng, sai mật khẩu) | ảnh log + ảnh dashboard |

## 4. Kết quả trên dữ liệu mô phỏng (chỉ xác nhận mã chạy đúng)

Chạy `neopulse simulate --sessions 6 --reset && neopulse validate`. Với seed mặc định: IC(OBI₃, 1 thanh) ngoài mẫu ≈ 0,13; độ thu hồi cảnh báo ≈ 79%, độ chính xác ≈ 86% trên 126 sự kiện cài. Tín hiệu và sự kiện đều do bộ mô phỏng cài sẵn nên các con số này **không nói gì về thị trường thật** và không được trình bày như kết quả nghiên cứu.

### Bổ sung 19/11/2026: giao diện bản tin

| Ca | Kiểm bằng | Kết quả |
|---|---|---|
| 8 tab, desktop 1440 và điện thoại 390, sáng/tối: không tràn ngang | puppeteer chụp từng tab | scrollWidth = viewport ở mọi tổ hợp |
| Màu bảng giá: trần/sàn ưu tiên hơn tăng/giảm; mọi số có dấu có ▲▼■ | vitest `fmt.test.ts` + rà ảnh | đạt |
| Số kiểu Việt trong câu do Python sinh | pytest `test_vn_digits_converts_numbers_only` | đạt |
| Trợ năng | Lighthouse mobile | Accessibility 100 |
| Hiệu năng | Lighthouse mobile, trung vị 5 lần | 71 → 76; First Load JS 244 → 117 kB |

