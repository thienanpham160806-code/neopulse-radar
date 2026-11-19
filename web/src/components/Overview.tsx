"use client";

/**
 * Tổng quan theo hướng B "Bản tin", ghép mobile kiểu C. Mở đầu bằng đồng hồ điểm nhịp + luận giải bằng lời thường
 * ("Hôm nay nghĩa là gì?"), sau đó mới tới biểu đồ, ngành và chi tiết. Mọi số do Python tính; web chỉ chọn câu
 * diễn giải theo dấu/độ lớn và hiển thị.
 */

import { useMemo } from "react";
import { isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { num, ratioPct, signed } from "@/lib/format";
import { mergeSeries, type LiveState } from "@/lib/live";
import { alertDigest, componentMeaning, GLOSSARY, missingComponents, RULE_PLAIN, scoreMeaning } from "@/lib/plain";
import type { AlertItem, Num, Payload, Severity } from "@/lib/types";
import { Gauge, Guide, Term } from "./Explain";
import { SectorCard } from "./SectorCard";
import { CompanyLink } from "./CompanyLink";
import { TechnicalChart } from "./TechnicalChart";
import { type Filters } from "./tabs";
import { Change, Note, SevTag, SignedMoney } from "./ui";

const SEV_ORDER: Severity[] = ["CAO", "TRUNG BÌNH", "THẤP"];
const ORDER = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"];
interface Ix { code: string; v: Num; ch: Num; pct: Num; adv: Num; dec: Num; nc: Num }

function IndexList({ rows, compact = false }: { rows: Ix[]; compact?: boolean }) {
  return (
    <dl className={compact ? "grid grid-cols-2 gap-x-4 gap-y-3" : "divide-y divide-line"}>
      {rows.map((x) => {
        const dir = (x.ch ?? 0) > 0 ? "up" : (x.ch ?? 0) < 0 ? "down" : "flat";
        return (
          <div key={x.code} className={compact ? "rounded-lg bg-surface p-3" : "flex items-baseline justify-between py-2"}>
            <dt className="text-sm font-semibold">{x.code}</dt>
            <dd className={compact ? "" : "text-right"}>
              <span key={`${x.v}`} className={`tnum rounded px-0.5 text-lg font-semibold ${TONE_CLASS[priceTone(x.ch)]} flash-${dir}`}>{num(x.v)}</span>
              <br /><Change value={x.pct} className="text-sm" />
              {isNum(x.adv) ? (
                <span className="tnum ml-2 text-xs text-muted" title="số mã tăng / đứng giá / giảm">
                  <span className="text-up">▲{num(x.adv, 0)}</span> <span className="text-refc">■{num(x.nc, 0)}</span> <span className="text-down">▼{num(x.dec, 0)}</span>
                </span>
              ) : null}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

/** Cảnh báo bằng lời thường; số thống kê (z, RVOL, ngưỡng) mở trong phần chi tiết. */
function AlertList({ items, limit }: { items: AlertItem[]; limit: number }) {
  if (!items.length) return <p className="py-2 text-sm text-muted">Chưa có điều gì bất thường ở mức đang lọc.</p>;
  return (
    <ul className="divide-y divide-line">
      {items.slice(0, limit).map((a, i) => (
        <li key={`${a.t}${a.symbol}${a.rule}${i}`}>
          <details className="group py-2">
            <summary className="flex cursor-pointer list-none items-start gap-2">
              <time className="tnum w-11 shrink-0 pt-0.5 text-sm text-muted">{a.t.slice(11, 16)}</time>
              <span className="min-w-0 flex-1 text-sm"><CompanyLink symbol={a.symbol} />: {RULE_PLAIN[a.rule] ?? a.rule_name}
                <span className="ml-1 text-xs text-accent group-open:hidden">· chi tiết</span></span>
              <SevTag sev={a.severity} />
            </summary>
            <p className="mt-1 pl-[3.25rem] text-xs text-muted">{a.message}. Cảnh báo là tín hiệu đáng xem, không phải khuyến nghị mua bán.</p>
            <p className="mt-2 pl-[3.25rem] text-sm"><CompanyLink symbol={a.symbol}>Tìm hiểu doanh nghiệp {a.symbol} →</CompanyLink></p>
          </details>
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
  const { items: allAlerts, nHigh, hot } = alertDigest(liveAlerts, p.alerts?.items ?? [], p.alerts?.by_severity?.CAO, p.meta.last_update);
  const alerts = allAlerts.filter((a) => SEV_ORDER.indexOf(a.severity) <= SEV_ORDER.indexOf(f.minSev)
    && (!f.sym || a.symbol.includes(f.sym.toUpperCase())));
  const summary = p.pulse?.summary ?? [];
  const baseSeries = p.pulse?.series;
  const livePoints = live?.points[code];
  const series = useMemo(() => mergeSeries((baseSeries ?? []).map((r) => ({ t: r.t, value: r.index })), livePoints ?? [])
    .map((q) => ({ time: q.t, value: q.v })), [baseSeries, livePoints]);
  const fs = p.foreign?.summary;

  // "Vì sao": hai thành phần ảnh hưởng nhiều nhất (|giá trị| x trọng số, cả hai do Python cho)
  const drivers = comps.filter((c) => isNum(c.value))
    .sort((a, b) => Math.abs((b.value as number) * b.weight) - Math.abs((a.value as number) * a.weight)).slice(0, 2);
  const missing = missingComponents(comps);
  const ix0 = ixs.find((x) => x.code === code) ?? ixs[0];

  return (
    <div>
      <Guide />

      {/* Phần đầu: đồng hồ (điểm nhấn) + luận giải bằng lời thường */}
      <section aria-labelledby="hero-title" className="grid grid-cols-1 items-center gap-6 rounded-2xl border border-line bg-surface p-4 sm:p-6 md:grid-cols-[1fr_240px]">
        <div className="order-2 border-t border-line pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
          <div className="mb-1 flex justify-center text-sm text-muted"><Term k="pulse">Điểm nhịp thị trường</Term></div>
          <Gauge score={score} label={label} />
          {!lp && p.pulse?.sensitivity && isNum(p.pulse.sensitivity.p05) ? (
            <p className="mt-1 text-center text-xs text-muted">Đổi trọng số ±50%: điểm trong khoảng {num(p.pulse.sensitivity.p05, 1)}–{num(p.pulse.sensitivity.p95, 1)}, nhãn giữ nguyên {ratioPct(p.pulse.sensitivity.label_stability)} số lần.</p>
          ) : null}
        </div>
        <div className="order-1 min-w-0">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted">Toàn cảnh phiên · {code}</p>
          <h2 id="hero-title" className="text-[clamp(1.5rem,3.6vw,2.3rem)] font-bold leading-tight tracking-tight [text-wrap:balance]">
            Thị trường {label.toLowerCase()}
          </h2>
          {ix0 ? (
            <p className="mt-1 text-base text-muted">{ix0.code} <b className={`tnum ${TONE_CLASS[priceTone(ix0.ch)]}`}>{num(ix0.v)}</b> <Change value={ix0.pct} />
              {isNum(ix0.adv) ? ` · ${num(ix0.adv, 0)} mã tăng, ${num(ix0.dec, 0)} mã giảm` : ""}</p>
          ) : null}
          <h3 className="mt-4 text-sm font-bold uppercase tracking-wide">Hôm nay nghĩa là gì?</h3>
          <ul className="mt-2 space-y-2 text-base leading-relaxed">
            <li><b>Trạng thái.</b> {scoreMeaning(score)}</li>
            {drivers.length ? <li><b>Vì sao.</b> {drivers.map((c) => componentMeaning(c.key, c.value).replace(/\.$/, "")).join("; ")}.
              {missing.length ? <span className="text-muted"> Chưa có dữ liệu: {missing.join(", ")}; điểm chỉ tính trên các thành phần còn lại.</span> : null}</li> : null}
            <li><b>Cần để ý.</b> {p.pulse?.divergence ? `${p.pulse.divergence} ` : ""}{nHigh
              ? <>{nHigh} cảnh báo mức cao trong phiên{hot.length ? `; trong danh sách hiện có, tập trung ở ${hot.join(", ")}` : ""}.{" "}
                <button onClick={onAlerts} className="text-accent underline underline-offset-4">Xem cảnh báo</button></>
              : "Chưa có cảnh báo mức cao."}</li>
          </ul>
        </div>
      </section>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          {/* điện thoại: chỉ số + cảnh báo trước phần chi tiết */}
          <div className="mb-8 space-y-4 lg:hidden">
            {ixs.length ? <section aria-label="Chỉ số"><IndexList rows={ixs} compact /></section> : null}
            <section aria-labelledby="m-alerts">
              <div className="flex items-baseline justify-between"><h2 id="m-alerts" className="text-base font-bold">Điều gì bất thường</h2>
                <button onClick={onAlerts} className="min-h-10 text-sm text-accent underline underline-offset-4">Xem tất cả</button></div>
              <AlertList items={alerts} limit={3} />
            </section>
          </div>

          <h3 className="text-xl font-bold">Chỉ số đi thế nào trong phiên</h3>
          <figure className="mt-2">
            {series.length > 1 ? <TechnicalChart key={code} symbol={code} intraday={series} intradayChart={p.chart} reference={row?.ref} /> : <p className="text-sm text-muted">Chưa đủ điểm dữ liệu để vẽ.</p>}
            <figcaption className="mt-1 border-t border-line pt-1 text-sm text-muted">
              <b className="text-fg">Hình 1.</b> {code}: khung Phiên dùng dữ liệu nội phiên đã ghi; các khung còn lại dùng giá đóng cửa ngày từ Vietcap. Rê chuột hoặc chạm để xem từng điểm; cuộn để thu phóng.
            </figcaption>
          </figure>


          <h3 className="mt-10 text-xl font-bold"><Term k="sector">Ngành nào kéo, ngành nào đè</Term></h3>
          <p className="mt-1 text-sm text-muted">Chạm vào một ngành để xem các mã trong ngành.</p>
          <div className="mt-2"><SectorCard sectors={p.sectors} live={lp?.sec ?? null} indexCode={code} /></div>

          <h3 className="mt-10 text-xl font-bold">Năm thành phần của điểm nhịp</h3>
          <p className="mt-1 text-sm text-muted">Mỗi thành phần từ −1 (rất tiêu cực) đến +1 (rất tích cực). Chạm để xem nó đo gì.</p>
          <ul className="mt-2 divide-y divide-line rounded-xl border border-line bg-surface">
            {comps.map((c) => {
              const tone = priceTone(c.value);
              return (
                <li key={c.key}>
                  <details className="px-3 py-2.5">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                      <span className="min-w-0"><b>{c.name}</b> <span className="text-sm text-muted">· trọng số {Math.round(c.weight * 100)}%</span>
                        <span className="block text-sm text-muted">{componentMeaning(c.key, c.value)}</span></span>
                      <span className={`tnum shrink-0 text-lg font-semibold ${TONE_CLASS[tone]}`}><span aria-hidden>{TONE_MARK[tone]} </span>{signed(c.value)}</span>
                    </summary>
                    <p className="mt-2 text-sm">{GLOSSARY[c.key]?.body}</p>
                  </details>
                </li>
              );
            })}
          </ul>

          {summary.length ? (
            <details className="mt-8 rounded-xl border border-line bg-surface p-3">
              <summary className="cursor-pointer font-semibold">Bản tóm tắt số liệu đầy đủ{lp ? " (theo ảnh chụp gần nhất)" : ""}</summary>
              <ul className="mt-2 max-w-[68ch] list-disc space-y-1.5 pl-5">{summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <Note>Câu chữ dựng từ mẫu câu gắn với số liệu, không phải dự báo hay khuyến nghị.</Note>
            </details>
          ) : null}
        </div>

        <aside className="hidden space-y-8 lg:block lg:border-l lg:border-line lg:pl-6">
          <section aria-labelledby="a-ix"><h2 id="a-ix" className="text-sm font-bold uppercase tracking-wide">Bảng chỉ số</h2><IndexList rows={ixs} /></section>
          <section aria-labelledby="a-al">
            <div className="flex items-baseline justify-between"><h2 id="a-al" className="text-sm font-bold uppercase tracking-wide">Điều gì bất thường</h2>
              <button onClick={onAlerts} className="min-h-10 text-sm text-accent underline underline-offset-4">Xem tất cả</button></div>
            <AlertList items={alerts} limit={6} />
          </section>
          <section aria-labelledby="a-fn">
            <h2 id="a-fn" className="text-sm font-bold uppercase tracking-wide"><Term k="foreign">Khối ngoại trong rổ</Term></h2>
            <p className="mt-1 text-2xl font-semibold"><SignedMoney value={fs?.net_val ?? null} /></p>
            <p className="text-sm text-muted">{(fs?.net_val ?? 0) >= 0 ? "Mua ròng" : "Bán ròng"} · {num(fs?.n_net_buy ?? null, 0)} mã mua ròng, {num(fs?.n_net_sell ?? null, 0)} mã bán ròng</p>
          </section>
        </aside>
      </div>
    </div>
  );
}
