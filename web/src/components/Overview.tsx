"use client";

/** Observations → evidence → anomalies → chart → validation. Financial metrics come from Python. */

import { useMemo } from "react";
import { dmyTime, isNum, priceTone, TONE_CLASS } from "@/lib/fmt";
import { num, ratioPct } from "@/lib/format";
import { mergeSeries, type LiveState } from "@/lib/live";
import { alertDigest, componentMeaning, marketSummary, missingComponents, RULE_PLAIN, scoreMeaning } from "@/lib/plain";
import type { AlertItem, Num, Payload, Severity } from "@/lib/types";
import { Gauge, Guide, Term } from "./Explain";
import { SectorCard } from "./SectorCard";
import { CompanyLink } from "./CompanyLink";
import { TechnicalChart } from "./TechnicalChart";
import { type Filters } from "./tabs";
import { Change, Note, SevTag, SignedMoney } from "./ui";
import { AlertDetail } from "./AlertDetail";
import { ComponentCoverage, MarketEvidence, ValidationSummary } from "./MarketEvidence";

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
            <div className="pl-[3.25rem]"><AlertDetail a={a} /></div>
            <p className="mt-2 pl-[3.25rem] text-sm"><CompanyLink symbol={a.symbol}>Tìm hiểu doanh nghiệp {a.symbol} →</CompanyLink></p>
          </details>
        </li>
      ))}
    </ul>
  );
}

export function Overview({ p, f, live, onNavigate }: { p: Payload; f: Filters; live?: LiveState | null; onNavigate: (tab: string) => void }) {
  const onAlerts = () => onNavigate("canh-bao");
  const code = p.index?.code ?? p.meta.index_code;
  const lp = live?.pulse && live.pulse.index_code === code ? live.pulse : null;
  const score = lp ? lp.score : p.pulse?.score ?? null;
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
  const ix0 = ixs.find((x) => x.code === code);

  return (
    <div>
      <Guide />

      <p className="mb-4 text-sm leading-relaxed text-muted"><b className="text-fg">Phạm vi đang đọc:</b> chỉ số và số mã tăng/giảm của {code}; sổ lệnh, khối ngoại trên {p.meta.n_symbols_computed} mã được ghi. {live ? "Giá và điểm nhịp đang nhận cập nhật nhanh; bảng chi tiết theo bản dữ liệu đầy đủ gần nhất. " : "Nhận định theo mốc dữ liệu đã nhận, không suy ra diễn biến sau mốc này. "}
        Bản đầy đủ đến {p.meta.last_update ? dmyTime(p.meta.last_update) : "chưa xác định"} (giờ Việt Nam).</p>

      {/* Phần đầu: đồng hồ (điểm nhấn) + luận giải bằng lời thường */}
      <section aria-labelledby="hero-title" className="grid grid-cols-1 items-center gap-6 rounded-2xl border border-line bg-surface p-4 sm:p-6 md:grid-cols-[1fr_240px]">
        <div className="order-2 border-t border-line pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
          <div className="mb-1 flex justify-center text-sm text-muted"><Term k="pulse">Điểm nhịp thị trường</Term></div>
          <Gauge score={score} label={scoreMeaning(score).replace(/\.$/, "")} />
          <ComponentCoverage comps={comps} />
          {!lp && p.pulse?.sensitivity && isNum(p.pulse.sensitivity.p05) ? (
            <details className="mt-3 text-xs leading-relaxed text-muted"><summary className="cursor-pointer py-2 text-center">Điểm phụ thuộc trọng số ra sao?</summary><Term k="sensitivity">Độ nhạy trọng số</Term>: đổi ±50%, khoảng điểm 5–95% là {num(p.pulse.sensitivity.p05, 1)}–{num(p.pulse.sensitivity.p95, 1)}; nhãn giữ nguyên {ratioPct(p.pulse.sensitivity.label_stability)} số lần thử. Đây không phải tỷ lệ dự báo đúng.</details>
          ) : null}
        </div>
        <div className="order-1 min-w-0">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted">Toàn cảnh phiên · {code}</p>
          <h2 id="hero-title" className="text-[clamp(1.5rem,3.6vw,2.3rem)] font-bold leading-tight tracking-tight [text-wrap:balance]">
            {scoreMeaning(score).replace(/\.$/, "")}
          </h2>
          {ix0 ? (
            <p className="mt-1 text-base text-muted">{ix0.code} <b className={`tnum ${TONE_CLASS[priceTone(ix0.ch)]}`}>{num(ix0.v)}</b> <Change value={ix0.pct} />
              {isNum(ix0.adv) ? ` · ${num(ix0.adv, 0)} mã tăng, ${num(ix0.dec, 0)} mã giảm` : ""}</p>
          ) : null}
          <h3 className="mt-4 text-sm font-bold uppercase tracking-wide">Đọc nhanh tại mốc cập nhật</h3>
          <ul className="mt-2 space-y-2 text-base leading-relaxed">
            <li><b>Đang diễn ra.</b> {marketSummary(code, ix0?.pct, ix0?.adv, ix0?.dec)}</li>
            {drivers.length ? <li><b>Điều gì đang tác động?</b> {drivers.map((c) => componentMeaning(c.key, c.value)).join(" ")}</li> : null}
            <li><b>Cần lưu ý.</b> {p.pulse?.divergence ? `${p.pulse.divergence} ` : ""}{nHigh
              ? <>Hệ thống đã ghi nhận {nHigh} lượt cảnh báo mức cao trong phiên{hot.length ? `; trong các cảnh báo đã tải, ${hot.join(", ")} xuất hiện nhiều` : ""}. Một mã có thể có nhiều cảnh báo; mở chi tiết để xem từng biến động.{" "}
                <button onClick={onAlerts} className="text-accent underline underline-offset-4">Xem cảnh báo</button></>
              : "Chưa ghi nhận cảnh báo mức cao trong phiên."}</li>
          </ul>
          {missing.length ? <p className="mt-4 rounded-xl bg-surface2 px-3 py-2 text-sm leading-relaxed text-muted">
            {missing.includes("Thanh khoản") ? "Chưa đủ dữ liệu để so sánh giá trị giao dịch với các phiên trước ở cùng thời điểm. " : ""}
            {missing.filter((name) => name !== "Thanh khoản").length ? `Chưa đủ dữ liệu cho: ${missing.filter((name) => name !== "Thanh khoản").join(", ")}. ` : ""}
            Điểm nhịp hiện chưa tính các phần này.
          </p> : null}
        </div>
      </section>

      <MarketEvidence comps={comps} onNavigate={(slug) => {
        if (slug === "tong-quan") document.getElementById("market-chart")?.focus();
        else onNavigate(slug);
      }} />

      <section aria-labelledby="unusual-title" className="mt-7 rounded-2xl bg-surface p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-semibold uppercase tracking-widest text-accent">Những điểm cần xem lại</p><h2 id="unusual-title" className="mt-1 text-xl font-bold">Biến động đáng chú ý trong rổ</h2></div>
          <button onClick={onAlerts} className="min-h-11 rounded-xl bg-surface2 px-4 text-sm font-semibold text-accent">Mở toàn bộ cảnh báo →</button></div>
        <p className="my-3 text-sm leading-relaxed text-muted">{alerts.length} lượt khớp bộ lọc trong danh sách đã tải; dưới đây là tối đa 5 lượt gần nhất. Bấm từng dòng để xem lý do và ngưỡng đo. Một mã có thể xuất hiện nhiều lần.</p>
        <AlertList items={alerts} limit={5} />
      </section>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          {ixs.length ? <section aria-label="Chỉ số" className="mb-6 lg:hidden"><IndexList rows={ixs} compact /></section> : null}

          <h3 id="market-chart" tabIndex={-1} className="scroll-mt-6 text-xl font-bold">Đặt tín hiệu vào diễn biến giá</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">Đối chiếu các tín hiệu bên trên với đường giá. <Term k="ma">MA và EMA</Term> giúp nhìn xu hướng, không tham gia điểm nhịp. Khung Phiên là dữ liệu đã ghi; khung ngày cung cấp bối cảnh dài hơn.</p>
          <figure className="mt-2">
            {series.length > 1 ? <TechnicalChart key={code} symbol={code} intraday={series} intradayChart={p.chart} reference={row?.ref} /> : <p className="text-sm text-muted">Chưa đủ điểm dữ liệu để vẽ.</p>}
            <figcaption className="mt-1 border-t border-line pt-1 text-sm text-muted">
              <b className="text-fg">Hình 1.</b> {code}: khung Phiên dùng dữ liệu nội phiên đã ghi; các khung còn lại dùng giá đóng cửa ngày từ Vietcap. Rê chuột hoặc chạm để xem từng điểm; cuộn để thu phóng.
            </figcaption>
          </figure>


          <h3 className="mt-10 text-xl font-bold"><Term k="sector">Đóng góp của các ngành vào chỉ số</Term></h3>
          <p className="mt-1 text-sm text-muted">Chạm vào một ngành để xem các mã trong ngành.</p>
          <div className="mt-2"><SectorCard sectors={p.sectors} live={lp?.sec ?? null} indexCode={code} /></div>

          {summary.length ? (
            <details className="mt-8 rounded-xl border border-line bg-surface p-3">
              <summary className="cursor-pointer font-semibold">Bản tóm tắt số liệu đầy đủ{lp ? " (theo bản dữ liệu gần nhất)" : ""}</summary>
              <ul className="mt-2 max-w-[68ch] list-disc space-y-1.5 pl-5">{summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <Note>Câu chữ dựng từ mẫu câu gắn với số liệu, không phải dự báo hay khuyến nghị.</Note>
            </details>
          ) : null}
        </div>

        <aside className="hidden space-y-8 lg:block lg:border-l lg:border-line lg:pl-6">
          <section aria-labelledby="a-ix"><h2 id="a-ix" className="text-sm font-bold uppercase tracking-wide">Bảng chỉ số</h2><IndexList rows={ixs} /></section>
          <section aria-labelledby="a-fn">
            <h2 id="a-fn" className="text-sm font-bold uppercase tracking-wide"><Term k="foreign">Khối ngoại trong rổ</Term></h2>
            <p className="mt-1 text-2xl font-semibold"><SignedMoney value={fs?.net_val ?? null} /></p>
            <p className="text-sm text-muted">{!isNum(fs?.net_val) ? "Chưa đủ dữ liệu" : fs.net_val > 0 ? "Mua ròng" : fs.net_val < 0 ? "Bán ròng" : "Mua và bán cân bằng"} · {num(fs?.n_net_buy ?? null, 0)} mã mua ròng, {num(fs?.n_net_sell ?? null, 0)} mã bán ròng</p>
          </section>
        </aside>
      </div>
      <ValidationSummary p={p} onNavigate={onNavigate} />
    </div>
  );
}
