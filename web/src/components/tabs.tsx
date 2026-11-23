"use client";

import { useMemo, useState } from "react";
import { CompanyLink } from "./CompanyLink";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, Treemap, XAxis, YAxis, ZAxis,
} from "recharts";
import { dash, hm, money, num, pct, ratioPct, signed } from "@/lib/format";
import { dmyTime } from "@/lib/fmt";
import type { AlertItem, BookRow, Payload, Severity } from "@/lib/types";
import { Card, Empty, Note, SevTag, SignedMoney, Stat, Td, Th, TOOLTIP_STYLE, signTone } from "./ui";
import { Term } from "./Glossary";
import { AlertDetail } from "./AlertDetail";

export interface Filters {
  sym: string;
  minSev: Severity;
}
const SEV_ORDER: Severity[] = ["CAO", "TRUNG BÌNH", "THẤP"];
const sevOk = (s: Severity, min: Severity) => SEV_ORDER.indexOf(s) <= SEV_ORDER.indexOf(min);
const symOk = (symbol: string, q: string) => !q || symbol.toUpperCase().includes(q.toUpperCase());
const gridProps = { strokeDasharray: "3 3", vertical: false } as const;

function AlertRow({ a }: { a: AlertItem }) {
  return (
    <li className="flex items-start gap-2 border-b border-line py-2 last:border-0">
      <SevTag sev={a.severity} />
      <div className="min-w-0 flex-1">
        <div className="text-sm"><CompanyLink symbol={a.symbol} /> <span className="text-muted">· {a.rule_name}</span></div>
        <details className="mt-1"><summary className="min-h-9 cursor-pointer text-sm text-accent">Vì sao có cảnh báo này?</summary><AlertDetail a={a} /></details>
      </div>
      <time className="tnum text-xs text-muted">{hm(a.t)}</time>
    </li>
  );
}

/* ------------------------------------------------------------------ Tổng quan */
/* ------------------------------------------------------------------ Sổ lệnh */
type BookKey = keyof BookRow;
function TreemapCell(props: { x?: number; y?: number; width?: number; height?: number; name?: string; obi?: number | null }) {
  const { x = 0, y = 0, width = 0, height = 0, name, obi } = props;
  const none = obi === null || obi === undefined;
  const strength = none ? 0 : Math.round(20 + 60 * Math.min(1, Math.abs(obi)));
  const fill = none ? "var(--surface2)" : `color-mix(in srgb, ${obi >= 0 ? "var(--up)" : "var(--down)"} ${strength}%, var(--surface))`;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} style={{ fill }} stroke="var(--surface)" strokeWidth={2} />
      {width > 34 && height > 20 ? <text x={x + 5} y={y + 15} style={{ fontSize: 11, fontWeight: 600, fill: "var(--fg)" }}>{name}</text> : null}
    </g>
  );
}

export function Book({ p, f }: { p: Payload; f: Filters }) {
  const rows = useMemo(() => (p.book?.rows ?? []).filter((r) => symOk(r.symbol, f.sym)), [p.book, f.sym]);
  const [sortKey, setSortKey] = useState<BookKey>("liq_score");
  const [asc, setAsc] = useState(false);
  const [pick, setPick] = useState<string>("");
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
  if (!p.book || !p.book.rows.length) return <Empty>Chưa có dữ liệu sổ lệnh cho bộ lọc hiện tại.</Empty>;
  const cur = rows.find((r) => r.symbol === pick) ?? rows[0];
  const ser = cur ? p.book.series[cur.symbol] : undefined;
  const tree = rows.filter((r) => (r.total_value ?? 0) > 0).slice(0, 60).map((r) => ({ name: r.symbol, size: r.total_value as number, obi: r.obi3 }));
  const terms: Partial<Record<BookKey, string>> = { last: "price", pct_change: "price", obi3: "book", spread_bps: "spread", depth_value: "depth", total_value: "turnover", slippage_bps: "slippage", fill_ratio: "fill", liq_score: "liq_score" };
  const head = (label: string, key: BookKey) => (
    <th scope="col" className="text-right">
      <span className="inline-flex items-center"><button className="min-h-10 whitespace-nowrap px-2 py-1.5 text-right text-xs font-medium text-muted hover:text-fg" onClick={() => (key === sortKey ? setAsc(!asc) : (setSortKey(key), setAsc(false)))}>
        {label}{sortKey === key ? (asc ? " ▲" : " ▼") : ""}
      </button>{terms[key] ? <Term k={terms[key]} /> : null}</span>
    </th>
  );
  return (
    <div className="grid grid-cols-1 gap-3">
      <p className="text-sm leading-relaxed text-muted">Mua bán ngay có tốn chi phí không, và lệnh chờ đang lệch về phía nào? Các bảng dưới đây chỉ xét {p.meta.n_symbols_computed} mã đã ghi, tại mốc dữ liệu đầy đủ gần nhất. Lệnh chờ có thể bị hủy trước khi khớp.</p>
      <Card title="Bản đồ áp lực sổ lệnh">
        {tree.length ? (
          <div className="h-72 w-full" role="img" aria-label="Bản đồ nhiệt áp lực sổ lệnh theo mã">
            <ResponsiveContainer>
              <Treemap data={tree} dataKey="size" isAnimationActive={false} content={<TreemapCell />} />
            </ResponsiveContainer>
          </div>
        ) : <Empty>Chưa có mã nào có giá trị khớp.</Empty>}
        <Note>Diện tích = giá trị khớp trong phiên; màu = OBI₃ (xanh: bên mua dày hơn, đỏ: bên bán dày hơn) trên 3 mức giá tốt nhất.</Note>
      </Card>

      <Card title="Bảng thanh khoản & trượt giá">
        <div className="scroll-x max-h-96 overflow-y-auto">
          <table className="w-full min-w-[720px] border-collapse">
            <thead className="sticky top-0 bg-surface">
              <tr>
                <th scope="col" className="px-2 py-1.5 text-left text-xs font-medium text-muted">Mã</th>
                {head("Giá", "last")}{head("% đổi", "pct_change")}{head("OBI₃", "obi3")}{head("Spread (bps)", "spread_bps")}
                {head("Độ sâu 3 mức", "depth_value")}{head("Giá trị khớp", "total_value")}{head("Trượt giá (bps)", "slippage_bps")}
                {head("Tỷ lệ khớp", "fill_ratio")}{head("Điểm thanh khoản", "liq_score")}
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.symbol} className="border-t border-line">
                  <Td right={false} className="font-semibold"><CompanyLink symbol={r.symbol} /></Td>
                  <Td>{num(r.last, 0)}</Td><Td className={signTone(r.pct_change)}>{pct(r.pct_change)}</Td>
                  <Td className={signTone(r.obi3)}>{signed(r.obi3)}</Td><Td>{num(r.spread_bps, 1)}</Td>
                  <Td>{money(r.depth_value)}</Td><Td>{money(r.total_value)}</Td><Td>{num(r.slippage_bps, 1)}</Td>
                  <Td>{ratioPct(r.fill_ratio)}</Td><Td>{num(r.liq_score, 0)}</Td>
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

      {cur ? (
        <Card
          title="Chi tiết một mã"
          action={
            <select aria-label="Chọn mã" value={cur.symbol} onChange={(e) => setPick(e.target.value)} className="rounded-md border border-line bg-surface px-2 py-1 text-sm">
              {rows.map((r) => <option key={r.symbol}>{r.symbol}</option>)}
            </select>
          }
        >
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label={<Term k="book">OBI₃</Term>} value={signed(cur.obi3)} tone={signTone(cur.obi3)} sub={<Term k="microprice">Microprice lệch {signed(cur.micro_dev_bps, 1)} bps</Term>} />
            <Stat label={<Term k="spread">Spread</Term>} value={`${num(cur.spread_bps, 1)} bps`} sub={<Term k="pressure">Bán/Mua = {num(cur.pressure)}</Term>} />
            <Stat label={<Term k="slippage">Trượt giá (mua)</Term>} value={`${num(cur.slippage_bps, 1)} bps`} sub={<Term k="fill">Khớp {ratioPct(cur.fill_ratio)}</Term>} />
            <Stat label={<Term k="liq_score">Điểm thanh khoản</Term>} value={num(cur.liq_score, 0)} sub={<Term k="amihud">Amihud {num(cur.amihud)} bps/tỷ</Term>} />
          </div>
          {cur.auction ? <Note>Đang trong phiên định kỳ (ATO/ATC): giá mức 1 không phải giá giới hạn nên chỉ báo sổ lệnh có thể trống.</Note> : null}
          {ser && ser.t.length > 1 ? (
            <div className="mt-3 h-64 w-full" role="img" aria-label={`Giá giữa và mất cân bằng sổ lệnh (OBI₃) của ${cur.symbol}`}>
              <ResponsiveContainer>
                <ComposedChart data={ser.t.map((t, i) => ({ t, mid: ser.mid[i], obi3: ser.obi3[i] }))} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="t" minTickGap={40} />
                  <YAxis yAxisId="l" domain={["auto", "auto"]} width={52} tickFormatter={(v: number) => num(v, 0)} />
                  <YAxis yAxisId="r" orientation="right" domain={[-1, 1]} width={34} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar yAxisId="r" dataKey="obi3" name="OBI₃" isAnimationActive={false}>
                    {ser.t.map((_, i) => <Cell key={i} fill={(ser.obi3[i] ?? 0) >= 0 ? "var(--up)" : "var(--down)"} fillOpacity={0.4} />)}
                  </Bar>
                  <Line yAxisId="l" dataKey="mid" name="Giá giữa" stroke="var(--fg)" dot={false} strokeWidth={2} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          ) : <Note>Chuỗi theo phút chỉ có cho {Object.keys(p.book.series).length} mã có giá trị khớp lớn nhất.</Note>}
        </Card>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ Khối ngoại */
export function Foreign({ p, f }: { p: Payload; f: Filters }) {
  const all = p.foreign?.rows ?? [];
  const rows = all.filter((r) => symOk(r.symbol, f.sym));
  if (!all.length) return <Empty>Chưa có dữ liệu khối ngoại.</Empty>;
  const bars = [...rows].sort((a, b) => (a.net ?? 0) - (b.net ?? 0));
  const bar = [...bars.slice(0, 8), ...bars.slice(-8)].filter((r, i, a) => a.findIndex((x) => x.symbol === r.symbol) === i);
  const scatter = rows.filter((r) => r.participation !== null && r.net_ratio !== null).map((r) => ({ x: r.participation as number, y: r.net_ratio as number, z: r.total_value ?? 1, s: r.symbol }));
  return (
    <div className="grid grid-cols-1 gap-3">
      <div className="grid gap-3 lg:grid-cols-2">
        <Card title="Khối ngoại mua/bán ròng theo mã (lớn nhất mỗi phía)">
          <div className="h-[28rem] w-full" role="img" aria-label="Biểu đồ khối ngoại mua bán ròng theo mã">
            <ResponsiveContainer>
              <BarChart data={bar} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid {...gridProps} horizontal={false} vertical />
                <XAxis type="number" tickFormatter={(v: number) => money(v)} />
                <YAxis type="category" dataKey="symbol" width={44} interval={0} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => money(v)} />
                <ReferenceLine x={0} stroke="var(--muted)" />
                <Bar dataKey="net" name="Ròng (đồng)" isAnimationActive={false}>
                  {bar.map((r) => <Cell key={r.symbol} fill={(r.net ?? 0) >= 0 ? "var(--up)" : "var(--down)"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Chiều và quy mô">
          <div className="h-80 w-full" role="img" aria-label="Đồ thị tỷ trọng khối ngoại so với mức ròng trên tổng">
            <ResponsiveContainer>
              <ScatterChart margin={{ left: 0, right: 12, top: 8, bottom: 8 }}>
                <CartesianGrid {...gridProps} vertical />
                <XAxis type="number" dataKey="x" name="Tỷ trọng khối ngoại" tickFormatter={(v: number) => ratioPct(v)} domain={[0, "auto"]} />
                <YAxis type="number" dataKey="y" name="Ròng/tổng" domain={[-1, 1]} width={40} />
                <ZAxis type="number" dataKey="z" range={[40, 260]} />
                <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="3 3" />
                <Tooltip {...TOOLTIP_STYLE} cursor={{ strokeDasharray: "3 3" }} formatter={(v: number, n: string) => (n === "Tỷ trọng khối ngoại" ? ratioPct(v, 1) : num(v, 2))} labelFormatter={() => ""} />
                <Scatter data={scatter} fill="var(--accent)" fillOpacity={0.7} isAnimationActive={false} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        <Note><Term k="foreign">Tỷ trọng và ròng/tổng</Term>: góc trên-phải là mua ròng với mức tham gia lớn hơn. Gần trục dọc là tỷ trọng nhỏ; chưa đủ để suy ra tác động giá.</Note>
        </Card>
      </div>
      <Card title="Bảng khối ngoại">
        <div className="scroll-x max-h-96 overflow-y-auto">
          <table className="w-full min-w-[640px] border-collapse">
            <thead className="sticky top-0 bg-surface"><tr><Th right={false}>Mã</Th><Th><Term k="foreign">Khối ngoại mua</Term></Th><Th><Term k="foreign">Khối ngoại bán</Term></Th><Th><Term k="foreign">Ròng</Term></Th><Th><Term k="foreign">Ròng/tổng</Term></Th><Th><Term k="foreign">Tỷ trọng khối ngoại</Term></Th><Th><Term k="room">Room khối ngoại đã dùng</Term></Th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} className="border-t border-line">
                  <Td right={false} className="font-semibold"><CompanyLink symbol={r.symbol} /></Td><Td>{money(r.buy)}</Td><Td>{money(r.sell)}</Td>
                  <Td><SignedMoney value={r.net} /></Td><Td>{signed(r.net_ratio)}</Td><Td>{ratioPct(r.participation)}</Td><Td>{ratioPct(r.room_used)}</Td>
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
export function Futures({ p }: { p: Payload }) {
  const fu = p.futures;
  if (!fu || !fu.available || !fu.state) {
    return <Empty>Chưa có dữ liệu hợp đồng tương lai khớp được với chỉ số VN30 trong phiên này. Chênh lệch cơ sở chỉ tính khi chọn chỉ số VN30 và bộ ghi có nhận dữ liệu hợp đồng tương lai.</Empty>;
  }
  const s = fu.state;
  return (
    <div className="grid grid-cols-1 gap-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={s.symbol ?? "HĐTL"} value={num(fu.future ?? null, 1)} sub={`cơ sở ${num(fu.spot ?? null, 2)}`} />
        <Stat label={<Term k="basis">Chênh lệch cơ sở</Term>} value={`${signed(s.basis)} điểm`} sub={pct(s.basis_pct)} tone={signTone(s.basis)} />
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
              <Area dataKey="basis" name="Chênh lệch cơ sở (điểm)" stroke="var(--warn)" fill="var(--warn)" fillOpacity={0.2} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <Note>Chênh lệch cơ sở thường tiến về mức thanh toán khi gần đáo hạn; các ảnh chụp nội phiên không bảo đảm chênh lệch bằng 0. Giá trị hợp lý dùng lãi suất giả định 4,5%/năm và cổ tức bằng 0. Dấu của chênh lệch cơ sở còn phản ánh chi phí vốn và cổ tức; không tự cho biết hướng giá tiếp theo.</Note>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Cảnh báo */
export function Alerts({ p, f }: { p: Payload; f: Filters }) {
  const al = p.alerts;
  const [rule, setRule] = useState("");
  if (!al || al.total === 0) return <Empty>Không có cảnh báo nào trong phiên.</Empty>;
  const items = al.items.filter((a) => sevOk(a.severity, f.minSev) && symOk(a.symbol, f.sym) && (!rule || a.rule === rule));
  return (
    <div className="grid grid-cols-1 gap-3">
      <div className="grid grid-cols-3 gap-3">
        {SEV_ORDER.map((s) => <Stat key={s} label={`${s === "CAO" ? "◆" : s === "TRUNG BÌNH" ? "◇" : "·"} ${s === "CAO" ? "Cao" : s === "TRUNG BÌNH" ? "Trung bình" : "Thấp"}`} value={al.by_severity[s] ?? 0} tone={s === "THẤP" ? "text-muted" : "text-fg"} />)}
      </div>
      <Card
        title={`${items.length} / ${al.total} cảnh báo`}
        action={
          <select aria-label="Lọc loại cảnh báo" value={rule} onChange={(e) => setRule(e.target.value)} className="max-w-[55%] rounded-md border border-line bg-surface px-2 py-1 text-sm">
            <option value="">Mọi loại</option>
            {Object.entries(al.rule_names).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        }
      >
        {items.length ? <ul>{items.map((a, i) => <AlertRow key={`${a.t}-${a.symbol}-${a.rule}-${i}`} a={a} />)}</ul> : <Empty>Không có cảnh báo khớp bộ lọc.</Empty>}
        {al.items.length < al.total ? <Note>Chỉ hiển thị {al.items.length} cảnh báo ưu tiên cao nhất trong số {al.total}.</Note> : null}
        <Note>Đây là số lượt cảnh báo, không phải số mã. Mỗi quy tắc có điều kiện riêng: <Term k="rvol">khối lượng tương đối</Term>, <Term k="anomaly">điểm z trong phiên</Term>, <Term k="book">mất cân bằng sổ lệnh</Term> hoặc <Term k="band">sát trần/sàn</Term>. Cảnh báo không xác nhận nguyên nhân và không phải khuyến nghị.</Note>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Xếp hạng */
function zCell(v: number | null) {
  if (v === null) return { background: "transparent" };
  const a = Math.min(1, Math.abs(v) / 3) * 0.55;
  return { background: `color-mix(in srgb, ${v >= 0 ? "var(--up)" : "var(--down)"} ${Math.round(a * 100)}%, transparent)` };
}
export function Ranking({ p, f }: { p: Payload; f: Filters }) {
  const all = p.ranking ?? [];
  const rows = all.filter((r) => symOk(r.symbol, f.sym));
  if (!all.length) return <Empty>Chưa có dữ liệu để xếp hạng.</Empty>;
  const zs: [string, string][] = [["momentum", "Động lượng"], ["flow", "Sổ lệnh"], ["foreign", "Khối ngoại"], ["liquidity", "Thanh khoản"], ["cost", "Chi phí"]];
  return (
    <Card title={<Term k="ranking">Xếp hạng đa yếu tố trong rổ</Term>}>
      <Note>Điểm = tổng có trọng số của z-score mặt cắt ngang (động lượng 30%, sổ lệnh 25%, khối ngoại 20%, thanh khoản 15%, chi phí 10%). Chỉ có nghĩa tương đối trong rổ, tại thời điểm tính.</Note>
      <div className="scroll-x mt-2 max-h-[34rem] overflow-y-auto">
        <table className="w-full min-w-[820px] border-collapse">
          <thead className="sticky top-0 bg-surface">
            <tr><Th>Hạng</Th><Th right={false}>Mã</Th><Th><Term k="ranking">Điểm</Term></Th><Th><Term k="price">Giá</Term></Th><Th>% đổi</Th><Th><Term k="book">OBI₃</Term></Th><Th><Term k="foreign">Khối ngoại ròng/tổng</Term></Th><Th><Term k="spread">Spread</Term></Th>{zs.map(([, n]) => <Th key={n}><Term k="ranking">z {n}</Term></Th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol} className="border-t border-line">
                <Td>{r.rank}</Td><Td right={false} className="font-semibold"><CompanyLink symbol={r.symbol} /></Td><Td>{num(r.score)}</Td><Td>{num(r.last, 0)}</Td>
                <Td className={signTone(r.pct_change)}>{pct(r.pct_change)}</Td><Td>{signed(r.obi3)}</Td><Td>{signed(r.net_ratio)}</Td><Td>{num(r.spread_bps, 1)}</Td>
                {zs.map(([k]) => <Td key={k}><span className="block rounded px-1" style={zCell(r.z[k] ?? null)}>{signed(r.z[k] ?? null, 1)}</span></Td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
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
    <div className="grid grid-cols-1 gap-3">
      <Card title="Kiểm chứng trên dữ liệu đã thu thập">
        <p className="text-sm leading-relaxed">Hệ thống kiểm tra tín hiệu sổ lệnh có liên hệ với thay đổi giá sau đó hay không, đồng thời thống kê dữ liệu thiếu và gián đoạn. Kết quả được tính lại khoảng 10 phút một lần, tách khỏi luồng cập nhật giá.</p>
        {v.generated_at ? <p className="mt-2 text-xs text-muted">Tính lúc {dmyTime(v.generated_at)}{v.data_until ? ` · Dữ liệu đến ${dmyTime(v.data_until)}` : ""} (giờ Việt Nam).</p> : null}
        {dq.n_sessions < 5 ? <p className="mt-3 rounded-lg bg-surface2 p-3 text-sm">Mới ghi nhận {dq.n_sessions} phiên. Kết quả hiện chỉ để tham khảo; cần thu thập thêm phiên trước khi đánh giá độ ổn định của tín hiệu.</p> : null}
      </Card>
      {v.simulated_signals_are_planted ? (
        <div role="note" className="rounded-xl border border-sim/40 bg-sim/10 p-3 text-sm text-sim">
          Trên dữ liệu MÔ PHỎNG, tín hiệu sổ lệnh được <b>cài sẵn</b> vào cơ chế sinh giá. Kết quả dưới đây chỉ xác nhận đường ống tính toán chạy đúng — <b>không</b> phải bằng chứng về thị trường thật.
        </div>
      ) : null}
      <Card title="Tín hiệu sổ lệnh có đi trước biến động giá?">
        <Note><Term k="sample">Trong mẫu: {v.ic.train.join(", ") || dash} · Ngoài mẫu: {v.ic.test.join(", ") || dash}</Term></Note>
        {v.ic.note ? <p className="mt-2 rounded-md bg-surface2 p-2 text-sm">{v.ic.note}</p> : null}
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
          <ul className="mt-1 text-sm">{Object.entries(dq.issues).map(([k, n]) => <li key={k} className="flex justify-between border-b border-line py-1"><span>{k}</span><span className="tnum">{n}</span></li>)}</ul>
        ) : <p className="text-sm text-muted">Không có.</p>}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Phương pháp */
export function Method() {
  return (
    <div className="grid grid-cols-1 gap-3">
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
                ["Chênh lệch cơ sở", "F − S; quy năm (F/S − 1)·365/ngày còn lại", "định giá HĐTL so với cơ sở"],
                ["z bền vững", "0,6745·(x − median)/MAD, cửa sổ 60 thanh trước", "bất thường khi |z| ≥ 3,5"],
                ["Điểm nhịp", "50 + 50·Σwᵢcᵢ; w = 30/25/20/15/10%", "trạng thái tổng hợp 0–100"],
              ].map(([a, b, c]) => (
                <tr key={a} className="border-t border-line"><td className="px-2 py-1.5 font-medium">{a}</td><td className="px-2 py-1.5">{b}</td><td className="px-2 py-1.5 text-muted">{c}</td></tr>
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
        <p className="mt-3 rounded-md bg-surface2 p-2 text-sm font-medium">Đây là công cụ phân tích học thuật, không phải lời khuyên đầu tư.</p>
        <p className="mt-3 text-sm"><a href="https://github.com/thienanpham160806-code/neopulse-radar/blob/main/docs/market-design-references.md" target="_blank" rel="noreferrer" className="text-accent underline underline-offset-4">Nguồn tham khảo thiết kế và cách áp dụng trong dự án ↗</a></p>
      </Card>
    </div>
  );
}

