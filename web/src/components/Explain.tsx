"use client";

/** Đồng hồ điểm nhịp (điểm nhấn của trang), nút giải thích thuật ngữ ⓘ, thẻ hướng dẫn đọc trang lần đầu. */
import { useEffect, useState } from "react";
import { isNum } from "@/lib/fmt";
import { num } from "@/lib/format";
export { Term } from "./Glossary";
import type { Num } from "@/lib/types";

/**
 * Đồng hồ nửa vòng 0–100. Năm dải theo đúng ranh giới nhãn của Python (35/45/55/65): đỏ = tiêu cực (giảm),
 * vàng = giằng co (tham chiếu), xanh = tích cực (tăng) - cùng nghĩa với quy ước bảng giá. Kim + số + nhãn chữ.
 */
export function Gauge({ score, label }: { score: Num; label: string }) {
  const cx = 160, cy = 150, r = 120;
  const pt = (v: number, rad = r) => {
    const a = Math.PI * (1 - v / 100);
    return [cx + rad * Math.cos(a), cy - rad * Math.sin(a)] as const;
  };
  const arc = (a: number, b: number) => {
    const [x1, y1] = pt(a), [x2, y2] = pt(b);
    return `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const bands: [number, number, string, number][] = [
    [0, 35, "var(--down)", 1], [35, 45, "var(--down)", 0.45], [45, 55, "var(--refc)", 0.7], [55, 65, "var(--up)", 0.45], [65, 100, "var(--up)", 1],
  ];
  const s = isNum(score) ? Math.max(0, Math.min(100, score)) : null;
  const [nx, ny] = s === null ? [cx, cy] : pt(s, r - 30);
  return (
    <figure className="m-0">
      <svg viewBox="0 0 320 200" className="mx-auto w-full max-w-[360px]" role="img"
        aria-label={s === null ? "Điểm nhịp: chưa đủ dữ liệu" : `Điểm nhịp ${num(s, 1)} trên 100, ${label}`}>
        {bands.map(([a, b, c, o], i) => (
          <path key={i} d={arc(a + 0.6, b - 0.6)} stroke={c} strokeOpacity={o} strokeWidth="22" fill="none" />
        ))}
        {[0, 35, 45, 55, 65, 100].map((t) => {
          const [x, y] = pt(t, r + 20);
          return <text key={t} x={x} y={y + 4} textAnchor="middle" style={{ fontSize: 11, fill: "var(--muted)" }}>{t}</text>;
        })}
        {s !== null ? (
          <g style={{ transformOrigin: `${cx}px ${cy}px`, ["--sweep" as string]: `${-(s / 100) * 180}deg` }} className="gauge-needle">
            <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="var(--fg)" strokeWidth="4" strokeLinecap="round" />
          </g>
        ) : null}
        <circle cx={cx} cy={cy} r="8" fill="var(--fg)" />
        <text x={cx} y={cy + 42} textAnchor="middle" className="tnum" style={{ fontSize: 40, fontWeight: 700, fill: "var(--fg)" }}>
          {s === null ? "—" : num(s, 1)}
        </text>
      </svg>
      <figcaption className="-mt-1 text-center text-base font-semibold">{label}</figcaption>
    </figure>
  );
}

const GUIDE_KEY = "np-guide-dismissed";

/** Thẻ hướng dẫn đọc trang cho lần đầu; đóng thì nhớ trên máy (localStorage, lỗi thì vẫn chạy). */
export function Guide() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      setShow(localStorage.getItem(GUIDE_KEY) !== "1");
    } catch {
      setShow(true);
    }
  }, []);
  if (!show) return null;
  const close = () => {
    setShow(false);
    try {
      localStorage.setItem(GUIDE_KEY, "1");
    } catch {
      /* bỏ qua */
    }
  };
  return (
    <details aria-label="Hướng dẫn đọc trang" className="mb-4 rounded-xl border border-line bg-surface px-4 py-2">
      <summary className="min-h-10 cursor-pointer py-2 text-sm font-semibold">Mới dùng NeoPulse? Xem cách đọc trang</summary>
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-bold">Đọc trang này thế nào?</h2>
        <button onClick={close} className="min-h-10 rounded-md px-2 text-sm text-muted underline underline-offset-4">Đã hiểu, ẩn đi</button>
      </div>
      <ol className="mt-2 grid gap-3 text-sm sm:grid-cols-3">
        <li><b>1. Đang xem dữ liệu nào?</b> Kiểm tra nguồn, thời điểm cập nhật và phạm vi rổ. Đọc phần tóm tắt để biết chỉ số và số đông cổ phiếu đang đi cùng chiều hay không.</li>
        <li><b>2. Vì sao có nhận định đó?</b> Xem năm nhóm bằng chứng, rồi mở bảng chi tiết. Đồng hồ chỉ tổng hợp phần có dữ liệu; điểm cao không đồng nghĩa mọi tín hiệu đều tốt.</li>
        <li><b>3. Điều gì cần kiểm tra thêm?</b> Mở từng cảnh báo và xem phần kiểm chứng. Bấm ⓘ hoặc “Tra cứu chỉ số” để hiểu số liệu và vai trò của nó trong đồ án.</li>
      </ol>
      <p className="mt-2 text-xs text-muted">Biểu tượng <b>i</b> cạnh một thuật ngữ mở lời giải thích. Đây là công cụ học thuật, không phải lời khuyên đầu tư.</p>
    </details>
  );
}
