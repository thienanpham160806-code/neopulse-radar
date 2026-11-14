# Từ điển dữ liệu

CSDL: SQLite (`NEOPULSE_DB_PATH`). Mọi dấu thời gian là chuỗi ISO 8601 có offset **+07:00** (Asia/Ho_Chi_Minh).
Cột `source`: `neo` = NEO API thật · `sim` = mô phỏng.

## `quotes` — ảnh chụp theo mã (cổ phiếu và HĐTL)

Khóa duy nhất: (`symbol`, `ts`, `source`).

| Cột | Kiểu | Trường NEO API | Đơn vị | Ghi chú |
|---|---|---|---|---|
| ts | TEXT | — | giờ VN | thời điểm **nhận** (stockInfo không có dấu thời gian) |
| trading_date | TEXT | tradingDate | YYYY-MM-DD | đổi từ dd/mm/YYYY |
| symbol | TEXT | symbol | | viết hoa |
| instrument | TEXT | stockType/marketCode | | `stock` \| `future` |
| market_code | TEXT | marketCode | | HOSE, HNX, UPCOM, FU |
| auction_flag | TEXT | bidPrice1/askPrice1 | | `ATO`/`ATC` khi mức 1 không phải giá số |
| ceiling, floor, ref | REAL | ceilingPrice, floorPrice, refPrice | đồng (CP) / điểm (HĐTL) | |
| bid1..3, ask1..3 | REAL | bidPrice*, askPrice* | như trên | mức 1 là chuỗi ở nguồn; 0 → trống |
| bid_vol1..3, ask_vol1..3 | REAL | bidVol*, askVol* | cổ phiếu / hợp đồng | |
| last, last_vol | REAL | closePrice, closeVol | | giá/KL khớp gần nhất |
| change, pct_change | REAL | priceChange, percentPriceChange | đồng, % | so với tham chiếu |
| open, high, low, avg_price | REAL | openPrice, highPrice, lowPrice, averagePrice | | |
| total_volume, total_value | REAL | totalTradingVolume, totalTradingValue | CP, đồng | **lũy kế** trong phiên |
| f_buy_vol, f_sell_vol | REAL | foreignBuyVolume, foreignSellVolume | CP | lũy kế |
| f_buy_val, f_sell_val | REAL | foreignBuyValue, foreignSellValue | đồng | lũy kế |
| f_remain, f_room | REAL | foreignRemain, foreignRoom | CP | |
| open_interest | REAL | openInterest | hợp đồng | chỉ HĐTL |
| maturity_date | TEXT | maturityDate | YYYY-MM-DD | chỉ HĐTL |
| underlying | TEXT | underlyingSymbol | | chỉ HĐTL |

## `index_ticks` — chỉ số và độ rộng

Khóa duy nhất: (`index_code`, `ts`, `source`).

| Cột | Trường NEO API | Ghi chú |
|---|---|---|
| ts | dateString + indexTime | thời điểm **sự kiện**; lệch tương lai > 5 phút → dùng thời điểm nhận và ghi `event_time_in_future` |
| index_code | indexCode | VNINDEX, VN30, HNXINDEX, UPCOMINDEX… |
| value, change, pct_change | indexValue, indexChange, indexPercentChange | điểm, điểm, % |
| total_volume, total_value | totalVolume, totalValue | lũy kế |
| advances, declines, no_change | advances, declines, noChange | số mã |
| n_ceiling, n_floor | numberOfCe, numberOfFl | số mã |
| market_status | marketStatus | ATO, LO, ATC, PT, C… |

## Bảng phụ

| Bảng | Nội dung |
|---|---|
| `sessions` | ts, market_code, market_status — kênh `marketSession` |
| `alerts` | ts, trading_date, symbol, rule, severity, value, threshold, message, source, dedupe_key (duy nhất) |
| `quality_log` | ts, source, kind, subject, detail — mọi vấn đề chất lượng dữ liệu |
| `ingest_runs` | mỗi lần chạy bộ ghi: started, ended, source, note, n_quotes, n_index, n_rejected, n_duplicates, n_reconnects |
| `sim_truth` | sự kiện bất thường được cài trong dữ liệu mô phỏng (đáp án để đo độ thu hồi) |

### Các loại `quality_log.kind`

| kind | Nghĩa | Xử lý |
|---|---|---|
| missing_symbol, no_price, not_a_dict | bản ghi không dùng được | loại |
| bad_type:\<trường\> | giá trị không ép được về số | trường để trống, giữ bản ghi |
| negative:\<cột\> | giá/khối lượng âm | cột để trống |
| crossed_book | mua₁ ≥ bán₁ ngoài phiên định kỳ | giữ, chỉ báo sổ lệnh để trống |
| price_outside_band | giá khớp ngoài [sàn, trần] | giữ, gắn cờ |
| high_below_low | cao nhất < thấp nhất | giữ, gắn cờ |
| late_or_out_of_order | khối lượng lũy kế giảm trong cùng phiên | loại |
| event_time_in_future | dấu thời gian chỉ số đi trước đồng hồ > 5 phút | thay bằng thời điểm nhận |
| unknown_message | thông điệp WebSocket không nhận diện được | ghi 300 ký tự đầu + `raw_dump/` |
| ws_rest_mismatch, reconcile | kết quả đối chiếu WebSocket với REST | ghi nhận |
| rest_cycle_failed, poll_failed, futures_bootstrap_failed | lỗi gọi REST | ghi nhận, bộ ghi tiếp tục |

Thông điệp lặp nguyên văn không ghi log từng cái mà đếm trong `ingest_runs.n_duplicates`.

## Biến dẫn xuất (tính khi đọc, không lưu)

`mid, spread_bps, obi1, obi3, obi_w, microprice, micro_dev_bps, pressure, bid_depth, ask_depth, depth_value, band_pos` — xem `docs/methodology.md`.
Thanh thời gian (`make_bars`): trạng thái cuối thanh + `vol`, `val`, `f_net_val` (phần tăng của số lũy kế), `ret` (lợi suất giá giữa).
