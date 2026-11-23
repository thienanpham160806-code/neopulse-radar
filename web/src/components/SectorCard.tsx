"use client";

import { Fragment, useState } from "react";

import { isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { num, signed } from "@/lib/format";
import type { Num, Sectors } from "@/lib/types";
import { Card, Note } from "./ui";
import { CompanyLink } from "./CompanyLink";

interface Row { sector: string; up: number; down: number; pct: Num; contrib: Num; symbols: string[] }

/** Ngành trong phiên: độ rộng, % bình quân theo vốn hóa, đóng góp điểm (ước lượng). Số do Python tính. */
export function SectorCard({ sectors, live, indexCode }: {
  sectors?: Sectors;
  live: { n: string; p: Num; c: Num; u: number; d: number }[] | null;
  indexCode: string;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const members = new Map((sectors?.rows ?? []).map((r) => [r.sector, r.symbols]));
  const rows: Row[] = live?.length
    ? live.map((r) => ({ sector: r.n, up: r.u, down: r.d, pct: r.p, contrib: r.c, symbols: members.get(r.n) ?? [] }))
    : (sectors?.rows ?? []).map((r) => ({ sector: r.sector, up: r.n_up, down: r.n_down, pct: r.pct_cap, contrib: r.contrib_pts, symbols: r.symbols }));
  if (!rows.length) return null;
  const maxAbs = Math.max(...rows.map((r) => (isNum(r.contrib) ? Math.abs(r.contrib) : 0)), 0.01);
  return (
    <Card title={`Ngành trong phiên${live?.length ? " · trực tiếp" : ""}`}>
      <div className="scroll-x">
        <table className="w-full border-collapse sm:min-w-[520px] text-sm">
          <thead>
            <tr className="text-xs text-muted">
              <th scope="col" className="px-2 py-1.5 text-left font-medium">Ngành</th>
              <th scope="col" className="px-2 py-1.5 text-right font-medium">Tăng / Giảm</th>
              <th scope="col" className="px-2 py-1.5 text-right font-medium">% bình quân vốn hóa</th>
              <th scope="col" className="px-2 py-1.5 text-left font-medium">Đóng góp vào {indexCode} <span className="hidden sm:inline">(điểm, ước lượng)</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const tone = priceTone(r.pct);
              const w = isNum(r.contrib) ? (Math.abs(r.contrib) / maxAbs) * 50 : 0;
              return (
                <Fragment key={r.sector}>
                <tr className="cursor-pointer border-t border-line hover:bg-surface2" onClick={() => setOpen(open === r.sector ? null : r.sector)}>
                  <td className="px-2 py-1.5 font-medium">
                    <button type="button" aria-expanded={open === r.sector} className="text-left" onClick={(e) => { e.stopPropagation(); setOpen(open === r.sector ? null : r.sector); }}>
                      <span aria-hidden className="mr-1 text-muted">{open === r.sector ? "▾" : "▸"}</span>{r.sector}
                    </button>
                  </td>
                  <td className="tnum px-2 py-1.5 text-right">
                    <span className="text-up">▲{r.up}</span> / <span className="text-down">▼{r.down}</span>
                  </td>
                  <td className={`tnum px-2 py-1.5 text-right ${TONE_CLASS[tone]}`}>
                    <span aria-hidden>{TONE_MARK[tone]} </span>{signed(r.pct)}%
                  </td>
                  <td className="px-2 py-1.5">
                    <div className="flex items-center gap-2">
                      <div className="relative hidden h-2 flex-1 rounded bg-surface2 sm:block" aria-hidden>
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
                {open === r.sector ? (
                  <tr className="bg-surface2"><td colSpan={4} className="px-3 py-2 text-sm">
                    {r.symbols.length ? <>Các mã trong ngành: <span className="inline-flex flex-wrap gap-x-3 gap-y-2">{r.symbols.map((s) => <CompanyLink key={s} symbol={s} />)}</span></> : "Chưa có danh sách mã cho ngành này."}
                  </td></tr>
                ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <Note>
        {sectors?.note ?? "Đóng góp điểm là ước lượng theo vốn hóa niêm yết, chưa điều chỉnh theo tỷ lệ cổ phiếu tự do chuyển nhượng."}
        {!live?.length && isNum(sectors?.contrib_sum) && isNum(sectors?.index_change)
          ? ` Tổng ước lượng ${num(sectors?.contrib_sum ?? null)} điểm so với thay đổi thật ${num(sectors?.index_change ?? null)} điểm.`
          : ""}
      </Note>
    </Card>
  );
}
