"use client";

import { useMemo, useState } from "react";
import { CompanyLink } from "./CompanyLink";
import { SectorCard } from "./SectorCard";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, Treemap, XAxis, YAxis, ZAxis,
} from "recharts";
import { dash, hm, money, num, pct, ratioPct, signed } from "@/lib/format";
import { dmyTime, isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { RULE_PLAIN } from "@/lib/plain";
import type { AlertItem, BookRow, Payload, Severity } from "@/lib/types";
import { Card, Change, Empty, Note, SevTag, SignedMoney, Stat, Td, Th, TOOLTIP_STYLE, signTone } from "./ui";
import { Term } from "./Glossary";
import { AlertDetail } from "./AlertDetail";

export interface Filters {
  sym: string;
  minSev: Severity;
}
export type WhySub = "nganh" | "so-lenh" | "khoi-ngoai" | "phai-sinh";
export type MethodSub = "phuong-phap" | "kiem-chung";

const SEV_ORDER: Severity[] = ["CAO", "TRUNG BÌNH", "THẤP"];
const sevOk = (s: Severity, min: Severity) => SEV_ORDER.indexOf(s) <= SEV_ORDER.indexOf(min);
const symOk = (symbol: string, q: string) => !q || symbol.toUpperCase().includes(q.toUpperCase());
const gridProps = { strokeDasharray: "3 3", vertical: false } as const;

function SymbolBtn({ symbol, onSelect }: { symbol: string; onSelect?: (s: string) => void }) {
  if (!onSelect) return <CompanyLink symbol={symbol} />;
  return (
    <button
      type="button"
      onClick={() => onSelect(symbol)}
      title={`Soi nội phiên mã ${symbol}`}
      className="font-semibold text-accent underline decoration-accent/30 underline-offset-4 hover:decoration-accent"
    >
      {symbol}
    </button>
  );
}

/* ------------------------------------------------------------------ Tab 2: Vì sao? (Gộp Ngành & Độ rộng · Sổ lệnh · Khối ngoại · Phái sinh) */
const WHY_SUBS: { id: WhySub; label: string }[] = [
  { id: "nganh", label: "Ngành & Độ rộng" },
  { id: "so-lenh", label: "Sổ lệnh & Thanh khoản" },
  { id: "khoi-ngoai", label: "Khối ngoại" },
  { id: "phai-sinh", label: "Phái sinh" },
];

export function WhyTab({
  p,
  f,
  sub,
  onSub,
  onSelectSymbol,
  onSwitchIndex,
}: {
  p: Payload;
  f: Filters;
  sub: WhySub;
  onSub: (next: WhySub) => void;
  onSelectSymbol?: (symbol: string) => void;
  onSwitchIndex?: (code: string) => void;
}) {
  return (
    <div className="panel-enter space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="tablist" aria-label="Phân mục giải thích nguyên nhân" className="scroll-x flex gap-1.5 rounded-xl border border-line bg-surface p-1">
          {WHY_SUBS.map((item, i) => (
            <button
              key={item.id}
              id={`why-sub-${item.id}`}
              type="button"
              role="tab"
              aria-selected={sub === item.id}
              tabIndex={sub === item.id ? 0 : -1}
              onClick={() => onSub(item.id)}
              onKeyDown={(e) => {
                const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: WHY_SUBS.length - 1 }[e.key];
                if (k === undefined) return;
                e.preventDefault();
                const next = WHY_SUBS[(k + WHY_SUBS.length) % WHY_SUBS.length];
                onSub(next.id);
                document.getElementById(`why-sub-${next.id}`)?.focus();
              }}
              className={`ui-transition min-h-9 whitespace-nowrap rounded-lg px-3 text-xs font-semibold sm:text-sm ${
                sub === item.id ? "bg-accent text-on-accent" : "text-muted hover:bg-surface2 hover:text-fg"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div key={sub} className="panel-enter">
        {sub === "nganh" ? (
          <BreadthAndSectors p={p} onSelectSymbol={onSelectSymbol} />
        ) : sub === "so-lenh" ? (
          <Book p={p} f={f} onSelectSymbol={onSelectSymbol} />
        ) : sub === "khoi-ngoai" ? (
          <Foreign p={p} f={f} onSelectSymbol={onSelectSymbol} />
        ) : (
          <Futures p={p} onSwitchIndex={onSwitchIndex} />
        )}
      </div>
    </div>
  );
}

function BreadthAndSectors({ p, onSelectSymbol }: { p: Payload; onSelectSymbol?: (s: string) => void }) {
  const code = p.index?.code ?? p.meta.index_code;
  const ex = p.breadth?.exchange ?? p.index?.row;
  const uni = p.breadth?.universe;
  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed text-muted">
        Mức tăng hoặc giảm có lan tỏa ra đa số cổ phiếu hay chỉ tập trung vào vài mã vốn hóa lớn? Đối chiếu số độ rộng của chỉ số <b className="text-fg">{code}</b> với số tự tính trên rổ <b className="tnum text-fg">{p.meta.n_symbols_computed}</b> mã và đóng góp theo từng ngành.
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label={<Term k="breadth">A/D chỉ số ({code})</Term>}
          value={signed(ex?.ad_ratio ?? null)}
          tone={signTone(ex?.ad_ratio ?? null)}
          sub={isNum(ex?.pct_advancing) ? `${ratioPct(ex?.pct_advancing, 0)} số mã tăng` : "chưa có tỷ lệ"}
        />
        <Stat
          label="Tăng / Đứng / Giảm"
          value={
            isNum(ex?.advances) ? (
              <span className="text-base">
                <span className="text-up">▲{num(ex?.advances, 0)}</span>{" "}
                <span className="text-refc">■{num(ex?.no_change, 0)}</span>{" "}
                <span className="text-down">▼{num(ex?.declines, 0)}</span>
              </span>
            ) : (
              dash
            )
          }
          sub={
            isNum(ex?.n_ceiling) || isNum(ex?.n_floor)
              ? <>Trần <span className="text-ceil font-semibold">▲▲{num(ex?.n_ceiling, 0)}</span> · Sàn <span className="text-floor font-semibold">▼▼{num(ex?.n_floor, 0)}</span></>
              : "số mã của chỉ số"
          }
        />
        <Stat
          label="A/D tự tính trên rổ"
          value={signed(uni?.ad_ratio ?? null)}
          tone={signTone(uni?.ad_ratio ?? null)}
          sub={
            isNum(uni?.advances)
              ? `▲${num(uni?.advances, 0)} tăng · ▼${num(uni?.declines, 0)} giảm`
              : `trên ${p.meta.n_symbols_computed} mã`
          }
        />
        <Stat
          label={<Term k="turnover">Giá trị khớp {code}</Term>}
          value={money(ex?.total_value ?? null)}
          sub={isNum(ex?.total_volume) ? `${num(ex?.total_volume, 0)} CP` : "lũy kế trong phiên"}
        />
      </div>
      {p.pulse?.divergence ? (
        <div role="note" className="rounded-xl border border-fg/30 bg-surface p-3 text-sm font-medium text-fg">
          <b>Cảnh báo phân kỳ độ rộng:</b> {p.pulse.divergence}
        </div>
      ) : null}
      <SectorCard sectors={p.sectors} live={null} indexCode={code} onSelectSymbol={onSelectSymbol} />
    </div>
  );
}

/* ------------------------------------------------------------------ Sổ lệnh & Thanh khoản */
type BookKey = keyof BookRow;
function TreemapCell(props: {
  x?: number; y?: number; width?: number; height?: number; name?: string; obi?: number | null;
  onSelectSymbol?: (s: string) => void;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, obi, onSelectSymbol } = props;
  const none = obi === null || obi === undefined;
  const strength = none ? 0 : Math.round(22 + 58 * Math.min(1, Math.abs(obi)));
  const fill = none ? "var(--surface-2)" : `color-mix(in srgb, ${obi >= 0 ? "var(--up)" : "var(--down)"} ${strength}%, var(--surface))`;
  return (
    <g
      onClick={() => (name && onSelectSymbol ? onSelectSymbol(name) : undefined)}
      style={{ cursor: onSelectSymbol && name ? "pointer" : "default" }}
    >
      <rect x={x} y={y} width={width} height={height} rx={4} style={{ fill }} stroke="var(--surface)" strokeWidth={2} />
      {width > 36 && height > 22 ? (
        <text x={x + 6} y={y + 15} style={{ fontSize: 11, fontWeight: 700, fill: "var(--fg)" }}>
          {name}
        </text>
      ) : null}
      {width > 54 && height > 36 && !none ? (
        <text x={x + 6} y={y + 29} style={{ fontSize: 10, fontWeight: 500, fill: "var(--fg)", opacity: 0.85 }}>
          {obi >= 0 ? "▲" : "▼"}{signed(obi, 2)}
        </text>
      ) : null}
    </g>
  );
}

export function Book({ p, f, onSelectSymbol }: { p: Payload; f: Filters; onSelectSymbol?: (s: string) => void }) {
  const rows = useMemo(() => (p.book?.rows ?? []).filter((r) => symOk(r.symbol, f.sym)), [p.book, f.sym]);
  const [sortKey, setSortKey] = useState<BookKey>("liq_score");
  const [asc, setAsc] = useState(false);
  const sorted = useMemo(() => {
    const d = [...rows];
    d.sort((a, b) => {
      const x = a[sortKey], y = b[sortKey];
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      return (asc ? 1 : -1) * (typeof x === "string" ? x.localeCompare(String(y)) : Number(x) - Number(y));
    });
    return d;
  }, [rows, sortKey, asc]);

  if (!p.book || !p.book.rows.length) return <Empty>Chưa có dữ liệu sổ lệnh cho phiên này.</Empty>;
  if (!rows.length) return <Empty>Không có mã nào khớp bộ lọc “{f.sym}” trong bảng sổ lệnh.</Empty>;

  const tree = rows
    .filter((r) => (r.total_value ?? 0) > 0)
    .slice(0, 60)
    .map((r) => ({ name: r.symbol, size: r.total_value as number, obi: r.obi3, pct: r.pct_change }));
  const terms: Partial<Record<BookKey, string>> = {
    last: "price", pct_change: "price", obi3: "book", spread_bps: "spread",
    depth_value: "depth", total_value: "turnover", slippage_bps: "slippage",
    fill_ratio: "fill", liq_score: "liq_score",
  };
  const head = (label: string, key: BookKey) => (
    <th scope="col" className="text-right">
      <span className="inline-flex items-center">
        <button
          type="button"
          className="min-h-9 whitespace-nowrap px-2 py-1 text-right text-xs font-medium text-muted hover:text-fg"
          onClick={() => (key === sortKey ? setAsc(!asc) : (setSortKey(key), setAsc(false)))}
        >
          {label}{sortKey === key ? (asc ? " ▲" : " ▼") : ""}
        </button>
        {terms[key] ? <Term k={terms[key]} /> : null}
      </span>
    </th>
  );

  return (
    <div className="grid grid-cols-1 gap-3.5">
      <p className="text-sm leading-relaxed text-muted">
        Mua bán ngay có tốn chi phí không, và lệnh chờ đang lệch về phía nào? Xét <b className="tnum text-fg">{p.meta.n_symbols_computed}</b> mã đã ghi tại mốc dữ liệu đầy đủ gần nhất. Bấm vào bất kỳ ô hoặc mã nào để mở <b>Chi tiết mã</b>.
      </p>

      <Card
        title="Bản đồ áp lực sổ lệnh (bấm ô để soi mã)"
        action={
          <div className="flex items-center gap-3 text-xs text-muted">
            <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-up/70 align-middle" /> Mua chờ dày hơn</span>
            <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-down/70 align-middle" /> Bán chờ dày hơn</span>
          </div>
        }
      >
        {tree.length ? (
          <div className="h-72 w-full" role="img" aria-label="Bản đồ nhiệt áp lực sổ lệnh theo mã">
            <ResponsiveContainer>
              <Treemap
                data={tree}
                dataKey="size"
                isAnimationActive={false}
                content={<TreemapCell onSelectSymbol={onSelectSymbol} />}
              >
                <Tooltip
                  {...TOOLTIP_STYLE}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload as { name: string; size: number; obi: number | null; pct: number | null };
                    return (
                      <div style={TOOLTIP_STYLE.contentStyle} className="px-3 py-2 text-xs">
                        <div className="font-bold text-fg">{d.name}</div>
                        <div className="tnum mt-1">Giá trị khớp: <b>{money(d.size)}</b></div>
                        <div className="tnum">OBI₃: <b className={signTone(d.obi)}>{signed(d.obi)}</b></div>
                        <div className="tnum">Biến động: <Change value={d.pct} /></div>
                        {onSelectSymbol ? <div className="mt-1 text-[11px] text-accent">Bấm để soi chi tiết →</div> : null}
                      </div>
                    );
                  }}
                />
              </Treemap>
            </ResponsiveContainer>
          </div>
        ) : (
          <Empty>Chưa có mã nào có giá trị khớp.</Empty>
        )}
        <Note>Diện tích = giá trị khớp trong phiên; màu = OBI₃ trên 3 mức giá tốt nhất. Lệnh chờ có thể bị hủy trước khi khớp.</Note>
      </Card>

      <Card title="Bảng thanh khoản & trượt giá">
        <div className="scroll-x max-h-[26rem] overflow-y-auto">
          <table className="w-full min-w-[760px] border-collapse">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr>
                <th scope="col" className="px-2.5 py-2 text-left text-xs font-medium text-muted">Mã</th>
                {head("Giá", "last")}{head("% đổi", "pct_change")}{head("OBI₃", "obi3")}{head("Spread (bps)", "spread_bps")}
                {head("Độ sâu 3 mức", "depth_value")}{head("Giá trị khớp", "total_value")}{head("Trượt giá (bps)", "slippage_bps")}
                {head("Tỷ lệ khớp", "fill_ratio")}{head("Điểm thanh khoản", "liq_score")}
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.symbol} className="ui-transition border-t border-line hover:bg-surface2/60">
                  <Td right={false} className="font-semibold"><SymbolBtn symbol={r.symbol} onSelect={onSelectSymbol} /></Td>
                  <Td>{num(r.last, 0)}</Td>
                  <Td><Change value={r.pct_change} /></Td>
                  <Td className={signTone(r.obi3)}>{isNum(r.obi3) ? `${TONE_MARK[priceTone(r.obi3)]} ` : ""}{signed(r.obi3)}</Td>
                  <Td>{num(r.spread_bps, 1)}</Td>
                  <Td>{money(r.depth_value)}</Td>
                  <Td>{money(r.total_value)}</Td>
                  <Td>{num(r.slippage_bps, 1)}</Td>
                  <Td>{ratioPct(r.fill_ratio)}</Td>
                  <Td className="font-semibold">{num(r.liq_score, 0)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>
          Trượt giá: chi phí ước lượng (so với giá giữa) khi MUA ngay lệnh {money(p.meta.order_value_vnd)} bằng cách đi qua 3 mức giá bán — là cận dưới vì giả định sổ lệnh đứng yên.
          Tỷ lệ khớp &lt; 100% nghĩa là 3 mức không đủ hấp thụ. Bảng chỉ có chỉ báo đã tổng hợp, không phải sổ lệnh thô.
        </Note>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Khối ngoại */
export function Foreign({ p, f, onSelectSymbol }: { p: Payload; f: Filters; onSelectSymbol?: (s: string) => void }) {
  const all = p.foreign?.rows ?? [];
  const rows = all.filter((r) => symOk(r.symbol, f.sym));
  if (!all.length) return <Empty>Chưa có dữ liệu khối ngoại cho phiên này.</Empty>;
  if (!rows.length) return <Empty>Không có mã nào khớp bộ lọc “{f.sym}” trong bảng khối ngoại.</Empty>;

  const bars = [...rows].sort((a, b) => (a.net ?? 0) - (b.net ?? 0));
  const bar = [...bars.slice(0, 8), ...bars.slice(-8)].filter((r, i, a) => a.findIndex((x) => x.symbol === r.symbol) === i);
  const scatter = rows
    .filter((r) => r.participation !== null && r.net_ratio !== null)
    .map((r) => ({ x: r.participation as number, y: r.net_ratio as number, z: r.total_value ?? 1, s: r.symbol, net: r.net }));

  return (
    <div className="grid grid-cols-1 gap-3.5">
      <div className="grid gap-3.5 lg:grid-cols-2">
        <Card title="Khối ngoại mua/bán ròng theo mã (lớn nhất mỗi phía)">
          <div className="h-[26rem] w-full" role="img" aria-label="Biểu đồ khối ngoại mua bán ròng theo mã">
            <ResponsiveContainer>
              <BarChart data={bar} layout="vertical" margin={{ left: 6, right: 10 }}>
                <CartesianGrid {...gridProps} horizontal={false} vertical />
                <XAxis type="number" tickFormatter={(v: number) => money(v)} />
                <YAxis type="category" dataKey="symbol" width={44} interval={0} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [money(v), "Ròng"]} />
                <ReferenceLine x={0} stroke="var(--muted)" />
                <Bar
                  dataKey="net"
                  name="Ròng (đồng)"
                  isAnimationActive={false}
                  style={{ cursor: onSelectSymbol ? "pointer" : "default" }}
                  onClick={(entry) => {
                    const sym = (entry as unknown as { symbol?: string })?.symbol;
                    if (sym && onSelectSymbol) onSelectSymbol(sym);
                  }}
                >
                  {bar.map((r) => (
                    <Cell key={r.symbol} fill={(r.net ?? 0) >= 0 ? "var(--up)" : "var(--down)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {onSelectSymbol ? <Note>Bấm vào thanh bất kỳ để mở Chi tiết mã nội phiên.</Note> : null}
        </Card>

        <Card title="Chiều và quy mô (rê chuột để xem từng mã)">
          <div className="h-[24rem] w-full" role="img" aria-label="Đồ thị tỷ trọng khối ngoại so với mức ròng trên tổng">
            <ResponsiveContainer>
              <ScatterChart margin={{ left: 0, right: 12, top: 8, bottom: 8 }}>
                <CartesianGrid {...gridProps} vertical />
                <XAxis type="number" dataKey="x" name="Tỷ trọng khối ngoại" tickFormatter={(v: number) => ratioPct(v)} domain={[0, "auto"]} />
                <YAxis type="number" dataKey="y" name="Ròng/tổng" domain={[-1, 1]} width={40} />
                <ZAxis type="number" dataKey="z" range={[50, 260]} />
                <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="3 3" />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  cursor={{ strokeDasharray: "3 3" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload as { s: string; x: number; y: number; net: number | null };
                    return (
                      <div style={TOOLTIP_STYLE.contentStyle} className="px-3 py-2 text-xs">
                        <div className="font-bold text-fg">{d.s}</div>
                        <div className="tnum mt-1">Ròng: <SignedMoney value={d.net} /></div>
                        <div className="tnum">Ròng/tổng: <b>{signed(d.y, 2)}</b></div>
                        <div className="tnum">Tỷ trọng khối ngoại: <b>{ratioPct(d.x, 1)}</b></div>
                      </div>
                    );
                  }}
                />
                <Scatter
                  data={scatter}
                  isAnimationActive={false}
                  style={{ cursor: onSelectSymbol ? "pointer" : "default" }}
                  onClick={(entry) => {
                    const sym = (entry as unknown as { s?: string })?.s;
                    if (sym && onSelectSymbol) onSelectSymbol(sym);
                  }}
                >
                  {scatter.map((pt) => (
                    <Cell
                      key={pt.s}
                      fill={pt.y > 0 ? "var(--up)" : pt.y < 0 ? "var(--down)" : "var(--refc)"}
                      fillOpacity={0.78}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <Note>
            <Term k="foreign">Tỷ trọng và ròng/tổng</Term>: góc trên-phải là mua ròng với mức tham gia lớn hơn; xanh lá = mua ròng, đỏ = bán ròng. Gần trục dọc là tỷ trọng nhỏ; chưa đủ để suy ra tác động giá.
          </Note>
        </Card>
      </div>

      <Card title="Bảng khối ngoại">
        <div className="scroll-x max-h-96 overflow-y-auto">
          <table className="w-full min-w-[640px] border-collapse">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr>
                <Th right={false}>Mã</Th>
                <Th><Term k="foreign">Khối ngoại mua</Term></Th>
                <Th><Term k="foreign">Khối ngoại bán</Term></Th>
                <Th><Term k="foreign">Ròng</Term></Th>
                <Th><Term k="foreign">Ròng/tổng</Term></Th>
                <Th><Term k="foreign">Tỷ trọng khối ngoại</Term></Th>
                <Th><Term k="room">Room khối ngoại đã dùng</Term></Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} className="ui-transition border-t border-line hover:bg-surface2/60">
                  <Td right={false} className="font-semibold"><SymbolBtn symbol={r.symbol} onSelect={onSelectSymbol} /></Td>
                  <Td>{money(r.buy)}</Td>
                  <Td>{money(r.sell)}</Td>
                  <Td><SignedMoney value={r.net} /></Td>
                  <Td className={signTone(r.net_ratio)}>{signed(r.net_ratio)}</Td>
                  <Td>{ratioPct(r.participation)}</Td>
                  <Td>{ratioPct(r.room_used)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Phái sinh */
export function Futures({ p, onSwitchIndex }: { p: Payload; onSwitchIndex?: (code: string) => void }) {
  const fu = p.futures;
  if (!fu || !fu.available || !fu.state) {
    return (
      <Empty>
        <p>Chưa có dữ liệu hợp đồng tương lai khớp được với chỉ số VN30 trong phiên này. Chênh lệch cơ sở chỉ tính khi chọn chỉ số VN30 và bộ ghi có nhận dữ liệu hợp đồng tương lai.</p>
        {onSwitchIndex && p.meta.index_code !== "VN30" ? (
          <button
            type="button"
            onClick={() => onSwitchIndex("VN30")}
            className="ui-transition mt-3 min-h-10 rounded-xl bg-accent px-4 text-xs font-semibold text-on-accent hover:opacity-90"
          >
            Chuyển sang chỉ số VN30 →
          </button>
        ) : null}
      </Empty>
    );
  }
  const s = fu.state;
  return (
    <div className="grid grid-cols-1 gap-3.5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={s.symbol ?? "HĐTL"} value={num(fu.future ?? null, 1)} sub={`cơ sở ${num(fu.spot ?? null, 2)}`} />
        <Stat label={<Term k="basis">Chênh lệch cơ sở</Term>} value={`${isNum(s.basis) ? `${TONE_MARK[priceTone(s.basis)]} ` : ""}${signed(s.basis)} điểm`} sub={pct(s.basis_pct)} tone={signTone(s.basis)} />
        <Stat label={<Term k="maturity">Ngày tới đáo hạn</Term>} value={num(s.dtm, 0)} sub={s.label ?? undefined} />
        <Stat label={<Term k="maturity">Lệch so với giá trị hợp lý</Term>} value={`${signed(s.mispricing)} điểm`} sub={s.z !== null ? <Term k="basis_z">z basis = {signed(s.z, 1)}</Term> : "chưa đủ dữ liệu cho z"} />
      </div>
      <Card title="Chênh lệch cơ sở (basis, F − S) theo phút">
        <div className="h-64 w-full" role="img" aria-label="Đồ thị chênh lệch cơ sở của hợp đồng tương lai theo phút">
          <ResponsiveContainer>
            <AreaChart data={fu.series.map((r) => ({ ...r, t: hm(r.t) }))} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="t" minTickGap={40} />
              <YAxis width={44} domain={["auto", "auto"]} />
              <Tooltip {...TOOLTIP_STYLE} />
              <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="3 3" />
              <Area dataKey="basis" name="Chênh lệch cơ sở (điểm)" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.18} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <Note>
          Chênh lệch cơ sở thường tiến về mức thanh toán khi gần đáo hạn; các ảnh chụp nội phiên không bảo đảm chênh lệch bằng 0. Giá trị hợp lý dùng lãi suất giả định 4,5%/năm và cổ tức bằng 0. Dấu của chênh lệch cơ sở còn phản ánh chi phí vốn và cổ tức; không tự cho biết hướng giá tiếp theo.
        </Note>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Tab 3: Bất thường (Cảnh báo) */
function AlertRow({ a, onSelectSymbol }: { a: AlertItem; onSelectSymbol?: (s: string) => void }) {
  return (
    <li className="border-b border-line py-3 last:border-0">
      <div className="flex items-start gap-2.5">
        <SevTag sev={a.severity} className="mt-0.5" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div className="text-sm">
              <SymbolBtn symbol={a.symbol} onSelect={onSelectSymbol} />
              <span className="text-muted"> · {a.rule_name}</span>
            </div>
            <time className="tnum text-xs text-muted">{hm(a.t)}</time>
          </div>
          <p className="mt-1 text-sm leading-snug text-fg/90">{RULE_PLAIN[a.rule] ?? a.message}</p>
          <details className="mt-1.5">
            <summary className="inline-flex min-h-8 cursor-pointer items-center text-xs font-semibold text-accent hover:underline">
              Xem giá trị kiểm tra & ngưỡng quy tắc
            </summary>
            <div className="mt-1.5 rounded-xl bg-surface2/60 p-3">
              <AlertDetail a={a} />
              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                {onSelectSymbol ? (
                  <button type="button" onClick={() => onSelectSymbol(a.symbol)} className="font-semibold text-accent underline underline-offset-4">
                    Soi nội phiên {a.symbol} →
                  </button>
                ) : null}
                <CompanyLink symbol={a.symbol}>Mở hồ sơ doanh nghiệp {a.symbol} ↗</CompanyLink>
              </div>
            </div>
          </details>
        </div>
      </div>
    </li>
  );
}

export function Alerts({
  p,
  f,
  onSelectSymbol,
  onFilterSev,
}: {
  p: Payload;
  f: Filters;
  onSelectSymbol?: (s: string) => void;
  onFilterSev?: (sev: Severity) => void;
}) {
  const al = p.alerts;
  const [rule, setRule] = useState("");
  if (!al || al.total === 0) return <Empty>Không có cảnh báo nào trong phiên này.</Empty>;
  const items = al.items.filter((a) => sevOk(a.severity, f.minSev) && symOk(a.symbol, f.sym) && (!rule || a.rule === rule));

  return (
    <div className="panel-enter grid grid-cols-1 gap-3.5">
      {/* 3 thẻ mức cảnh báo — bấm trực tiếp để chọn ngưỡng lọc */}
      <div className="grid grid-cols-3 gap-2.5 sm:gap-3" role="group" aria-label="Lọc theo mức cảnh báo">
        {SEV_ORDER.map((s) => {
          const active = f.minSev === s;
          const label = s === "CAO" ? "◆ Cao (chỉ mức Cao)" : s === "TRUNG BÌNH" ? "◇ Từ Trung bình" : "· Tất cả (gồm Thấp)";
          return (
            <button
              key={s}
              type="button"
              aria-pressed={active}
              onClick={() => onFilterSev?.(s)}
              className={`ui-transition card-elev rounded-2xl border p-3 text-left ${
                active ? "border-accent bg-surface2 ring-1 ring-accent" : "border-line bg-surface hover:bg-surface2/60"
              }`}
            >
              <div className="text-xs font-medium text-muted">{label}</div>
              <div className="tnum mt-1 text-2xl font-bold leading-tight text-fg">{al.by_severity[s] ?? 0}</div>
            </button>
          );
        })}
      </div>

      <Card
        title={`${items.length} / ${al.total} lượt cảnh báo`}
        action={
          <select
            aria-label="Lọc loại cảnh báo"
            value={rule}
            onChange={(e) => setRule(e.target.value)}
            className="min-h-9 max-w-full rounded-lg border border-line bg-bg px-2.5 text-xs sm:text-sm"
          >
            <option value="">Mọi quy tắc</option>
            {Object.entries(al.rule_names).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        }
      >
        {items.length ? (
          <ul>{items.map((a, i) => <AlertRow key={`${a.t}-${a.symbol}-${a.rule}-${i}`} a={a} onSelectSymbol={onSelectSymbol} />)}</ul>
        ) : (
          <Empty>Không có cảnh báo khớp bộ lọc hiện tại. Thử chuyển sang mức “Tất cả” hoặc xóa bộ lọc mã.</Empty>
        )}
        {al.items.length < al.total ? (
          <Note>Chỉ hiển thị {al.items.length} cảnh báo ưu tiên cao nhất trong số {al.total}.</Note>
        ) : null}
        <Note>
          Đây là số lượt cảnh báo, không phải số mã. Mỗi quy tắc có điều kiện riêng: <Term k="rvol">khối lượng tương đối</Term>, <Term k="anomaly">điểm z trong phiên</Term>, <Term k="book">mất cân bằng sổ lệnh</Term> hoặc <Term k="band">sát trần/sàn</Term>. Cảnh báo không xác nhận nguyên nhân và không phải khuyến nghị.
        </Note>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Tab 4: Chi tiết mã (Soi 1 mã nội phiên + Xếp hạng đa yếu tố) */
function zCell(v: number | null) {
  if (v === null) return { background: "transparent" };
  const a = Math.min(1, Math.abs(v) / 3) * 0.48;
  return { background: `color-mix(in srgb, ${v >= 0 ? "var(--up)" : "var(--down)"} ${Math.round(a * 100)}%, transparent)` };
}

export function StockDetailTab({
  p,
  f,
  selectedSymbol,
  onSelectSymbol,
}: {
  p: Payload;
  f: Filters;
  selectedSymbol: string;
  onSelectSymbol: (s: string) => void;
}) {
  const bookRows = useMemo(() => p.book?.rows ?? [], [p.book?.rows]);
  const foreignRows = useMemo(() => p.foreign?.rows ?? [], [p.foreign?.rows]);
  const rankRows = useMemo(() => p.ranking ?? [], [p.ranking]);

  const allSymbols = useMemo(() => {
    const set = new Set<string>();
    for (const r of bookRows) set.add(r.symbol);
    for (const r of rankRows) set.add(r.symbol);
    for (const r of foreignRows) set.add(r.symbol);
    return Array.from(set).sort();
  }, [bookRows, rankRows, foreignRows]);

  const filteredSymbols = allSymbols.filter((s) => symOk(s, f.sym));
  const activeSym =
    (selectedSymbol && allSymbols.includes(selectedSymbol) ? selectedSymbol : null) ??
    filteredSymbols[0] ??
    allSymbols[0] ??
    "";

  const curBook = bookRows.find((r) => r.symbol === activeSym) ?? null;
  const curForeign = foreignRows.find((r) => r.symbol === activeSym) ?? null;
  const curRank = rankRows.find((r) => r.symbol === activeSym) ?? null;
  const curAlerts = (p.alerts?.items ?? []).filter((a) => a.symbol === activeSym);
  const ser = activeSym ? p.book?.series?.[activeSym] : undefined;

  // Các mã có cảnh báo CAO làm gợi ý chọn nhanh
  const quickPicks = useMemo(() => {
    const high = (p.alerts?.items ?? []).filter((a) => a.severity === "CAO").map((a) => a.symbol);
    return Array.from(new Set([...high, ...rankRows.slice(0, 4).map((r) => r.symbol)])).slice(0, 6);
  }, [p.alerts?.items, rankRows]);

  if (!allSymbols.length) {
    return <Empty>Chưa có dữ liệu từng mã trong phiên này để soi chi tiết.</Empty>;
  }

  return (
    <div className="panel-enter space-y-4">
      {/* Thanh chọn mã nhanh */}
      <section className="card-elev rounded-2xl border border-line bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <span>Chọn mã soi nội phiên:</span>
              <select
                aria-label="Chọn mã cổ phiếu để soi chi tiết"
                value={activeSym}
                onChange={(e) => onSelectSymbol(e.target.value)}
                className="min-h-10 rounded-xl border border-line bg-bg px-3 text-sm font-bold text-fg"
              >
                {allSymbols.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            {quickPicks.length ? (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-muted">Chú ý:</span>
                {quickPicks.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onSelectSymbol(s)}
                    aria-pressed={activeSym === s}
                    className={`ui-transition min-h-8 rounded-lg px-2.5 text-xs font-semibold ${
                      activeSym === s ? "bg-accent text-on-accent" : "bg-surface2 text-fg hover:bg-line"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {activeSym ? (
            <CompanyLink symbol={activeSym}>Mở hồ sơ doanh nghiệp {activeSym} ↗</CompanyLink>
          ) : null}
        </div>

        {/* Tóm tắt nội phiên của mã đang chọn */}
        {activeSym ? (
          <div className="mt-4 border-t border-line pt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <div className="flex items-baseline gap-3">
                  <h2 className="text-2xl font-bold">{activeSym}</h2>
                  {curBook ? (
                    <>
                      <span className={`tnum text-xl font-bold ${TONE_CLASS[priceTone(curBook.pct_change)]}`}>
                        {num(curBook.last, 0)}
                      </span>
                      <Change value={curBook.pct_change} className="text-sm font-semibold" />
                    </>
                  ) : null}
                </div>
                <p className="mt-0.5 text-xs text-muted">
                  Dữ liệu nội phiên tại mốc {p.meta.last_update ? dmyTime(p.meta.last_update) : dash}
                  {curRank ? ` · Hạng đa yếu tố #${curRank.rank}/${rankRows.length} (điểm ${num(curRank.score)})` : ""}
                </p>
              </div>
              {curBook ? (
                <div className="tnum text-xs text-muted">
                  Giá trị khớp phiên: <b className="text-fg">{money(curBook.total_value)}</b>
                  {" · "}Độ sâu 3 mức: <b className="text-fg">{money(curBook.depth_value)}</b>
                </div>
              ) : null}
            </div>

            {curBook ? (
              <div className="mt-3.5 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat
                  label={<Term k="book">OBI₃</Term>}
                  value={`${isNum(curBook.obi3) ? `${TONE_MARK[priceTone(curBook.obi3)]} ` : ""}${signed(curBook.obi3)}`}
                  tone={signTone(curBook.obi3)}
                  sub={<Term k="microprice">Microprice lệch {signed(curBook.micro_dev_bps, 1)} bps</Term>}
                />
                <Stat
                  label={<Term k="spread">Spread</Term>}
                  value={`${num(curBook.spread_bps, 1)} bps`}
                  sub={<Term k="pressure">Bán/Mua = {num(curBook.pressure)}</Term>}
                />
                <Stat
                  label={<Term k="slippage">Trượt giá (mua)</Term>}
                  value={`${num(curBook.slippage_bps, 1)} bps`}
                  sub={<Term k="fill">Khớp {ratioPct(curBook.fill_ratio)}</Term>}
                />
                <Stat
                  label={<Term k="liq_score">Điểm thanh khoản</Term>}
                  value={num(curBook.liq_score, 0)}
                  sub={<Term k="amihud">Amihud {num(curBook.amihud)} bps/tỷ</Term>}
                />
              </div>
            ) : (
              <Note>Chưa có chỉ báo sổ lệnh cho mã này trong phiên hiện tại.</Note>
            )}

            {curBook?.auction ? (
              <Note>Đang trong phiên định kỳ (ATO/ATC): giá mức 1 không phải giá giới hạn nên chỉ báo sổ lệnh có thể trống.</Note>
            ) : null}

            {/* Khối ngoại & cảnh báo của chính mã này */}
            <div className="mt-3.5 grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-line bg-bg/50 p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                  <Term k="foreign">Khối ngoại mã {activeSym}</Term>
                </h3>
                {curForeign ? (
                  <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    <div><dt className="text-muted">Ròng</dt><dd className="mt-0.5 text-sm font-bold"><SignedMoney value={curForeign.net} /></dd></div>
                    <div><dt className="text-muted">Tỷ trọng khối ngoại</dt><dd className="tnum mt-0.5 text-sm font-semibold">{ratioPct(curForeign.participation)}</dd></div>
                    <div><dt className="text-muted">Khối ngoại mua / bán</dt><dd className="tnum mt-0.5">{money(curForeign.buy)} / {money(curForeign.sell)}</dd></div>
                    <div><dt className="text-muted">Room khối ngoại đã dùng</dt><dd className="tnum mt-0.5">{ratioPct(curForeign.room_used)}</dd></div>
                  </dl>
                ) : (
                  <p className="mt-2 text-xs text-muted">Chưa ghi nhận giao dịch khối ngoại cho {activeSym}.</p>
                )}
              </div>

              <div className="rounded-xl border border-line bg-bg/50 p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Cảnh báo phiên của {activeSym} ({curAlerts.length})
                </h3>
                {curAlerts.length ? (
                  <ul className="mt-1.5 space-y-1.5 text-xs">
                    {curAlerts.slice(0, 4).map((a, i) => (
                      <li key={i} className="flex items-start justify-between gap-2">
                        <span className="flex items-center gap-1.5">
                          <SevTag sev={a.severity} />
                          <span>{RULE_PLAIN[a.rule] ?? a.rule_name}</span>
                        </span>
                        <time className="tnum shrink-0 text-muted">{hm(a.t)}</time>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-muted">Không có cảnh báo bất thường nào cho {activeSym} trong phiên.</p>
                )}
              </div>
            </div>

            {/* Biểu đồ Giá giữa & OBI₃ theo phút */}
            {ser && ser.t.length > 1 ? (
              <div className="mt-4">
                <h3 className="mb-1.5 text-xs font-semibold text-muted">Giá giữa và OBI₃ theo phút — {activeSym}</h3>
                <div className="h-64 w-full" role="img" aria-label={`Giá giữa và OBI₃ của ${activeSym}`}>
                  <ResponsiveContainer>
                    <ComposedChart data={ser.t.map((t, i) => ({ t, mid: ser.mid[i], obi3: ser.obi3[i] }))} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
                      <CartesianGrid {...gridProps} />
                      <XAxis dataKey="t" minTickGap={40} />
                      <YAxis yAxisId="l" domain={["auto", "auto"]} width={52} tickFormatter={(v: number) => num(v, 0)} />
                      <YAxis yAxisId="r" orientation="right" domain={[-1, 1]} width={34} />
                      <Tooltip {...TOOLTIP_STYLE} />
                      <Bar yAxisId="r" dataKey="obi3" name="OBI₃" isAnimationActive={false}>
                        {ser.t.map((_, i) => <Cell key={i} fill={(ser.obi3[i] ?? 0) >= 0 ? "var(--up)" : "var(--down)"} fillOpacity={0.45} />)}
                      </Bar>
                      <Line yAxisId="l" dataKey="mid" name="Giá giữa" stroke="var(--fg)" dot={false} strokeWidth={2} isAnimationActive={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <Note>Chuỗi theo phút chỉ có cho {Object.keys(p.book?.series ?? {}).length} mã có giá trị khớp lớn nhất trong phiên.</Note>
            )}
          </div>
        ) : null}
      </section>

      {/* Bảng xếp hạng đa yếu tố — bấm từng dòng để đổi mã đang soi phía trên */}
      <Ranking p={p} f={f} selectedSymbol={activeSym} onSelectSymbol={onSelectSymbol} />
    </div>
  );
}

/* ------------------------------------------------------------------ Xếp hạng */
export function Ranking({
  p,
  f,
  selectedSymbol,
  onSelectSymbol,
}: {
  p: Payload;
  f: Filters;
  selectedSymbol?: string;
  onSelectSymbol?: (s: string) => void;
}) {
  const all = p.ranking ?? [];
  const rows = all.filter((r) => symOk(r.symbol, f.sym));
  if (!all.length) return <Empty>Chưa có dữ liệu để xếp hạng.</Empty>;
  if (!rows.length) return <Empty>Không có mã nào khớp bộ lọc “{f.sym}” trong bảng xếp hạng.</Empty>;
  const zs: [string, string][] = [["momentum", "Động lượng"], ["flow", "Sổ lệnh"], ["foreign", "Khối ngoại"], ["liquidity", "Thanh khoản"], ["cost", "Chi phí"]];
  return (
    <Card title={<Term k="ranking">Xếp hạng đa yếu tố trong rổ</Term>}>
      <Note>
        Điểm = tổng có trọng số của z-score mặt cắt ngang (động lượng 30%, sổ lệnh 25%, khối ngoại 20%, thanh khoản 15%, chi phí 10%). Chỉ có nghĩa tương đối trong rổ, tại thời điểm tính. {onSelectSymbol ? "Bấm một dòng để soi nhanh mã đó ở phía trên." : ""}
      </Note>
      <div className="scroll-x mt-2.5 max-h-[30rem] overflow-y-auto">
        <table className="w-full min-w-[820px] border-collapse">
          <thead className="sticky top-0 z-10 bg-surface">
            <tr>
              <Th>Hạng</Th>
              <Th right={false}>Mã</Th>
              <Th><Term k="ranking">Điểm</Term></Th>
              <Th><Term k="price">Giá</Term></Th>
              <Th>% đổi</Th>
              <Th><Term k="book">OBI₃</Term></Th>
              <Th><Term k="foreign">Khối ngoại ròng/tổng</Term></Th>
              <Th><Term k="spread">Spread</Term></Th>
              {zs.map(([, n]) => <Th key={n}><Term k="ranking">z {n}</Term></Th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isSelected = selectedSymbol === r.symbol;
              return (
                <tr
                  key={r.symbol}
                  onClick={() => onSelectSymbol?.(r.symbol)}
                  className={`ui-transition border-t border-line ${onSelectSymbol ? "cursor-pointer" : ""} ${
                    isSelected ? "bg-surface2 font-medium" : "hover:bg-surface2/50"
                  }`}
                >
                  <Td>{r.rank}</Td>
                  <Td right={false} className="font-semibold">
                    <SymbolBtn symbol={r.symbol} onSelect={onSelectSymbol} />
                  </Td>
                  <Td className="font-semibold">{num(r.score)}</Td>
                  <Td>{num(r.last, 0)}</Td>
                  <Td><Change value={r.pct_change} /></Td>
                  <Td className={signTone(r.obi3)}>{signed(r.obi3)}</Td>
                  <Td className={signTone(r.net_ratio)}>{signed(r.net_ratio)}</Td>
                  <Td>{num(r.spread_bps, 1)}</Td>
                  {zs.map(([k]) => (
                    <Td key={k}>
                      <span className="block rounded px-1" style={zCell(r.z[k] ?? null)}>
                        {signed(r.z[k] ?? null, 1)}
                      </span>
                    </Td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ Tab 5: Phương pháp (Phương pháp & Giới hạn | Kiểm chứng & Dữ liệu) */
export function MethodTab({ p, sub, onSub }: { p: Payload; sub: MethodSub; onSub: (next: MethodSub) => void }) {
  const subs: { id: MethodSub; label: string }[] = [
    { id: "phuong-phap", label: "Phương pháp & Giới hạn" },
    { id: "kiem-chung", label: "Kiểm chứng & Dữ liệu" },
  ];
  return (
    <div className="panel-enter space-y-4">
      <div role="tablist" aria-label="Phân mục học thuật" className="inline-flex gap-1.5 rounded-xl border border-line bg-surface p-1">
        {subs.map((item, i) => (
          <button
            key={item.id}
            id={`method-sub-${item.id}`}
            type="button"
            role="tab"
            aria-selected={sub === item.id}
            tabIndex={sub === item.id ? 0 : -1}
            onClick={() => onSub(item.id)}
            onKeyDown={(e) => {
              const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: subs.length - 1 }[e.key];
              if (k === undefined) return;
              e.preventDefault();
              const next = subs[(k + subs.length) % subs.length];
              onSub(next.id);
              document.getElementById(`method-sub-${next.id}`)?.focus();
            }}
            className={`ui-transition min-h-9 rounded-lg px-3.5 text-xs font-semibold sm:text-sm ${
              sub === item.id ? "bg-accent text-on-accent" : "text-muted hover:bg-surface2 hover:text-fg"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div key={sub} className="panel-enter min-w-0">
        {sub === "kiem-chung" ? <Validation p={p} /> : <Method />}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Kiểm chứng */
const VALIDATION_COLS: Record<string, [string, string]> = {
  "tín hiệu": ["Tín hiệu", "book"], "tầm nhìn (thanh)": ["Sau bao nhiêu thanh", "sample"], "mẫu": ["Nhóm phiên", "sample"],
  n_bars: ["Số thanh", "sample"], n_obs: ["Cặp quan sát", "sample"], ic_mean: ["IC trung bình", "ic"],
  ic_tstat: ["t-stat của IC", "tstat"], hit_rate: ["Tỷ lệ cùng chiều (0–1)", "hit_rate"], spread_bps: ["Q5−Q1 (bps)", "hit_rate"],
};
const SIGNAL_TERMS: Record<string, string> = { obi3: "book", obi1: "obi1", obi_w: "obi_w", micro_dev_bps: "microprice" };
export function Validation({ p }: { p: Payload }) {
  const v = p.validation;
  if (!v) return <Empty>Chưa nhận được kết quả kiểm chứng từ bộ xử lý dữ liệu. Khi có kết quả, trang sẽ tự cập nhật. Mục này kiểm tra chất lượng dữ liệu và mối liên hệ giữa tín hiệu với biến động giá; không phải xác nhận tín hiệu chắc chắn dự báo đúng.</Empty>;
  const cols = v.ic.table.length ? Object.keys(v.ic.table[0]) : [];
  const dq = v.data_quality;
  return (
    <div className="grid grid-cols-1 gap-3.5">
      <Card title="Kiểm chứng trên dữ liệu đã thu thập">
        <p className="text-sm leading-relaxed">Hệ thống kiểm tra tín hiệu sổ lệnh có liên hệ với thay đổi giá sau đó hay không, đồng thời thống kê dữ liệu thiếu và gián đoạn. Kết quả được tính lại khoảng 10 phút một lần, tách khỏi luồng cập nhật giá.</p>
        {v.generated_at ? <p className="mt-2 text-xs text-muted">Tính lúc {dmyTime(v.generated_at)}{v.data_until ? ` · Dữ liệu đến ${dmyTime(v.data_until)}` : ""} (giờ Việt Nam).</p> : null}
        {dq.n_sessions < 5 ? <p className="mt-3 rounded-xl bg-surface2 p-3 text-sm">Mới ghi nhận {dq.n_sessions} phiên. Kết quả hiện chỉ để tham khảo; cần thu thập thêm phiên trước khi đánh giá độ ổn định của tín hiệu.</p> : null}
      </Card>
      {v.simulated_signals_are_planted ? (
        <div role="note" className="rounded-2xl border border-sim/40 bg-sim/10 p-3.5 text-sm text-sim">
          Trên dữ liệu MÔ PHỎNG, tín hiệu sổ lệnh được <b>cài sẵn</b> vào cơ chế sinh giá. Kết quả dưới đây chỉ xác nhận đường ống tính toán chạy đúng — <b>không</b> phải bằng chứng về thị trường thật.
        </div>
      ) : null}
      <Card title="Tín hiệu sổ lệnh có đi trước biến động giá?">
        <Note><Term k="sample">Trong mẫu: {v.ic.train.join(", ") || dash} · Ngoài mẫu: {v.ic.test.join(", ") || dash}</Term></Note>
        {v.ic.note ? <p className="mt-2 rounded-lg bg-surface2 p-2.5 text-sm">{v.ic.note}</p> : null}
        {cols.length ? (
          <div className="scroll-x mt-2">
            <table className="w-full min-w-[560px] border-collapse">
              <thead><tr>{cols.map((c) => <Th key={c} right={false}>{VALIDATION_COLS[c] ? <Term k={VALIDATION_COLS[c][1]}>{VALIDATION_COLS[c][0]}</Term> : c}</Th>)}</tr></thead>
              <tbody>
                {v.ic.table.map((r, i) => (
                  <tr key={i} className="border-t border-line">{cols.map((c) => <Td key={c} right={false}>{c === "tín hiệu" && SIGNAL_TERMS[String(r[c])] ? <Term k={SIGNAL_TERMS[String(r[c])]}>{String(r[c])}</Term> : typeof r[c] === "number" ? num(r[c] as number, Number.isInteger(r[c]) ? 0 : 4) : String(r[c] ?? dash)}</Td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <Note>
          IC: tương quan hạng Spearman giữa tín hiệu cuối thanh t và lợi suất giá giữa t→t+h, tính theo mặt cắt ngang từng thanh rồi lấy trung bình. t-stat chưa hiệu chỉnh tự tương quan nên bị thổi phồng phần nào.
          Q5−Q1 chưa trừ spread và phí nên không phải lợi nhuận khả thi. Dưới 5 phiên, kết quả chỉ minh họa.
        </Note>
      </Card>
      {v.ic_by_session.length ? (
        <Card title="IC theo từng phiên (OBI₃, 1 thanh)">
          <div className="h-52 w-full" role="img" aria-label="IC theo từng phiên">
            <ResponsiveContainer>
              <BarChart data={v.ic_by_session} margin={{ left: 0, right: 0, top: 8 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="trading_date" tickFormatter={(d: string) => d.slice(5)} />
                <YAxis width={44} />
                <Tooltip {...TOOLTIP_STYLE} />
                <ReferenceLine y={0} stroke="var(--muted)" />
                <Bar dataKey="ic_mean" name="IC" isAnimationActive={false}>{v.ic_by_session.map((r, i) => <Cell key={i} fill={(r.ic_mean ?? 0) >= 0 ? "var(--up)" : "var(--down)"} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
      <Card title="Chất lượng dữ liệu">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Ảnh chụp đã lưu" value={num(dq.n_quotes, 0)} />
          <Stat label={<Term k="sample">Số phiên</Term>} value={dq.n_sessions} sub={dq.n_sessions >= 5 ? "đạt mốc tối thiểu; cần thêm mẫu" : "chưa đủ 5 phiên"} />
          <Stat label="Số mã" value={dq.n_symbols} />
          <Stat label="Khoảng trống bất thường" value={dq.n_gaps} />
        </div>
        <h3 className="mt-3 text-xs font-medium text-muted">Vấn đề đã ghi nhận theo loại</h3>
        {Object.keys(dq.issues).length ? (
          <ul className="mt-1 text-sm">{Object.entries(dq.issues).map(([k, n]) => <li key={k} className="flex justify-between border-b border-line py-1.5"><span>{k}</span><span className="tnum font-medium">{n}</span></li>)}</ul>
        ) : <p className="mt-1 text-sm text-muted">Không có.</p>}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Phương pháp */
export function Method() {
  return (
    <div className="grid grid-cols-1 gap-3.5">
      <Card title="Chuỗi xử lý">
        <p className="text-sm leading-relaxed">
          Dữ liệu thị trường từ SSI FastConnect hoặc NEO API được kiểm tra chất lượng, sau đó Python tính các chỉ báo tổng hợp. Web nhận cập nhật mới trong phiên và dùng dữ liệu đã lưu khi nguồn cập nhật tạm dừng. Hồ sơ doanh nghiệp và lịch sử giá lấy từ Vietcap.
          Web <b>chỉ hiển thị kết quả</b>; các công thức chỉ báo và phân tích tài chính được tính bằng Python.
        </p>
      </Card>
      <Card title="Công thức chính">
        <div className="scroll-x">
          <table className="w-full min-w-[520px] border-collapse text-sm">
            <thead><tr><Th right={false}>Chỉ báo</Th><Th right={false}>Công thức</Th><Th right={false}>Ý nghĩa</Th></tr></thead>
            <tbody>
              {[
                ["Spread", "(bán₁ − mua₁) / giá giữa × 10⁴ (bps)", "chi phí khứ hồi tức thời"],
                ["OBI₃", "(ΣKL mua − ΣKL bán) / (ΣKL mua + ΣKL bán), 3 mức", "> 0: bên mua dày hơn"],
                ["Microprice", "(bán₁·KLmua₁ + mua₁·KLbán₁) / (KLmua₁ + KLbán₁)", "giá giữa có trọng số độ sâu"],
                ["A/D", "(tăng − giảm) / (tăng + giảm)", "độ lan tỏa"],
                ["Khối ngoại ròng/tổng", "(mua − bán) / (mua + bán)", "mức độ một chiều của khối ngoại"],
                ["Chênh lệch cơ sở", "F − S; quy năm (F/S − 1)·365/ngày còn lại", "định giá hợp đồng tương lai so với cơ sở"],
                ["z bền vững", "0,6745·(x − median)/MAD, cửa sổ 60 thanh trước", "bất thường khi |z| ≥ 3,5"],
                ["Điểm nhịp", "50 + 50·Σwᵢcᵢ; w = 30/25/20/15/10%", "trạng thái tổng hợp 0–100"],
              ].map(([a, b, c]) => (
                <tr key={a} className="border-t border-line"><td className="px-2.5 py-2 font-medium">{a}</td><td className="px-2.5 py-2">{b}</td><td className="px-2.5 py-2 text-muted">{c}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>Đầy đủ công thức, giả định và tài liệu tham khảo: docs/methodology.md trong mã nguồn.</Note>
      </Card>
      <Card title="Giới hạn cần biết khi đọc số">
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
          <li><b>Phân biệt dữ liệu trực tiếp và dữ liệu đã lưu.</b> Xem nguồn và thời điểm cập nhật trên thanh trạng thái. Khi bộ ghi dừng, máy ngủ hoặc mất kết nối, số liệu mới sẽ ngừng đến; web hiển thị dữ liệu đã lưu và báo độ trễ. Phiên lịch sử là số liệu cố định của phiên được chọn.</li>
          <li><b>Chỉ 3 mức giá tốt nhất</b>: OBI và độ sâu bỏ sót lệnh ở xa và lệnh ẩn; trượt giá là cận dưới.</li>
          <li><b>Thời điểm dùng là lúc nhận</b>, không phải dấu thời gian sự kiện, nên độ trễ mạng lẫn vào chuỗi.</li>
          <li><b>Rổ theo dõi hữu hạn</b> (mặc định VN30): khối ngoại và sổ lệnh là của rổ, không phải toàn thị trường; độ rộng lấy từ số của sàn.</li>
          <li><b>Giá trị giao dịch lũy kế từ SSI là ước lượng</b> (giá trung bình × khối lượng), nên các chỉ báo theo giá trị kém chính xác hơn.</li>
          <li><b>Trọng số điểm nhịp là lựa chọn thiết kế</b>, không phải ước lượng; xem độ nhạy ở tab Tổng quan. Điểm mô tả hiện trạng, không dự báo.</li>
          <li><b>IC chưa trừ độ chênh giá mua-bán và phí</b>; t-stat chưa hiệu chỉnh tự tương quan. Kết quả yếu hoặc không có ý nghĩa được báo đúng như vậy.</li>
          <li>Phiên định kỳ (ATO/ATC): giá mức 1 không phải giá giới hạn, nên chỉ báo sổ lệnh để trống.</li>
          <li>Sản phẩm <b>không đặt lệnh</b>; các API giao dịch và tài khoản bị chặn trong mã nguồn.</li>
        </ul>
        <p className="mt-3 rounded-xl bg-surface2 p-3 text-sm font-medium">Đây là công cụ phân tích học thuật, không phải lời khuyên đầu tư.</p>
        <p className="mt-3 text-sm">
          <a href="https://github.com/thienanpham160806-code/neopulse-radar/blob/main/docs/market-design-references.md" target="_blank" rel="noreferrer" className="text-accent underline underline-offset-4">
            Nguồn tham khảo thiết kế và cách áp dụng trong dự án ↗
          </a>
        </p>
      </Card>
    </div>
  );
}
