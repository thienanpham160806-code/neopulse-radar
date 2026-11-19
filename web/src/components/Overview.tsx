"use client";

/**
 * Tổng quan theo hướng B "Bản tin" (đã chọn 19/11/2026): tiêu đề trả lời "khỏe hay yếu", câu dẫn, Hình 1 có chú thích,
 * các mục kể chuyện; cột phụ (desktop) có bảng chỉ số + cảnh báo. Trên điện thoại (ghép C): dải chỉ số và cảnh báo lên đầu.
 * Mọi số do Python tính; ở đây chỉ chọn số trực tiếp (nếu có, đúng nguồn/chỉ số) hay số snapshot để hiển thị.
 */
import dynamic from "next/dynamic";
import { isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { hm, num, ratioPct, signed } from "@/lib/format";
import { mergeSeries, type LiveState } from "@/lib/live";
import type { AlertItem, Num, Payload, Severity } from "@/lib/types";
import { SectorCard } from "./SectorCard";
import { type Filters } from "./tabs";
import { Change, Note, ScoreScale, SevTag, SignedMoney } from "./ui";

// Recharts tải lười: không chặn lần vẽ đầu (Lighthouse TBT)
const IndexChart = dynamic(() => import("./IndexChart"), {
  ssr: false, loading: () => <div className="h-64 animate-pulse rounded bg-surface2" aria-hidden />,
});

const SEV_ORDER: Severity[] = ["CAO", "TRUNG BÌNH", "THẤP"];
const ORDER = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"];
interface Ix { code: string; v: Num; ch: Num; pct: Num; adv: Num; dec: Num; nc: Num }

function IndexList({ rows, compact = false }: { rows: Ix[]; compact?: boolean }) {
  return (
    <dl className={compact ? "grid grid-cols-2 gap-x-4 gap-y-2" : "divide-y divide-line"}>
      {rows.map((x) => {
        const dir = (x.ch ?? 0) > 0 ? "up" : (x.ch ?? 0) < 0 ? "down" : "flat";
        return (
          <div key={x.code} className={compact ? "" : "flex items-baseline justify-between py-2"}>
            <dt className="text-sm font-semibold">{x.code}</dt>
            <dd className={compact ? "" : "text-right"}>
              <span key={`${x.v}`} className={`tnum rounded px-0.5 text-lg font-semibold ${TONE_CLASS[priceTone(x.ch)]} flash-${dir}`}>{num(x.v)}</span>
              <br /><Change value={x.pct} className="text-sm" />
              {!compact && isNum(x.adv) ? (
                <span className="tnum ml-2 text-xs text-muted"><span className="text-up">▲{num(x.adv, 0)}</span> <span className="text-refc">■{num(x.nc, 0)}</span> <span className="text-down">▼{num(x.dec, 0)}</span></span>
              ) : null}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

function AlertList({ items, limit }: { items: AlertItem[]; limit: number }) {
  if (!items.length) return <p className="text-sm text-muted">Chưa có cảnh báo ở mức đang lọc.</p>;
  return (
    <ul className="divide-y divide-line">
      {items.slice(0, limit).map((a, i) => (
        <li key={`${a.t}${a.symbol}${a.rule}${i}`} className="flex items-start gap-2 py-2">
          <time className="tnum w-11 shrink-0 pt-0.5 text-sm text-muted">{a.t.slice(11, 16)}</time>
          <div className="min-w-0 flex-1 text-sm"><b>{a.symbol}</b> · {a.rule_name}<div className="text-xs text-muted">{a.message}</div></div>
          <SevTag sev={a.severity} />
        </li>
      ))}
    </ul>
  );
}

export function Overview({ p, f, live, onAlerts }: { p: Payload; f: Filters; live?: LiveState | null; onAlerts?: () => void }) {
  const code = p.index?.code ?? p.meta.index_code;
  const lp = live?.pulse && live.pulse.index_code === code ? live.pulse : null;
  const score = lp ? lp.score : p.pulse?.score ?? null;
  const label = lp ? lp.label : p.pulse?.label ?? "Không đủ dữ liệu";
  const comps = lp ? lp.comps.map((c) => ({ key: c.k, name: c.n, weight: c.w, value: c.v })) : p.pulse?.components ?? [];
  const row = p.index?.row;
  const ixs: Ix[] = live?.tick
    ? ORDER.filter((c) => live.tick?.ix[c]).map((c) => ({ code: c, ...live.tick!.ix[c] }))
    : row ? [{ code, v: row.value, ch: row.change, pct: row.pct_change, adv: row.advances, dec: row.declines, nc: row.no_change }] : [];
  const liveAlerts: AlertItem[] = (lp ? live?.alerts ?? [] : []).map((a) => ({ t: a.t, symbol: a.s, rule: a.rule,
    rule_name: p.alerts?.rule_names[a.rule] ?? a.rule, severity: a.sev, message: a.msg, value: null, threshold: null }));
  const alerts = [...liveAlerts, ...(p.alerts?.items ?? [])]
    .filter((a) => SEV_ORDER.indexOf(a.severity) <= SEV_ORDER.indexOf(f.minSev) && (!f.sym || a.symbol.includes(f.sym.toUpperCase())));
  const summary = p.pulse?.summary ?? [];
  const dek = live?.tick && ixs.length
    ? `${ixs.map((x) => `${x.code} ${num(x.v)} (${signed(x.pct)}%)`).join(" · ")}. Điểm nhịp cập nhật khoảng 10 giây một lần.`
    : summary[1] ?? summary[0] ?? "Chưa có nhận định.";
  const pts = live?.points[code] ?? [];
  const series = (pts.length ? mergeSeries((p.pulse?.series ?? []).map((r) => ({ t: r.t, value: r.index })), pts)
    : (p.pulse?.series ?? []).filter((r) => r.index !== null).map((r) => ({ t: r.t, v: r.index as number })))
    .map((q) => ({ t: hm(q.t), v: q.v }));
  const ref = row?.ref ?? null;
  const fs = p.foreign?.summary;

  return (
    <article className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        {/* điện thoại: chỉ số + cảnh báo lên đầu (ưu tiên 2-3), trước phần kể chuyện */}
        <div className="mb-6 space-y-4 lg:hidden">
          {ixs.length ? <section aria-label="Chỉ số"><IndexList rows={ixs} compact /></section> : null}
          <section aria-labelledby="m-alerts">
            <div className="flex items-baseline justify-between"><h2 id="m-alerts" className="text-base font-bold">Cảnh báo mới nhất</h2>
              <button onClick={onAlerts} className="min-h-10 text-sm text-accent underline underline-offset-4">Xem tất cả</button></div>
            <AlertList items={alerts} limit={3} />
          </section>
        </div>

        <h2 className="text-[clamp(1.6rem,4.5vw,2.6rem)] font-bold leading-tight tracking-tight [text-wrap:balance]">
          Thị trường {label.toLowerCase()}: điểm nhịp <span className="tnum">{num(score, 1)}</span>/100
        </h2>
        <p className="mt-3 max-w-[68ch] text-lg leading-relaxed text-muted">{dek}</p>
        <div className="mt-5 max-w-md"><ScoreScale score={score} /></div>
        {!lp && p.pulse?.sensitivity && isNum(p.pulse.sensitivity.p05) ? (
          <Note>Đổi mỗi trọng số ±50%: điểm dao động {num(p.pulse.sensitivity.p05, 1)}–{num(p.pulse.sensitivity.p95, 1)}, nhãn giữ nguyên trong {ratioPct(p.pulse.sensitivity.label_stability)} số lần thử. Điểm mô tả hiện trạng, không dự báo.</Note>
        ) : null}
        {p.pulse?.divergence ? <p className="mt-4 max-w-[68ch] border-l-0 bg-surface2 p-3 text-sm"><b>Phân kỳ chỉ số – độ rộng:</b> {p.pulse.divergence}</p> : null}

        <figure className="mt-6">
          {series.length > 1 ? (
            <IndexChart data={series} code={code} refValue={ref} />
          ) : <p className="text-sm text-muted">Chưa đủ điểm dữ liệu để vẽ.</p>}
          <figcaption className="mt-1 border-t border-line pt-1 text-sm text-muted">
            <b className="text-fg">Hình 1.</b> {code} trong phiên theo phút{isNum(ref) ? ", đường đứt màu vàng là giá tham chiếu" : ""}.
            {live?.tick ? " Điểm cuối cập nhật trực tiếp." : ""}
          </figcaption>
        </figure>

        <h3 className="mt-8 text-xl font-bold">Ngành nào kéo, ngành nào đè</h3>
        <div className="mt-2"><SectorCard sectors={p.sectors} live={lp?.sec ?? null} indexCode={code} /></div>

        <h3 className="mt-8 text-xl font-bold">Vì sao điểm nhịp như vậy</h3>
        <ul className="mt-2 max-w-xl divide-y divide-line">
          {comps.map((c) => {
            const tone = priceTone(c.value);
            return (
              <li key={c.key} className="flex items-baseline justify-between py-1.5">
                <span>{c.name} <span className="text-sm text-muted">· trọng số {Math.round(c.weight * 100)}%</span></span>
                <span className={`tnum ${TONE_CLASS[tone]}`}><span aria-hidden>{TONE_MARK[tone]} </span>{signed(c.value)}</span>
              </li>
            );
          })}
        </ul>
        <Note>Mỗi thành phần nằm trong [−1; 1]; dương là nghiêng tích cực. Công thức ở mục Phương pháp & giới hạn.</Note>

        {summary.length ? (
          <>
            <h3 className="mt-8 text-xl font-bold">Nhận định từ số liệu{lp ? " (theo ảnh chụp gần nhất)" : ""}</h3>
            <ul className="mt-2 max-w-[68ch] list-disc space-y-1.5 pl-5">{summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
            <Note>Câu chữ dựng từ mẫu câu gắn với số liệu, không phải dự báo hay khuyến nghị.</Note>
          </>
        ) : null}
      </div>

      <aside className="hidden space-y-6 lg:block lg:border-l lg:border-line lg:pl-6">
        <section aria-labelledby="a-ix"><h2 id="a-ix" className="text-sm font-bold uppercase tracking-wide">Bảng chỉ số</h2><IndexList rows={ixs} /></section>
        <section aria-labelledby="a-al">
          <div className="flex items-baseline justify-between"><h2 id="a-al" className="text-sm font-bold uppercase tracking-wide">Cảnh báo mới nhất</h2>
            <button onClick={onAlerts} className="min-h-10 text-sm text-accent underline underline-offset-4">Xem tất cả</button></div>
          <AlertList items={alerts} limit={6} />
        </section>
        <section aria-labelledby="a-fn">
          <h2 id="a-fn" className="text-sm font-bold uppercase tracking-wide">Khối ngoại trong rổ</h2>
          <p className="mt-1 text-xl font-semibold"><SignedMoney value={fs?.net_val ?? null} /></p>
          <p className="text-sm text-muted">{num(fs?.n_net_buy ?? null, 0)} mã mua ròng · {num(fs?.n_net_sell ?? null, 0)} mã bán ròng</p>
        </section>
      </aside>
    </article>
  );
}
