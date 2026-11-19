/**
 * Lời giải thích bằng tiếng Việt thường cho người không chuyên. Chỉ là văn bản diễn giải các con số Python đã tính
 * (chọn câu theo dấu/độ lớn), không tính thêm chỉ báo nào.
 */
import { isNum } from "./fmt";
import type { Num } from "./types";

export const GLOSSARY: Record<string, { title: string; body: string }> = {
  pulse: {
    title: "Điểm nhịp thị trường (0–100)",
    body: "Gộp 5 tín hiệu: độ rộng (bao nhiêu mã tăng so với giảm), động lượng chỉ số, sổ lệnh, khối ngoại và thanh khoản. 50 là cân bằng; trên 55 nghiêng tích cực, dưới 45 nghiêng tiêu cực. Điểm mô tả hiện trạng, không dự báo.",
  },
  breadth: { title: "Độ rộng", body: "So số mã tăng với số mã giảm. Chỉ số tăng nhưng phần lớn mã giảm nghĩa là chỉ vài mã lớn kéo." },
  momentum: { title: "Động lượng chỉ số", body: "Chỉ số đang đi mạnh hay yếu so với mức dao động thường ngày của chính nó." },
  book: { title: "Sổ lệnh (OBI)", body: "Bên mua hay bên bán đang đặt chờ dày hơn ở 3 mức giá tốt nhất. Dương: người mua chờ nhiều hơn." },
  foreign: { title: "Khối ngoại", body: "Nhà đầu tư nước ngoài đang mua ròng (dương) hay bán ròng (âm) trong rổ đang theo dõi." },
  liquidity: { title: "Thanh khoản", body: "Tiền vào thị trường hôm nay nhiều hay ít so với các phiên trước ở cùng thời điểm." },
  basis: { title: "Basis phái sinh", body: "Chênh lệch giữa giá hợp đồng tương lai VN30 và chỉ số VN30. Dương: thị trường phái sinh kỳ vọng cao hơn hiện tại." },
  rvol: { title: "RVOL", body: "Khối lượng giao dịch so với mức bình thường của chính mã đó ở cùng giờ trong 20 phiên trước. 3 lần trở lên là bất thường." },
  sector: { title: "Đóng góp theo ngành", body: "Ngành đó kéo chỉ số lên hay đè xuống bao nhiêu điểm, ước lượng theo vốn hóa (chưa điều chỉnh free-float nên chỉ gần đúng)." },
};

/** Thành phần đang nói gì: dựa vào dấu và độ lớn của giá trị (−1..1) do Python tính. */
export function componentMeaning(key: string, v: Num): string {
  if (!isNum(v)) return "Chưa đủ dữ liệu để đánh giá.";
  const strength = Math.abs(v) >= 0.5 ? "rõ" : Math.abs(v) >= 0.2 ? "vừa" : "nhẹ";
  const pos = v > 0.05, neg = v < -0.05;
  const t: Record<string, [string, string, string]> = {
    breadth: ["Số mã tăng áp đảo số mã giảm", "Số mã giảm áp đảo số mã tăng", "Số mã tăng và giảm gần cân bằng"],
    momentum: ["Chỉ số đang đi lên so với nhịp thường ngày", "Chỉ số đang đi xuống so với nhịp thường ngày", "Chỉ số gần như đứng yên"],
    book: ["Người mua đặt chờ dày hơn người bán", "Người bán đặt chờ dày hơn người mua", "Lệnh chờ mua và bán gần cân bằng"],
    foreign: ["Khối ngoại đang mua ròng", "Khối ngoại đang bán ròng", "Khối ngoại gần như đứng ngoài"],
    liquidity: ["Tiền vào nhiều hơn các phiên trước cùng giờ", "Tiền vào ít hơn các phiên trước cùng giờ", "Thanh khoản như thường lệ"],
  };
  const [up, down, flat] = t[key] ?? ["Nghiêng tích cực", "Nghiêng tiêu cực", "Trung tính"];
  return pos ? `${up} (mức ${strength}).` : neg ? `${down} (mức ${strength}).` : `${flat}.`;
}

/** Ý nghĩa của điểm nhịp theo dải nhãn (35/45/55/65 do Python quy định). */
export function scoreMeaning(score: Num): string {
  if (!isNum(score)) return "Chưa đủ dữ liệu để kết luận.";
  if (score >= 65) return "Đa số cổ phiếu cùng tăng, tiền và lệnh mua ủng hộ: sức khỏe thị trường tốt và lan tỏa.";
  if (score >= 55) return "Thị trường nghiêng về phía tích cực nhưng chưa lan tỏa mạnh.";
  if (score >= 45) return "Hai phe giằng co, chưa nghiêng hẳn về phía nào.";
  if (score >= 35) return "Thị trường nghiêng về phía tiêu cực, bên bán chiếm ưu thế nhẹ.";
  return "Đa số cổ phiếu cùng giảm, áp lực bán lan rộng.";
}

/** Cảnh báo bằng lời thường (số thống kê để trong phần chi tiết). */
export const RULE_PLAIN: Record<string, string> = {
  volume_spike: "Khối lượng khớp tăng vọt so với bình thường",
  spread_blowout: "Chênh lệch giá mua – bán bỗng giãn rộng (khó mua bán sát giá)",
  price_jump: "Giá đổi đột ngột trong một phút",
  foreign_flow: "Khối ngoại mua hoặc bán dồn dập bất thường",
  book_pressure: "Sổ lệnh lệch hẳn về một phía nhiều phút liền",
  near_limit: "Giá đang sát trần hoặc sát sàn",
};
