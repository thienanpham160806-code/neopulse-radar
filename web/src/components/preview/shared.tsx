"use client";

import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { num, pct, signed } from "@/lib/format";
import type { Num } from "@/lib/types";
import type { PreviewState } from "./usePreview";

/** Thanh của BẢN XEM TRƯỚC (không thuộc thiết kế): đổi hướng và trạng thái minh họa. */
export function PreviewBar({ variant, state, tab }: { variant: "a" | "b" | "c"; state: PreviewState; tab: string | null }) {
  const names = { a: "A · Terminal", b: "B · Bản tin", c: "C · Ứng dụng" };
  const q = (s: PreviewState) => `?state=${s}${tab ? `&tab=${tab}` : ""}`;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 bg-[#111827] px-3 py-1.5 text-xs text-[#e5e7eb]">
      <b>Bản xem trước</b>
      {(["a", "b", "c"] as const).map((v) => (
        <Link key={v} href={`/preview/${v}${q(state)}`} aria-current={v === variant ? "page" : undefined}
          className={`rounded px-1.5 py-0.5 ${v === variant ? "bg-white text-[#111827]" : "underline-offset-2 hover:underline"}`}>
          {names[v]}
        </Link>
      ))}
      <span className="text-[#9ca3af]">Trạng thái:</span>
      {([["live", "Trực tiếp"], ["snapshot", "Snapshot"], ["error", "Lỗi"]] as const).map(([s, label]) => (
        <Link key={s} href={`/preview/${variant}${q(s)}`} aria-current={s === state ? "true" : undefined}
          className={`rounded px-1.5 py-0.5 ${s === state ? "bg-white text-[#111827]" : "underline-offset-2 hover:underline"}`}>
          {label}
        </Link>
      ))}
    </div>
  );
}

/** Thay đổi giá có ký hiệu (không phụ thuộc màu) và màu theo quy ước bảng giá. */
export function Change({ value, unit = "%", d = 2, className = "" }: { value: Num; unit?: string; d?: number; className?: string }) {
  const tone = priceTone(value);
  return (
    <span className={`tnum ${TONE_CLASS[tone]} ${className}`}>
      <span aria-hidden>{TONE_MARK[tone]} </span>
      {unit === "%" ? pct(value, d) : `${signed(value, d)}${unit}`}
    </span>
  );
}

export const SEV_LABEL: Record<string, string> = { CAO: "Cao", "TRUNG BÌNH": "Trung bình", THẤP: "Thấp" };

/** Mức cảnh báo: chữ + hình (không dùng đỏ/xanh vì đỏ/xanh dành cho giảm/tăng giá). */
export function SevTag({ sev, className = "" }: { sev: string; className?: string }) {
  const shape = sev === "CAO" ? "◆" : sev === "TRUNG BÌNH" ? "◇" : "·";
  // vàng = tham chiếu, đỏ/xanh = giá: mức cảnh báo dùng độ đậm của mực (đặc / viền / nhạt) + hình
  const tone = sev === "CAO" ? "bg-fg text-bg" : sev === "TRUNG BÌNH" ? "border border-fg text-fg" : "border border-line text-muted";
  return <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-semibold ${tone} ${className}`}><span aria-hidden>{shape}</span>{SEV_LABEL[sev] ?? sev}</span>;
}

export function IndexLine({ data, height = 180, color = "var(--accent)" }: { data: { t: string; v: number }[]; height?: number; color?: string }) {
  if (data.length < 2) return <p className="text-sm text-muted">Chưa đủ điểm dữ liệu để vẽ.</p>;
  return (
    <div style={{ height }} role="img" aria-label="Diễn biến chỉ số trong phiên">
      <ResponsiveContainer>
        <LineChart data={data.map((d) => ({ t: d.t.slice(11, 16), v: d.v }))} margin={{ top: 6, right: 4, left: 0, bottom: 0 }}>
          <XAxis dataKey="t" minTickGap={48} tickLine={false} axisLine={false} />
          <YAxis domain={["auto", "auto"]} width={46} tickLine={false} axisLine={false} tickFormatter={(v: number) => num(v, 0)} />
          <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12, color: "var(--fg)" }}
            formatter={(v: number) => [num(v), "Chỉ số"]} />
          <Line dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export const scoreTone = (s: Num) => (!isNum(s) ? "text-muted" : s >= 55 ? "text-up" : s < 45 ? "text-down" : "text-refc");

export function Disclaimer({ className = "" }: { className?: string }) {
  return <p className={`text-xs ${className}`}>Công cụ phân tích học thuật. <b>Không phải lời khuyên đầu tư.</b></p>;
}
