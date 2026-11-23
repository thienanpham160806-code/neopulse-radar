/**
 * Lời giải thích bằng tiếng Việt thường cho người không chuyên. Chỉ là văn bản diễn giải các con số Python đã tính
 * (chọn câu theo dấu/độ lớn), không tính thêm chỉ báo nào.
 */
import { isNum } from "./fmt";
import { num } from "./format";
import type { AlertItem, Num } from "./types";

export { GLOSSARY } from "./glossary";

/** Thành phần đang nói gì: dựa vào dấu và độ lớn của giá trị (−1..1) do Python tính. */
export function componentMeaning(key: string, v: Num): string {
  if (!isNum(v)) return "Chưa đủ dữ liệu để đánh giá.";
  const pos = v > 0.05, neg = v < -0.05;
  const t: Record<string, [string, string, string]> = {
    breadth: ["Số cổ phiếu tăng đang nhiều hơn số giảm", "Số cổ phiếu giảm đang nhiều hơn số tăng", "Số cổ phiếu tăng và giảm gần bằng nhau"],
    momentum: ["Mức tăng của chỉ số đang góp phần nâng điểm nhịp", "Mức giảm của chỉ số đang kéo điểm nhịp xuống", "Biến động của chỉ số hiện ít tác động đến điểm nhịp"],
    book: ["Nhìn chung, lệnh chờ mua đang trội hơn lệnh chờ bán", "Nhìn chung, lệnh chờ bán đang trội hơn lệnh chờ mua", "Lệnh chờ mua và bán gần cân bằng"],
    foreign: ["Khối ngoại đang mua nhiều hơn bán trong rổ theo dõi", "Khối ngoại đang bán nhiều hơn mua trong rổ theo dõi", "Giá trị mua và bán của khối ngoại gần bằng nhau"],
    liquidity: ["Giá trị giao dịch cao hơn các phiên trước ở cùng thời điểm", "Giá trị giao dịch thấp hơn các phiên trước ở cùng thời điểm", "Giá trị giao dịch gần với mức thường thấy ở cùng thời điểm"],
  };
  const [up, down, flat] = t[key] ?? ["Nghiêng tích cực", "Nghiêng tiêu cực", "Trung tính"];
  return `${pos ? up : neg ? down : flat}.`;
}

/**
 * Ý nghĩa của điểm nhịp theo dải nhãn (35/45/55/65 do Python quy định). Chỉ nói mức nghiêng của điểm tổng hợp:
 * điểm cao không bảo đảm từng thành phần đều tích cực (CX-013), nên không khẳng định độ rộng/dòng tiền ở đây.
 */
export function scoreMeaning(score: Num): string {
  if (!isNum(score)) return "Chưa đủ dữ liệu để kết luận.";
  if (score >= 65) return "Tín hiệu chung đang khá tích cực.";
  if (score >= 55) return "Tín hiệu chung hơi nghiêng về chiều tích cực.";
  if (score >= 45) return "Các tín hiệu đang khá cân bằng.";
  if (score >= 35) return "Tín hiệu chung hơi nghiêng về chiều tiêu cực.";
  return "Tín hiệu chung đang khá yếu.";
}

/** Describe supplied index/breadth facts; a score alone never establishes either. */
export function marketSummary(code: string, change: Num | undefined, advances: Num | undefined, declines: Num | undefined): string {
  const parts = [];
  if (isNum(change)) parts.push(change === 0 ? `${code} đang ở mức tham chiếu.` : `${code} đang ${change > 0 ? "tăng" : "giảm"} ${num(Math.abs(change))}% so với mức tham chiếu.`);
  if (isNum(advances) && isNum(declines)) {
    parts.push(declines > advances
      ? `Trong nhóm cổ phiếu của chỉ số này, có ${num(declines, 0)} mã giảm và ${num(advances, 0)} mã tăng.`
      : `Trong nhóm cổ phiếu của chỉ số này, có ${num(advances, 0)} mã tăng và ${num(declines, 0)} mã giảm.`);
  }
  return parts.join(" ") || "Chưa đủ dữ liệu giá và số mã tăng, giảm để mô tả diễn biến lúc này.";
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
