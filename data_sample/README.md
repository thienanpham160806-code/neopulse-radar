# Dữ liệu mẫu

Thư mục có **hai loại** tệp; tên tệp cho biết loại.

## Mô phỏng (`*_sim_*`)

Do `neopulse.neo_api.sim` sinh ra (seed 7, phiên 2026-11-13, bước 5 phút, 5 mã + 1 HĐTL). **Không phải dữ liệu thị trường.**
Mục đích: cho người chấm thấy cấu trúc dữ liệu sau chuẩn hóa mà không cần tài khoản.

| Tệp | Nội dung |
|---|---|
| `quotes_sim_2026-11-13.csv` | bảng `quotes` (xem `docs/data_dictionary.md`) |
| `index_ticks_sim_2026-11-13.csv` | bảng `index_ticks` |
| `raw_messages_sim.json` | một thông điệp thô mỗi loại, đúng lược đồ camelCase của NEO API |

## Dữ liệu SSI thật, đã tổng hợp (`bars_ssi_<ngày>.csv`)

Chỉ có trong gói nộp `.zip`. Tệp do `tools/package_submission.py` sinh lúc đóng gói từ SQLite (chỉ đọc), cho phiên SSI mới nhất (27/11/2026). Không commit vào Git.
- Mỗi dòng là một thanh 1 phút của một mã VN30. Các cột: `trading_date, symbol, bar, spread_bps, obi1, obi3, obi_w, micro_dev_bps, pressure, band_pos, pct_change, ret, vol, val, f_net_val, rvol_bar`. Số làm tròn 6 chữ số thập phân.
- **Không có giá hay sổ lệnh thô từng tick:** không có giá mua/bán, giá khớp, giá giữa hay khối lượng từng mức giá.

## Dữ liệu thật đầy đủ

Dữ liệu thu qua `neopulse record` nằm ở `data/` và **không** được commit. Muốn xuất một phiên để kiểm tra cục bộ: `neopulse export --source ssi --date <ngày> --out-dir data_sample`.
