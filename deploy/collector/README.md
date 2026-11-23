# Bộ thu cloud: gói triển khai, chưa kích hoạt

Yêu cầu của chủ dự án: **0 đồng, không thẻ, không dùng credits/trial**. Thư mục này chuẩn bị bộ thu hiện hữu để chạy trên Linux/container; chưa tạo tài nguyên cloud, chuyển khóa hoặc tắt bộ ghi Windows.

## Ứng viên và điều kiện phải xác minh

Kiểm tra ngày 23/11/2026:

- [Trang giá Northflank](https://northflank.com/pricing) ghi Sandbox miễn phí, không cần thẻ, luôn hoạt động, có giới hạn tài nguyên hàng tháng. Đây là ứng viên cần kiểm tra trên tài khoản thực tế.
- [Tài liệu billing Northflank](https://northflank.com/docs/v1/application/billing/pricing-on-northflank) lại yêu cầu mọi người thêm phương thức thanh toán. Hai nguồn chính thức mâu thuẫn; **chưa xác nhận được đăng ký và tạo đủ tài nguyên không cần thẻ**.
- Cũng chưa xác minh Sandbox cho phép đủ RAM và ổ lưu bền trong hạn mức miễn phí. Nếu giao diện yêu cầu thẻ, nâng gói, trả tiền hoặc không có lưu trữ bền miễn phí thì dừng; không tạo tài nguyên trả phí thay thế.
- [Render Free](https://render.com/docs/free) không có ổ bền cho web service, có thể ngủ/khởi động lại. Không dùng thư mục tạm của gói này để coi là đã lưu được các phiên.
- [GitHub Actions](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions) có giới hạn sử dụng như hạ tầng cho ứng dụng. Không thêm workflow chạy bộ thu phục vụ web suốt nhiều giờ chỉ vì runner công khai không tính tiền.

## Chạy và lưu dữ liệu

Image dùng `deploy/collector/Dockerfile`, build context là gốc repository. `.dockerignore` chỉ cho phép mã nguồn cần thiết; không đưa `.env`, SQLite, thư mục dữ liệu, Git hay máy ảo vào image.

- Một replica, chạy thường trực; không cần cổng HTTP công khai.
- Cần Linux và volume bền gắn vào `/data`, quyền ghi cho UID/GID `10001:10001`.
- Lịch theo `Asia/Ho_Chi_Minh`, không theo múi giờ máy chủ: 08:50 các ngày thứ Hai–thứ Sáu mở bộ ghi và relay. Bộ ghi dừng 15:05; relay có thêm thời gian đến 15:10 để cập nhật bản đầy đủ.
- Ngoài khung giờ không khởi động bộ ghi. Ngày lễ có thể điền `NEOPULSE_MARKET_HOLIDAYS`; không tự giả lập một phiên nếu không nhận được dữ liệu.
- Tiến trình con chết sớm được khởi động lại với thời gian chờ tăng dần. Khóa file ngăn hai supervisor dùng chung một volume.
- SQLite vẫn là dữ liệu gốc, dùng cùng adapter SSI và cùng công thức Python. Web tiếp tục đọc chỉ báo tổng hợp từ Redis và Ably; không nhận SQLite/sổ lệnh thô.
- Sau phiên/dừng có kiểm soát: dùng SQLite backup API, kiểm tra integrity, rồi thay `backups/latest.sqlite`. Đây là bản sao **cùng volume**, không thay thế bản sao ngoài nhà cung cấp. Mất volume vẫn có thể mất cả hai.

## Secret và cấu hình

Dùng danh sách trong `runtime.env.example`. Chỉ cần SSI key/secret, khóa Ably, URL/token Redis hiện có; không cần khóa giao dịch/tài khoản, Telegram hay khóa AI.

Khóa SSI hiện chỉ được phép ở máy thu cũ; trước khi chuyển phải có xác nhận cụ thể về nhà cung cấp nhận khóa. Không gửi token qua chat, không thêm chúng vào image hoặc file Git.

Kiểm tra cấu hình mà chưa gọi SSI hoặc khởi động tiến trình con:

```sh
python -m neopulse.analytics.cloud_recorder --check
```

Kiểm tra này chỉ xác nhận cấu hình hiện diện, không xác nhận xác thực SSI, dung lượng RAM hoặc độ bền thực tế.

## Bộ nhớ và phép tính

Đo trên Windows với dữ liệu SSI hiện có: đường cũ đạt khoảng 1.302 MiB khi dựng tổng quan rồi kiểm chứng; sau tối ưu còn khoảng 567 MiB trong lượt đo tương ứng. Đây chưa phải đo Linux/container, cũng chưa gồm mọi tiến trình cùng lúc; **không kết luận gói 512 MB chạy được**. Cần thử trên gói ít nhất 1 GB nếu Sandbox cho phép miễn phí.

Tối ưu chỉ đổi cách đọc: tính thanh theo từng phiên rồi ghép; chất lượng dữ liệu chỉ đọc timestamp và các tổng đếm SQL. Không thay tần suất thanh, bỏ tick, cắt lịch sử hay thay công thức/trọng số.

## Chuyển nguồn ghi và nghiệm thu trước khi cho laptop ngủ

1. Xác nhận tài khoản tạo được đủ compute + volume mà không thẻ/trả tiền/credits. Build image, giữ lệnh khởi động ở `--check`.
2. Gắn volume. Tạo tệp thử không nhạy cảm, thay container thật và kiểm tra tệp còn nguyên; sau đó mới đặt `NEOPULSE_PERSISTENCE_CONFIRMED=1`.
3. Dùng SQLite backup API lấy bản nhất quán của dữ liệu cũ (không chép riêng `.sqlite` khi WAL đang ghi). Sau xác nhận nơi nhận, chuyển bản này vào volume riêng tư; so sánh số phiên/bản ghi và integrity trước khi dùng.
4. Cấu hình các Secret sau khi được phép. Thử xác thực/stream trên môi trường cloud, đo RAM, kiểm tra đứt kết nối và restart.
5. Chuyển tại ranh giới phiên: dừng lịch ghi local rồi mới bật cloud. Không để hai relay cùng nguồn/ngày ghi đè latest của nhau. Giữ nguyên dữ liệu local để quay lại khi cần.
6. Trong giờ giao dịch xác nhận bản ghi SSI tăng, web nhận đúng ngày và timestamp, điểm nhịp được tính từ dữ liệu mới. Xác nhận volume còn dữ liệu sau restart và cập nhật cuối phiên có kiểm chứng.
7. Chỉ khi các bước trên đạt mới thông báo có thể tắt laptop. Nếu quay về local, dừng cloud trước và chuyển lại bản dữ liệu mới nhất đã kiểm tra; không ghi đè bằng bản local cũ.

Chưa hoàn thành: tài khoản/giới hạn free thực tế, build và chạy Linux, truyền khóa, seed dữ liệu, thử SSI từ cloud và nghiệm thu trọn phiên.
