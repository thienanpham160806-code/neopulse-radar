# Chất lượng dữ liệu: nối lại và hợp đồng tương lai

Kiểm tra ngày 28/11/2026. Nguồn số liệu:
- bảng `ingest_runs` trong `data/neopulse.sqlite`;
- log bộ ghi `out/record_YYYYMMDD.log`, không commit;
- [report/data/sessions.csv](../report/data/sessions.csv).

## Vì sao ngày 20/11 nối lại 121 lần

| phiên | lần nối lại (ingest_runs) | lượt kết nối thành công trong log | cảnh báo trong log, theo loại |
|---|---|---|---|
| 19/11 | 19 | 15 | `SsiApiError` 7 · `TimeoutError` 4 |
| 20/11 | 121 | 27 | `SsiApiError: Không kết nối được máy chủ SSI: ConnectError` 71 · `gaierror [Errno 11001] getaddrinfo failed` 25 · `ConnectionClosedError` 7 · `TimeoutError` 1 |
| 23/11 | 24 | 25 | `ConnectionClosedError` 2 |
| 25/11 | 39 | 36 | `ConnectionClosedError` 9 · `TimeoutError` 2 · `gaierror` 2 |
| 26/11 | 53 | 47 | `ConnectionClosedError` 18 · `TimeoutError` 6 · `ConnectionResetError` 1 |
| 27/11 | 60 | 56 | `ConnectionClosedError` 30 · `TimeoutError` 6 · `SsiApiError` 1 · SSI từ chối đăng ký 2 |

Ngày 20/11:
- 96 lỗi `SsiApiError` và `gaierror` nằm trong khoảng **12:46:46 đến 13:57:59**: 17 lỗi trong giờ 12, 79 lỗi trong giờ 13.
- Lỗi `gaierror` nghĩa là máy ghi không phân giải được tên miền SSI. Lỗi `ConnectError` nghĩa là không mở được kết nối TCP. Cả hai là **mất mạng phía máy ghi** (mạng ký túc xá), không phải lỗi của SSI hay của mã.
- Bộ ghi thử lại với độ trễ tăng dần, tối đa 60 giây (`neo_api/ws.py`, `max_backoff_s`). Vì vậy một lần mất mạng khoảng 71 phút sinh ra hàng trăm lần thử, và bộ đếm `n_reconnects` cộng cả các lần thử thất bại.
- Dữ liệu giá trống từ 13:04:09 đến 14:00:03. Khớp với `sessions.csv`: khoảng trống lớn nhất 56 phút giao dịch, bắt đầu 13:04.

**Không liên quan tới giới hạn 100 chủ đề.**
- Ngày 20/11 bộ ghi đăng ký 128 chủ đề, SSI nhận đủ, không có dòng "Rejected". Log ghi "đăng ký 128 chủ đề" 143 lần từ 20 đến 27/11. SSI chỉ từ chối vào ngày 27/11.
- Ngày 27/11, lúc 08:51:16 và 09:04:14, SSI trả `Rejected (subscription limit reached): 28 topic(s)`. Phần bị từ chối gồm các chủ đề chỉ số, nên web giữ dữ liệu 26/11.
- Sửa ở commit 55b5934: đăng ký tối đa 100 chủ đề, chỉ số đứng đầu. Sau khi khởi động lại lúc 09:13:59, log ghi "đăng ký 97 chủ đề" 54 lần và không còn bị từ chối.

**Trước và sau bản sửa 55b5934:**

| | trước (27/11 trước 09:13) | sau (27/11 từ 09:13:59) |
|---|---|---|
| chủ đề đăng ký | 128 | 97 |
| SSI từ chối | 28 chủ đề | không |
| tick chỉ số | không có từ 08:51 tới 09:14 | có từ 09:14 |

Các lần nối lại còn lại (23 đến 27/11) chủ yếu là `ConnectionClosedError: sent 1011 (internal error) keepalive ping timeout`:
- Kết nối bị đóng khi gói ping giữ kết nối không được trả lời kịp.
- Bộ ghi tự nối lại sau vài giây, không mất phút dữ liệu nào đáng kể: khoảng trống lớn nhất ba phiên 25 đến 27/11 là 4, 10, 13 phút và đều rơi vào cuối phiên (`sessions.csv`).
- **Không có lỗi mã cần sửa thêm.** Giới hạn còn lại: máy ghi chạy trên mạng ký túc xá không ổn định.

## Hợp đồng tương lai VN30 (41I1GC000) và tab Phái sinh

| phiên | bản ghi HĐTL | giờ đầu | giờ cuối | giá khớp thấp nhất | giá khớp cao nhất |
|---|---|---|---|---|---|
| 19/11 | 9.876 | 10:46:10 | 14:40:07 | 1.788,1 | 1.797,8 |
| 20/11 | 89.719 | 09:31:28 | 14:45:04 | 1.764,4 | 1.780,2 |
| 23/11 | 123.044 | 10:16:03 | 14:45:03 | 1.758,3 | 1.799,5 |
| 25/11 | 189.637 | 08:58:16 | 14:45:03 | 1.769,9 | 1.799,5 |
| 26/11 | 229.870 | 08:55:18 | 14:45:03 | 1.730,6 | 1.774,0 |
| 27/11 | 149.238 | 09:13:59 | 14:45:28 | 1.737,0 | 1.762,5 |

- HĐTL được ghi ở cả 6 phiên.
- Snapshot 27/11 (`sessions/ssi_2026-11-27_VN30.json`, khối `futures`) có số thật:
  - giá HĐTL 1.757,1 và VN30 1.753,53;
  - basis +3,57 điểm (+0,2036%), contango, còn 20 ngày đến đáo hạn;
  - chuỗi basis 241 điểm từ 09:14 đến 14:45.
- Ngày 27/11 HĐTL chỉ có từ 09:13:59, vì bộ ghi khởi động lại lúc đó (xem trên).
