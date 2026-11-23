/** One dictionary for contextual labels and full lookup. Examples are illustrative, never live quotes. */
export interface GlossaryEntry {
  title: string; aliases: string[]; unit: string; body: string; reading: string;
  example: string; role: string; formula: string; limit: string; tab: string;
  source?: { title: string; url: string };
}

export const METHOD_URL = "https://github.com/thienanpham160806-code/neopulse-radar/blob/main/docs/methodology.md";
export const GLOSSARY: Record<string, GlossaryEntry> = {
  price: {
    title: "Giá và mức thay đổi so với tham chiếu", aliases: ["Last", "giá khớp", "pct_change", "% đổi"], unit: "đồng/cổ phiếu hoặc điểm chỉ số; %",
    tab: "tong-quan", body: "Giá khớp gần nhất hoặc giá trị chỉ số được ghi, so với mức tham chiếu của phiên.", reading: "Dương là cao hơn tham chiếu, âm là thấp hơn. % thay đổi khác số điểm tăng/giảm.",
    example: "Chỉ số từ mức tham chiếu 1.800 xuống 1.782 là giảm 18 điểm, tương đương −1%.", role: "Sự kiện quan sát nền tảng để đối chiếu các chỉ báo và đọc biểu đồ.",
    formula: "% đổi = (giá hiện tại/giá tham chiếu − 1) × 100.", limit: "Luôn đọc thời điểm cập nhật. Chỉ số dùng đơn vị điểm, cổ phiếu dùng đơn vị giá do nguồn ghi trên bảng.",
  },
  turnover: {
    title: "Giá trị và khối lượng giao dịch", aliases: ["GT khớp", "GTGD", "total_value", "volume"], unit: "đồng; cổ phiếu", tab: "so-lenh",
    body: "Khối lượng là số cổ phiếu đã khớp; giá trị là số tiền giao dịch. Cả hai khác với lượng lệnh đang chờ trên sổ.",
    reading: "Số lũy kế tăng dần trong phiên; số của một thanh chỉ là giao dịch trong khoảng đó.", example: "10.000 cổ phiếu khớp ở 50.000 đồng tương ứng 500 triệu đồng giá trị giao dịch.",
    role: "Cho biết quy mô tham gia; dùng làm trọng số sổ lệnh, yếu tố thanh khoản và mức nền phát hiện bất thường.",
    formula: "Giá trị giao dịch = tổng(giá khớp × khối lượng). Với một số trường SSI, đồ án ước lượng từ giá trung bình × khối lượng lũy kế.",
    limit: "Giá trị ước lượng có thể khác số chính thức. Đọc cùng giờ và cùng phạm vi, không so đoạn ghi dở với một phiên trọn.",
  },
  band: {
    title: "Vị trí so với trần/sàn", aliases: ["band_pos", "near limit", "sát trần", "sát sàn"], unit: "−1 đến +1", tab: "canh-bao",
    body: "Đặt giá khớp gần nhất vào biên độ giữa tham chiếu và trần/sàn do nguồn cung cấp.", reading: "+1 là trần, −1 là sàn theo thước đo đã chặn. |vị trí| từ 0,9 là quy tắc sát biên của đồ án.",
    example: "Tham chiếu 100, trần 107, giá 106,3 cho vị trí 0,9: đã đi 90% khoảng từ tham chiếu đến trần.", role: "Phát hiện cổ phiếu gần biên độ để người xem soi kỹ giá và khả năng khớp.",
    formula: "(giá − tham chiếu)/(giá trần − tham chiếu), chặn trong [−1, 1].",
    limit: "Đây là quy tắc theo biên độ, không dùng z-score và không phải tín hiệu chắc chắn tiếp tục tăng/giảm.",
  },
  obi1: {
    title: "Mất cân bằng ở mức giá tốt nhất", aliases: ["OBI1", "OBI₁"], unit: "−1 đến +1", tab: "kiem-chung",
    body: "So khối lượng mua và bán chỉ ở mức giá tốt nhất của mỗi phía.", reading: "Dương: mua dày hơn; âm: bán dày hơn. Không bao gồm mức 2 và 3.",
    example: "Mua mức 1 có 300 cổ phiếu, bán mức 1 có 100 cho OBI₁ = 0,5.", role: "Tín hiệu đối chiếu trong kiểm chứng để xem dùng một mức khác ba mức như thế nào.",
    formula: "(KL mua₁ − KL bán₁)/(KL mua₁ + KL bán₁).", limit: "Lệnh chờ có thể hủy, không phải giao dịch đã thực hiện; không thay OBI₃ trong điểm nhịp.",
  },
  pulse: {
    title: "Điểm nhịp thị trường", aliases: ["Market Pulse Score", "MPS"], unit: "0–100 điểm", tab: "tong-quan",
    body: "Một con số tóm tắt năm góc nhìn: độ rộng, động lượng chỉ số, lệnh chờ, khối ngoại và thanh khoản.",
    reading: "50 là điểm giữa; từ 55 nghiêng tích cực, từ 65 khá tích cực; dưới 45 nghiêng tiêu cực, dưới 35 khá yếu. Các thành phần có thể trái chiều nhau.",
    example: "Điểm 60 chỉ cho biết tổng tín hiệu nghiêng tích cực; không có nghĩa xác suất tăng giá là 60%.",
    role: "Tóm tắt trạng thái hiện tại để người xem biết nên mở nhóm bằng chứng nào trước.",
    formula: "50 + 50 × Σ(wᵢ × cᵢ). Trọng số gốc: độ rộng 30%, động lượng 25%, sổ lệnh 20%, khối ngoại 15%, thanh khoản 10%.",
    limit: "Thiếu thành phần thì chuẩn hóa lại trọng số trên phần có dữ liệu. Dưới 50% trọng số gốc có dữ liệu thì không kết luận. Đây là mô tả, không phải dự báo.",
  },
  breadth: {
    title: "Độ rộng thị trường", aliases: ["Breadth", "A/D", "AD ratio", "phân kỳ"], unit: "−1 đến +1", tab: "tong-quan",
    body: "Cho biết mức tăng hoặc giảm có lan ra nhiều cổ phiếu hay chỉ tập trung ở vài mã lớn.",
    reading: "Dương: nhiều mã tăng hơn giảm. Âm: nhiều mã giảm hơn tăng. Mã đứng giá không nằm trong mẫu số A/D.",
    example: "20 mã tăng, 10 mã giảm cho A/D = (20 − 10)/(20 + 10) ≈ 0,33.",
    role: "Đầu vào có trọng số gốc 30% của điểm nhịp; giúp phát hiện chỉ số và số đông cổ phiếu đi ngược chiều.",
    formula: "A/D = (số mã tăng − số mã giảm)/(số mã tăng + số mã giảm).",
    limit: "Số tăng/giảm thuộc chỉ số được chọn; sổ lệnh và khối ngoại chỉ thuộc rổ đang ghi. Hai phạm vi có thể khác nhau.",
  },
  momentum: {
    title: "Động lượng chỉ số", aliases: ["Momentum", "sigma", "σ"], unit: "−1 đến +1 sau chuẩn hóa", tab: "tong-quan",
    body: "Đặt mức thay đổi của chỉ số cạnh thước đo dao động của chính chỉ số đó để đọc độ mạnh của chuyển động.",
    reading: "Dương góp phần nâng điểm nhịp; âm kéo điểm nhịp xuống. Gần 0 là tác động nhỏ.",
    example: "Chỉ số tăng 1% và σ = 1 điểm % thì thành phần ≈ tanh(1) = 0,76.",
    role: "Đầu vào trọng số gốc 25% của điểm nhịp, bổ sung biên độ cho góc nhìn số mã tăng/giảm.",
    formula: "tanh(% thay đổi chỉ số / σ). σ lấy từ độ lệch chuẩn thay đổi cuối phiên của ít nhất 5 phiên đã lưu; chưa đủ dùng mặc định 1,0 điểm %.",
    limit: "Ít lịch sử thì thước đo dùng giá trị mặc định; không nên diễn giải thành mức dao động đã được ước lượng chắc chắn.",
  },
  book: {
    title: "Mất cân bằng sổ lệnh", aliases: ["OBI", "OBI3", "OBI₃", "Order Book Imbalance"], unit: "−1 đến +1", tab: "so-lenh",
    body: "So khối lượng đang chờ mua và chờ bán ở ba mức giá tốt nhất. Đây là lệnh đang chờ, chưa phải giao dịch đã khớp.",
    reading: "Dương: mua dày hơn; âm: bán dày hơn. Gần 0: hai phía gần cân bằng.",
    example: "Mua chờ 300 cổ phiếu, bán chờ 100 cho OBI₃ = 0,5.",
    role: "Bình quân OBI₃ theo giá trị khớp là đầu vào trọng số gốc 20% của điểm nhịp; OBI₃ cũng được dùng cho cảnh báo và kiểm chứng.",
    formula: "(Σ khối lượng mua − Σ khối lượng bán)/(Σ khối lượng mua + Σ khối lượng bán), lấy 3 mức.",
    limit: "Chỉ thấy 3 mức; lệnh có thể bị hủy và không bao gồm lệnh ẩn. Trong ATO/ATC, chỉ báo sổ lệnh được để trống.",
  },
  obi_w: {
    title: "OBI có trọng số theo mức giá", aliases: ["OBIw", "OBI_w", "OBI weighted"], unit: "−1 đến +1", tab: "kiem-chung",
    body: "Một cách đo lệch mua/bán coi lệnh gần giá tốt nhất quan trọng hơn lệnh ở mức xa.",
    reading: "Dấu giống OBI₃; giá trị có thể khác vì ba mức không được tính ngang nhau.",
    example: "Cùng 300 cổ phiếu mua chờ, lượng ở mức 1 có ảnh hưởng lớn hơn lượng ở mức 3.",
    role: "Tín hiệu đối chiếu trong phần kiểm chứng, không thay thế OBI₃ trong điểm nhịp hiện tại.",
    formula: "Công thức OBI nhưng nhân khối lượng từng mức với 1, 1/2, 1/3 trước khi cộng.",
    limit: "Vẫn chỉ quan sát ba mức giá; không phải độ chắc chắn của việc khớp lệnh.",
  },
  spread: {
    title: "Độ chênh giá mua-bán", aliases: ["Spread", "Chênh lệch giá mua – bán", "bid ask", "spread_bps"], unit: "bps", tab: "so-lenh",
    body: "Khoảng cách giữa giá bán tốt nhất và giá mua tốt nhất, chia cho giá giữa để so sánh các mã.",
    reading: "Càng rộng, chi phí mua bán ngay một lệnh nhỏ thường càng lớn. Spread không cho biết giá sắp tăng hay giảm.",
    example: "Mua tốt nhất 99, bán tốt nhất 101: giá giữa 100, spread = 200 bps = 2%.",
    role: "Đo chi phí tức thời; là yếu tố của điểm thanh khoản, xếp hạng và cảnh báo giãn spread.",
    formula: "(giá bán₁ − giá mua₁)/giá giữa × 10.000.",
    limit: "Chưa tính phí, thay đổi sổ lệnh và tác động của lệnh lớn.",
  },
  bps: {
    title: "Điểm cơ bản", aliases: ["bps", "basis point", "bp"], unit: "1 bps = 0,01%", tab: "so-lenh",
    body: "Đơn vị nhỏ dùng để đọc chênh lệch giá hoặc lợi suất mà không phải viết nhiều số thập phân.",
    reading: "100 bps bằng 1%; 10 bps bằng 0,1%. Đừng nhầm bps với điểm của chỉ số VN30.",
    example: "Trượt giá 5 bps tương đương 0,05% so với mức giá được dùng làm gốc.",
    role: "Thống nhất đơn vị cho spread, trượt giá, microprice và lợi suất kiểm chứng.",
    formula: "Tỷ lệ dạng thập phân × 10.000 = bps.", limit: "Phải đọc kèm mức giá làm gốc và loại chi phí đang đo.",
  },
  mid: {
    title: "Giá giữa", aliases: ["Midpoint", "mid", "midprice"], unit: "đồng/cổ phiếu", tab: "so-lenh",
    body: "Mức nằm giữa giá mua tốt nhất và giá bán tốt nhất.", reading: "Là mốc so sánh hai phía, không phải giá chắc chắn có thể giao dịch.",
    example: "Giá mua 49.900 và giá bán 50.100 cho giá giữa 50.000 đồng.", role: "Mốc gốc tính spread, trượt giá và lợi suất tương lai trong kiểm chứng.",
    formula: "(giá mua₁ + giá bán₁)/2.", limit: "Không phải giá khớp gần nhất; cần cả hai phía sổ lệnh hợp lệ.",
  },
  microprice: {
    title: "Giá vi mô", aliases: ["Microprice", "Giá giữa có trọng số khối lượng", "micro_dev_bps"], unit: "đồng/cổ phiếu; độ lệch theo bps", tab: "so-lenh",
    body: "Điều chỉnh giá giữa theo khối lượng chờ ở giá mua/bán tốt nhất.", reading: "Mua chờ dày hơn đẩy giá này gần phía bán hơn. Độ lệch dương không bảo đảm giá sẽ tăng.",
    example: "Mua 99 với khối lượng 300, bán 101 với khối lượng 100 cho giá có trọng số 100,5.", role: "Tín hiệu vi cấu trúc bổ sung, dùng đối chiếu với biến động giá sau đó.",
    formula: "(giá bán₁ × KL mua₁ + giá mua₁ × KL bán₁)/(KL mua₁ + KL bán₁). Độ lệch = (microprice/mid − 1) × 10.000.",
    limit: "Đồ án dùng công thức có trọng số ở mức 1; không phải toàn bộ mô hình micro-price đã hiệu chỉnh trong nghiên cứu Stoikov.",
  },
  depth: {
    title: "Độ sâu 3 mức", aliases: ["Depth", "depth_value"], unit: "đồng", tab: "so-lenh",
    body: "Tổng giá trị lệnh chờ mua và bán quan sát được ở ba mức giá tốt nhất.", reading: "Càng lớn thì lượng chờ nhìn thấy càng dày; chưa nói bên nào trội hơn.",
    example: "Lệnh mua chờ trị giá 2 tỷ và bán chờ 3 tỷ cho độ sâu tổng 5 tỷ đồng.", role: "Một thành phần xếp hạng thanh khoản tương đối trong rổ.",
    formula: "Σ(giá muaᵢ × KL muaᵢ + giá bánᵢ × KL bánᵢ), i = 1..3.", limit: "Không bao gồm mức xa hơn hay lệnh ẩn; có thể thay đổi trước khi giao dịch.",
  },
  pressure: {
    title: "Tỷ lệ áp lực bán/mua", aliases: ["Pressure", "Bán/Mua"], unit: "lần", tab: "so-lenh",
    body: "So tổng khối lượng chờ bán với tổng khối lượng chờ mua ở ba mức.", reading: "Trên 1: bán chờ dày hơn; dưới 1: mua chờ dày hơn. Khác OBI: điểm cân bằng ở 1, không phải 0.",
    example: "Bán chờ 200, mua chờ 100 cho tỷ lệ 2 lần.", role: "Cách đọc bổ sung cho áp lực của sổ lệnh một mã.", formula: "Σ KL bán / Σ KL mua.", limit: "Mẫu số bằng 0 thì không có tỷ lệ hợp lệ; không dùng để dự đoán chắc chắn giá.",
  },
  slippage: {
    title: "Trượt giá ước lượng", aliases: ["Slippage", "walk book"], unit: "bps so với giá giữa", tab: "so-lenh",
    body: "Ước lượng phải trả cao hơn giá giữa bao nhiêu khi mua ngay bằng một lệnh có giá trị giả định hiển thị trên trang.", reading: "Càng cao càng tốn chi phí. Luôn đọc cùng tỷ lệ khớp vì ba mức giá có thể không đủ cho cả lệnh.",
    example: "Giá giữa 100, giá mua bình quân qua các mức là 100,1: trượt giá 10 bps.", role: "Biến áp lực/độ sâu thành chi phí giao dịch dễ hiểu.",
    formula: "(giá khớp bình quân/giá giữa − 1) × 10.000; đi lần lượt qua 3 mức bán.", limit: "Giả định sổ lệnh đứng yên; chỉ đo phần quan sát được, chưa có phí hoặc tác động ngoài ba mức.",
  },
  fill: {
    title: "Tỷ lệ khớp mô phỏng", aliases: ["Fill ratio", "fill_ratio"], unit: "%", tab: "so-lenh",
    body: "Phần khối lượng của lệnh mua giả định mà ba mức giá bán hiện có hấp thụ được.", reading: "Dưới 100% nghĩa là cần thêm độ sâu ngoài phần đang quan sát để khớp đủ.",
    example: "Muốn mua 1.000 cổ phiếu nhưng ba mức chỉ có 700: tỷ lệ khớp 70%.", role: "Bổ sung giới hạn cho ước lượng trượt giá, tránh coi lệnh khớp một phần là khớp toàn bộ.",
    formula: "Khối lượng mô phỏng khớp / khối lượng yêu cầu.", limit: "Đây là mô phỏng trên ảnh chụp; không gửi lệnh thật hoặc bảo đảm thực thi.",
  },
  liquidity: {
    title: "Thanh khoản so với cùng giờ", aliases: ["Liquidity", "GTGD kỳ vọng"], unit: "−1 đến +1 sau chuẩn hóa", tab: "tong-quan",
    body: "So giá trị giao dịch lũy kế của chỉ số với mức thường thấy ở cùng số phút giao dịch của các phiên trước.", reading: "Dương: giá trị khớp cao hơn mức đối chiếu. Âm: thấp hơn. Nhiều giao dịch không đồng nghĩa giá tăng.",
    example: "Hiện tại 2.000 tỷ, trung vị cùng giờ 1.000 tỷ thì tỷ lệ 2 lần; thành phần chuẩn hóa khoảng 0,6.", role: "Đầu vào trọng số gốc 10% của điểm nhịp, cho biết mức độ tham gia bằng giao dịch đã thực hiện.",
    formula: "tanh(ln(GTGD hiện tại / trung vị GTGD cùng thời điểm của ít nhất 3 phiên trước)).",
    limit: "Chưa đủ ba phiên đối chiếu thì để trống. Điểm thanh khoản từng mã là một chỉ số khác.",
  },
  liq_score: {
    title: "Điểm thanh khoản", aliases: ["Điểm TK", "liquidity score", "liq_score"], unit: "0–100 điểm tương đối", tab: "so-lenh",
    body: "Xếp các mã trong rổ theo spread, độ sâu, giá trị khớp và mức biến động giá trên một đơn vị giao dịch.", reading: "Cao hơn nghĩa là thuận lợi hơn so với các mã khác đang được theo dõi, không phải thang chất lượng tuyệt đối.",
    example: "Điểm 80 không có nghĩa lệnh có xác suất khớp 80%.", role: "Giúp chọn mã để soi thanh khoản; tách biệt thành phần thanh khoản của điểm nhịp.",
    formula: "Trung bình hạng phân vị: spread thấp, độ sâu cao, giá trị khớp cao, Amihud thấp; nhân 100. Bỏ qua yếu tố thiếu.",
    limit: "Thay rổ hoặc số yếu tố có dữ liệu có thể đổi thứ hạng; không phải đề xuất mua bán.",
  },
  amihud: {
    title: "Mức kém thanh khoản Amihud nội phiên", aliases: ["Amihud", "illiquidity"], unit: "bps/tỷ đồng", tab: "so-lenh",
    body: "Ước lượng giá dịch chuyển bao nhiêu trên một tỷ đồng giao dịch ở từng thanh, rồi lấy trung vị.", reading: "Cao: giá dịch chuyển nhiều với ít tiền giao dịch; thấp: ít dịch chuyển hơn trên cùng giá trị.",
    example: "Một thanh biến động tuyệt đối 4 bps với 2 tỷ đồng giao dịch cho tỷ số 2 bps/tỷ.", role: "Một yếu tố của điểm thanh khoản tương đối.",
    formula: "Trung vị(|lợi suất thanh theo bps| / giá trị khớp thanh theo tỷ đồng).", limit: "Biến thể nội phiên phỏng theo Amihud (2002), không phải phép đo nguyên bản ở tần suất ngày; cần loại mẫu số không dương.",
  },
  foreign: {
    title: "Khối ngoại mua ròng/bán ròng", aliases: ["Foreign flow", "Dòng tiền khối ngoại", "NN", "ròng/tổng", "net ratio", "participation"], unit: "đồng; tỷ lệ −1..+1; tỷ trọng %", tab: "khoi-ngoai",
    body: "Mua ròng là giá trị nhà đầu tư nước ngoài mua trừ bán trong rổ đang ghi.", reading: "Đọc cả chiều và quy mô: mua ròng lớn trong giao dịch khối ngoại nhưng chiếm rất ít thanh khoản của mã có thể ít đáng chú ý hơn.",
    example: "Mua 8 tỷ, bán 2 tỷ: ròng +6 tỷ; ròng/tổng = 0,6. Nếu mã khớp 100 tỷ, tỷ trọng khối ngoại là 5% theo quy ước của đồ án.",
    role: "Ròng/tổng toàn rổ là đầu vào trọng số gốc 15% của điểm nhịp; biến động bất thường được cảnh báo riêng.",
    formula: "Ròng = mua − bán. Ròng/tổng = (mua − bán)/(mua + bán). Tỷ trọng = (mua + bán)/(2 × giá trị khớp).",
    limit: "Chỉ thuộc các mã đang ghi, không phải toàn thị trường. Không có giao dịch hoặc thiếu nguồn thì không tự coi là trung tính.",
  },
  room: {
    title: "Room khối ngoại đã dùng", aliases: ["Foreign room", "room_used"], unit: "%", tab: "khoi-ngoai",
    body: "Phần hạn mức sở hữu nước ngoài đã sử dụng so với tổng hạn mức nguồn dữ liệu cung cấp.", reading: "Gần 100% là phần còn lại nhỏ; không có nghĩa khối ngoại đang mua thêm trong phiên.",
    example: "Tổng room 100 triệu cổ phiếu, còn 20 triệu thì đã dùng 80%.", role: "Ngữ cảnh về giới hạn sở hữu khi đọc dòng tiền khối ngoại.", formula: "1 − room còn lại / tổng room.", limit: "Phụ thuộc độ mới và định nghĩa hạn mức của nguồn; không phải tỷ lệ sở hữu trên toàn bộ cổ phiếu.",
  },
  basis: {
    title: "Chênh lệch cơ sở", aliases: ["Basis", "Chênh lệch hợp đồng tương lai và cơ sở", "F − S"], unit: "điểm chỉ số; %", tab: "phai-sinh",
    body: "Giá hợp đồng tương lai VN30 trừ chỉ số VN30 được ghép gần thời điểm đó.", reading: "Dương: hợp đồng đắt hơn cơ sở; âm: rẻ hơn. Dấu này còn liên quan chi phí vốn, cổ tức và thời gian đáo hạn.",
    example: "Hợp đồng 1.805 điểm và VN30 1.800 điểm: basis +5 điểm.", role: "Bổ sung ngữ cảnh phái sinh, không nằm trong năm thành phần điểm nhịp hiện tại.",
    formula: "Basis = F − S; basis (%) = (F − S)/S × 100. Chỉ ghép giá cơ sở đã xuất hiện trước đó, không quá 2 phút.",
    limit: "Basis dương không tự chứng minh kỳ vọng tăng; basis âm không tự tạo cơ hội arbitrage.",
    source: { title: "CME Group: Equity Index Basis", url: "https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/what-is-equity-index-basis" },
  },
  maturity: {
    title: "Ngày đến đáo hạn và giá trị hợp lý", aliases: ["DTM", "carry", "mispricing", "đáo hạn"], unit: "ngày; %/năm; điểm", tab: "phai-sinh",
    body: "Số ngày còn lại và mức định giá tham chiếu giúp đặt basis vào bối cảnh chi phí vốn.", reading: "Khoảng lệch so với mô hình là kết quả dưới các giả định, không phải khẳng định hợp đồng bị định giá sai.",
    example: "Cùng một basis nhưng hợp đồng còn 1 ngày và còn 30 ngày có ý nghĩa khác nhau.", role: "Giải thích chênh lệch giữa tương lai và cơ sở trong tab phái sinh.",
    formula: "Carry quy năm dạng tỷ lệ = (F/S − 1) × 365/DTM; nhân 100 để đọc %/năm. F* = S × [1 + (r − q) × DTM/365], mặc định r = 4,5%/năm, q = 0.",
    limit: "Lãi suất/cổ tức là giả định. Quy năm dễ rất lớn khi sắp đáo hạn; DTM không dương thì không tính tỷ lệ này.",
  },
  basis_z: {
    title: "Độ bất thường của chênh lệch cơ sở trong phiên", aliases: ["basis z", "basis_state", "z phái sinh"], unit: "điểm z", tab: "phai-sinh",
    body: "Đặt basis theo % mới nhất cạnh các quan sát basis đã ghi trước đó trong tập dữ liệu phái sinh đang xét.",
    reading: "Dương là cao hơn trung vị; âm là thấp hơn. Không phải z của lợi suất cổ phiếu hay một xác suất.",
    example: "z basis lớn cho biết chênh lệch khác mức nền đã quan sát, chưa chứng minh có cơ hội giao dịch.",
    role: "Bổ sung ngữ cảnh cho mức lệch hợp đồng tương lai so với cơ sở.",
    formula: "0,6745 × (basis% hiện tại − median basis% trước đó)/MAD; cần ít nhất 30 quan sát trước, không dùng quan sát hiện tại vào mức nền.",
    limit: "Dùng lịch sử trước đó trong tập basis đang xét, khác cửa sổ 60 thanh của cảnh báo cổ phiếu. MAD không dương thì để trống; phụ thuộc chất lượng ghép cơ sở/HĐTL.",
  },
  rvol: {
    title: "Khối lượng tương đối", aliases: ["RVOL", "Relative Volume", "volume spike"], unit: "lần", tab: "canh-bao",
    body: "So khối lượng khớp trong một thanh với khối lượng kỳ vọng của chính mã đó ở cùng thời điểm.", reading: "3 lần nghĩa là cao gấp ba mức nền dùng để đối chiếu; chưa cho biết lực mua hay bán chiếm ưu thế.",
    example: "Thanh vừa khớp 90.000 cổ phiếu, mức kỳ vọng 30.000: RVOL = 3 lần.", role: "Phát hiện khối lượng tăng bất thường. Không có mức nền RVOL thì quy tắc dùng z bền vững trong phiên.",
    formula: "KL thanh / [KL trung bình 20 phiên × phần tỷ trọng thời gian của thanh]. Profile thời gian dùng dữ liệu ghi khi đủ ít nhất 3 phiên đạt tiêu chí độ phủ; thiếu thì giả định đều theo phút giao dịch.",
    limit: "Profile đều bỏ qua hình chữ U và ATC. RVOL không phải phép so sánh đơn giản với khối lượng cả ngày.",
  },
  anomaly: {
    title: "Điểm z bền vững", aliases: ["Robust z", "Độ bất thường so với lịch sử gần", "z bền vững", "MAD", "median", "z-score nội phiên"], unit: "điểm z", tab: "canh-bao",
    body: "Đo mức khác thường của một thanh so với các thanh trước đó của chính mã ấy trong phiên.", reading: "|z| càng lớn càng xa mức nền. Dấu cho biết phía nào của mức nền; không phải xác suất xảy ra sự kiện.",
    example: "z = 4 vượt ngưỡng thường dùng 3,5 của đồ án; vẫn phải đọc quy tắc và điều kiện phụ.", role: "Nền thống kê cho cảnh báo spread, giá và khối ngoại; dự phòng cho khối lượng khi thiếu RVOL.",
    formula: "0,6745 × (x − median)/MAD, cửa sổ 60 thanh trước, tối thiểu 20 thanh. Khối lượng lấy log(1 + x).",
    limit: "MAD bằng 0 thì không kết luận. Cửa sổ chỉ dùng dữ liệu trước thanh đang xét; một số quy tắc dùng OBI/biên độ thay vì z.",
  },
  ranking: {
    title: "Xếp hạng đa yếu tố", aliases: ["Ranking", "z-score mặt cắt ngang", "factor", "n_factors"], unit: "điểm z tổng hợp; thứ hạng", tab: "xep-hang",
    body: "So từng mã với các mã khác trong cùng rổ ở cùng thời điểm, dựa trên giá, lệnh chờ, khối ngoại, thanh khoản và chi phí.", reading: "Hạng cao là nổi bật tương đối theo bộ yếu tố này; không phải thứ tự ưu tiên đầu tư.",
    example: "Một mã đứng đầu rổ 30 mã có thể vẫn giảm giá nếu cả rổ đều yếu.", role: "Giúp chọn mã để kiểm tra sâu sau khi đọc bối cảnh thị trường.",
    formula: "z mặt cắt ngang cắt ở ±3; tổng trọng số động lượng 30%, OBI₃ 25%, khối ngoại 20%, log giá trị khớp 15%, −độ chênh giá mua-bán 10%. Thiếu yếu tố thì chuẩn hóa lại.",
    limit: "Khác z bất thường theo thời gian. Thứ hạng phụ thuộc rổ, thời điểm và số yếu tố có dữ liệu.",
  },
  ic: {
    title: "Hệ số thông tin", aliases: ["IC", "Hệ số liên hệ tín hiệu và lợi suất", "Information Coefficient", "Spearman", "ic_mean"], unit: "−1 đến +1", tab: "kiem-chung",
    body: "Kiểm tra mã có tín hiệu cao hơn ở cuối thanh có thường đạt lợi suất giá giữa cao hơn sau đó hay không.", reading: "Dương: hai thứ hạng đi cùng chiều; âm: ngược chiều; gần 0: ít liên hệ theo phép đo này.",
    example: "IC 0,05 là tương quan hạng nhỏ, không phải lợi nhuận 5% hay tỷ lệ đoán đúng 5%.", role: "Bằng chứng thực nghiệm để đánh giá tín hiệu sổ lệnh trên các phiên đã ghi.",
    formula: "Spearman theo mặt cắt ngang từng thanh (ít nhất 8 mã), rồi lấy trung bình qua các thanh; lợi suất t → t+h không vượt phiên.",
    limit: "Tương quan không chứng minh nhân quả hoặc lợi nhuận giao dịch. Ít phiên thì kết quả mới mang tính minh họa.",
  },
  tstat: {
    title: "Thống kê t của IC", aliases: ["t-stat", "ic_tstat", "t statistic"], unit: "không có đơn vị", tab: "kiem-chung",
    body: "Đặt IC trung bình cạnh độ dao động của các IC để xem mức trung bình khác 0 đến đâu dưới giả định của phép kiểm định.", reading: "Trị tuyệt đối lớn hơn thường đáng chú ý hơn, nhưng chưa thể kết luận nếu giả định thống kê không phù hợp.",
    example: "IC trung bình 0,02, sai số chuẩn 0,01 cho t = 2; tự tương quan có thể làm sai số chuẩn thực lớn hơn.", role: "Đọc cùng IC, số thanh và phần ngoài mẫu khi đánh giá tín hiệu.", formula: "IC trung bình / (độ lệch chuẩn IC / √số thanh).",
    limit: "Chưa hiệu chỉnh tự tương quan giữa các thanh. Không diễn giải riêng t-stat thành xác suất tín hiệu đúng.",
  },
  sample: {
    title: "Trong mẫu, ngoài mẫu và cỡ mẫu", aliases: ["Train", "test", "split", "n_bars", "n_obs", "horizon"], unit: "phiên; thanh; cặp quan sát", tab: "kiem-chung",
    body: "Tách các phiên theo thứ tự thời gian: nhóm đầu để xem trong mẫu, nhóm sau để đối chiếu ngoài mẫu.", reading: "n_bars là số thanh có IC hợp lệ; n_obs là số cặp tín hiệu–lợi suất hợp lệ. Horizon là số thanh từ lúc tín hiệu xuất hiện đến mốc đo lợi suất về sau.",
    example: "Với 5 phiên, 3 phiên đầu nằm trong mẫu và 2 phiên cuối ngoài mẫu; đây vẫn là mẫu ngắn.", role: "Giảm việc đánh giá trên chính đoạn đã quan sát và làm rõ lượng bằng chứng thực có.",
    formula: "Tách theo thời gian với tỷ lệ mục tiêu 60% phiên đầu / 40% phiên sau; không xáo trộn và không ghép lợi suất sang phiên khác.",
    limit: "Đạt 5 phiên mới là mốc thu thập tối thiểu của đồ án, chưa chứng minh khả năng tổng quát dài hạn. Thanh liên tiếp không độc lập.",
  },
  hit_rate: {
    title: "Tỷ lệ cùng chiều và chênh lệch Q5−Q1", aliases: ["Hit rate", "spread_bps kiểm chứng", "Q5", "Q1"], unit: "tỷ lệ 0–1; bps", tab: "kiem-chung",
    body: "Tỷ lệ cùng chiều so dấu tín hiệu với dấu lợi suất sau đó. Q5−Q1 so lợi suất nhóm 20% tín hiệu cao nhất và thấp nhất.", reading: "Hai số này bổ sung cho IC; chưa mô phỏng một chiến lược thực thi được.",
    example: "Q5−Q1 = 2 bps có thể bị chi phí giao dịch lớn hơn xóa hết.", role: "Đối chiếu nhiều mặt của kết quả kiểm chứng, tránh chỉ chọn một con số đẹp.",
    formula: "Hit rate: trung bình dấu tín hiệu = dấu lợi suất, bỏ cặp bằng 0. Q5−Q1: lợi suất bình quân nhóm cao trừ nhóm thấp theo từng thanh, rồi lấy trung bình.",
    limit: "Chưa trừ spread, phí hay tác động thị trường. Tỷ lệ đúng chiều không phải xác suất thắng của một giao dịch tương lai.",
  },
  sensitivity: {
    title: "Độ nhạy với trọng số", aliases: ["Sensitivity", "label stability", "p05", "p95"], unit: "khoảng điểm; % lần giữ nhãn", tab: "tong-quan",
    body: "Thử thay mỗi trọng số điểm nhịp trong khoảng ±50% để xem kết luận có phụ thuộc nhiều vào cách gán trọng số hay không.", reading: "Giữ nguyên nhãn nhiều lần là ổn định trước phép thử trọng số này; không phải dự báo chính xác nhiều lần.",
    example: "Giữ nhãn 80% nghĩa là 80% bộ trọng số thử cho cùng nhãn, không có nghĩa đúng 80% diễn biến sau đó.", role: "Minh bạch lựa chọn thiết kế trọng số của đồ án.",
    formula: "Xáo trộn trọng số, chuẩn hóa lại rồi báo phân vị 5–95% của điểm và tỷ lệ giữ nhãn gốc.",
    limit: "Chỉ thử độ nhạy trọng số tại ảnh chụp đó; không kiểm chứng chất lượng dữ liệu hoặc hiệu quả dự báo. Không cập nhật cùng nhịp live.",
  },
  sector: {
    title: "Đóng góp ước lượng theo ngành", aliases: ["Sector", "contrib_pts", "vốn hóa"], unit: "điểm chỉ số; %", tab: "tong-quan",
    body: "Gom các mã trong rổ theo ngành để xem nhóm nào đang kéo hoặc đè chỉ số.", reading: "Đóng góp dương là kéo lên; âm là kéo xuống theo phép xấp xỉ vốn hóa của đồ án.",
    example: "Ngành đóng góp ước lượng −2 điểm nghĩa là đang đè chỉ số theo mô hình xấp xỉ, không phải số đóng góp chính thức.", role: "Giải thích chuyển động chỉ số bằng nhóm cổ phiếu cụ thể.",
    formula: "Vốn hóa = CP niêm yết × giá tham chiếu; đóng góp = tỷ trọng vốn hóa rổ × % đổi × chỉ số tham chiếu.",
    limit: "Chưa điều chỉnh free-float và giới hạn tỷ trọng; tổng đóng góp có thể khác biến động chỉ số thật.",
  },
  ma: {
    title: "Đường trung bình MA và EMA", aliases: ["MA", "SMA", "EMA", "moving average"], unit: "cùng đơn vị với giá/chỉ số", tab: "tong-quan",
    body: "Làm mượt chuỗi giá để dễ nhìn hướng đi. MA coi các điểm ngang nhau; EMA coi trọng điểm gần đây hơn.", reading: "Chu kỳ dài thường mượt hơn và phản ứng chậm hơn. Đường nội phiên và đường theo phiên ngày dùng hai chuỗi khác nhau.",
    example: "MA20 ở khung ngày dùng 20 phiên, không phải 20 ngày lịch; ở khung Phiên dùng 20 điểm nội phiên đã ghi.", role: "Bổ sung ngữ cảnh biểu đồ; không tham gia công thức điểm nhịp.", formula: "MAₙ = trung bình n điểm. EMA dùng α = 2/(n+1), khởi tạo bằng MA của n điểm đầu.",
    limit: "Chỉ xuất hiện khi đủ lịch sử. Chuỗi nội phiên dừng tại mốc dữ liệu đã tính, có thể chậm hơn điểm giá live.",
  },
};

export function normalizeLookup(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").replace(/₃/g, "3").toLowerCase();
}

export function searchGlossary(query: string): [string, GlossaryEntry][] {
  const phrase = normalizeLookup(query).trim();
  const words = phrase.split(/\s+/).filter(Boolean);
  const matches = Object.entries(GLOSSARY).filter(([key, g]) => words.every((word) =>
    normalizeLookup([key, g.title, ...g.aliases].join(" ")).includes(word)));
  const exact = ([key, g]: [string, GlossaryEntry]) => [key, g.title, ...g.aliases].some((s) => normalizeLookup(s) === phrase);
  return matches.sort((a, b) => Number(exact(b)) - Number(exact(a)));
}
