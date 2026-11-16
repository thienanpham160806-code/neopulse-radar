# Dữ liệu mẫu — MÔ PHỎNG

Mọi tệp trong thư mục này do `neopulse.neo_api.sim` sinh ra (seed 7, phiên 2026-11-13, bước 5 phút, 5 mã + 1 HĐTL).
**Không phải dữ liệu thị trường**, không lấy từ NEO API. Mục đích: cho người chấm thấy cấu trúc dữ liệu sau chuẩn hóa mà không cần tài khoản.

| Tệp | Nội dung |
|---|---|
| `quotes_sim_2026-11-13.csv` | bảng `quotes` (xem `docs/data_dictionary.md`) |
| `index_ticks_sim_2026-11-13.csv` | bảng `index_ticks` |
| `raw_messages_sim.json` | một thông điệp thô mỗi loại, đúng lược đồ camelCase của NEO API |

Dữ liệu thật thu qua `neopulse record` nằm ở `data/` và **không** được commit (có thể chứa thông tin gắn với tài khoản).
Khi đã có dữ liệu thật, xuất một phần để nộp kèm: `neopulse export --source neo --date <ngày> --out-dir data_sample`.
