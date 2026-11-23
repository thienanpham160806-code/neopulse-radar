"use client";

/** Đồng hồ điểm nhịp (thu gọn hợp cột trái Bento), nút giải thích ⓘ, hướng dẫn đọc trang dạng nút mở (không gây CLS). */
import { useState } from "react";
import { isNum } from "@/lib/fmt";
import { num } from "@/lib/format";
export { Term } from "./Glossary";
import type { Num } from "@/lib/types";

/**
 * Đồng hồ nửa vòng 0–100. Năm dải theo đúng ranh giới nhãn của Python (35/45/55/65): đỏ = tiêu cực (giảm),
 * vàng = giằng co (tham chiếu), xanh = tích cực (tăng) — cùng nghĩa với quy ước bảng giá. Kim + số + nhãn chữ.
 */
export function Gauge({ score, label, compact = false }: { score: Num; label: string; compact?: boolean }) {
  const cx = 140, cy = 122, r = 96;
  const pt = (v: number, rad = r) => {
    const a = Math.PI * (1 - v / 100);
    return [cx + rad * Math.cos(a), cy - rad * Math.sin(a)] as const;
  };
  const arc = (a: number, b: number) => {
    const [x1, y1] = pt(a), [x2, y2] = pt(b);
    return `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const bands: [number, number, string, number][] = [
    [0, 35, "var(--down)", 1],
    [35, 45, "var(--down)", 0.45],
    [45, 55, "var(--refc)", 0.72],
    [55, 65, "var(--up)", 0.45],
    [65, 100, "var(--up)", 1],
  ];
  const s = isNum(score) ? Math.max(0, Math.min(100, score)) : null;
  const [nx, ny] = s === null ? [cx, cy] : pt(s, r - 24);

  return (
    <figure className="m-0">
      <svg
        viewBox="0 0 280 172"
        className={`mx-auto w-full ${compact ? "max-w-[215px]" : "max-w-[280px]"}`}
        role="img"
        aria-label={s === null ? "Điểm nhịp: chưa đủ dữ liệu" : `Điểm nhịp ${num(s, 1)} trên 100, ${label}`}
      >
        {bands.map(([a, b, c, o], i) => (
          <path key={i} d={arc(a + 0.7, b - 0.7)} stroke={c} strokeOpacity={o} strokeWidth="18" fill="none" />
        ))}
        {[0, 35, 45, 55, 65, 100].map((t) => {
          const [x, y] = pt(t, r + 16);
          return (
            <text key={t} x={x} y={y + 3} textAnchor="middle" style={{ fontSize: 10, fill: "var(--muted)" }}>
              {t}
            </text>
          );
        })}
        {s !== null ? (
          <g style={{ transformOrigin: `${cx}px ${cy}px`, ["--sweep" as string]: `${-(s / 100) * 180}deg` }} className="gauge-needle">
            <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="var(--fg)" strokeWidth="3.5" strokeLinecap="round" />
          </g>
        ) : null}
        <circle cx={cx} cy={cy} r="6.5" fill="var(--fg)" />
        <text x={cx} y={cy + 36} textAnchor="middle" className="tnum" style={{ fontSize: 32, fontWeight: 700, fill: "var(--fg)" }}>
          {s === null ? "—" : num(s, 1)}
        </text>
        <text x={cx + 39} y={cy + 36} textAnchor="start" className="tnum" style={{ fontSize: 11, fill: "var(--muted)" }}>
          /100
        </text>
      </svg>
      <figcaption className="-mt-1 text-center text-sm font-semibold leading-snug">{label}</figcaption>
    </figure>
  );
}

/** Hướng dẫn đọc trang theo yêu cầu (không tự bung sau hydration → loại bỏ CLS). */
export function GuideButton() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="quick-guide-panel"
        className="ui-transition inline-flex min-h-9 items-center gap-1 rounded-lg border border-line bg-surface px-2.5 text-xs font-medium text-muted hover:bg-surface2 hover:text-fg"
      >
        <span aria-hidden>?</span>
        <span className="sr-only sm:not-sr-only">Cách đọc</span>
      </button>
      {open ? (
        <div
          id="quick-guide-panel"
          role="region"
          aria-label="Hướng dẫn đọc trang"
          className="panel-enter absolute right-0 top-11 z-40 w-[min(92vw,30rem)] rounded-2xl border border-line bg-surface p-4 shadow-lg"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-bold">Đọc NeoPulse trong 5 giây</h2>
            <button type="button" onClick={() => setOpen(false)} className="rounded-md px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">
              Đóng ×
            </button>
          </div>
          <ol className="mt-2.5 space-y-2 text-xs leading-relaxed text-muted">
            <li><b className="text-fg">1. Khỏe hay yếu?</b> Kiểm tra nguồn, giờ cập nhật ở thanh trên; xem chỉ số, độ rộng tăng/giảm và điểm nhịp.</li>
            <li><b className="text-fg">2. Vì sao?</b> Đọc 5 thành phần chuẩn hóa (−1…+1) rồi mở tab <i>Vì sao?</i> để soi ngành, sổ lệnh, khối ngoại, phái sinh.</li>
            <li><b className="text-fg">3. Có gì bất thường?</b> Bấm vào cảnh báo hoặc bất kỳ mã nào để mở <i>Chi tiết mã</i> và hồ sơ doanh nghiệp. Bấm <b>ⓘ</b> để tra cứu chỉ số ngay tại chỗ.</li>
          </ol>
          <p className="mt-2.5 border-t border-line pt-2 text-[11px] text-muted">
            Công cụ phân tích học thuật, không phải lời khuyên đầu tư.
          </p>
        </div>
      ) : null}
    </div>
  );
}
