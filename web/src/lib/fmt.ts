/**
 * Định dạng kiểu Việt Nam + màu theo quy ước bảng giá.
 * Tái sử dụng có chọn lọc từ invest-system-phase2/lib/fmt.ts (cùng tác giả): giữ bnLabel, dmy (kèm giờ), cls;
 * BỎ RATING_COLOR (MUA/BÁN/KHẢ QUAN...) vì sản phẩm này không đưa khuyến nghị. Bổ sung màu trần (tím) và sàn (xanh lơ).
 * Khác bản gốc: phần trăm ở đây đã là đơn vị % (Python xuất 1,23 nghĩa là 1,23%), không phải tỷ lệ 0,0123.
 */
import type { Num } from "./types";

const nf = (d: number) => new Intl.NumberFormat("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
export const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** VND -> "1,2 nghìn tỷ đồng" / "345 tỷ đồng" (bản gốc bnLabel). */
export function bnLabel(v: Num | undefined): string {
  if (!isNum(v)) return "—";
  if (Math.abs(v) >= 1e15) return `${nf(1).format(v / 1e15)} triệu tỷ đồng`;
  if (Math.abs(v) >= 1e12) return `${nf(1).format(v / 1e12)} nghìn tỷ đồng`;
  return `${nf(0).format(v / 1e9)} tỷ đồng`;
}

/** "2026-11-19T10:05:00+07:00" -> "10:05, 19/11/2026"; "2026-11-19" -> "19/11/2026" (bản gốc dmy). */
export function dmyTime(s: string | null | undefined): string {
  if (!s) return "—";
  const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
  if (!m) return String(s);
  return (m[4] ? `${m[4]}:${m[5]}, ` : "") + `${m[3]}/${m[2]}/${m[1]}`;
}

export type PriceTone = "up" | "down" | "ref" | "ceil" | "floor";

/**
 * Màu theo quy ước bảng giá Việt Nam: xanh lá tăng, đỏ giảm, vàng đứng giá/tham chiếu, tím trần, xanh lơ sàn.
 * Có giá trần/sàn thì ưu tiên trần/sàn; không có thì xét dấu thay đổi.
 */
export function priceTone(change: Num | undefined, last?: Num, ceiling?: Num, floor?: Num): PriceTone {
  if (isNum(last) && isNum(ceiling) && last >= ceiling) return "ceil";
  if (isNum(last) && isNum(floor) && last <= floor) return "floor";
  if (!isNum(change) || change === 0) return "ref";
  return change > 0 ? "up" : "down";
}

/** Lớp Tailwind tương ứng (bản gốc cls, thêm trần/sàn). */
export const TONE_CLASS: Record<PriceTone, string> = {
  up: "text-up", down: "text-down", ref: "text-refc", ceil: "text-ceil", floor: "text-floor",
};

/** Ký hiệu không phụ thuộc màu cho người mù màu. */
export const TONE_MARK: Record<PriceTone, string> = { up: "▲", down: "▼", ref: "■", ceil: "▲▲", floor: "▼▼" };

export function cls(change: Num | undefined): string {
  return TONE_CLASS[priceTone(change)];
}
