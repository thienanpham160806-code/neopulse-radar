"use client";

import { isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { num, signed } from "@/lib/format";
import type { Num, Sectors } from "@/lib/types";
import { Card, Note } from "./ui";

interface Row { sector: string; up: number; down: number; pct: Num; contrib: Num }

/** Ngành trong phiên: độ rộng, % bình quân theo vốn hóa, đóng góp điểm (ước lượng). Số do Python tính. */
export function SectorCard({ sectors, live, indexCode }: {
  sectors?: Sectors;
  live: { n: string; p: Num; c: Num; u: number; d: number }[] | null;
  indexCode: string;
}) {
  const rows: Row[] = live?.length
    ? live.map((r) => ({ sector: r.n, up: r.u, down: r.d, pct: r.p, contrib: r.c }))
    : (sectors?.rows ?? []).map((r) => ({ sector: r.sector, up: r.n_up, down: r.n_down, pct: r.pct_cap, contrib: r.contrib_pts }));
  if (!rows.length) return null;
  const maxAbs = Math.max(...rows.map((r) => (isNum(r.contrib) ? Math.abs(r.contrib) : 0)), 0.01);
  return (
    <Card title={`Ngành trong phiên${live?.length ? " · trực tiếp" : ""}`}>
      <div className="scroll-x">
        <table className="w-full min-w-[520px] border-collapse text-sm">
          <thead>
            <tr className="text-xs text-muted">
              <th scope="col" className="px-2 py-1.5 text-left font-medium">Ngành</th>
              <th scope="col" className="px-2 py-1.5 text-right font-medium">Tăng / Giảm</th>
              <th scope="col" className="px-2 py-1.5 text-right font-medium">% bình quân vốn hóa</th>
              <th scope="col" className="px-2 py-1.5 text-left font-medium">Đóng góp vào {indexCode} (điểm, ước lượng)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const tone = priceTone(r.pct);
              const w = isNum(r.contrib) ? (Math.abs(r.contrib) / maxAbs) * 50 : 0;
              return (
                <tr key={r.sector} className="border-t border-line">
                  <td className="px-2 py-1.5 font-medium">{r.sector}</td>
                  <td className="tnum px-2 py-1.5 text-right">
                    <span className="text-up">▲{r.up}</span> / <span className="text-down">▼{r.down}</span>
                  </td>
                  <td className={`tnum px-2 py-1.5 text-right ${TONE_CLASS[tone]}`}>
                    <span aria-hidden>{TONE_MARK[tone]} </span>{signed(r.pct)}%
                  </td>
                  <td className="px-2 py-1.5">
                    <div className="flex items-center gap-2">
                      <div className="relative h-2 flex-1 rounded bg-surface2" aria-hidden>
                        <div className="absolute left-1/2 top-[-2px] h-3 w-px bg-line" />
                        <div
                          className="absolute top-0 h-2 rounded"
                          style={{
                            background: (r.contrib ?? 0) >= 0 ? "var(--up)" : "var(--down)",
                            width: `${w}%`,
                            left: (r.contrib ?? 0) >= 0 ? "50%" : `${50 - w}%`,
                          }}
                        />
                      </div>
                      <span className={`tnum w-14 text-right ${TONE_CLASS[priceTone(r.contrib)]}`}>{signed(r.contrib, 2)}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Note>
        {sectors?.note ?? "Đóng góp điểm là ước lượng theo vốn hóa niêm yết, chưa điều chỉnh free-float."}
        {!live?.length && isNum(sectors?.contrib_sum) && isNum(sectors?.index_change)
          ? ` Tổng ước lượng ${num(sectors?.contrib_sum ?? null)} điểm so với thay đổi thật ${num(sectors?.index_change ?? null)} điểm.`
          : ""}
      </Note>
    </Card>
  );
}
