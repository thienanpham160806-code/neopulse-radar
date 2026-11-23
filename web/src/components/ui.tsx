import type { ReactNode } from "react";
import type { Num } from "@/lib/types";
import { bnLabel, isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { pct, signed } from "@/lib/format";

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: "var(--surface)",
    border: "1px solid var(--line)",
    borderRadius: 10,
    fontSize: 12,
    color: "var(--fg)",
    boxShadow: "var(--shadow-float)",
  },
  labelStyle: { color: "var(--muted)", fontWeight: 600, marginBottom: 2 },
  itemStyle: { color: "var(--fg)" },
} as const;

export function Card({ title, children, className = "", action }: { title?: ReactNode; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <section className={`card-elev min-w-0 rounded-2xl border border-line bg-surface p-3.5 sm:p-4 ${className}`}>
      {title || action ? (
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
          {title ? <h2 className="text-sm font-semibold tracking-tight">{title}</h2> : <span />}
          {action}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function signTone(x: Num | undefined): string {
  if (x === null || x === undefined || x === 0) return "text-fg";
  return x > 0 ? "text-up" : "text-down";
}

export function Stat({ label, value, sub, tone = "text-fg" }: { label: ReactNode; value: ReactNode; sub?: ReactNode; tone?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`tnum mt-0.5 text-xl font-semibold leading-tight ${tone}`}>{value}</div>
      {sub ? <div className="tnum mt-0.5 text-xs text-muted">{sub}</div> : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div role="status" className="rounded-2xl border border-dashed border-line bg-surface p-6 text-center text-sm leading-relaxed text-muted">
      {children}
    </div>
  );
}

export function SkeletonBlock({ className = "h-32" }: { className?: string }) {
  return <div aria-hidden className={`skeleton rounded-2xl ${className}`} />;
}

export function TabSkeleton() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">Đang tải nội dung…</span>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <SkeletonBlock className="h-24" />
        <SkeletonBlock className="h-24" />
        <SkeletonBlock className="h-24" />
      </div>
      <SkeletonBlock className="h-72" />
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-xs leading-relaxed text-muted">{children}</p>;
}

export function Pill({ children, tone = "bg-surface2 text-fg" }: { children: ReactNode; tone?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}>{children}</span>;
}

export const SEV_TONE: Record<string, string> = {
  CAO: "bg-fg text-bg",
  "TRUNG BÌNH": "border border-fg text-fg",
  THẤP: "bg-surface2 text-muted",
};

/** Thanh ngang hai phía cho giá trị trong [-1, 1]. */
export function CenterBar({ value }: { value: Num }) {
  if (value === null) return <div className="h-2 rounded-full bg-surface2" />;
  const w = Math.min(1, Math.abs(value)) * 50;
  return (
    <div className="relative h-2 rounded-full bg-surface2" role="img" aria-label={`thành phần chuẩn hóa ${value.toFixed(2)}`}>
      <div className="absolute left-1/2 top-[-2px] h-3 w-px bg-line" />
      <div
        className="ui-transition absolute top-0 h-2 rounded-full"
        style={{
          background: value > 0 ? "var(--up)" : value < 0 ? "var(--down)" : "var(--refc)",
          width: `${Math.max(w, value === 0 ? 2 : 0)}%`,
          left: value >= 0 ? "50%" : `${50 - w}%`,
        }}
      />
    </div>
  );
}

export function Th({ children, right = true }: { children: ReactNode; right?: boolean }) {
  return <th className={`whitespace-nowrap px-2.5 py-2 text-xs font-medium text-muted ${right ? "text-right" : "text-left"}`}>{children}</th>;
}
export function Td({ children, right = true, className = "" }: { children: ReactNode; right?: boolean; className?: string }) {
  return <td className={`tnum whitespace-nowrap px-2.5 py-2 text-sm ${right ? "text-right" : "text-left"} ${className}`}>{children}</td>;
}

/** Thang điểm nhịp 0–100 màu TRUNG TÍNH (không mượn màu giá); vạch 35/45/55/65 là ranh giới nhãn. */
export function ScoreScale({ score }: { score: Num }) {
  const x = isNum(score) ? Math.max(0, Math.min(100, score)) : null;
  return (
    <div role="img" aria-label={x === null ? "Chưa đủ dữ liệu cho điểm nhịp" : `Điểm nhịp ${x} trên thang 0 đến 100`}>
      <div className="relative h-2 rounded-full bg-surface2">
        {[35, 45, 55, 65].map((c) => <span key={c} className="absolute top-0 h-2 w-px bg-line" style={{ left: `${c}%` }} />)}
        {x !== null ? <span className="absolute -top-1 h-4 w-1.5 -translate-x-1/2 rounded bg-fg" style={{ left: `${x}%` }} /> : null}
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted"><span>0 · tiêu cực</span><span>50</span><span>tích cực · 100</span></div>
    </div>
  );
}

/** Thay đổi có ký hiệu ▲▼■ (không phụ thuộc màu) + màu theo quy ước bảng giá. */
export function Change({ value, unit = "%", d = 2, className = "" }: { value: Num; unit?: string; d?: number; className?: string }) {
  const tone = priceTone(value);
  return (
    <span className={`tnum ${TONE_CLASS[tone]} ${className}`}>
      <span aria-hidden>{TONE_MARK[tone]} </span>{unit === "%" ? pct(value, d) : `${signed(value, d)}${unit}`}
    </span>
  );
}

/** Tiền ròng (VD khối ngoại) có ▲▼ và màu: dương = mua ròng, âm = bán ròng. */
export function SignedMoney({ value, className = "" }: { value: Num; className?: string }) {
  const tone = priceTone(value);
  return (
    <span className={`tnum ${TONE_CLASS[tone]} ${className}`}>
      <span aria-hidden>{TONE_MARK[tone]} </span>{isNum(value) ? `${value > 0 ? "+" : value < 0 ? "−" : ""}${bnLabel(Math.abs(value))}` : "—"}
    </span>
  );
}

/** Mức cảnh báo: độ đậm của mực + hình (◆ cao, ◇ trung bình, · thấp); không dùng đỏ/xanh/vàng (dành cho giá). */
export function SevTag({ sev, className = "" }: { sev: string; className?: string }) {
  const label: Record<string, string> = { CAO: "Cao", "TRUNG BÌNH": "Trung bình", THẤP: "Thấp" };
  const shape = sev === "CAO" ? "◆" : sev === "TRUNG BÌNH" ? "◇" : "·";
  const tone = sev === "CAO" ? "bg-fg text-bg" : sev === "TRUNG BÌNH" ? "border border-fg text-fg" : "border border-line text-muted";
  return <span className={`inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold ${tone} ${className}`}><span aria-hidden>{shape}</span>{label[sev] ?? sev}</span>;
}
