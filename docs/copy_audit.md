# Rà soát câu chữ hiển thị

Phạm vi: giao diện web (`web/src`), bản tin HTML (`src/neopulse/analytics/templates/`), cảnh báo và nhận định do Python sinh (`alerts.py`, `explain.py`, `notify.py`, `view.py`, `company.py`, `telegram_cloud.py`), thông báo dòng lệnh (`cli.py`) và tài liệu (`README.md`, `docs/*.md`, `report/README.md`, `web/README.md`). Không đổi logic, số liệu, công thức, tên biến/hàm, khóa JSON hay bố cục. Thuật ngữ chuẩn: [`docs/thuat_ngu.md`](thuat_ngu.md).

## Hướng dẫn văn phong

1. **Giọng.** Tiếng Việt chuẩn, có dấu đầy đủ, trung tính như bản tin của công ty chứng khoán. Không tiếng lóng, emoji, dấu chấm than hay từ cường điệu ("bùng nổ", "tăng vọt", "dồn dập", "cực mạnh").
2. **Mô tả, không khuyến nghị.** Không dùng "nên mua/bán/theo dõi", "cơ hội". Cảnh báo theo khuôn *hiện tượng – mức độ – căn cứ*: "Khối lượng HPG cao gấp 3,2 lần mức thường thấy cùng khung giờ (ngưỡng 3,0)".
3. **Nhãn.** Ngắn, viết hoa chữ cái đầu. Không VIẾT HOA toàn bộ, trừ nhãn MÔ PHỎNG và mã chứng khoán. Khóa dữ liệu (`CAO`, `TRUNG BÌNH`, `THẤP`) giữ nguyên; chỉ đổi cách hiển thị.
4. **Thông báo lỗi.** Ba ý: chuyện gì xảy ra – vì sao (nếu biết) – người dùng làm gì tiếp. Không đưa tên lệnh, đường dẫn tệp, mã HTTP hay tên dịch vụ nội bộ ra màn hình người xem.
5. **Trạng thái rỗng.** Giải thích vì sao chưa có dữ liệu: ngoài giờ giao dịch, chưa ghi phiên, nguồn chưa trả, bộ lọc quá hẹp.
6. **Số và thời gian.** Định dạng Việt Nam (1.234,56); đơn vị luôn ghi rõ (điểm, %, bps, tỷ đồng, cổ phiếu, lần); thời điểm "14:05:32, 19/11/2026" theo giờ Việt Nam.
7. **Thuật ngữ.** Một khái niệm một tên, theo `docs/thuat_ngu.md`. Tên tiếng Anh/viết tắt chỉ đặt trong ngoặc ở lần đầu trên mỗi màn hình hoặc trong công thức. Lần đầu xuất hiện trên mỗi màn hình có tooltip ⓘ.
8. **Miễn trừ trách nhiệm.** Một câu duy nhất: "Công cụ phân tích học thuật. Không phải lời khuyên đầu tư." Giữ nguyên nhãn MÔ PHỎNG và ký hiệu ▲▼.
9. **Tài liệu.** Văn phong học thuật – kỹ thuật, câu ngắn, chủ động. Bỏ câu thừa và tự khen. Giữ trung thực về giới hạn: chuyển từ NEO API sang SSI vì IP whitelist, dữ liệu ước lượng, số phiên thật đã ghi.

## Vấn đề đã xác định (đọc thủ công)

| Nhóm | Ví dụ điển hình | Vị trí |
|---|---|---|
| Tiếng lóng | "Bro muốn nhận nội dung nào?" | `TelegramSignup.tsx` |
| Cường điệu, khẩu ngữ | "Bùng nổ khối lượng", "tăng vọt", "dồn dập", "lệch hẳn", "bỗng giãn rộng", "Ngành nào kéo, ngành nào đè" | `alerts.py`, `plain.ts`, `Overview.tsx`, `glossary.ts` |
| Giọng khuyến nghị | Tiêu đề "Nên theo dõi."; "không phải thứ tự nên mua" | `Overview.tsx`, `glossary.ts` |
| Thuật ngữ không nhất quán | "NN"/"khối ngoại"; "Basis"/"cơ sở"; "HĐTL"/"hợp đồng tương lai"; "Giãn chênh lệch mua-bán"/"Chênh lệch giá mua – bán"/spread; "Điểm TK"/"Điểm thanh khoản"; "GT khớp"/"giá trị khớp"; "z nội phiên"/"z bền vững"/"z-score bền vững" | `tabs.tsx`, `alerts.py`, `briefing.html.j2` |
| VIẾT HOA toàn bộ | "THẤP", "TRUNG BÌNH" ở nhãn mức cảnh báo; "TRỰC TIẾP"; tiêu đề phụ "NEOPULSE / KẾT NỐI TỰ NGUYỆN", "KHÁM PHÁ"; "bên MUA/BÁN dày hơn"; "[CẢNH BÁO CAO]" | `ui.tsx`, `tabs.tsx`, `StatusBar.tsx`, `trang-chu`, `thong-bao`, `alerts.py`, `telegram_cloud.py` |
| Trộn Anh – Việt | "snapshot", "Blob", "Worker cloud", "Bot", "Secret", "token", "free-float", "chat ID", "public/data trống" | `status.ts`, `data.ts`, `thong-bao`, `SectorCard.tsx`, `StatusBar.tsx` |
| Chi tiết kỹ thuật trên màn hình | "máy ghi hoặc `neopulse publish` có thể đã dừng"; "tính báo cáo bằng Python"; "Ably từ chối cấp token (HTTP …)"; "JSON không có khối meta" | `status.ts`, `RemoteCompany.tsx`, `ably-token/route.ts`, `parse.ts` |
| Lỗi thiếu hướng xử lý | "Không đọc được dữ liệu.", "Dữ liệu không hợp lệ.", "Không tải được dữ liệu." | `api/data/route.ts`, `RemoteCompany.tsx`, `page.tsx` |
| Miễn trừ không thống nhất | Bốn biến thể: "Công cụ học thuật. Không phải…", "…không phải khuyến nghị đầu tư", "Thông tin tham khảo, không phải khuyến nghị đầu tư", "Không phải khuyến nghị đầu tư." | `SiteFooter.tsx`, `thong-bao`, `notify.py`, `telegram_cloud.py`, `briefing.html.j2` |
| Định dạng số trong cảnh báo | "RVOL = 3.2 lần", "OBI₃ = +0.62" dùng dấu chấm thập phân | `alerts.py` |
| Nội dung lỗi thời | Mô tả CLI "radar nhịp thị trường trên NEO API" trong khi nguồn thật là SSI FastConnect; README ghi 2 phiên thật và 229 ca kiểm thử | `cli.py`, `README.md` |
| Nhãn mơ hồ | "Hình 1." đứng riêng; "Các mục"; "Thêm"; "Mã tính / loại" | `Overview.tsx`, `Dashboard.tsx`, `StatusBar.tsx` |

Tài liệu (`README.md`, `docs/*.md`, `report/README.md`, `web/README.md`) đã ở văn phong kỹ thuật, không có tiếng lóng hay emoji. Việc cần làm: thống nhất thuật ngữ theo bảng trên, cập nhật số phiên thật và số ca kiểm thử, rút gọn câu dài, bỏ trùng lặp giữa README và `web/README.md`.


## Thống kê cờ tự động

Tổng 1050 chuỗi hiển thị (đã loại docstring, log nội bộ và `glossary.ts`; glossary được rà riêng ở trên).

| Vấn đề | Số chuỗi |
|---|---|
| Anh-Việt | 46 |
| VIẾT HOA toàn bộ | 35 |
| Thuật ngữ chưa thống nhất | 23 |
| Chi tiết kỹ thuật lộ ra người dùng | 14 |
| Lỗi thiếu hướng xử lý | 9 |
| Lóng/cường điệu | 7 |
| Miễn trừ chưa thống nhất | 6 |
| Giọng khuyến nghị | 1 |

Cờ do biểu thức tìm kiếm gắn, có thể sót hoặc nhầm; các mục ở phần "Vấn đề đã xác định" là kết quả đọc thủ công.


## Bảng kê chuỗi hiển thị

| Vị trí | Chuỗi hiện tại | Vấn đề |
|---|---|---|
| `web/src/app/api/ably-token/route.ts:16` | Chưa cấu hình kênh trực tiếp. | — |
| `web/src/app/api/ably-token/route.ts:32` | Ably từ chối cấp token (HTTP ${res.status}). | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/app/api/ably-token/route.ts:41` | Không liên lạc được Ably. | Chi tiết kỹ thuật lộ ra người dùng, Lỗi thiếu hướng xử lý |
| `web/src/app/api/data/route.ts:14` | Không đọc được dữ liệu. | Lỗi thiếu hướng xử lý |
| `web/src/app/doanh-nghiep/page.tsx:8` | Doanh nghiệp | — |
| `web/src/app/doanh-nghiep/page.tsx:9` | NeoPulse · Tìm hiểu doanh nghiệp | — |
| `web/src/app/doanh-nghiep/page.tsx:10` | Đằng sau mỗi mã cổ phiếu | — |
| `web/src/app/doanh-nghiep/page.tsx:11` | Doanh nghiệp làm gì, kinh doanh ra sao và sức khỏe tài chính thế nào? Mở hồ sơ để đọc tổng quan, phân tích báo cáo tài chính, dòng tiền và định giá. | — |
| `web/src/app/doanh-nghiep/page.tsx:14` | Dữ liệu công khai qua Vietcap/vnstock. Mỗi hồ sơ ghi riêng ngày giá và kỳ báo cáo; đây là tài liệu phân tích học thuật, không phải lời khuyên đầu tư. | — |
| `web/src/app/error.tsx:6` | Không hiển thị được trang | — |
| `web/src/app/error.tsx:11` | Thử lại | — |
| `web/src/app/error.tsx:12` | Công cụ phân tích học thuật. Không phải lời khuyên đầu tư. | — |
| `web/src/app/layout.tsx:20` | Radar nhịp thị trường, áp lực sổ lệnh và cảnh báo bất thường nội phiên. Không phải lời khuyên đầu tư. | — |
| `web/src/app/loading.tsx:4` | Đang tải dữ liệu… | — |
| `web/src/app/page.tsx:14` | Công cụ phân tích học thuật. Không phải lời khuyên đầu tư. | — |
| `web/src/app/page.tsx:25` | Không đọc được dữ liệu mẫu hay dữ liệu trực tiếp. | Lỗi thiếu hướng xử lý |
| `web/src/app/page.tsx:26` | Không tải được dữ liệu | Lỗi thiếu hướng xử lý |
| `web/src/app/thong-bao/page.tsx:4` | Biết khi cần chú ý. | — |
| `web/src/app/thong-bao/page.tsx:4` | NEOPULSE / KẾT NỐI TỰ NGUYỆN | — |
| `web/src/app/thong-bao/page.tsx:4` | Nhận cảnh báo và tin doanh nghiệp, chính sách ngay trong Telegram. Bạn chọn nội dung, mã theo dõi và có thể dừng bất cứ lúc nào. | — |
| `web/src/app/thong-bao/page.tsx:4` | Nhận tin Telegram | — |
| `web/src/app/thong-bao/page.tsx:4` | Theo dõi ít hơn. | — |
| `web/src/app/thong-bao/page.tsx:5` | /stop hoặc /delete | — |
| `web/src/app/thong-bao/page.tsx:5` | Bật thêm tin doanh nghiệp hoặc chính sách; dùng off để tắt. | — |
| `web/src/app/thong-bao/page.tsx:5` | Chỉ theo dõi mã bạn quan tâm. | — |
| `web/src/app/thong-bao/page.tsx:5` | Hủy nhận tin và xóa đăng ký đang hoạt động. | — |
| `web/src/app/thong-bao/page.tsx:5` | Sau khi đăng ký | — |
| `web/src/app/thong-bao/page.tsx:5` | Trở lại toàn bộ VN30. | — |
| `web/src/app/thong-bao/page.tsx:5` | Xem cài đặt đang dùng. | — |
| `web/src/app/thong-bao/page.tsx:6` | Bot không phụ thuộc laptop để nhận đăng ký hoặc lấy RSS. Cảnh báo thị trường mới vẫn cần nguồn NeoPulse được cập nhật; nếu bộ ghi dừng, bot không tạo tín hiệ… | Anh-Việt |
| `web/src/app/thong-bao/page.tsx:6` | Chỉ lưu chat ID, tùy chọn nhận tin và khóa chống lặp. Dữ liệu đăng ký được mã hóa trước khi lưu bản sao cloud; khóa mã hóa nằm trong GitHub Secret. /delete x… | Anh-Việt |
| `web/src/app/thong-bao/page.tsx:6` | Công cụ học thuật. Không phải lời khuyên đầu tư. | Miễn trừ chưa thống nhất |
| `web/src/app/thong-bao/page.tsx:6` | Nguồn tin, nhịp gửi & quyền riêng tư | — |
| `web/src/app/thong-bao/page.tsx:6` | Tin doanh nghiệp lọc theo mã xuất hiện trong tiêu đề; có thể bỏ sót bài chỉ ghi tên công ty. Tin chính sách lấy từ Báo Chính phủ, luôn kèm link gốc; ngày đăn… | — |
| `web/src/app/thong-bao/page.tsx:6` | Worker cloud kiểm tra khoảng 15 phút/lượt, có thể trễ theo lịch GitHub Actions. Không phải cảnh báo tức thời; tối đa 10 tin/người/lượt, không gửi lại tin đã … | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/app/trang-chu/page.tsx:4` | >KHÁM PHÁ / {n}</span><h2 className= | VIẾT HOA toàn bộ |
| `web/src/app/trang-chu/page.tsx:4` | >Khám phá thị trường ↗</Link></section><div className= | — |
| `web/src/app/trang-chu/page.tsx:4` | Công cụ phân tích học thuật · Không phải lời khuyên đầu tư. Nguồn và thời điểm dữ liệu được ghi tại từng trang. | — |
| `web/src/app/trang-chu/page.tsx:4` | Hiểu nhịp thị trường. | — |
| `web/src/app/trang-chu/page.tsx:4` | Khám phá thị trường ↗ | — |
| `web/src/app/trang-chu/page.tsx:4` | Một không gian để theo dõi diễn biến trong phiên và đọc câu chuyện đằng sau từng mã cổ phiếu VN30. | — |
| `web/src/app/trang-chu/page.tsx:4` | NEOPULSE / GÓC NHÌN THỊ TRƯỜNG | — |
| `web/src/app/trang-chu/page.tsx:4` | Nhìn sâu doanh nghiệp. | — |
| `web/src/components/AlertDetail.tsx:13` | . Đơn vị và cách đối chiếu xem trong mô tả cảnh báo. | — |
| `web/src/components/AlertDetail.tsx:13` | Giá trị kiểm tra: | — |
| `web/src/components/AlertDetail.tsx:13` | · Ngưỡng quy tắc: | — |
| `web/src/components/AlertDetail.tsx:14` | Bản tin nhanh chưa kèm giá trị và ngưỡng đo. Chờ bản dữ liệu đầy đủ để đối chiếu; không suy ra mức nền từ câu thông báo. | — |
| `web/src/components/AlertDetail.tsx:15` | Hiểu chỉ số của quy tắc | — |
| `web/src/components/AlertDetail.tsx:15` | · Đây là biến động cần xem lại, chưa cho biết nguyên nhân hay hướng giá tiếp theo. | — |
| `web/src/components/CompanyCharts.tsx:10` | Giá & chỉ báo | — |
| `web/src/components/CompanyCharts.tsx:10` | So với VN-Index | — |
| `web/src/components/CompanyDirectory.tsx:6` | ).replace(/đ/g, | — |
| `web/src/components/CompanyDirectory.tsx:17` | Nhóm doanh nghiệp | — |
| `web/src/components/CompanyDirectory.tsx:17` | Toàn thị trường (${entries.length}) | — |
| `web/src/components/CompanyDirectory.tsx:17` | VN100 · báo cáo sẵn (${ready}/100) | — |
| `web/src/components/CompanyDirectory.tsx:19` | Tìm mã, tên doanh nghiệp hoặc ngành | — |
| `web/src/components/CompanyDirectory.tsx:19` | Ví dụ: VND, Hòa Phát, ngân hàng… | — |
| `web/src/components/CompanyDirectory.tsx:20` | >Tất cả sàn</option>{[ | — |
| `web/src/components/CompanyDirectory.tsx:20` | Sàn giao dịch | — |
| `web/src/components/CompanyDirectory.tsx:20` | Tất cả sàn | — |
| `web/src/components/CompanyDirectory.tsx:21` | · hiển thị ${(current - 1) * 24 + 1}–${Math.min(current * 24, rows.length)} | — |
| `web/src/components/CompanyDirectory.tsx:23` | Không tìm thấy cổ phiếu khớp bộ lọc. Thử đổi sàn hoặc nhóm doanh nghiệp. | — |
| `web/src/components/CompanyDirectory.tsx:24` | Phân trang doanh nghiệp | — |
| `web/src/components/CompanyDirectory.tsx:24` | Trước | — |
| `web/src/components/CompanyDirectory.tsx:24` | Đi đến trang doanh nghiệp | — |
| `web/src/components/CompanyLink.tsx:5` | Xem hồ sơ doanh nghiệp ${symbol} | — |
| `web/src/components/CompanyReportView.tsx:10` | Doanh nghiệp & ngành | — |
| `web/src/components/CompanyReportView.tsx:10` | Tài chính & kinh doanh | — |
| `web/src/components/CompanyReportView.tsx:10` | Tóm tắt & rủi ro | — |
| `web/src/components/CompanyReportView.tsx:10` | Định giá & giả định | — |
| `web/src/components/CompanyReportView.tsx:12` | Tăng trưởng doanh thu | — |
| `web/src/components/CompanyReportView.tsx:13` | Tăng trưởng LNST công ty mẹ | — |
| `web/src/components/CompanyReportView.tsx:14` | Biên hoạt động cốt lõi | — |
| `web/src/components/CompanyReportView.tsx:15` | ROE · lợi nhuận/vốn chủ bình quân | — |
| `web/src/components/CompanyReportView.tsx:16` | Thanh toán hiện hành | — |
| `web/src/components/CompanyReportView.tsx:16` | Thanh toán nhanh | — |
| `web/src/components/CompanyReportView.tsx:16` | lần | — |
| `web/src/components/CompanyReportView.tsx:17` | Khả năng trả lãi | — |
| `web/src/components/CompanyReportView.tsx:17` | Nợ vay/vốn chủ | — |
| `web/src/components/CompanyReportView.tsx:17` | lần | — |
| `web/src/components/CompanyReportView.tsx:18` | Số ngày phải thu | — |
| `web/src/components/CompanyReportView.tsx:18` | Số ngày tồn kho | — |
| `web/src/components/CompanyReportView.tsx:18` | ngày | — |
| `web/src/components/CompanyReportView.tsx:19` | Chu kỳ chuyển đổi tiền mặt | — |
| `web/src/components/CompanyReportView.tsx:19` | Số ngày phải trả | — |
| `web/src/components/CompanyReportView.tsx:19` | ngày | — |
| `web/src/components/CompanyReportView.tsx:20` | Chi phí hoạt động/thu nhập (CIR) | — |
| `web/src/components/CompanyReportView.tsx:20` | Dòng tiền kinh doanh/LNST | — |
| `web/src/components/CompanyReportView.tsx:20` | lần | — |
| `web/src/components/CompanyReportView.tsx:21` | Cho vay/tiền gửi khách hàng | — |
| `web/src/components/CompanyReportView.tsx:26` | Chỉ tiêu | — |
| `web/src/components/CompanyReportView.tsx:28` | Chưa có số liệu cho phần này. | — |
| `web/src/components/CompanyReportView.tsx:35` | Doanh nghiệp | — |
| `web/src/components/CompanyReportView.tsx:37` | NeoPulse · Hồ sơ phân tích doanh nghiệp | — |
| `web/src/components/CompanyReportView.tsx:39` | đồng/CP | — |
| `web/src/components/CompanyReportView.tsx:40` | Chưa rõ | — |
| `web/src/components/CompanyReportView.tsx:43` | Mục lục hồ sơ | — |
| `web/src/components/CompanyReportView.tsx:44` | Đọc theo trình tự: hiểu hoạt động → xem hiệu quả → nhận diện rủi ro → đối chiếu định giá. | — |
| `web/src/components/CompanyReportView.tsx:46` | 01 · Doanh nghiệp & ngành | — |
| `web/src/components/CompanyReportView.tsx:47` | Nguồn dữ liệu chưa cung cấp mô tả hoạt động doanh nghiệp. | — |
| `web/src/components/CompanyReportView.tsx:48` | ${num(p.valuation.market_cap, 0)} tỷ | — |
| `web/src/components/CompanyReportView.tsx:48` | Cổ phiếu lưu hành | — |
| `web/src/components/CompanyReportView.tsx:48` | Ngày niêm yết | — |
| `web/src/components/CompanyReportView.tsx:48` | Sở hữu nước ngoài | — |
| `web/src/components/CompanyReportView.tsx:48` | Vốn hóa theo giá trên | — |
| `web/src/components/CompanyReportView.tsx:49` | Chưa có dữ liệu cổ đông. | — |
| `web/src/components/CompanyReportView.tsx:49` | Cổ đông được nguồn công bố | — |
| `web/src/components/CompanyReportView.tsx:50` | Ban lãnh đạo | — |
| `web/src/components/CompanyReportView.tsx:50` | Chưa có dữ liệu lãnh đạo. | — |
| `web/src/components/CompanyReportView.tsx:51` | Chưa đủ dữ liệu giá so sánh. | — |
| `web/src/components/CompanyReportView.tsx:51` | Diễn biến giá so với thị trường | — |
| `web/src/components/CompanyReportView.tsx:52` | tối đa 250 | — |
| `web/src/components/CompanyReportView.tsx:56` | 02 · Tài chính & kết quả kinh doanh | — |
| `web/src/components/CompanyReportView.tsx:57` | BCTC năm hợp nhất · tỷ đồng. “—” là chưa có dữ liệu, không phải bằng 0. | — |
| `web/src/components/CompanyReportView.tsx:58` | Chưa có đủ báo cáo tài chính để phân tích. | — |
| `web/src/components/CompanyReportView.tsx:59` | ${title} · tỷ đồng | — |
| `web/src/components/CompanyReportView.tsx:59` | Dòng tiền | — |
| `web/src/components/CompanyReportView.tsx:59` | Kết quả kinh doanh | — |
| `web/src/components/CompanyReportView.tsx:59` | Tài sản & nguồn vốn | — |
| `web/src/components/CompanyReportView.tsx:60` | Khả năng sinh lời, thanh khoản & hiệu quả | — |
| `web/src/components/CompanyReportView.tsx:60` | Tỷ số | — |
| `web/src/components/CompanyReportView.tsx:61` | )} /></div><Note>Tích ba thành phần bằng ROE {fmt(r.roe, | — |
| `web/src/components/CompanyReportView.tsx:61` | Biên ròng | — |
| `web/src/components/CompanyReportView.tsx:61` | Phân rã ROE · DuPont ${latest ?? ""} | — |
| `web/src/components/CompanyReportView.tsx:62` | Mã | — |
| `web/src/components/CompanyReportView.tsx:62` | Năm | — |
| `web/src/components/CompanyReportView.tsx:62` | Tăng trưởng | — |
| `web/src/components/CompanyReportView.tsx:62` | Đối chiếu doanh nghiệp | — |
| `web/src/components/CompanyReportView.tsx:64` | 03 · Tóm tắt & điều cần theo dõi | — |
| `web/src/components/CompanyReportView.tsx:66` | BCTC năm mô tả quá khứ; chưa bao gồm kết quả quý mới hơn hay kế hoạch kinh doanh mới. | — |
| `web/src/components/CompanyReportView.tsx:66` | Biên lợi nhuận, tồn kho và dòng tiền có thể thay đổi theo chu kỳ ngành; cần đọc thuyết minh trước khi kết luận. | — |
| `web/src/components/CompanyReportView.tsx:66` | Cho vay/tiền gửi và CIR không thay thế phân tích nợ xấu, dự phòng, an toàn vốn và cơ cấu kỳ hạn. | — |
| `web/src/components/CompanyReportView.tsx:66` | Ngày giá và năm BCTC khác nhau; bội số dưới đây dùng lợi nhuận năm gần nhất đã tải, không phải lợi nhuận 12 tháng gần nhất. | — |
| `web/src/components/CompanyReportView.tsx:66` | Nhận định được dựng từ số liệu; chưa có phân tích chiến lược, thị phần hoặc lợi thế cạnh tranh được kiểm chứng riêng. | — |
| `web/src/components/CompanyReportView.tsx:66` | Rủi ro & giới hạn khi đọc | — |
| `web/src/components/CompanyReportView.tsx:69` | 04 · Định giá & giả định | — |
| `web/src/components/CompanyReportView.tsx:70` | chưa có | — |
| `web/src/components/CompanyReportView.tsx:71` | EV/EBITDA ước tính | — |
| `web/src/components/CompanyReportView.tsx:71` | P/B · vốn chủ công ty mẹ | — |
| `web/src/components/CompanyReportView.tsx:71` | P/E · LNST công ty mẹ | — |
| `web/src/components/CompanyReportView.tsx:71` | lần | — |
| `web/src/components/CompanyReportView.tsx:72` | Chiết khấu dòng tiền · bảng độ nhạy minh họa | — |
| `web/src/components/CompanyReportView.tsx:74` | Giá trị vốn chủ/CP · đồng · FCFF trừ nợ vay ròng và lợi ích không kiểm soát | — |
| `web/src/components/CompanyReportView.tsx:75` | Chưa có đủ đầu vào dòng tiền và giả định để dựng DCF có thể kiểm chứng. | — |
| `web/src/components/CompanyReportView.tsx:75` | FCFF = EBIT hoạt động × (1 − thuế) + khấu hao − chi TSCĐ − thay đổi vốn lưu động hoạt động. EBIT hoạt động = lãi gộp − chi bán hàng − chi quản lý, loại thu n… | — |
| `web/src/components/CompanyReportView.tsx:78` | Công cụ học thuật. Không phải lời khuyên đầu tư. | Miễn trừ chưa thống nhất |
| `web/src/components/CompanyReportView.tsx:78` | Nguồn & phương pháp | — |
| `web/src/components/Dashboard.tsx:19` | Đang tải… | — |
| `web/src/components/Dashboard.tsx:28` | Cảnh báo | — |
| `web/src/components/Dashboard.tsx:28` | Khối ngoại | — |
| `web/src/components/Dashboard.tsx:28` | Kiểm chứng & dữ liệu | — |
| `web/src/components/Dashboard.tsx:28` | Phái sinh | — |
| `web/src/components/Dashboard.tsx:28` | Phương pháp & giới hạn | — |
| `web/src/components/Dashboard.tsx:28` | Sổ lệnh & thanh khoản | — |
| `web/src/components/Dashboard.tsx:28` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:28` | Xếp hạng | — |
| `web/src/components/Dashboard.tsx:31` | Khối ngoại | — |
| `web/src/components/Dashboard.tsx:31` | Phái sinh | — |
| `web/src/components/Dashboard.tsx:31` | Sổ lệnh & thanh khoản | — |
| `web/src/components/Dashboard.tsx:31` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:32` | Cảnh báo | — |
| `web/src/components/Dashboard.tsx:32` | Kiểm chứng & dữ liệu | — |
| `web/src/components/Dashboard.tsx:32` | Phương pháp & giới hạn | — |
| `web/src/components/Dashboard.tsx:32` | Xếp hạng | — |
| `web/src/components/Dashboard.tsx:34` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:36` | Cảnh báo | — |
| `web/src/components/Dashboard.tsx:36` | Khối ngoại | — |
| `web/src/components/Dashboard.tsx:36` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:37` | Cảnh báo | — |
| `web/src/components/Dashboard.tsx:37` | Khối ngoại | — |
| `web/src/components/Dashboard.tsx:37` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:73` | hết phiên đăng nhập | — |
| `web/src/components/Dashboard.tsx:77` | lỗi mạng | Lỗi thiếu hướng xử lý |
| `web/src/components/Dashboard.tsx:119` | Nhịp thị trường | — |
| `web/src/components/Dashboard.tsx:119` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:127` | ${mode.reason} — đang hiển thị snapshot. | Anh-Việt |
| `web/src/components/Dashboard.tsx:133` | Nhịp thị trường | — |
| `web/src/components/Dashboard.tsx:134` | Hiểu thị trường đang chuyển động ra sao, xem bằng chứng và tìm những biến động cần chú ý. | — |
| `web/src/components/Dashboard.tsx:143` | · mới nhất | — |
| `web/src/components/Dashboard.tsx:147` | Phiên | — |
| `web/src/components/Dashboard.tsx:148` | Chọn phiên giao dịch | — |
| `web/src/components/Dashboard.tsx:150` | >Mới nhất{meta.trading_date ? ` (${dmy(meta.trading_date)})` : | Anh-Việt |
| `web/src/components/Dashboard.tsx:155` | Chỉ số | — |
| `web/src/components/Dashboard.tsx:156` | Chọn chỉ số | — |
| `web/src/components/Dashboard.tsx:161` | Lọc mã… | — |
| `web/src/components/Dashboard.tsx:161` | Lọc theo mã | — |
| `web/src/components/Dashboard.tsx:165` | Cảnh báo từ | — |
| `web/src/components/Dashboard.tsx:166` | Ngưỡng mức cảnh báo | — |
| `web/src/components/Dashboard.tsx:168` | Mức cao | — |
| `web/src/components/Dashboard.tsx:169` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/Dashboard.tsx:169` | Trung bình trở lên | — |
| `web/src/components/Dashboard.tsx:170` | THẤP | VIẾT HOA toàn bộ |
| `web/src/components/Dashboard.tsx:170` | Tất cả | — |
| `web/src/components/Dashboard.tsx:177` | Các mục | — |
| `web/src/components/Dashboard.tsx:202` | Phương pháp & giới hạn | — |
| `web/src/components/Dashboard.tsx:204` | Chưa có dữ liệu để hiển thị | — |
| `web/src/components/Dashboard.tsx:208` | Tải lại | — |
| `web/src/components/Dashboard.tsx:209` | Phương pháp & giới hạn | — |
| `web/src/components/Dashboard.tsx:209` | Đọc phương pháp | — |
| `web/src/components/Dashboard.tsx:212` | Tổng quan | — |
| `web/src/components/Dashboard.tsx:213` | Sổ lệnh & thanh khoản | — |
| `web/src/components/Dashboard.tsx:214` | Khối ngoại | — |
| `web/src/components/Dashboard.tsx:215` | Phái sinh | — |
| `web/src/components/Dashboard.tsx:216` | Cảnh báo | — |
| `web/src/components/Dashboard.tsx:217` | Xếp hạng | — |
| `web/src/components/Dashboard.tsx:218` | Kiểm chứng & dữ liệu | — |
| `web/src/components/Dashboard.tsx:223` | Thêm | — |
| `web/src/components/Dashboard.tsx:224` | Điều hướng chính | — |
| `web/src/components/Dashboard.tsx:239` | Thêm | — |
| `web/src/components/Disclosures.tsx:25` | Chưa có dữ liệu. | — |
| `web/src/components/Disclosures.tsx:25` | Sự kiện công bố · ${events.length} | — |
| `web/src/components/Disclosures.tsx:25` | Toàn bộ sự kiện 10 năm gần nhất theo Vietcap, mới nhất ở trên. | — |
| `web/src/components/Disclosures.tsx:26` | Chưa có dữ liệu. | — |
| `web/src/components/Disclosures.tsx:26` | Cập nhật ${dmyTime(updated)}, làm mới mỗi 15 phút. | — |
| `web/src/components/Disclosures.tsx:26` | Nguồn | — |
| `web/src/components/Disclosures.tsx:26` | Tin & báo cáo gần đây | — |
| `web/src/components/Disclosures.tsx:26` | Đang lấy tin mới nhất… | — |
| `web/src/components/Explain.tsx:32` | Điểm nhịp ${num(s, 1)} trên 100, ${label} | — |
| `web/src/components/Explain.tsx:32` | Điểm nhịp: chưa đủ dữ liệu | — |
| `web/src/components/Explain.tsx:77` | Hướng dẫn đọc trang | — |
| `web/src/components/Explain.tsx:78` | Mới dùng NeoPulse? Xem cách đọc trang | — |
| `web/src/components/Explain.tsx:80` | Đọc trang này thế nào? | — |
| `web/src/components/Explain.tsx:81` | Đã hiểu, ẩn đi | — |
| `web/src/components/Explain.tsx:84` | 1. Đang xem dữ liệu nào? | — |
| `web/src/components/Explain.tsx:84` | Kiểm tra nguồn, thời điểm cập nhật và phạm vi rổ. Đọc phần tóm tắt để biết chỉ số và số đông cổ phiếu đang đi cùng chiều hay không. | — |
| `web/src/components/Explain.tsx:85` | 2. Vì sao có nhận định đó? | — |
| `web/src/components/Explain.tsx:85` | Xem năm nhóm bằng chứng, rồi mở bảng chi tiết. Đồng hồ chỉ tổng hợp phần có dữ liệu; điểm cao không đồng nghĩa mọi tín hiệu đều tốt. | — |
| `web/src/components/Explain.tsx:86` | 3. Điều gì cần kiểm tra thêm? | — |
| `web/src/components/Explain.tsx:86` | Mở từng cảnh báo và xem phần kiểm chứng. Bấm ⓘ hoặc “Tra cứu chỉ số” để hiểu số liệu và vai trò của nó trong đồ án. | — |
| `web/src/components/Explain.tsx:88` | Biểu tượng | — |
| `web/src/components/Explain.tsx:88` | cạnh một thuật ngữ mở lời giải thích. Đây là công cụ học thuật, không phải lời khuyên đầu tư. | — |
| `web/src/components/Glossary.tsx:55` | Tra cứu chỉ số | — |
| `web/src/components/Glossary.tsx:56` | × | — |
| `web/src/components/Glossary.tsx:56` | Đóng | — |
| `web/src/components/Glossary.tsx:58` | Tìm tên chỉ số hoặc viết tắt | — |
| `web/src/components/Glossary.tsx:60` | Ví dụ: do rong, OBI, IC… | — |
| `web/src/components/Glossary.tsx:63` | Kết quả tra cứu | — |
| `web/src/components/Glossary.tsx:70` | Không tìm thấy. Thử tên ngắn hơn hoặc viết tắt như OBI, RVOL, IC. | — |
| `web/src/components/Glossary.tsx:73` | Hiểu chỉ số để đọc đúng dữ liệu | — |
| `web/src/components/Glossary.tsx:76` | Đơn vị: | — |
| `web/src/components/Glossary.tsx:78` | Đọc con số thế nào? | — |
| `web/src/components/Glossary.tsx:80` | Ví dụ minh họa · không phải số liệu hiện tại | — |
| `web/src/components/Glossary.tsx:81` | Vì sao có trong đồ án? | — |
| `web/src/components/Glossary.tsx:83` | Giới hạn khi sử dụng | — |
| `web/src/components/Glossary.tsx:86` | Công thức và nguồn tham khảo | — |
| `web/src/components/Glossary.tsx:88` | Phương pháp và giả định của NeoPulse ↗ | — |
| `web/src/components/Glossary.tsx:94` | Xem nơi sử dụng chỉ số → | — |
| `web/src/components/Glossary.tsx:104` | Tra cứu chỉ số | — |
| `web/src/components/Glossary.tsx:111` | Giải thích: ${entry.title} | — |
| `web/src/components/IndexChart.tsx:12` | Diễn biến ${code} trong phiên | — |
| `web/src/components/IndexChart.tsx:20` | Tham chiếu ${num(refValue)} | — |
| `web/src/components/MarketEvidence.tsx:9` | Đa số cổ phiếu đang tăng hay giảm? | — |
| `web/src/components/MarketEvidence.tsx:10` | Chỉ số đang chuyển động mạnh đến đâu? | — |
| `web/src/components/MarketEvidence.tsx:11` | Lệnh chờ đang nghiêng về phía nào? | — |
| `web/src/components/MarketEvidence.tsx:12` | Khối ngoại đang mua hay bán ròng? | — |
| `web/src/components/MarketEvidence.tsx:13` | Giao dịch sôi động hơn thường lệ không? | — |
| `web/src/components/MarketEvidence.tsx:18` | Từ nhận định đến bằng chứng | — |
| `web/src/components/MarketEvidence.tsx:19` | Năm góc nhìn, mỗi góc trả lời một câu hỏi | — |
| `web/src/components/MarketEvidence.tsx:20` | Các số dưới đây là thành phần đã chuẩn hóa từ −1 đến +1 để ghép vào điểm nhịp, không phải % tăng giá. Trọng số gốc là lựa chọn thiết kế; phần thiếu được bỏ q… | — |
| `web/src/components/MarketEvidence.tsx:32` | Mở bảng bằng chứng → | — |
| `web/src/components/MarketEvidence.tsx:32` | Xem diễn biến bên dưới ↓ | — |
| `web/src/components/MarketEvidence.tsx:44` | Mức độ bằng chứng | — |
| `web/src/components/MarketEvidence.tsx:45` | Đã kiểm tra gì, còn thiếu gì? | — |
| `web/src/components/MarketEvidence.tsx:46` | Xem kiểm chứng & dữ liệu → | — |
| `web/src/components/MarketEvidence.tsx:50` | Phiên đã ghi | — |
| `web/src/components/MarketEvidence.tsx:51` | Mã đã có dữ liệu | — |
| `web/src/components/MarketEvidence.tsx:52` | Ảnh chụp sổ lệnh | — |
| `web/src/components/MarketEvidence.tsx:53` | Khoảng trống bất thường | — |
| `web/src/components/MarketEvidence.tsx:55` | Kiểm chứng đặt câu hỏi: | — |
| `web/src/components/MarketEvidence.tsx:55` | So sánh theo thứ tự phiên, tách | — |
| `web/src/components/MarketEvidence.tsx:55` | trong mẫu và ngoài mẫu | — |
| `web/src/components/MarketEvidence.tsx:55` | tín hiệu sổ lệnh có liên hệ với thay đổi giá sau đó không? | — |
| `web/src/components/MarketEvidence.tsx:56` | Chưa đủ 5 phiên tối thiểu của đồ án; kết quả mới có tính minh họa. | — |
| `web/src/components/MarketEvidence.tsx:56` | Đã đạt mốc 5 phiên tối thiểu của đồ án; vẫn cần nhiều phiên hơn để đánh giá tính ổn định. | — |
| `web/src/components/MarketEvidence.tsx:57` | · Dữ liệu đến ${dmyTime(v.data_until)} | — |
| `web/src/components/MarketEvidence.tsx:58` | Bản dữ liệu này chưa có kết quả kiểm chứng. Số liệu quan sát và điểm tổng hợp hiện có chưa đủ để kết luận tín hiệu dự báo tốt. Mở mục kiểm chứng để xem kết q… | — |
| `web/src/components/MarketEvidence.tsx:59` | Dữ liệu mô phỏng: tín hiệu được cài sẵn, chỉ kiểm tra được đường tính toán; không phải bằng chứng về thị trường thật. | — |
| `web/src/components/Overview.tsx:20` | THẤP | VIẾT HOA toàn bộ |
| `web/src/components/Overview.tsx:20` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/Overview.tsx:36` | số mã tăng / đứng giá / giảm | — |
| `web/src/components/Overview.tsx:50` | Chưa có điều gì bất thường ở mức đang lọc. | — |
| `web/src/components/Overview.tsx:59` | · chi tiết | — |
| `web/src/components/Overview.tsx:103` | Giá và điểm nhịp đang nhận cập nhật nhanh; bảng chi tiết theo bản dữ liệu đầy đủ gần nhất. | — |
| `web/src/components/Overview.tsx:103` | Nhận định theo mốc dữ liệu đã nhận, không suy ra diễn biến sau mốc này. | — |
| `web/src/components/Overview.tsx:103` | Phạm vi đang đọc: | — |
| `web/src/components/Overview.tsx:104` | chưa xác định | — |
| `web/src/components/Overview.tsx:109` | Điểm nhịp thị trường | — |
| `web/src/components/Overview.tsx:113` | Điểm phụ thuộc trọng số ra sao? | — |
| `web/src/components/Overview.tsx:113` | Độ nhạy trọng số | — |
| `web/src/components/Overview.tsx:123` | · ${num(ix0.adv, 0)} mã tăng, ${num(ix0.dec, 0)} mã giảm | — |
| `web/src/components/Overview.tsx:125` | Đọc nhanh tại mốc cập nhật | — |
| `web/src/components/Overview.tsx:127` | Đang diễn ra. | — |
| `web/src/components/Overview.tsx:128` | Điều gì đang tác động? | — |
| `web/src/components/Overview.tsx:129` | Nên theo dõi. | Giọng khuyến nghị |
| `web/src/components/Overview.tsx:130` | ; trong các cảnh báo đã tải, ${hot.join(", ")} xuất hiện nhiều | — |
| `web/src/components/Overview.tsx:130` | }. Một mã có thể có nhiều cảnh báo; mở chi tiết để xem từng biến động.{ | — |
| `web/src/components/Overview.tsx:131` | Xem cảnh báo | — |
| `web/src/components/Overview.tsx:132` | Chưa ghi nhận cảnh báo mức cao trong phiên. | — |
| `web/src/components/Overview.tsx:135` | Chưa đủ dữ liệu để so sánh giá trị giao dịch với các phiên trước ở cùng thời điểm. | — |
| `web/src/components/Overview.tsx:135` | Thanh khoản | — |
| `web/src/components/Overview.tsx:136` | Chưa đủ dữ liệu cho: ${missing.filter((name) => name !== "Thanh khoản").join(", ")}. | — |
| `web/src/components/Overview.tsx:136` | Thanh khoản | — |
| `web/src/components/Overview.tsx:148` | Biến động đáng chú ý trong rổ | — |
| `web/src/components/Overview.tsx:148` | Những điểm cần xem lại | — |
| `web/src/components/Overview.tsx:149` | Mở toàn bộ cảnh báo → | — |
| `web/src/components/Overview.tsx:156` | Chỉ số | — |
| `web/src/components/Overview.tsx:158` | Đặt tín hiệu vào diễn biến giá | — |
| `web/src/components/Overview.tsx:159` | MA và EMA | — |
| `web/src/components/Overview.tsx:159` | giúp nhìn xu hướng, không tham gia điểm nhịp. Khung Phiên là dữ liệu đã ghi; khung ngày cung cấp bối cảnh dài hơn. | — |
| `web/src/components/Overview.tsx:159` | Đối chiếu các tín hiệu bên trên với đường giá. | — |
| `web/src/components/Overview.tsx:161` | Chưa đủ điểm dữ liệu để vẽ. | — |
| `web/src/components/Overview.tsx:163` | Hình 1. | — |
| `web/src/components/Overview.tsx:168` | Ngành nào kéo, ngành nào đè | Lóng/cường điệu |
| `web/src/components/Overview.tsx:169` | Chạm vào một ngành để xem các mã trong ngành. | — |
| `web/src/components/Overview.tsx:174` | (theo ảnh chụp gần nhất) | — |
| `web/src/components/Overview.tsx:176` | Câu chữ dựng từ mẫu câu gắn với số liệu, không phải dự báo hay khuyến nghị. | — |
| `web/src/components/Overview.tsx:182` | Bảng chỉ số | — |
| `web/src/components/Overview.tsx:184` | Khối ngoại trong rổ | — |
| `web/src/components/Overview.tsx:186` | 0 ? "Mua ròng" : fs.net_val | — |
| `web/src/components/Overview.tsx:186` | Bán ròng | — |
| `web/src/components/Overview.tsx:186` | Chưa đủ dữ liệu | — |
| `web/src/components/Overview.tsx:186` | Mua ròng | — |
| `web/src/components/Overview.tsx:186` | Mua và bán cân bằng | — |
| `web/src/components/RemoteCompany.tsx:14` | Không tải được dữ liệu. | Lỗi thiếu hướng xử lý |
| `web/src/components/RemoteCompany.tsx:15` | Dữ liệu không hợp lệ. | Lỗi thiếu hướng xử lý |
| `web/src/components/RemoteCompany.tsx:21` | Chưa có phân ngành | — |
| `web/src/components/RemoteCompany.tsx:21` | Danh mục cổ phiếu Việt Nam | — |
| `web/src/components/RemoteCompany.tsx:21` | Doanh nghiệp | — |
| `web/src/components/RemoteCompany.tsx:21` | Không tìm thấy mã trong danh mục | — |
| `web/src/components/RemoteCompany.tsx:22` | Mã này chưa có trong danh mục HOSE/HNX/UPCoM hiện tại. | — |
| `web/src/components/RemoteCompany.tsx:22` | Đang tải BCTC công khai và tính báo cáo bằng Python. Thông tin cơ bản đã sẵn có; lần mở đầu có thể mất vài chục giây. | Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/components/RemoteCompany.tsx:23` | Thử tải lại báo cáo | — |
| `web/src/components/RemoteCompany.tsx:24` | Không thay dữ liệu thiếu bằng 0 hoặc tự tạo nhận định. Công cụ học thuật, không phải lời khuyên đầu tư. | — |
| `web/src/components/SectorCard.tsx:27` | Ngành trong phiên${live?.length ? " · trực tiếp" : ""} | — |
| `web/src/components/SectorCard.tsx:32` | Ngành | — |
| `web/src/components/SectorCard.tsx:33` | Tăng / Giảm | — |
| `web/src/components/SectorCard.tsx:34` | % bình quân vốn hóa | — |
| `web/src/components/SectorCard.tsx:35` | (điểm, ước lượng) | — |
| `web/src/components/SectorCard.tsx:75` | Chưa có danh sách mã cho ngành này. | — |
| `web/src/components/SectorCard.tsx:75` | Các mã trong ngành: | — |
| `web/src/components/SectorCard.tsx:85` | Đóng góp điểm là ước lượng theo vốn hóa niêm yết, chưa điều chỉnh free-float. | Anh-Việt |
| `web/src/components/SectorCard.tsx:87` | Tổng ước lượng ${num(sectors?.contrib_sum ?? null)} điểm so với thay đổi thật ${num(sectors?.index_change ?? null)} điểm. | — |
| `web/src/components/SiteFooter.tsx:4` | Phạm Ngọc Thiên An | — |
| `web/src/components/SiteFooter.tsx:12` | Thông tin website và liên hệ | — |
| `web/src/components/SiteFooter.tsx:15` | Về NeoPulse Radar | — |
| `web/src/components/SiteFooter.tsx:16` | Hiểu nhịp thị trường | — |
| `web/src/components/SiteFooter.tsx:17` | Theo dõi thị trường chứng khoán Việt Nam, nhận diện những biến động đáng chú ý và tìm hiểu sức khỏe tài chính của doanh nghiệp. | — |
| `web/src/components/SiteFooter.tsx:18` | >Doanh nghiệp</Link><Link href= | — |
| `web/src/components/SiteFooter.tsx:18` | >Thị trường</Link><Link href= | — |
| `web/src/components/SiteFooter.tsx:18` | Doanh nghiệp | — |
| `web/src/components/SiteFooter.tsx:18` | Khám phá NeoPulse | — |
| `web/src/components/SiteFooter.tsx:18` | Nhận thông báo | — |
| `web/src/components/SiteFooter.tsx:18` | Thị trường | — |
| `web/src/components/SiteFooter.tsx:21` | Liên hệ người phát triển | — |
| `web/src/components/SiteFooter.tsx:23` | Phát triển và vận hành NeoPulse Radar. Liên hệ để góp ý, báo lỗi hoặc trao đổi về website. | — |
| `web/src/components/SiteFooter.tsx:25` | Email trường | — |
| `web/src/components/SiteFooter.tsx:26` | Email cá nhân | — |
| `web/src/components/SiteFooter.tsx:27` | Điện thoại | — |
| `web/src/components/SiteFooter.tsx:32` | Thông tin website | — |
| `web/src/components/SiteFooter.tsx:33` | Nguồn dữ liệu | — |
| `web/src/components/SiteFooter.tsx:33` | SSI FastConnect cho thị trường; Vietcap cho hồ sơ doanh nghiệp và lịch sử giá. Thời điểm cập nhật được ghi tại từng trang. | — |
| `web/src/components/SiteFooter.tsx:33` | Địa chỉ truy cập | — |
| `web/src/components/SiteFooter.tsx:34` | Cách tính chỉ báo & giới hạn dữ liệu → | — |
| `web/src/components/SiteFooter.tsx:38` | Công cụ phân tích học thuật. Thông tin tham khảo, không phải khuyến nghị đầu tư. | Miễn trừ chưa thống nhất |
| `web/src/components/SiteFooter.tsx:39` | Quay về đầu trang | — |
| `web/src/components/SiteFooter.tsx:39` | Về đầu trang | — |
| `web/src/components/SiteHeader.tsx:5` | Trang chủ | — |
| `web/src/components/SiteHeader.tsx:8` | NeoPulse · Trang chủ | — |
| `web/src/components/SiteHeader.tsx:9` | Doanh nghiệp | — |
| `web/src/components/SiteHeader.tsx:9` | Khu vực | — |
| `web/src/components/SiteHeader.tsx:9` | Nhận tin | — |
| `web/src/components/SiteHeader.tsx:9` | Thị trường | — |
| `web/src/components/SiteHeader.tsx:9` | }`}>Doanh nghiệp</Link><Link href= | — |
| `web/src/components/SiteHeader.tsx:9` | }`}>Thị trường</Link><Link href= | — |
| `web/src/components/SiteHeader.tsx:11` | Đường dẫn | — |
| `web/src/components/StatusBar.tsx:29` | TRỰC TIẾP | VIẾT HOA toàn bộ |
| `web/src/components/StatusBar.tsx:39` | Không phải thời gian thực | — |
| `web/src/components/StatusBar.tsx:40` | Chi tiết dữ liệu ▾ | — |
| `web/src/components/StatusBar.tsx:48` | Nguồn: | — |
| `web/src/components/StatusBar.tsx:54` | Tin lúc: | — |
| `web/src/components/StatusBar.tsx:55` | (giờ VN) | — |
| `web/src/components/StatusBar.tsx:58` | Độ trễ: | — |
| `web/src/components/StatusBar.tsx:59` | ${(live.latencyMs / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} giây | — |
| `web/src/components/StatusBar.tsx:65` | Snapshot lúc: | Anh-Việt |
| `web/src/components/StatusBar.tsx:66` | (giờ VN) | — |
| `web/src/components/StatusBar.tsx:69` | Cách đây: | — |
| `web/src/components/StatusBar.tsx:72` | Không phải thời gian thực | — |
| `web/src/components/StatusBar.tsx:74` | Số liệu đến: | — |
| `web/src/components/StatusBar.tsx:81` | Cập nhật: | — |
| `web/src/components/StatusBar.tsx:82` | (giờ VN) | — |
| `web/src/components/StatusBar.tsx:86` | Cách đây: | — |
| `web/src/components/StatusBar.tsx:93` | Mã tính / loại: | — |
| `web/src/components/StatusBar.tsx:97` | Số phiên đã lưu: | — |
| `web/src/components/StatusBar.tsx:104` | DỮ LIỆU MÔ PHỎNG | — |
| `web/src/components/tabs.tsx:20` | THẤP | VIẾT HOA toàn bộ |
| `web/src/components/tabs.tsx:20` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/tabs.tsx:31` | Vì sao có cảnh báo này? | — |
| `web/src/components/tabs.tsx:69` | Chưa có dữ liệu sổ lệnh cho bộ lọc hiện tại. | — |
| `web/src/components/tabs.tsx:84` | Bản đồ áp lực sổ lệnh | — |
| `web/src/components/tabs.tsx:86` | Bản đồ nhiệt áp lực sổ lệnh theo mã | — |
| `web/src/components/tabs.tsx:91` | Chưa có mã nào có giá trị khớp. | — |
| `web/src/components/tabs.tsx:92` | Diện tích = giá trị khớp trong phiên; màu = OBI₃ (xanh: bên mua dày hơn, đỏ: bên bán dày hơn) trên 3 mức giá tốt nhất. | — |
| `web/src/components/tabs.tsx:95` | Bảng thanh khoản & trượt giá | — |
| `web/src/components/tabs.tsx:100` | Mã | — |
| `web/src/components/tabs.tsx:101` | % đổi | — |
| `web/src/components/tabs.tsx:101` | Giá | — |
| `web/src/components/tabs.tsx:102` | GT khớp | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:102` | Trượt giá (bps) | — |
| `web/src/components/tabs.tsx:102` | Độ sâu 3 mức | — |
| `web/src/components/tabs.tsx:103` | Tỷ lệ khớp | — |
| `web/src/components/tabs.tsx:103` | Điểm TK | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:127` | Soi một mã | — |
| `web/src/components/tabs.tsx:129` | Chọn mã | — |
| `web/src/components/tabs.tsx:137` | Trượt giá (mua) | — |
| `web/src/components/tabs.tsx:138` | Điểm thanh khoản | — |
| `web/src/components/tabs.tsx:140` | Đang trong phiên định kỳ (ATO/ATC): giá mức 1 không phải giá giới hạn nên chỉ báo sổ lệnh có thể trống. | — |
| `web/src/components/tabs.tsx:142` | Giá giữa và OBI₃ của ${cur.symbol} | — |
| `web/src/components/tabs.tsx:168` | Chưa có dữ liệu khối ngoại. | — |
| `web/src/components/tabs.tsx:175` | Mua/bán ròng theo mã (mạnh nhất hai phía) | — |
| `web/src/components/tabs.tsx:176` | Biểu đồ khối ngoại mua bán ròng theo mã | — |
| `web/src/components/tabs.tsx:184` | Ròng (đồng) | — |
| `web/src/components/tabs.tsx:191` | Chiều và quy mô | — |
| `web/src/components/tabs.tsx:192` | Đồ thị tỷ trọng khối ngoại so với mức ròng trên tổng | — |
| `web/src/components/tabs.tsx:200` | Tỷ trọng NN | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:205` | : góc trên-phải là mua ròng với mức tham gia lớn hơn. Gần trục dọc là tỷ trọng nhỏ; chưa đủ để suy ra tác động giá. | — |
| `web/src/components/tabs.tsx:205` | Tỷ trọng và ròng/tổng | — |
| `web/src/components/tabs.tsx:208` | Bảng khối ngoại | — |
| `web/src/components/tabs.tsx:211` | Mã | — |
| `web/src/components/tabs.tsx:211` | NN bán | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:211` | Room đã dùng | — |
| `web/src/components/tabs.tsx:211` | Ròng | — |
| `web/src/components/tabs.tsx:211` | Ròng/tổng | — |
| `web/src/components/tabs.tsx:211` | Tỷ trọng NN | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:231` | Chưa có dữ liệu hợp đồng tương lai khớp được với chỉ số VN30 trong phiên này. Basis chỉ tính khi chọn chỉ số VN30 và bộ ghi có nhận dữ liệu HĐTL (cần điền NE… | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:237` | HĐTL | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:237` | cơ sở ${num(fu.spot ?? null, 2)} | — |
| `web/src/components/tabs.tsx:238` | ${signed(s.basis)} điểm | — |
| `web/src/components/tabs.tsx:239` | Ngày tới đáo hạn | — |
| `web/src/components/tabs.tsx:240` | ${signed(s.mispricing)} điểm | — |
| `web/src/components/tabs.tsx:240` | Lệch so với giá trị hợp lý | — |
| `web/src/components/tabs.tsx:240` | chưa đủ dữ liệu cho z | — |
| `web/src/components/tabs.tsx:242` | Basis (F − S) theo phút | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:243` | Đồ thị basis hợp đồng tương lai theo phút | — |
| `web/src/components/tabs.tsx:251` | Basis (điểm) | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:255` | Basis thường tiến về mức thanh toán khi gần đáo hạn; các ảnh chụp nội phiên không bảo đảm chênh lệch bằng 0. Giá trị hợp lý dùng lãi suất giả định 4,5%/năm v… | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:265` | Không có cảnh báo nào trong phiên. | — |
| `web/src/components/tabs.tsx:270` | ${s === "CAO" ? "◆" : s === "TRUNG BÌNH" ? "◇" : "·"} ${s} | VIẾT HOA toàn bộ |
| `web/src/components/tabs.tsx:270` | THẤP | VIẾT HOA toàn bộ |
| `web/src/components/tabs.tsx:273` | ${items.length} / ${al.total} cảnh báo | — |
| `web/src/components/tabs.tsx:275` | Lọc loại cảnh báo | — |
| `web/src/components/tabs.tsx:276` | Mọi loại | — |
| `web/src/components/tabs.tsx:281` | Không có cảnh báo khớp bộ lọc. | — |
| `web/src/components/tabs.tsx:283` | . Cảnh báo không xác nhận nguyên nhân và không phải khuyến nghị. | — |
| `web/src/components/tabs.tsx:283` | hoặc | — |
| `web/src/components/tabs.tsx:283` | khối lượng tương đối | — |
| `web/src/components/tabs.tsx:283` | lệch sổ lệnh | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:283` | sát trần/sàn | — |
| `web/src/components/tabs.tsx:283` | z nội phiên | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:283` | Đây là số lượt cảnh báo, không phải số mã. Mỗi quy tắc có điều kiện riêng: | — |
| `web/src/components/tabs.tsx:298` | Chưa có dữ liệu để xếp hạng. | — |
| `web/src/components/tabs.tsx:299` | Chi phí | — |
| `web/src/components/tabs.tsx:299` | Khối ngoại | — |
| `web/src/components/tabs.tsx:299` | Sổ lệnh | — |
| `web/src/components/tabs.tsx:299` | Thanh khoản | — |
| `web/src/components/tabs.tsx:299` | Động lượng | — |
| `web/src/components/tabs.tsx:301` | Xếp hạng đa yếu tố trong rổ | — |
| `web/src/components/tabs.tsx:302` | Điểm = tổng có trọng số của z-score mặt cắt ngang (động lượng 30%, sổ lệnh 25%, khối ngoại 20%, thanh khoản 15%, chi phí 10%). Chỉ có nghĩa tương đối trong r… | — |
| `web/src/components/tabs.tsx:306` | % đổi | — |
| `web/src/components/tabs.tsx:306` | Giá | — |
| `web/src/components/tabs.tsx:306` | Hạng | — |
| `web/src/components/tabs.tsx:306` | Mã | — |
| `web/src/components/tabs.tsx:306` | NN ròng/tổng | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:306` | Điểm | — |
| `web/src/components/tabs.tsx:325` | Nhóm phiên | — |
| `web/src/components/tabs.tsx:325` | Sau bao nhiêu thanh | — |
| `web/src/components/tabs.tsx:325` | Tín hiệu | — |
| `web/src/components/tabs.tsx:325` | mẫu | — |
| `web/src/components/tabs.tsx:325` | tín hiệu | — |
| `web/src/components/tabs.tsx:325` | tầm nhìn (thanh) | — |
| `web/src/components/tabs.tsx:326` | Cặp quan sát | — |
| `web/src/components/tabs.tsx:326` | IC trung bình | — |
| `web/src/components/tabs.tsx:326` | Số thanh | — |
| `web/src/components/tabs.tsx:327` | Tỷ lệ cùng chiều (0–1) | — |
| `web/src/components/tabs.tsx:327` | t-stat của IC | — |
| `web/src/components/tabs.tsx:332` | Chưa nhận được kết quả kiểm chứng từ bộ xử lý dữ liệu. Khi có kết quả, trang sẽ tự cập nhật. Mục này kiểm tra chất lượng dữ liệu và mối liên hệ giữa tín hiệu… | — |
| `web/src/components/tabs.tsx:337` | Kiểm chứng trên dữ liệu đã thu thập | — |
| `web/src/components/tabs.tsx:338` | Hệ thống kiểm tra tín hiệu sổ lệnh có liên hệ với thay đổi giá sau đó hay không, đồng thời thống kê dữ liệu thiếu và gián đoạn. Kết quả được tính lại khoảng … | — |
| `web/src/components/tabs.tsx:339` | · Dữ liệu đến ${dmyTime(v.data_until)} | — |
| `web/src/components/tabs.tsx:344` | cài sẵn | — |
| `web/src/components/tabs.tsx:344` | không | — |
| `web/src/components/tabs.tsx:344` | vào cơ chế sinh giá. Kết quả dưới đây chỉ xác nhận đường ống tính toán chạy đúng — | — |
| `web/src/components/tabs.tsx:347` | Tín hiệu sổ lệnh có đi trước biến động giá? | — |
| `web/src/components/tabs.tsx:356` | tín hiệu | — |
| `web/src/components/tabs.tsx:368` | IC theo từng phiên (OBI₃, 1 thanh) | — |
| `web/src/components/tabs.tsx:369` | IC theo từng phiên | — |
| `web/src/components/tabs.tsx:383` | Chất lượng dữ liệu | — |
| `web/src/components/tabs.tsx:385` | Ảnh chụp đã lưu | — |
| `web/src/components/tabs.tsx:386` | Số phiên | — |
| `web/src/components/tabs.tsx:386` | chưa đủ 5 phiên | — |
| `web/src/components/tabs.tsx:386` | đạt mốc tối thiểu; cần thêm mẫu | — |
| `web/src/components/tabs.tsx:387` | Số mã | — |
| `web/src/components/tabs.tsx:388` | Khoảng trống bất thường | — |
| `web/src/components/tabs.tsx:390` | Vấn đề đã ghi nhận theo loại | — |
| `web/src/components/tabs.tsx:393` | Không có. | — |
| `web/src/components/tabs.tsx:403` | Chuỗi xử lý | — |
| `web/src/components/tabs.tsx:406` | chỉ hiển thị kết quả | — |
| `web/src/components/tabs.tsx:409` | Công thức chính | — |
| `web/src/components/tabs.tsx:412` | Chỉ báo | — |
| `web/src/components/tabs.tsx:412` | Công thức | — |
| `web/src/components/tabs.tsx:412` | Ý nghĩa | — |
| `web/src/components/tabs.tsx:415` | (bán₁ − mua₁) / giá giữa × 10⁴ (bps) | — |
| `web/src/components/tabs.tsx:415` | chi phí khứ hồi tức thời | — |
| `web/src/components/tabs.tsx:416` | (ΣKL mua − ΣKL bán) / (ΣKL mua + ΣKL bán), 3 mức | — |
| `web/src/components/tabs.tsx:416` | > 0: bên mua dày hơn | — |
| `web/src/components/tabs.tsx:417` | (bán₁·KLmua₁ + mua₁·KLbán₁) / (KLmua₁ + KLbán₁) | — |
| `web/src/components/tabs.tsx:417` | giá giữa có trọng số độ sâu | — |
| `web/src/components/tabs.tsx:418` | (tăng − giảm) / (tăng + giảm) | — |
| `web/src/components/tabs.tsx:418` | độ lan tỏa | — |
| `web/src/components/tabs.tsx:419` | (mua − bán) / (mua + bán) | — |
| `web/src/components/tabs.tsx:419` | NN ròng/tổng | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:419` | mức độ một chiều của khối ngoại | — |
| `web/src/components/tabs.tsx:420` | F − S; quy năm (F/S − 1)·365/ngày còn lại | — |
| `web/src/components/tabs.tsx:420` | định giá HĐTL so với cơ sở | Thuật ngữ chưa thống nhất |
| `web/src/components/tabs.tsx:421` | 0,6745·(x − median)/MAD, cửa sổ 60 thanh trước | — |
| `web/src/components/tabs.tsx:421` | bất thường khi \|z\| ≥ 3,5 | — |
| `web/src/components/tabs.tsx:421` | z bền vững | — |
| `web/src/components/tabs.tsx:422` | 50 + 50·Σwᵢcᵢ; w = 30/25/20/15/10% | — |
| `web/src/components/tabs.tsx:422` | trạng thái tổng hợp 0–100 | — |
| `web/src/components/tabs.tsx:422` | Điểm nhịp | — |
| `web/src/components/tabs.tsx:429` | Đầy đủ công thức, giả định và tài liệu tham khảo: docs/methodology.md trong mã nguồn. | — |
| `web/src/components/tabs.tsx:431` | Giới hạn cần biết khi đọc số | — |
| `web/src/components/tabs.tsx:433` | Phân biệt dữ liệu trực tiếp và dữ liệu đã lưu. | — |
| `web/src/components/tabs.tsx:433` | Xem nguồn và thời điểm cập nhật trên thanh trạng thái. Khi bộ ghi dừng, máy ngủ hoặc mất kết nối, số liệu mới sẽ ngừng đến; web hiển thị dữ liệu đã lưu và bá… | — |
| `web/src/components/tabs.tsx:434` | : OBI và độ sâu bỏ sót lệnh ở xa và lệnh ẩn; trượt giá là cận dưới. | — |
| `web/src/components/tabs.tsx:434` | Chỉ 3 mức giá tốt nhất | — |
| `web/src/components/tabs.tsx:435` | , không phải dấu thời gian sự kiện → độ trễ mạng lẫn vào chuỗi. | — |
| `web/src/components/tabs.tsx:435` | Thời điểm dùng là lúc nhận | — |
| `web/src/components/tabs.tsx:436` | (mặc định VN30): khối ngoại và sổ lệnh là của rổ, không phải toàn thị trường; độ rộng lấy từ số của sàn. | — |
| `web/src/components/tabs.tsx:436` | Rổ theo dõi hữu hạn | — |
| `web/src/components/tabs.tsx:437` | (giá trung bình × khối lượng), nên các chỉ báo theo giá trị kém chính xác hơn. | — |
| `web/src/components/tabs.tsx:437` | Giá trị giao dịch lũy kế từ SSI là ước lượng | — |
| `web/src/components/tabs.tsx:438` | , không phải ước lượng; xem độ nhạy ở tab Tổng quan. Điểm mô tả hiện trạng, không dự báo. | — |
| `web/src/components/tabs.tsx:438` | Trọng số điểm nhịp là lựa chọn thiết kế | — |
| `web/src/components/tabs.tsx:439` | ; t-stat chưa hiệu chỉnh tự tương quan. Kết quả yếu hoặc không có ý nghĩa được báo đúng như vậy. | — |
| `web/src/components/tabs.tsx:439` | IC chưa trừ spread và phí | — |
| `web/src/components/tabs.tsx:440` | Phiên định kỳ (ATO/ATC): giá mức 1 không phải giá giới hạn → chỉ báo sổ lệnh để trống. | — |
| `web/src/components/tabs.tsx:441` | ; endpoint giao dịch/tài khoản bị chặn trong mã nguồn. | Anh-Việt |
| `web/src/components/tabs.tsx:441` | Sản phẩm | — |
| `web/src/components/tabs.tsx:441` | không đặt lệnh | — |
| `web/src/components/tabs.tsx:443` | Đây là công cụ phân tích học thuật, không phải lời khuyên đầu tư. | — |
| `web/src/components/tabs.tsx:444` | Nguồn tham khảo thiết kế và cách áp dụng trong dự án ↗ | — |
| `web/src/components/TechnicalChart.tsx:23` | Phiên | — |
| `web/src/components/TechnicalChart.tsx:26` | Tất cả | — |
| `web/src/components/TechnicalChart.tsx:36` | Phiên | — |
| `web/src/components/TechnicalChart.tsx:36` | Tất cả | — |
| `web/src/components/TechnicalChart.tsx:37` | Chu kỳ ${name} | — |
| `web/src/components/TechnicalChart.tsx:38` | Tham chiếu phiên đang xem | — |
| `web/src/components/TechnicalChart.tsx:40` | ${history!.source} · ${history!.unit} · ${data.length} phiên có dữ liệu (${dmy(history!.from)}–${dmy(history!.to)}) | — |
| `web/src/components/TechnicalChart.tsx:40` | Nội phiên đã ghi · không có dữ liệu phút của các phiên chưa thu thập. MA/EMA nội phiên (nếu có) dừng ở mốc snapshot; không tính từ giá lịch sử ngày. | Anh-Việt |
| `web/src/components/TechnicalChart.tsx:41` | Chưa tải được lịch sử ngày; hiển thị dữ liệu sẵn có. Thử tải lại trang. | — |
| `web/src/components/TechnicalChart.tsx:42` | Chưa đủ phiên để vẽ một số đường đã chọn. | — |
| `web/src/components/TechnicalChart.tsx:44` | MA là trung bình đơn giản; EMA dùng hệ số 2/(n+1), khởi tạo bằng MA của n phiên đầu. Chu kỳ tính theo số phiên, không theo ngày lịch. Tín hiệu kỹ thuật không… | — |
| `web/src/components/TelegramSignup.tsx:6` | Bro muốn nhận nội dung nào? | Lóng/cường điệu |
| `web/src/components/TelegramSignup.tsx:6` | Cảnh báo thị trường mức CAO | — |
| `web/src/components/TelegramSignup.tsx:6` | Nguồn Báo Chính phủ. Phân biệt bài viết/đề xuất và văn bản có hiệu lực. | — |
| `web/src/components/TelegramSignup.tsx:6` | Tin chính sách & văn bản | — |
| `web/src/components/TelegramSignup.tsx:6` | Tin doanh nghiệp đáng chú ý | — |
| `web/src/components/TelegramSignup.tsx:6` | Tiêu đề có nhắc mã theo dõi từ RSS CafeF, kèm link bài gốc. | — |
| `web/src/components/TelegramSignup.tsx:6` | Tín hiệu bất thường từ dữ liệu NeoPulse, kèm mã và thời điểm. | — |
| `web/src/components/TelegramSignup.tsx:7` | Chọn ít nhất một nhóm tin để đăng ký. | — |
| `web/src/components/TelegramSignup.tsx:7` | Mở Telegram và nhấn Start ↗ | — |
| `web/src/components/TelegramSignup.tsx:8` | Chỉ đăng ký sau khi bạn nhấn Start trong Telegram. Website không yêu cầu tài khoản hay thu thập số điện thoại của bạn. Không đăng ký cũng sử dụng được toàn b… | — |
| `web/src/components/ThemeToggle.tsx:58` | Chuyển sang giao diện ${theme === "dark" ? "sáng" : "tối"} | — |
| `web/src/components/ThemeToggle.tsx:71` | Sáng | — |
| `web/src/components/ThemeToggle.tsx:71` | Tối | — |
| `web/src/components/TradingViewChart.tsx:56` | Tham chiếu phiên | — |
| `web/src/components/TradingViewChart.tsx:60` | ${symbol}${comparison ? " / VN-Index · ngày đầu = 100" : " · chỉ số"} | — |
| `web/src/components/TradingViewChart.tsx:60` | Mở trên TradingView ↗ | — |
| `web/src/components/TradingViewChart.tsx:61` | Biểu đồ tương tác ${symbol} | — |
| `web/src/components/TradingViewChart.tsx:61` | Chưa đủ điểm dữ liệu để vẽ biểu đồ. | — |
| `web/src/components/TradingViewChart.tsx:62` | Cuộn để thu phóng, kéo để di chuyển, chạm để đọc giá trị. Dữ liệu NeoPulse theo nguồn và thời điểm ghi trên trang; không phải luồng giá từ TradingView. Thời … | — |
| `web/src/components/TradingViewChart.tsx:63` | TradingView Lightweight Charts™ · Copyright (с) 2025 TradingView, Inc. | — |
| `web/src/components/ui.tsx:55` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/ui.tsx:64` | giá trị ${value.toFixed(2)} | — |
| `web/src/components/ui.tsx:85` | Chưa đủ dữ liệu cho điểm nhịp | — |
| `web/src/components/ui.tsx:85` | Điểm nhịp ${x} trên thang 0 đến 100 | — |
| `web/src/components/ui.tsx:90` | 0 · tiêu cực | — |
| `web/src/components/ui.tsx:90` | tích cực · 100 | — |
| `web/src/components/ui.tsx:117` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/ui.tsx:117` | Thấp | — |
| `web/src/components/ui.tsx:117` | Trung bình | — |
| `web/src/components/ui.tsx:119` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/components/useLive.ts:40` | không lấy được token | Anh-Việt |
| `web/src/lib/data.ts:25` | HTTP ${res.status} khi đọc ${rel} | Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/lib/data.ts:61` | : ""} trong danh sách đã xuất. | — |
| `web/src/lib/data.ts:61` | Không có phiên ${date}${code ? | — |
| `web/src/lib/data.ts:95` | Không tải được phiên mới trên cloud; đang dùng dữ liệu đã lưu. Kiểm tra thời điểm cập nhật. | Anh-Việt |
| `web/src/lib/data.ts:102` | Không đọc được Blob (${e instanceof Error ? e.message : "lỗi không xác định"}). | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/lib/data.ts:109` | ${notice ?? ""} Không đọc được snapshot tĩnh (${e instanceof Error ? e.message : "lỗi không xác định"}). | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/lib/data.ts:116` | ${notice ? notice + " " : ""}Chưa có snapshot dữ liệu thật (public/data trống): đang hiển thị dữ liệu MẪU MÔ PHỎNG đi kèm mã nguồn. | Anh-Việt, VIẾT HOA toàn bộ |
| `web/src/lib/fmt.ts:15` | ${nf(1).format(v / 1e15)} triệu tỷ | — |
| `web/src/lib/fmt.ts:16` | ${nf(1).format(v / 1e12)} nghìn tỷ | — |
| `web/src/lib/fmt.ts:17` | ${nf(0).format(v / 1e9)} tỷ | — |
| `web/src/lib/format.ts:22` | ${nf(1).format(x / 1e12)} nghìn tỷ | — |
| `web/src/lib/format.ts:23` | ${nf(1).format(x / 1e9)} tỷ | — |
| `web/src/lib/format.ts:24` | ${nf(1).format(x / 1e6)} triệu | — |
| `web/src/lib/live.ts:26` | THẤP | VIẾT HOA toàn bộ |
| `web/src/lib/live.ts:26` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `web/src/lib/live.ts:157` | Lỗi kết nối trực tiếp: ${error} | — |
| `web/src/lib/live.ts:158` | Chưa kết nối kênh trực tiếp | — |
| `web/src/lib/live.ts:159` | Chưa nhận tin trực tiếp nào | — |
| `web/src/lib/live.ts:160` | Chưa có dữ liệu trực tiếp | — |
| `web/src/lib/live.ts:161` | Quá 60 giây không có tin trực tiếp | — |
| `web/src/lib/live.ts:163` | Bộ ghi không có dữ liệu mới quá 60 giây | — |
| `web/src/lib/live.ts:165` | Ngoài giờ giao dịch | — |
| `web/src/lib/live.ts:166` | Bộ phát đã kết thúc phiên | — |
| `web/src/lib/live.ts:167` | Đang nhận tin trực tiếp | — |
| `web/src/lib/parse.ts:12` | JSON không có khối meta. | Anh-Việt |
| `web/src/lib/parse.ts:15` | Phiên bản schema ${String(m.schema_version)} chưa được hỗ trợ (cần ${SUPPORTED_SCHEMA}). | Anh-Việt |
| `web/src/lib/parse.ts:18` | meta thiếu trường bắt buộc (generated_at, source, is_simulated). | Anh-Việt |
| `web/src/lib/parse.ts:22` | meta.data_status không hợp lệ. | Anh-Việt |
| `web/src/lib/parse.ts:28` | index.json không hợp lệ. | — |
| `web/src/lib/plain.ts:13` | Chưa đủ dữ liệu để đánh giá. | — |
| `web/src/lib/plain.ts:16` | Số cổ phiếu giảm đang nhiều hơn số tăng | — |
| `web/src/lib/plain.ts:16` | Số cổ phiếu tăng và giảm gần bằng nhau | — |
| `web/src/lib/plain.ts:16` | Số cổ phiếu tăng đang nhiều hơn số giảm | — |
| `web/src/lib/plain.ts:17` | Biến động của chỉ số hiện ít tác động đến điểm nhịp | — |
| `web/src/lib/plain.ts:17` | Mức giảm của chỉ số đang kéo điểm nhịp xuống | — |
| `web/src/lib/plain.ts:17` | Mức tăng của chỉ số đang góp phần nâng điểm nhịp | — |
| `web/src/lib/plain.ts:18` | Lệnh chờ mua và bán gần cân bằng | — |
| `web/src/lib/plain.ts:18` | Nhìn chung, lệnh chờ bán đang trội hơn lệnh chờ mua | — |
| `web/src/lib/plain.ts:18` | Nhìn chung, lệnh chờ mua đang trội hơn lệnh chờ bán | — |
| `web/src/lib/plain.ts:19` | Giá trị mua và bán của khối ngoại gần bằng nhau | — |
| `web/src/lib/plain.ts:19` | Khối ngoại đang bán nhiều hơn mua trong rổ theo dõi | — |
| `web/src/lib/plain.ts:19` | Khối ngoại đang mua nhiều hơn bán trong rổ theo dõi | — |
| `web/src/lib/plain.ts:20` | Giá trị giao dịch cao hơn các phiên trước ở cùng thời điểm | — |
| `web/src/lib/plain.ts:20` | Giá trị giao dịch gần với mức thường thấy ở cùng thời điểm | — |
| `web/src/lib/plain.ts:20` | Giá trị giao dịch thấp hơn các phiên trước ở cùng thời điểm | — |
| `web/src/lib/plain.ts:22` | Nghiêng tiêu cực | — |
| `web/src/lib/plain.ts:22` | Nghiêng tích cực | — |
| `web/src/lib/plain.ts:22` | Trung tính | — |
| `web/src/lib/plain.ts:31` | Chưa đủ dữ liệu để kết luận. | — |
| `web/src/lib/plain.ts:32` | Tín hiệu chung đang khá tích cực. | — |
| `web/src/lib/plain.ts:33` | Tín hiệu chung hơi nghiêng về chiều tích cực. | — |
| `web/src/lib/plain.ts:34` | Các tín hiệu đang khá cân bằng. | — |
| `web/src/lib/plain.ts:35` | Tín hiệu chung hơi nghiêng về chiều tiêu cực. | — |
| `web/src/lib/plain.ts:36` | Tín hiệu chung đang khá yếu. | — |
| `web/src/lib/plain.ts:42` | ${code} đang ${change > 0 ? "tăng" : "giảm"} ${num(Math.abs(change))}% so với mức tham chiếu. | — |
| `web/src/lib/plain.ts:42` | ${code} đang ở mức tham chiếu. | — |
| `web/src/lib/plain.ts:45` | Trong nhóm cổ phiếu của chỉ số này, có ${num(declines, 0)} mã giảm và ${num(advances, 0)} mã tăng. | — |
| `web/src/lib/plain.ts:46` | Trong nhóm cổ phiếu của chỉ số này, có ${num(advances, 0)} mã tăng và ${num(declines, 0)} mã giảm. | — |
| `web/src/lib/plain.ts:86` | Khối lượng khớp tăng vọt so với bình thường | Lóng/cường điệu |
| `web/src/lib/plain.ts:87` | Chênh lệch giá mua – bán bỗng giãn rộng (khó mua bán sát giá) | Lóng/cường điệu, Thuật ngữ chưa thống nhất |
| `web/src/lib/plain.ts:88` | Giá đổi đột ngột trong một phút | — |
| `web/src/lib/plain.ts:89` | Khối ngoại mua hoặc bán dồn dập bất thường | Lóng/cường điệu |
| `web/src/lib/plain.ts:90` | Sổ lệnh lệch hẳn về một phía nhiều phút liền | Lóng/cường điệu |
| `web/src/lib/plain.ts:91` | Giá đang sát trần hoặc sát sàn | — |
| `web/src/lib/status.ts:37` | ${Math.round(sec)} giây | — |
| `web/src/lib/status.ts:38` | ${Math.round(sec / 60)} phút | — |
| `web/src/lib/status.ts:39` | ${(sec / 3600).toFixed(1)} giờ | — |
| `web/src/lib/status.ts:51` | Lỗi dữ liệu | Lỗi thiếu hướng xử lý |
| `web/src/lib/status.ts:55` | Dữ liệu mô phỏng — không phải dữ liệu thị trường. | — |
| `web/src/lib/status.ts:55` | MÔ PHỎNG | — |
| `web/src/lib/status.ts:59` | Chưa mở cửa | — |
| `web/src/lib/status.ts:59` | Nghỉ trưa | — |
| `web/src/lib/status.ts:59` | Phiên đã kết thúc | — |
| `web/src/lib/status.ts:60` | Nghỉ trưa (11:30–13:00). | — |
| `web/src/lib/status.ts:60` | Phiên chưa mở cửa. | — |
| `web/src/lib/status.ts:60` | Phiên đã kết thúc. | — |
| `web/src/lib/status.ts:61` | ${why} Hiển thị dữ liệu của lần cập nhật cuối. | — |
| `web/src/lib/status.ts:67` | Dữ liệu cũ | — |
| `web/src/lib/status.ts:68` | Đang trong giờ giao dịch nhưng bản đẩy lên web đã cũ — máy ghi hoặc `neopulse publish` có thể đã dừng. | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `web/src/lib/status.ts:73` | Phiên đã kết thúc | — |
| `web/src/lib/status.ts:76` | Không rõ tuổi dữ liệu | — |
| `web/src/lib/status.ts:76` | Thiếu mốc thời gian cập nhật. | — |
| `web/src/lib/status.ts:77` | Dữ liệu mới | — |
| `web/src/lib/status.ts:77` | Đang nhận dữ liệu. | — |
| `web/src/lib/status.ts:78` | Dữ liệu chưa được làm mới gần đây. | — |
| `web/src/lib/status.ts:78` | Hơi trễ | — |
| `web/src/lib/status.ts:79` | Bộ ghi hoặc đường đẩy dữ liệu có thể đã dừng, hoặc mất kết nối. | — |
| `web/src/lib/status.ts:79` | Dữ liệu cũ | — |
| `web/src/lib/status.ts:89` | Không phải thời gian thực: số liệu cố định tại thời điểm snapshot. | Anh-Việt |
| `web/src/lib/status.ts:93` | Snapshot giữa phiên | Anh-Việt |
| `web/src/lib/status.ts:94` | ${base} Thị trường có thể đã thay đổi sau lúc snapshot. | Anh-Việt |
| `web/src/lib/status.ts:98` | Snapshot cuối phiên | Anh-Việt |
| `web/src/lib/types.ts:4` | THẤP | VIẾT HOA toàn bộ |
| `web/src/lib/types.ts:4` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/alerts.py:12` | đáng xem | — |
| `src/neopulse/analytics/alerts.py:28` | Bùng nổ khối lượng | Lóng/cường điệu |
| `src/neopulse/analytics/alerts.py:28` | Giãn chênh lệch mua-bán | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/alerts.py:29` | Dòng tiền NN bất thường | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/alerts.py:29` | Giá biến động đột ngột | — |
| `src/neopulse/analytics/alerts.py:30` | Sát trần/sàn | — |
| `src/neopulse/analytics/alerts.py:30` | Sổ lệnh lệch kéo dài | — |
| `src/neopulse/analytics/alerts.py:81` | THẤP | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/alerts.py:81` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/alerts.py:113` | {name}: RVOL = {r.value:.1f} lần mức thường thấy cùng giờ (ngưỡng {RVOL_SPIKE:g}) | — |
| `src/neopulse/analytics/alerts.py:115` | bên BÁN dày hơn | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/alerts.py:115` | bên MUA dày hơn | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/alerts.py:116` | {name}: OBI₃ = {r.value:+.2f} ({side}) trong {OBI_PERSIST} thanh liên tiếp | — |
| `src/neopulse/analytics/alerts.py:118` | {name}: giá ở {abs(r.value) * 100:.0f}% biên độ {'trần' if r.value > 0 else 'sàn'} | — |
| `src/neopulse/analytics/alerts.py:121` | {name}: NN {'mua' if r.value > 0 else 'bán'} ròng đột biến ({z}) | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/alerts.py:123` | {name}: {z} (ngưỡng {r.threshold}) | — |
| `src/neopulse/analytics/explain.py:33` | MÔ PHỎNG | — |
| `src/neopulse/analytics/explain.py:33` | nguồn | — |
| `src/neopulse/analytics/explain.py:33` | phiên | — |
| `src/neopulse/analytics/explain.py:73` | Danh sách câu nhận định, mỗi câu gắn với số liệu cụ thể. | — |
| `src/neopulse/analytics/explain.py:76` | Chưa có dữ liệu để nhận định. | — |
| `src/neopulse/analytics/explain.py:81` | Điểm nhịp thị trường {p.score:.1f}/100 - {p.label}. Thành phần chi phối: {top}. | — |
| `src/neopulse/analytics/explain.py:83` | Thiếu dữ liệu cho: | — |
| `src/neopulse/analytics/explain.py:84` | - điểm được tính trên các thành phần còn lại. | — |
| `src/neopulse/analytics/explain.py:86` | {v.index_code} ở {r['value']:,.2f} ({r.get('pct_change', float('nan')):+.2f}%), | — |
| `src/neopulse/analytics/explain.py:87` | {r.get('advances', 0):.0f} mã tăng / {r.get('declines', 0):.0f} mã giảm, | — |
| `src/neopulse/analytics/explain.py:88` | {r.get('n_ceiling', 0):.0f} trần / {r.get('n_floor', 0):.0f} sàn; | — |
| `src/neopulse/analytics/explain.py:89` | giá trị giao dịch {fmt_money(r.get('total_value'))}. | — |
| `src/neopulse/analytics/explain.py:91` | Phân kỳ: | — |
| `src/neopulse/analytics/explain.py:94` | bán ròng | — |
| `src/neopulse/analytics/explain.py:94` | mua ròng | — |
| `src/neopulse/analytics/explain.py:95` | Khối ngoại {side} {fmt_money(abs(fs['net_val']))} trong rổ theo dõi | — |
| `src/neopulse/analytics/explain.py:96` | ({fs['n_net_buy']} mã mua ròng, {fs['n_net_sell']} mã bán ròng); | — |
| `src/neopulse/analytics/explain.py:97` | mua ròng mạnh nhất {v.foreign.index[0]}, bán ròng mạnh nhất {v.foreign.index[-1]}. | — |
| `src/neopulse/analytics/explain.py:100` | , z = {bs['z']:+.1f} so với trong phiên | — |
| `src/neopulse/analytics/explain.py:101` | {bs['symbol']}: basis {bs['basis']:+.2f} điểm ({bs['basis_pct']:+.2f}%) - {bs['label']}, | — |
| `src/neopulse/analytics/explain.py:102` | còn {bs['dtm']:.0f} ngày tới đáo hạn{z}. | — |
| `src/neopulse/analytics/explain.py:105` | không có | — |
| `src/neopulse/analytics/explain.py:106` | {len(v.alerts)} cảnh báo trong phiên, {len(hi)} mức CAO (mã: {names}). | — |
| `src/neopulse/analytics/explain.py:163` | lỗi gọi API: {type(e).__name__} | — |
| `src/neopulse/analytics/explain.py:166` | số không có trong dữ liệu: {bad[:5]} | — |
| `src/neopulse/analytics/explain.py:168` | đầu ra chứa ngôn ngữ khuyến nghị | — |
| `src/neopulse/analytics/notify.py:12` | Công cụ phân tích học thuật - không phải khuyến nghị đầu tư. | Miễn trừ chưa thống nhất |
| `src/neopulse/analytics/notify.py:17` | [MÔ PHỎNG] | — |
| `src/neopulse/analytics/notify.py:23` | Chưa cấu hình Telegram - bỏ qua gửi. | — |
| `src/neopulse/analytics/notify.py:45` | THẤP | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/notify.py:45` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/view.py:38` | Chưa có dữ liệu. | — |
| `src/neopulse/analytics/view.py:98` | Chưa có dữ liệu cho nguồn '{source}'. Hãy chạy bộ ghi hoặc tạo dữ liệu mô phỏng. | — |
| `src/neopulse/analytics/view.py:111` | Không có dữ liệu cho phiên {day} với bộ lọc hiện tại. | — |
| `src/neopulse/analytics/view.py:123` | Dữ liệu MÔ PHỎNG - không phải dữ liệu thị trường. | — |
| `src/neopulse/analytics/view.py:125` | Đang nhận dữ liệu. | — |
| `src/neopulse/analytics/view.py:128` | Dữ liệu đã cũ {v.age_seconds / 60:.0f} phút - bộ ghi có thể đã dừng, mất kết nối | — |
| `src/neopulse/analytics/view.py:129` | hoặc thị trường đang nghỉ. | — |
| `src/neopulse/analytics/view.py:131` | Dữ liệu lịch sử của phiên {day} (đã đóng). | — |
| `src/neopulse/analytics/view.py:192` | {x / 1e9:,.1f} tỷ | — |
| `src/neopulse/analytics/view.py:194` | {x / 1e6:,.1f} triệu | — |
| `src/neopulse/analytics/view.py:222` | SSI REST ngày (20 phiên) | — |
| `src/neopulse/analytics/view.py:225` | {min(20, hist['trading_date'].nunique())} phiên đã ghi | — |
| `src/neopulse/analytics/view.py:228` | giả định phân bổ đều theo phút | — |
| `src/neopulse/analytics/view.py:228` | thực nghiệm từ các phiên đã ghi | — |
| `src/neopulse/analytics/briefing.py:58` | THẤP | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/briefing.py:58` | TRUNG BÌNH | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/anomaly.py:22` | z-score bền vững của từng điểm so với cửa sổ `window` điểm liền trước nó. | — |
| `src/neopulse/analytics/validation.py:72` | Không có dữ liệu. | Lỗi thiếu hướng xử lý |
| `src/neopulse/analytics/validation.py:78` | ngoài mẫu | — |
| `src/neopulse/analytics/validation.py:78` | trong mẫu | — |
| `src/neopulse/analytics/validation.py:82` | mẫu | — |
| `src/neopulse/analytics/validation.py:82` | tín hiệu | — |
| `src/neopulse/analytics/validation.py:82` | tầm nhìn (thanh) | — |
| `src/neopulse/analytics/validation.py:87` | Mới có {n_days} phiên (< 5 phiên khuyến nghị của đề): kết quả chỉ mang tính minh họa. | — |
| `src/neopulse/analytics/company.py:114` | không dùng được vnstock: {type(e).__name__} | — |
| `src/neopulse/analytics/company.py:122` | vnstock bị chặn giới hạn | — |
| `src/neopulse/analytics/company.py:333` | Chi phí bán hàng | — |
| `src/neopulse/analytics/company.py:333` | Doanh thu thuần | — |
| `src/neopulse/analytics/company.py:333` | Lợi nhuận gộp | — |
| `src/neopulse/analytics/company.py:334` | Chi phí quản lý doanh nghiệp | — |
| `src/neopulse/analytics/company.py:334` | Doanh thu tài chính | — |
| `src/neopulse/analytics/company.py:335` | Chi phí lãi vay | — |
| `src/neopulse/analytics/company.py:335` | Lợi nhuận sau thuế | — |
| `src/neopulse/analytics/company.py:335` | Lợi nhuận trước thuế | — |
| `src/neopulse/analytics/company.py:336` | LNST cổ đông công ty mẹ | — |
| `src/neopulse/analytics/company.py:337` | Tiền và tương đương tiền | — |
| `src/neopulse/analytics/company.py:337` | Đầu tư tài chính ngắn hạn | — |
| `src/neopulse/analytics/company.py:338` | Hàng tồn kho | — |
| `src/neopulse/analytics/company.py:338` | Phải thu ngắn hạn | — |
| `src/neopulse/analytics/company.py:338` | Tài sản ngắn hạn | — |
| `src/neopulse/analytics/company.py:339` | Nợ ngắn hạn | — |
| `src/neopulse/analytics/company.py:339` | Tài sản cố định | — |
| `src/neopulse/analytics/company.py:339` | Tổng tài sản | — |
| `src/neopulse/analytics/company.py:340` | Nợ phải trả | — |
| `src/neopulse/analytics/company.py:340` | Vay dài hạn | — |
| `src/neopulse/analytics/company.py:340` | Vay ngắn hạn | — |
| `src/neopulse/analytics/company.py:340` | Vốn chủ sở hữu | — |
| `src/neopulse/analytics/company.py:341` | Chi mua sắm TSCĐ | — |
| `src/neopulse/analytics/company.py:341` | Dòng tiền kinh doanh (CFO) | — |
| `src/neopulse/analytics/company.py:341` | Dòng tiền đầu tư | — |
| `src/neopulse/analytics/company.py:342` | Cổ tức đã trả | — |
| `src/neopulse/analytics/company.py:342` | Dòng tiền tài chính | — |
| `src/neopulse/analytics/company.py:345` | Lãi thuần từ dịch vụ | — |
| `src/neopulse/analytics/company.py:345` | Thu nhập lãi thuần | — |
| `src/neopulse/analytics/company.py:345` | Tổng thu nhập hoạt động | — |
| `src/neopulse/analytics/company.py:346` | Chi phí dự phòng rủi ro tín dụng | — |
| `src/neopulse/analytics/company.py:346` | Chi phí hoạt động | — |
| `src/neopulse/analytics/company.py:347` | LNST cổ đông công ty mẹ | — |
| `src/neopulse/analytics/company.py:347` | Lợi nhuận trước thuế | — |
| `src/neopulse/analytics/company.py:348` | Cho vay khách hàng | — |
| `src/neopulse/analytics/company.py:348` | Tiền gửi của khách hàng | — |
| `src/neopulse/analytics/company.py:349` | Tổng tài sản | — |
| `src/neopulse/analytics/company.py:349` | Vốn chủ sở hữu | — |
| `src/neopulse/analytics/company.py:350` | Chi mua sắm TSCĐ | — |
| `src/neopulse/analytics/company.py:350` | Cổ tức đã trả | — |
| `src/neopulse/analytics/company.py:350` | Dòng tiền kinh doanh (CFO) | — |
| `src/neopulse/analytics/company.py:360` | Nhận định tự động: mỗi câu gắn với số đã tính, không dự báo, không khuyến nghị. | — |
| `src/neopulse/analytics/company.py:365` | Doanh thu thuần | — |
| `src/neopulse/analytics/company.py:365` | Tổng thu nhập hoạt động | — |
| `src/neopulse/analytics/company.py:369` | ({'+' if g >= 0 else ''}{g * 100:.1f}% so với {ys[-2]}) | — |
| `src/neopulse/analytics/company.py:369` | {head} năm {y} đạt {top / BN:,.0f} tỷ đồng | — |
| `src/neopulse/analytics/company.py:370` | ; LNST cổ đông công ty mẹ {c['npat_parent'] / BN:,.0f} tỷ đồng | — |
| `src/neopulse/analytics/company.py:376` | cao hơn | — |
| `src/neopulse/analytics/company.py:376` | m + 0.002 else "thấp hơn" if r["gross_margin"] | — |
| `src/neopulse/analytics/company.py:376` | thấp hơn | — |
| `src/neopulse/analytics/company.py:377` | Biên lợi nhuận gộp {_pct(r['gross_margin'])}, {word} bình quân các năm trước ({_pct(m)}); biên ròng {_pct(r['net_margin'])}. | — |
| `src/neopulse/analytics/company.py:380` | ROE {_pct(r['roe'])} = biên ròng {_pct(r['net_margin'])} × vòng quay tài sản {r['asset_turnover']:.2f} lần | — |
| `src/neopulse/analytics/company.py:381` | × đòn bẩy {r['leverage']:.2f} lần (DuPont). | — |
| `src/neopulse/analytics/company.py:386` | Cho vay/tiền gửi khách hàng {_pct(r['ldr'])}; chi phí hoạt động/thu nhập (CIR) {_pct(r['cir'])}. | — |
| `src/neopulse/analytics/company.py:389` | Nợ vay ròng | — |
| `src/neopulse/analytics/company.py:389` | Tiền và đầu tư ngắn hạn vượt nợ vay: tiền mặt ròng | — |
| `src/neopulse/analytics/company.py:389` | {abs(nd) / BN:,.0f} tỷ đồng | — |
| `src/neopulse/analytics/company.py:390` | ; nợ vay/vốn chủ {r['debt_to_equity']:.2f} lần. | — |
| `src/neopulse/analytics/company.py:395` | Dòng tiền kinh doanh dương {pos}/{have} năm có dữ liệu. | — |
| `src/neopulse/analytics/company.py:396` | Dòng tiền tự do (CFO trừ chi TSCĐ) năm {y}: {r['fcf'] / BN:,.0f} tỷ đồng. | — |
| `src/neopulse/analytics/company.py:397` | Chưa đủ dữ liệu dòng tiền tự do năm gần nhất. | — |
| `src/neopulse/analytics/company.py:399` | , so với trung vị nhóm so sánh {peer_med['pe']:.1f} lần | — |
| `src/neopulse/analytics/company.py:400` | Theo giá {price.get('date') or ''}: P/E {val['pe']:.1f} lần{cmp}; P/B {val['pb']:.2f} lần. | — |
| `src/neopulse/analytics/company.py:401` | P/E {val['pe']:.1f} lần{cmp}. | — |
| `src/neopulse/analytics/company.py:404` | Một năm qua giá {sym} {'+' if one['stock'] >= 0 else ''}{one['stock'] * 100:.1f}%, VN-Index | — |
| `src/neopulse/analytics/company.py:410` | Bảng độ nhạy minh họa, FCFF nền cố định 5 năm, không giả làm dự phóng riêng doanh nghiệp. | — |
| `src/neopulse/analytics/company.py:414` | Không áp dụng FCFF giản lược cho ngân hàng, bảo hiểm hoặc công ty tài chính; cần mô hình vốn chủ và giả định ngành riêng. | — |
| `src/neopulse/analytics/company.py:417` | Cần ít nhất hai năm BCTC liên tiếp và số cổ phiếu để dựng FCFF. | — |
| `src/neopulse/analytics/company.py:421` | Thiếu khoản mục FCFF, nợ vay, tiền, lợi ích không kiểm soát hoặc hai năm liên tiếp. Không thay dữ liệu thiếu bằng 0 để đưa ra giá trị. | — |
| `src/neopulse/analytics/company.py:428` | FCFF nền không dương; cần dự phóng chuyển đổi hoạt động thay vì kéo dài dòng tiền hiện tại. | — |
| `src/neopulse/analytics/company.py:460` | Cùng nhóm ngành ICB cấp 2 trong dữ liệu đã tải | — |
| `src/neopulse/analytics/company.py:462` | Chưa có doanh nghiệp khác cùng ngành trong dữ liệu đã tải; không dùng ngành khác làm nhóm so sánh | — |
| `src/neopulse/analytics/company.py:465` | Nhóm bán lẻ/phân phối tham khảo theo báo cáo MWG: MWG, FRT, DGW, PNJ; có khác biệt phân ngành ICB và mô hình kinh doanh | — |
| `src/neopulse/analytics/company.py:487` | Số liệu BCTC năm hợp nhất; đơn vị tỷ đồng trừ khi ghi khác. | — |
| `src/neopulse/analytics/company.py:488` | Tỷ số dùng bình quân đầu kỳ và cuối kỳ cho các khoản mục bảng cân đối khi có năm trước. | — |
| `src/neopulse/analytics/company.py:489` | EBIT ước tính = lợi nhuận trước thuế + chi phí lãi vay; EBITDA = EBIT + khấu hao (từ LCTT). | — |
| `src/neopulse/analytics/company.py:490` | P/E và EV/EBITDA dùng kết quả cả năm gần nhất đã tải, không phải số liệu 12 tháng gần nhất. | — |
| `src/neopulse/analytics/company.py:491` | DCF nếu có chỉ là bảng độ nhạy theo giả định minh họa, không phải dự phóng hay giá mục tiêu. | — |
| `src/neopulse/analytics/company.py:492` | Không có khuyến nghị mua/bán: đây là hồ sơ mô tả, không phải lời khuyên đầu tư. | — |
| `src/neopulse/analytics/company.py:524` | Mã doanh nghiệp không hợp lệ | — |
| `src/neopulse/analytics/company_remote.py:34` | Mã không hợp lệ | — |
| `src/neopulse/analytics/company_remote.py:47` | Nguồn chưa có dữ liệu | — |
| `src/neopulse/analytics/company_remote.py:60` | Vietcap · tải theo yêu cầu | — |
| `src/neopulse/analytics/company_remote.py:66` | Chưa đủ BCTC năm từ nguồn | — |
| `src/neopulse/analytics/company_remote.py:86` | Vietcap · giá đóng cửa ngày | — |
| `src/neopulse/analytics/company_remote.py:86` | đồng/CP | — |
| `src/neopulse/analytics/company_remote.py:89` | Hồ sơ tải theo yêu cầu: chưa có cổ đông và lãnh đạo trong lần tải này; không thay dữ liệu thiếu bằng 0. | — |
| `src/neopulse/analytics/telegram_cloud.py:18` | NEOPULSE RADAR — TRỢ LÝ THEO DÕI THỊ TRƯỜNG\n\n | — |
| `src/neopulse/analytics/telegram_cloud.py:19` | Bot gửi cảnh báo bất thường, tin doanh nghiệp và tin chính sách theo lựa chọn của bạn. Không đặt lệnh, không khuyến nghị mua/bán.\n\n | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:20` | Mở website: {BASE}\nChọn nhóm tin: {BASE}/thong-bao\nXem doanh nghiệp: {BASE}/doanh-nghiep\n\n | — |
| `src/neopulse/analytics/telegram_cloud.py:21` | BẮT ĐẦU\n/start: đăng ký cảnh báo mức CAO\n/help: xem hướng dẫn này\n | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/telegram_cloud.py:22` | /news on hoặc off: tin doanh nghiệp\n/laws on hoặc off: tin chính sách từ Chính phủ\n | — |
| `src/neopulse/analytics/telegram_cloud.py:23` | /watch MWG,FPT: lọc mã (tối đa 30)\n/all: toàn bộ VN30\n/status: xem cài đặt\n | — |
| `src/neopulse/analytics/telegram_cloud.py:24` | /stop hoặc /delete: hủy và xóa đăng ký\n | — |
| `src/neopulse/analytics/telegram_cloud.py:25` | Tin tự động gửi theo đợt khoảng 15 phút; lịch cloud có thể trễ. Nguồn giá cần được NeoPulse cập nhật để có cảnh báo mới. Không phải lời khuyên đầu tư. | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:77` | Đã hủy và xóa đăng ký NeoPulse. Bot sẽ không gửi thêm tin. /start để đăng ký lại. | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:91` | NeoPulse Radar\n{BASE}\nHồ sơ doanh nghiệp: {BASE}/doanh-nghiep\nNhóm tin: {BASE}/thong-bao | — |
| `src/neopulse/analytics/telegram_cloud.py:94` | Bạn chưa đăng ký. Gửi /start nếu muốn nhận thông báo. | — |
| `src/neopulse/analytics/telegram_cloud.py:97` | Dùng {cmd} on hoặc {cmd} off. | — |
| `src/neopulse/analytics/telegram_cloud.py:104` | Mã không hợp lệ hoặc chưa có trong danh sách hồ sơ. Ví dụ /watch MWG,FPT; tối đa 30 mã. | — |
| `src/neopulse/analytics/telegram_cloud.py:111` | Bật | — |
| `src/neopulse/analytics/telegram_cloud.py:111` | Tắt | — |
| `src/neopulse/analytics/telegram_cloud.py:112` | Cài đặt nhận tin NeoPulse\nCảnh báo: {flag('alerts')}\nTin doanh nghiệp: {flag('news')}\nChính sách: {flag('laws')}\n | — |
| `src/neopulse/analytics/telegram_cloud.py:113` | Mã theo dõi: {', '.join(user['symbols']) or 'Toàn bộ VN30'}\n/stop để hủy và xóa đăng ký. | — |
| `src/neopulse/analytics/telegram_cloud.py:132` | RSS không an toàn | — |
| `src/neopulse/analytics/telegram_cloud.py:145` | nghị định\|thông tư\|luật\|thuế\|chứng khoán\|trái phiếu\|chính sách\|dự thảo | — |
| `src/neopulse/analytics/telegram_cloud.py:147` | \nTin/bài chính sách; có thể là dự thảo/đề xuất. Hiệu lực: xem văn bản gốc, không suy ra từ ngày đăng. | — |
| `src/neopulse/analytics/telegram_cloud.py:149` | [{allowed_host}] {title}\nĐăng: {item.findtext('pubDate')}\n{link}{suffix} | — |
| `src/neopulse/analytics/telegram_cloud.py:186` | Worker sẵn sàng; chưa có đăng ký đang hoạt động. | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:201` | [CẢNH BÁO CAO] {a['symbol']} · {a['t']}\n{a['message']}\n{BASE}/doanh-nghiep/{a['symbol']}\nKhông phải khuyến nghị đầu tư. | VIẾT HOA toàn bộ, Miễn trừ chưa thống nhất |
| `src/neopulse/analytics/telegram_cloud.py:209` | Nguồn {category} tạm không truy cập được; sẽ thử ở lượt sau. | — |
| `src/neopulse/analytics/telegram_cloud.py:255` | Worker hoàn tất; đã gửi {sent} tin mới. Không ghi người nhận vào log. | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:261` | Thiếu Secret Telegram của worker cloud | Anh-Việt |
| `src/neopulse/analytics/telegram_cloud.py:270` | Worker chưa hoàn tất: {type(exc).__name__}; trạng thái đã lưu sẽ được giữ lại để retry. | Anh-Việt |
| `src/neopulse/cli.py:45` | \nLỖI: thiếu SSI_API_KEY/SSI_API_SECRET trong .env (tạo tại https://developers.ssi.com.vn). | — |
| `src/neopulse/cli.py:51` | \nKết nối REST SSI: OK. Rổ {s.universe_index}: {len(members)} mã. Số request đã gửi: {c.request_count} | — |
| `src/neopulse/cli.py:54` | \nLỖI SSI API: {e} | — |
| `src/neopulse/cli.py:61` | Cấu hình (bí mật đã che): | — |
| `src/neopulse/cli.py:64` | \nNEOPULSE_MODE=sim -> không gọi API thật. Đặt NEOPULSE_MODE=live và điền .env để kiểm tra kết nối. | — |
| `src/neopulse/cli.py:69` | \nLỖI: thiếu NEO_USERNAME/NEO_PASSWORD (hoặc NEO_ACCESS_TOKEN) trong .env. | — |
| `src/neopulse/cli.py:74` | \nKết nối REST: OK. Trạng thái phiên: | — |
| `src/neopulse/cli.py:76` | Rổ {s.universe_index}: {len(members)} mã. Tổng số request đã gửi: {c.request_count} | — |
| `src/neopulse/cli.py:79` | \nLỖI NEO API: {e} | — |
| `src/neopulse/cli.py:90` | Đã sinh dữ liệu MÔ PHỎNG vào {s.db_path}: {json.dumps(res, ensure_ascii=False)} | — |
| `src/neopulse/cli.py:97` | phải trong khoảng 0,2-60 giây | — |
| `src/neopulse/cli.py:108` | Bộ ghi cần NEOPULSE_MODE=live. (Dùng `neopulse simulate` nếu chỉ muốn chạy thử.) | Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:113` | Thiếu SSI_API_KEY/SSI_API_SECRET trong .env. | — |
| `src/neopulse/cli.py:116` | Kết thúc ghi (SSI): | — |
| `src/neopulse/cli.py:119` | Thiếu thông tin đăng nhập NEO API trong .env. | — |
| `src/neopulse/cli.py:123` | Kết thúc ghi: | — |
| `src/neopulse/cli.py:130` | SSI không có endpoint REST giá/sổ lệnh thời gian thực nên không có chế độ polling; dùng `neopulse record`. | Anh-Việt, Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:133` | Polling cần NEOPULSE_MODE=live và thông tin đăng nhập trong .env. | — |
| `src/neopulse/cli.py:135` | Kết thúc polling: | Anh-Việt |
| `src/neopulse/cli.py:154` | Phiên {v.trading_date}: {len(v.alerts)} cảnh báo | — |
| `src/neopulse/cli.py:155` | ({(v.alerts['severity'] == 'CAO').sum() if len(v.alerts) else 0} mức CAO); đã gửi Telegram: {sent} | — |
| `src/neopulse/cli.py:172` | Đã xuất bản tin: {out} | — |
| `src/neopulse/cli.py:187` | Chưa có dữ liệu nguồn '{src}'. | — |
| `src/neopulse/cli.py:191` | == KIỂM CHỨNG · nguồn={src}{' (MÔ PHỎNG)' if src == 'sim' else ''} · thanh={args.freq} == | — |
| `src/neopulse/cli.py:193` | \n[1] Dữ liệu: {dq['n_quotes']:,} ảnh chụp · {dq['n_symbols']} mã · {dq['n_sessions']} phiên · | — |
| `src/neopulse/cli.py:194` | {len(dq['gaps'])} khoảng trống bất thường | — |
| `src/neopulse/cli.py:195` | Vấn đề chất lượng theo loại: | — |
| `src/neopulse/cli.py:195` | không có | — |
| `src/neopulse/cli.py:197` | \n[2] Tín hiệu sổ lệnh -> lợi suất kế tiếp (bps). Trong mẫu: {res['train']} · Ngoài mẫu: {res['test']} | — |
| `src/neopulse/cli.py:200` | LƯU Ý: | VIẾT HOA toàn bộ |
| `src/neopulse/cli.py:201` | \n[3] IC theo từng phiên (obi3, 1 thanh): | — |
| `src/neopulse/cli.py:204` | \n[4] Cảnh báo: {len(al)} trên {dq['n_sessions']} phiên; theo quy tắc: {al['rule'].value_counts().to_dict() if len(al) else {}} | — |
| `src/neopulse/cli.py:207` | Đối chiếu với sự kiện cài sẵn (chỉ có ở dữ liệu mô phỏng): | — |
| `src/neopulse/cli.py:208` | \nNHẮC LẠI: dữ liệu mô phỏng có tín hiệu được cài sẵn - các con số trên chỉ xác nhận mã nguồn tính đúng. | — |
| `src/neopulse/cli.py:211` | Đã lưu bảng IC: {args.out} | — |
| `src/neopulse/cli.py:226` | {p}: {len(df):,} dòng | — |
| `src/neopulse/cli.py:244` | {Path(args.out) / e['path']}  (phiên {e['trading_date']}, {e['index_code']}, điểm nhịp {e['pulse_score']}) | — |
| `src/neopulse/cli.py:245` | Đã xuất {len(entries)} tệp JSON{' MÔ PHỎNG' if src == 'sim' else ''} vào {args.out} (latest.json, sessions/, index.json). | Anh-Việt |
| `src/neopulse/cli.py:259` | LỖI: {e} | VIẾT HOA toàn bộ |
| `src/neopulse/cli.py:262` | {res.out_dir / e['path']}  (phiên {e['trading_date']}, {e['index_code']}, {e.get('snapshot_kind')}) | — |
| `src/neopulse/cli.py:263` | Đã ghi snapshot{' MÔ PHỎNG' if src == 'sim' else ''} vào {res.out_dir} ({len(res.entries)} tệp phiên + latest + index). | Anh-Việt |
| `src/neopulse/cli.py:265` | Đã triển khai: {res.url or '(không đọc được URL từ đầu ra vercel)'} | — |
| `src/neopulse/cli.py:267` | Chưa triển khai. Thêm --deploy (hoặc chạy `vercel --prod` trong web/) để đưa lên Vercel. | — |
| `src/neopulse/cli.py:275` | refdata: {len(d['reference'])} mã có phân ngành, {len(d['avg_volume'])} mã có KL TB 20 phiên | — |
| `src/neopulse/cli.py:276` | (tạo lúc {d['generated_at'] or 'chưa có - chạy --refresh'}) | — |
| `src/neopulse/cli.py:279` | Cần NEOPULSE_MODE=live, NEOPULSE_SOURCE=ssi và khóa SSI để lấy dữ liệu tham chiếu. | — |
| `src/neopulse/cli.py:289` | Đã lưu {p}: {len(data['reference'])} mã phân ngành, {len(data['avg_volume'])}/{len(syms)} mã có KL TB | — |
| `src/neopulse/cli.py:290` | {data['sessions']} phiên (nguồn: {', '.join(srcs) or '—'}); {n_req} request REST. | — |
| `src/neopulse/cli.py:309` | Đã xuất {export_cached(raw, args.out)} biểu đồ lịch sử và MA/EMA. | — |
| `src/neopulse/cli.py:314` | Hồ sơ doanh nghiệp (BCTC năm, hồ sơ, giá) qua vnstock/Vietcap -> web/public/data/company/. Không cần khóa SSI. | Anh-Việt |
| `src/neopulse/cli.py:326` | Mã doanh nghiệp không hợp lệ. | — |
| `src/neopulse/cli.py:339` | [{i}/{len(syms)}] {sym}: dừng ({e}); chạy lại sau, các mã đã lấy vẫn giữ. | — |
| `src/neopulse/cli.py:342` | [{i}/{len(syms)}] {sym}: {len(raw['income']['years'])} năm BCTC, {len(raw['prices'])} phiên giá | — |
| `src/neopulse/cli.py:349` | Chưa có dữ liệu thô. Chạy: neopulse company --refresh | — |
| `src/neopulse/cli.py:354` | Đã ghi {len(raws)} hồ sơ doanh nghiệp vào {out} | — |
| `src/neopulse/cli.py:366` | LỖI: {e} | VIẾT HOA toàn bộ |
| `src/neopulse/cli.py:369` | Đã dừng live-relay. | Anh-Việt |
| `src/neopulse/cli.py:371` | Kết thúc live-relay: {st.sent} · lỗi {st.failed} | Anh-Việt |
| `src/neopulse/cli.py:383` | LỖI: {e} | VIẾT HOA toàn bộ |
| `src/neopulse/cli.py:386` | Đã dừng publish. | Anh-Việt |
| `src/neopulse/cli.py:388` | Kết thúc publish: {stats.cycles} chu kỳ, {stats.uploads} tệp đã đẩy, {stats.failures} lỗi | Anh-Việt |
| `src/neopulse/cli.py:389` | (dry-run: chỉ ghi cục bộ) | Anh-Việt |
| `src/neopulse/cli.py:394` | NeoPulse Radar - radar nhịp thị trường trên NEO API | — |
| `src/neopulse/cli.py:400` | nguồn dữ liệu (mặc định: tự chọn) | — |
| `src/neopulse/cli.py:401` | phiên YYYY-MM-DD (mặc định: phiên mới nhất) | — |
| `src/neopulse/cli.py:408` | bước thời gian (giây) | — |
| `src/neopulse/cli.py:409` | xóa dữ liệu mô phỏng cũ trước khi sinh | — |
| `src/neopulse/cli.py:412` | giờ dừng HH:MM (giờ VN) | — |
| `src/neopulse/cli.py:415` | giây giữa hai lần ghi lô xuống SQLite (mặc định 5; dùng 1 khi chạy live-relay) | Anh-Việt |
| `src/neopulse/cli.py:423` | gửi cảnh báo mức CAO qua Telegram | — |
| `src/neopulse/cli.py:440` | xuất JSON cho giao diện web (chỉ đọc SQLite) | Anh-Việt |
| `src/neopulse/cli.py:442` | nhiều chỉ số, cách nhau dấu phẩy (VD VN30,VNINDEX); chỉ số đầu là latest.json | — |
| `src/neopulse/cli.py:444` | xuất mọi phiên đã lưu | — |
| `src/neopulse/cli.py:445` | bỏ khối kiểm chứng (nhanh hơn) | — |
| `src/neopulse/cli.py:446` | lệnh giả định đo trượt giá (triệu đồng) | — |
| `src/neopulse/cli.py:448` | dữ liệu tham chiếu: phân ngành + KL trung bình 20 phiên (REST SSI) | — |
| `src/neopulse/cli.py:449` | gọi REST SSI để cập nhật (chạy trước phiên) | — |
| `src/neopulse/cli.py:451` | lịch sử ngày và MA/EMA cho web, tính bằng Python | Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:452` | lấy lại lịch sử VN30/VNINDEX từ nguồn công khai | — |
| `src/neopulse/cli.py:455` | hồ sơ doanh nghiệp + phân tích BCTC cho web (vnstock/Vietcap, dữ liệu công khai) | — |
| `src/neopulse/cli.py:456` | tải lại từ vnstock (khoảng 30 giây mỗi mã) | — |
| `src/neopulse/cli.py:457` | danh sách mã, phân cách dấu phẩy (mặc định: rổ VN30 tham chiếu) | — |
| `src/neopulse/cli.py:460` | phát số liệu tổng hợp lên Ably kênh neopulse:live (chỉ đọc SQLite) | Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:461` | mặc định: nguồn thật đang cấu hình, hoặc sim | — |
| `src/neopulse/cli.py:462` | giờ dừng HH:MM (giờ VN) | — |
| `src/neopulse/cli.py:463` | ghi tin ra out/live_dryrun.jsonl, không gọi Ably | Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:464` | số người xem giả định để ước tính hạn mức Ably | Chi tiết kỹ thuật lộ ra người dùng |
| `src/neopulse/cli.py:465` | phát lại phiên với tốc độ x lần (mặc định: 10 với sim, 0 = thật) | — |
| `src/neopulse/cli.py:467` | xuất snapshot tĩnh vào web/public/data/ và tùy chọn --deploy lên Vercel (khuyên dùng) | Anh-Việt |
| `src/neopulse/cli.py:468` | mặc định: nguồn thật đang cấu hình, hoặc sim | — |
| `src/neopulse/cli.py:469` | phiên YYYY-MM-DD hoặc 'latest' (mặc định) | — |
| `src/neopulse/cli.py:471` | nhiều chỉ số, cách nhau dấu phẩy (VD VN30,VNINDEX) | — |
| `src/neopulse/cli.py:472` | thư mục ghi JSON (đã .gitignore) | Anh-Việt |
| `src/neopulse/cli.py:474` | xuất mọi phiên đã lưu | — |
| `src/neopulse/cli.py:477` | chạy `vercel --prod --yes` trong web/ và in URL | — |
| `src/neopulse/cli.py:479` | TÙY CHỌN, tốn hạn mức: đẩy JSON lên Vercel Blob theo chu kỳ (Hobby chỉ 2.000 thao tác/tháng) | Anh-Việt, VIẾT HOA toàn bộ |
| `src/neopulse/cli.py:480` | mặc định: nguồn thật đang cấu hình, hoặc sim | — |
| `src/neopulse/cli.py:483` | giây giữa hai lần đẩy | — |
| `src/neopulse/cli.py:484` | giờ dừng HH:MM (giờ VN) | — |
| `src/neopulse/cli.py:485` | thư mục làm việc cục bộ | — |
| `src/neopulse/cli.py:486` | chỉ ghi cục bộ, không gọi mạng | — |
| `src/neopulse/cli.py:507` | Cấu hình không hợp lệ: {e} | — |
| `src/neopulse/analytics/templates/briefing.html.j2:6` | NeoPulse Radar · Bản tin phiên | — |
| `src/neopulse/analytics/templates/briefing.html.j2:32` | NeoPulse Radar · Bản tin phiên | — |
| `src/neopulse/analytics/templates/briefing.html.j2:33` | "MÔ PHỎNG" if v.is_simulated else ("SSI FastConnect" if v.source == "ssi" else "NEO API (VPBankS)") | — |
| `src/neopulse/analytics/templates/briefing.html.j2:33` | Chỉ số theo dõi: | — |
| `src/neopulse/analytics/templates/briefing.html.j2:33` | MÔ PHỎNG | — |
| `src/neopulse/analytics/templates/briefing.html.j2:33` | · Nguồn dữ liệu: | — |
| `src/neopulse/analytics/templates/briefing.html.j2:34` | (giờ Việt Nam) · Lập lúc | — |
| `src/neopulse/analytics/templates/briefing.html.j2:34` | Dữ liệu cập nhật lần cuối: | — |
| `src/neopulse/analytics/templates/briefing.html.j2:35` | DỮ LIỆU MÔ PHỎNG — mọi con số dưới đây do bộ giả lập sinh ra để trình diễn, không phản ánh thị trường thật. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:39` | Điểm nhịp thị trường | — |
| `src/neopulse/analytics/templates/briefing.html.j2:44` | Độ rộng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:46` | trần | — |
| `src/neopulse/analytics/templates/briefing.html.j2:46` | · sàn | — |
| `src/neopulse/analytics/templates/briefing.html.j2:47` | Khối ngoại (rổ) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:49` | mã bán ròng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:49` | mã mua ròng · | — |
| `src/neopulse/analytics/templates/briefing.html.j2:52` | Nhận định (sinh từ số liệu, không phải khuyến nghị) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:56` | trong phiên | — |
| `src/neopulse/analytics/templates/briefing.html.j2:56` | Đường đứt: giá tham chiếu. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:57` | Điểm nhịp trong phiên | — |
| `src/neopulse/analytics/templates/briefing.html.j2:57` | Đường đứt: mức trung tính 50. Không gồm thành phần thanh khoản. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:60` | Phân rã điểm nhịp | — |
| `src/neopulse/analytics/templates/briefing.html.j2:61` | Giá trị [-1, 1] | — |
| `src/neopulse/analytics/templates/briefing.html.j2:61` | Thành phần | — |
| `src/neopulse/analytics/templates/briefing.html.j2:61` | Trọng số | — |
| `src/neopulse/analytics/templates/briefing.html.j2:61` | Vị trí | — |
| `src/neopulse/analytics/templates/briefing.html.j2:62` | c.value\|signed if c.value is not none else "thiếu dữ liệu" | — |
| `src/neopulse/analytics/templates/briefing.html.j2:62` | thiếu dữ liệu | — |
| `src/neopulse/analytics/templates/briefing.html.j2:64` | cho điểm trong khoảng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:64` | Độ nhạy: xáo trộn trọng số ±50 | — |
| `src/neopulse/analytics/templates/briefing.html.j2:65` | nhãn trạng thái giữ nguyên trong | — |
| `src/neopulse/analytics/templates/briefing.html.j2:65` | số lần thử. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:69` | Xếp hạng đa yếu tố (đầu bảng) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:70` | Mã | — |
| `src/neopulse/analytics/templates/briefing.html.j2:70` | NN ròng/tổng | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/templates/briefing.html.j2:70` | Điểm | — |
| `src/neopulse/analytics/templates/briefing.html.j2:73` | Thanh khoản yếu nhất trong rổ | — |
| `src/neopulse/analytics/templates/briefing.html.j2:74` | Mã | — |
| `src/neopulse/analytics/templates/briefing.html.j2:74` | Trượt giá 500tr (bps) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:74` | Điểm TK | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/templates/briefing.html.j2:74` | Độ sâu 3 mức | — |
| `src/neopulse/analytics/templates/briefing.html.j2:79` | Khối ngoại mua ròng mạnh nhất | — |
| `src/neopulse/analytics/templates/briefing.html.j2:80` | Mã | — |
| `src/neopulse/analytics/templates/briefing.html.j2:80` | Room đã dùng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:80` | Ròng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:80` | Ròng/tổng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:80` | Tỷ trọng NN | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/templates/briefing.html.j2:82` | Khối ngoại bán ròng mạnh nhất | — |
| `src/neopulse/analytics/templates/briefing.html.j2:83` | Mã | — |
| `src/neopulse/analytics/templates/briefing.html.j2:83` | Room đã dùng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:83` | Ròng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:83` | Ròng/tổng | — |
| `src/neopulse/analytics/templates/briefing.html.j2:83` | Tỷ trọng NN | Thuật ngữ chưa thống nhất |
| `src/neopulse/analytics/templates/briefing.html.j2:88` | Phái sinh · | — |
| `src/neopulse/analytics/templates/briefing.html.j2:89` | điểm ( | — |
| `src/neopulse/analytics/templates/briefing.html.j2:90` | còn | — |
| `src/neopulse/analytics/templates/briefing.html.j2:90` | ngày tới đáo hạn; lệch so với giá trị hợp lý (chi phí lưu giữ) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:90` | điểm. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:93` | Cảnh báo đáng chú ý ( | — |
| `src/neopulse/analytics/templates/briefing.html.j2:93` | trong phiên) | — |
| `src/neopulse/analytics/templates/briefing.html.j2:94` | Giờ | — |
| `src/neopulse/analytics/templates/briefing.html.j2:94` | Mã | — |
| `src/neopulse/analytics/templates/briefing.html.j2:94` | Mức | — |
| `src/neopulse/analytics/templates/briefing.html.j2:94` | Nội dung | — |
| `src/neopulse/analytics/templates/briefing.html.j2:96` | 'CAO' if a.severity == 'CAO' else ('TB' if a.severity == 'TRUNG BÌNH' else 'THAP') | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/templates/briefing.html.j2:96` | tag {{ 'CAO' if a.severity == 'CAO' else ('TB' if a.severity == 'TRUNG BÌNH' else 'THAP') }} | VIẾT HOA toàn bộ |
| `src/neopulse/analytics/templates/briefing.html.j2:97` | Không có cảnh báo nào trong phiên. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:101` | Phương pháp. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:101` | Điểm nhịp = 50 + 50·Σwᵢcᵢ trên 5 thành phần (độ rộng, động lượng chỉ số, sổ lệnh, khối ngoại, thanh khoản). | — |
| `src/neopulse/analytics/templates/briefing.html.j2:102` | OBI₃ = (ΣKL mua − ΣKL bán)/(tổng) trên 3 mức giá. Cảnh báo dùng z-score bền vững (median/MAD), ngưỡng 3,5. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:103` | Chi tiết: docs/methodology.md. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:104` | Chỉ thấy 3 mức giá tốt nhất; cổ phiếu không có dấu thời gian sự kiện nên dùng thời điểm nhận; điểm nhịp mô tả hiện trạng, | — |
| `src/neopulse/analytics/templates/briefing.html.j2:104` | Giới hạn. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:105` | không dự báo. | — |
| `src/neopulse/analytics/templates/briefing.html.j2:105` | Đây là công cụ phân tích học thuật, không phải khuyến nghị đầu tư. | Miễn trừ chưa thống nhất |
