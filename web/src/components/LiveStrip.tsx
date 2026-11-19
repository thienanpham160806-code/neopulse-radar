"use client";

import type { TickData } from "@/lib/live";
import { num, pct, signed } from "@/lib/format";

const ORDER = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"] as const;

/** Dải chỉ số trực tiếp: giá trị, thay đổi có ▲▼ (không chỉ dựa vào màu), tăng/giảm; nháy nền khi số đổi. */
export function LiveStrip({ tick }: { tick: TickData }) {
  return (
    <section aria-label="Chỉ số trực tiếp" className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {ORDER.filter((c) => tick.ix[c]).map((code) => {
        const x = tick.ix[code];
        const dir = (x.ch ?? 0) > 0 ? "up" : (x.ch ?? 0) < 0 ? "down" : "flat";
        const tone = dir === "up" ? "text-up" : dir === "down" ? "text-down" : "text-warn";
        const arrow = dir === "up" ? "▲" : dir === "down" ? "▼" : "■";
        return (
          <div key={code} className="rounded-xl border border-line bg-surface p-3">
            <div className="text-xs text-muted">{code}</div>
            {/* key theo giá trị để chạy lại hiệu ứng nháy mỗi khi số đổi */}
            <div key={`${x.v}`} className={`tnum mt-0.5 rounded text-xl font-semibold leading-tight ${tone} flash-${dir}`}>
              {num(x.v)}
            </div>
            <div className={`tnum text-xs ${tone}`}>
              <span aria-hidden>{arrow} </span>
              {signed(x.ch)} điểm ({pct(x.pct)})
            </div>
            <div className="tnum mt-0.5 text-xs text-muted">
              <span className="text-up">▲{num(x.adv, 0)}</span> · <span className="text-warn">■{num(x.nc, 0)}</span> ·{" "}
              <span className="text-down">▼{num(x.dec, 0)}</span>
            </div>
          </div>
        );
      })}
    </section>
  );
}
