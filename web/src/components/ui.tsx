import type { ReactNode } from "react";
import type { Num } from "@/lib/types";

export const TOOLTIP_STYLE = {
  contentStyle: { background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12, color: "var(--fg)" },
  labelStyle: { color: "var(--muted)" },
} as const;

export function Card({ title, children, className = "", action }: { title?: ReactNode; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-3 sm:p-4 ${className}`}>
      {title || action ? (
        <div className="mb-2 flex items-center justify-between gap-2">
          {title ? <h2 className="text-sm font-semibold">{title}</h2> : <span />}
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

export function Stat({ label, value, sub, tone = "text-fg" }: { label: string; value: ReactNode; sub?: ReactNode; tone?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`tnum mt-0.5 text-xl font-semibold leading-tight ${tone}`}>{value}</div>
      {sub ? <div className="tnum mt-0.5 text-xs text-muted">{sub}</div> : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">{children}</div>;
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-xs leading-relaxed text-muted">{children}</p>;
}

export function Pill({ children, tone = "bg-surface2 text-fg" }: { children: ReactNode; tone?: string }) {
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{children}</span>;
}

export const SEV_TONE: Record<string, string> = {
  CAO: "bg-down/15 text-down",
  "TRUNG BÌNH": "bg-warn/20 text-warn",
  THẤP: "bg-surface2 text-muted",
};

/** Đồng hồ nửa vòng 0–100, các dải màu theo nhãn của Python (35/45/55/65). */
export function Gauge({ score, label }: { score: Num; label: string }) {
  const cx = 110, cy = 92, r = 84;
  const pt = (v: number, rad = r) => {
    const a = Math.PI * (1 - v / 100);
    return [cx + rad * Math.cos(a), cy - rad * Math.sin(a)] as const;
  };
  const arc = (a: number, b: number) => {
    const [x1, y1] = pt(a), [x2, y2] = pt(b);
    return `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const bands: [number, number, string][] = [[0, 35, "var(--down)"], [35, 45, "var(--warn)"], [45, 55, "var(--muted)"], [55, 65, "var(--up)"], [65, 100, "var(--up)"]];
  const [nx, ny] = score === null ? [cx, cy] : pt(score, r - 18);
  return (
    <figure className="m-0">
      <svg viewBox="0 0 220 138" role="img" aria-label={score === null ? "Điểm nhịp: chưa đủ dữ liệu" : `Điểm nhịp ${score} trên 100, ${label}`} className="mx-auto w-full max-w-[280px]">
        {bands.map(([a, b, c], i) => (
          <path key={i} d={arc(a, b)} stroke={c} strokeOpacity={i === 3 ? 0.55 : i === 4 ? 1 : i === 2 ? 0.45 : i === 1 ? 0.7 : 1} strokeWidth="14" fill="none" />
        ))}
        {score !== null ? <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="var(--fg)" strokeWidth="3" strokeLinecap="round" /> : null}
        <circle cx={cx} cy={cy} r="5" fill="var(--fg)" />
        <text x={cx} y={cy + 36} textAnchor="middle" className="tnum" style={{ fontSize: 30, fontWeight: 700, fill: "var(--fg)" }}>
          {score === null ? "—" : score.toFixed(1)}
        </text>
        <text x="20" y="112" style={{ fontSize: 10, fill: "var(--muted)" }}>0</text>
        <text x="190" y="112" style={{ fontSize: 10, fill: "var(--muted)" }}>100</text>
      </svg>
      <figcaption className="text-center text-sm font-medium">{label}</figcaption>
    </figure>
  );
}

/** Thanh ngang hai phía cho giá trị trong [-1, 1]. */
export function CenterBar({ value }: { value: Num }) {
  if (value === null) return <div className="h-2 rounded bg-surface2" />;
  const w = Math.min(1, Math.abs(value)) * 50;
  return (
    <div className="relative h-2 rounded bg-surface2" role="img" aria-label={`giá trị ${value.toFixed(2)}`}>
      <div className="absolute left-1/2 top-[-2px] h-3 w-px bg-line" />
      <div
        className="absolute top-0 h-2 rounded"
        style={{ background: value >= 0 ? "var(--up)" : "var(--down)", width: `${w}%`, left: value >= 0 ? "50%" : `${50 - w}%` }}
      />
    </div>
  );
}

export function Th({ children, right = true }: { children: ReactNode; right?: boolean }) {
  return <th className={`whitespace-nowrap px-2 py-1.5 text-xs font-medium text-muted ${right ? "text-right" : "text-left"}`}>{children}</th>;
}
export function Td({ children, right = true, className = "" }: { children: ReactNode; right?: boolean; className?: string }) {
  return <td className={`tnum whitespace-nowrap px-2 py-1.5 text-sm ${right ? "text-right" : "text-left"} ${className}`}>{children}</td>;
}
