/**
 * Lời giải thích bằng tiếng Việt thường cho người không chuyên. Chỉ là văn bản diễn giải các con số Python đã tính
 * (chọn câu theo dấu/độ lớn), không tính thêm chỉ báo nào.
 */
import { isNum } from "./fmt";
import type { AlertItem, Num } from "./types";

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
    foreign: ["Khối ngoại đang mua ròng", "Khối ngoại đang bán ròng", "Khối ngoại mua và bán gần cân bằng"],
    liquidity: ["Tiền vào nhiều hơn các phiên trước cùng giờ", "Tiền vào ít hơn các phiên trước cùng giờ", "Thanh khoản như thường lệ"],
  };
  const [up, down, flat] = t[key] ?? ["Nghiêng tích cực", "Nghiêng tiêu cực", "Trung tính"];
  return pos ? `${up} (mức ${strength}).` : neg ? `${down} (mức ${strength}).` : `${flat}.`;
}

/**
 * Ý nghĩa của điểm nhịp theo dải nhãn (35/45/55/65 do Python quy định). Chỉ nói mức nghiêng của điểm tổng hợp:
 * điểm cao không bảo đảm từng thành phần đều tích cực (CX-013), nên không khẳng định độ rộng/dòng tiền ở đây.
 */
export function scoreMeaning(score: Num): string {
  if (!isNum(score)) return "Chưa đủ dữ liệu để kết luận.";
  if (score >= 65) return "Các tín hiệu cộng lại nghiêng rõ về phía tích cực.";
  if (score >= 55) return "Các tín hiệu cộng lại nghiêng nhẹ về phía tích cực.";
  if (score >= 45) return "Các tín hiệu gần cân bằng, chưa nghiêng hẳn về phía nào.";
  if (score >= 35) return "Các tín hiệu cộng lại nghiêng nhẹ về phía tiêu cực.";
  return "Các tín hiệu cộng lại nghiêng rõ về phía tiêu cực.";
}

const alertTime = (t: string) => Date.parse(t);
const alertKey = (a: AlertItem) => `${Number.isFinite(alertTime(a.t)) ? alertTime(a.t) : a.t}|${a.symbol}|${a.rule}`;

/**
 * Gộp cảnh báo live với snapshot, bỏ trùng theo (giờ, mã, quy tắc) (CX-014). Số cảnh báo CAO trong phiên lấy tổng
 * Python đã đếm (by_severity, không bị cắt MAX_ALERTS) cộng các cảnh báo live mới hơn snapshot; "hot" xếp theo tần suất.
 */
export function alertDigest(live: AlertItem[], snap: AlertItem[], snapHigh: number | undefined, snapshotAt?: string | null) {
  const seen = new Set<string>();
  const unique = (rows: AlertItem[]) => rows.filter((a) => {
    const key = alertKey(a);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const base = unique(snap);
  const last = snapshotAt && Number.isFinite(alertTime(snapshotAt)) ? alertTime(snapshotAt)
    : Math.max(-Infinity, ...base.map((a) => alertTime(a.t)).filter(Number.isFinite));
  const fresh = unique(live);
  const items = [...fresh, ...base].sort((a, b) => alertTime(b.t) - alertTime(a.t));
  const nHigh = (snapHigh ?? snap.filter((a) => a.severity === "CAO").length)
    + fresh.filter((a) => a.severity === "CAO" && alertTime(a.t) > last).length;
  const count = new Map<string, number>();
  for (const a of items) if (a.severity === "CAO") count.set(a.symbol, (count.get(a.symbol) ?? 0) + 1);
  const hot = [...count.entries()].sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0])).slice(0, 3).map(([s]) => s);
  return { items, nHigh, hot };
}

/** Thành phần không có dữ liệu (Python chuẩn hóa lại trọng số trên phần còn lại). */
export function missingComponents(comps: { name: string; value: Num }[]): string[] {
  return comps.filter((c) => !isNum(c.value)).map((c) => c.name);
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
