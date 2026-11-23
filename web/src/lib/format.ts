import type { Num } from "./types";

const nf = (d: number) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: d, minimumFractionDigits: d });

export const dash = "—";
export function num(x: Num | undefined, d = 2): string {
  return x === null || x === undefined ? dash : nf(d).format(x);
}
export function signed(x: Num | undefined, d = 2): string {
  return x === null || x === undefined ? dash : `${x > 0 ? "+" : ""}${nf(d).format(x)}`;
}
export function pct(x: Num | undefined, d = 2): string {
  return x === null || x === undefined ? dash : `${signed(x, d)}%`;
}
export function ratioPct(x: Num | undefined, d = 0): string {
  return x === null || x === undefined ? dash : `${nf(d).format(x * 100)}%`;
}
/** Giá trị đồng theo thói quen Việt Nam: nghìn tỷ / tỷ / triệu. */
export function money(x: Num | undefined): string {
  if (x === null || x === undefined) return dash;
  const a = Math.abs(x);
  if (a >= 1e12) return `${nf(1).format(x / 1e12)} nghìn tỷ đồng`;
  if (a >= 1e9) return `${nf(1).format(x / 1e9)} tỷ đồng`;
  if (a >= 1e6) return `${nf(1).format(x / 1e6)} triệu đồng`;
  return `${nf(0).format(x)} đồng`;
}
export function dmy(isoDate: string | null): string {
  if (!isoDate) return dash;
  const [y, m, d] = isoDate.split("-");
  return d && m && y ? `${d}/${m}/${y}` : isoDate;
}
/** "2026-11-19T10:05:30.000+07:00" -> "10:05:30" */
export function clock(iso: string | null): string {
  if (!iso) return dash;
  const m = /T(\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? m[1] : dash;
}
/** "2026-11-19T10:05:00+07:00" -> "10:05" */
export function hm(iso: string): string {
  return iso.slice(11, 16);
}
