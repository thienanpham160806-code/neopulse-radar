"use client";

/**
 * Phương án B (Bàn điều khiển 3 Cột / Radar Cockpit) + 4 điều kiện đã duyệt:
 * 1. Cột "Vì sao?" giữ câu giải thích thường + ghi rõ thanh là thành phần chuẩn hóa (-1..+1, không phải % hay điểm đóng góp).
 * 2. Thu nhỏ đồng hồ, tận dụng cột trái (chỉ số, độ rộng, tóm tắt, khoảng thời gian ghi nhận & cảnh báo thiếu dữ liệu);
 *    không ép biểu đồ/ngành vào màn hình đầu — biểu đồ tải lười có chiều cao đầy đủ bên dưới.
 * 3. Mobile ưu tiên: hai số chính -> lý do ngắn + "3 tín hiệu nổi bật" (cho mở đủ 5) -> cảnh báo.
 * 4. Nguồn, thời điểm, thiếu dữ liệu luôn dễ thấy; tra cứu ⓘ mở ngay tại chỗ.
 */

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { dmyTime, isNum, priceTone, TONE_CLASS, TONE_MARK } from "@/lib/fmt";
import { hm, num, ratioPct, signed } from "@/lib/format";
import { mergeSeries, type LiveState } from "@/lib/live";
import { alertDigest, componentMeaning, marketSummary, missingComponents, RULE_PLAIN, scoreMeaning } from "@/lib/plain";
import type { AlertItem, Num, Payload, PulseComponent, Severity } from "@/lib/types";
import { GLOSSARY } from "@/lib/glossary";
import { Gauge, Term } from "./Explain";
import { SectorCard } from "./SectorCard";
import { CompanyLink } from "./CompanyLink";
import { type Filters } from "./tabs";
import { CenterBar, Change, Note, SevTag, SignedMoney, SkeletonBlock } from "./ui";
import { AlertDetail } from "./AlertDetail";
import { ComponentCoverage, ValidationSummary } from "./MarketEvidence";

// Tải lười TradingView Lightweight Charts khi cuộn tới gần khung biểu đồ để tối ưu TBT/LCP mà vẫn giữ nguyên chiều cao tránh CLS
const ChartSkeleton = () => (
  <div role="status" aria-live="polite" className="space-y-3">
    <span className="sr-only">Đang tải biểu đồ giá…</span>
    <div className="flex gap-2">
      <SkeletonBlock className="h-9 w-16 rounded-full" />
      <SkeletonBlock className="h-9 w-12 rounded-full" />
      <SkeletonBlock className="h-9 w-12 rounded-full" />
      <SkeletonBlock className="h-9 w-12 rounded-full" />
    </div>
    <SkeletonBlock className="h-72 w-full sm:h-96" />
  </div>
);

const TechnicalChart = dynamic(() => import("./TechnicalChart").then((m) => m.TechnicalChart), {
  ssr: false,
  loading: ChartSkeleton,
});

function DeferredTechnicalChart(props: {
  symbol: string;
  intraday: { time: string; value: number }[];
  intradayChart?: Payload["chart"];
  reference?: number | null;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = hostRef.current;
    if (!el || visible) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { rootMargin: "240px 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [visible]);

  return (
    <div ref={hostRef} className="min-h-[340px] sm:min-h-[430px]">
      {visible ? <TechnicalChart {...props} /> : <ChartSkeleton />}
    </div>
  );
}

const SEV_ORDER: Severity[] = ["CAO", "TRUNG BÌNH", "THẤP"];
const ORDER = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"];
interface Ix { code: string; v: Num; ch: Num; pct: Num; adv: Num; dec: Num; nc: Num }

function BreadthBar({ adv, nc, dec }: { adv: Num; nc: Num; dec: Num }) {
  if (!isNum(adv) || !isNum(dec)) return null;
  const flat = isNum(nc) ? nc : 0;
  const total = adv + dec + flat;
  if (total <= 0) return null;
  const wUp = (adv / total) * 100;
  const wFlat = (flat / total) * 100;
  const wDown = (dec / total) * 100;
  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-xs tnum">
        <span className="font-semibold text-up">▲ {num(adv, 0)} tăng</span>
        {flat > 0 ? <span className="text-refc">■ {num(flat, 0)}</span> : null}
        <span className="font-semibold text-down">▼ {num(dec, 0)} giảm</span>
      </div>
      <div className="mt-1 flex h-2 w-full overflow-hidden rounded-full bg-surface2" role="img" aria-label={`${num(adv, 0)} mã tăng, ${num(flat, 0)} đứng giá, ${num(dec, 0)} mã giảm`}>
        <div className="ui-transition h-full bg-up" style={{ width: `${wUp}%` }} />
        {wFlat > 0 ? <div className="ui-transition h-full bg-refc" style={{ width: `${wFlat}%` }} /> : null}
        <div className="ui-transition h-full bg-down" style={{ width: `${wDown}%` }} />
      </div>
    </div>
  );
}

function ComponentRow({
  c,
  onNavigate,
  className = "",
}: {
  c: PulseComponent;
  onNavigate: (tab: string) => void;
  className?: string;
}) {
  const tone = priceTone(c.value);
  const targetTab = c.key === "breadth" ? "nganh" : (GLOSSARY[c.key]?.tab ?? "tong-quan");
  const actionTitle = c.key === "breadth" ? "Mở ngành & độ rộng" : c.key === "momentum" ? "Xem biểu đồ diễn biến giá" : "Mở bảng bằng chứng";
  return (
    <li className={`border-b border-line/70 py-2 last:border-0 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5 text-xs font-semibold">
          <Term k={c.key}>{c.name}</Term>
          <span className="tnum shrink-0 rounded bg-surface2 px-1.5 py-0.5 text-[11px] font-medium text-muted">
            {num(c.weight * 100, 0)}%
          </span>
        </div>
        <button
          type="button"
          onClick={() => onNavigate(targetTab)}
          title={actionTitle}
          className={`ui-transition tnum inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-bold hover:bg-surface2 ${
            isNum(c.value) ? TONE_CLASS[tone] : "text-muted"
          }`}
        >
          <span aria-hidden>{isNum(c.value) ? TONE_MARK[tone] : ""}</span>
          <span>{signed(c.value)}</span>
          <span aria-hidden className="ml-0.5 font-normal text-accent">→</span>
        </button>
      </div>
      <div className="mt-1.5">
        <CenterBar value={c.value} />
      </div>
      {!isNum(c.value) ? (
        <p className="mt-1 text-[11px] text-muted">Chưa đủ dữ liệu — bỏ qua và chuẩn hóa lại trọng số phần còn lại.</p>
      ) : null}
    </li>
  );
}

/** Danh sách cảnh báo gọn trong cột 3; bấm mã soi Chi tiết mã nội phiên, mở dòng xem số kiểm tra/ngưỡng. */
function AlertList({
  items,
  limit,
  onSelectSymbol,
  liveKeys,
}: {
  items: AlertItem[];
  limit: number;
  onSelectSymbol?: (symbol: string) => void;
  liveKeys: Set<string>;
}) {
  if (!items.length) {
    return (
      <p className="rounded-xl border border-dashed border-line bg-bg/60 px-3 py-4 text-center text-xs text-muted">
        Chưa ghi nhận biến động bất thường ở mức đang lọc.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-line/80">
      {items.slice(0, limit).map((a, i) => {
        const isLiveNew = liveKeys.has(`${a.t}|${a.symbol}|${a.rule}`);
        return (
          <li key={`${a.t}${a.symbol}${a.rule}${i}`} className={isLiveNew ? "alert-enter" : ""}>
            <details className="group py-2">
              <summary className="flex cursor-pointer list-none items-start gap-2">
                <SevTag sev={a.severity} className="mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    {onSelectSymbol ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onSelectSymbol(a.symbol);
                        }}
                        className="font-semibold text-accent underline decoration-accent/30 underline-offset-4 hover:decoration-accent"
                        title={`Soi nội phiên mã ${a.symbol}`}
                      >
                        {a.symbol}
                      </button>
                    ) : (
                      <CompanyLink symbol={a.symbol} />
                    )}
                    <time className="tnum shrink-0 text-xs text-muted">{a.t.slice(11, 16)}</time>
                  </div>
                  <p className="mt-0.5 text-xs leading-snug text-fg/90">
                    {RULE_PLAIN[a.rule] ?? a.rule_name}
                    <span className="ml-1 font-medium text-accent group-open:hidden">· chi tiết</span>
                  </p>
                </div>
              </summary>
              <div className="mt-2 rounded-xl bg-surface2/60 p-2.5 text-xs">
                <AlertDetail a={a} />
                <div className="mt-2 flex flex-wrap gap-3 pt-1">
                  {onSelectSymbol ? (
                    <button
                      type="button"
                      onClick={() => onSelectSymbol(a.symbol)}
                      className="font-semibold text-accent underline underline-offset-4"
                    >
                      Soi nội phiên {a.symbol} →
                    </button>
                  ) : null}
                  <CompanyLink symbol={a.symbol}>Hồ sơ doanh nghiệp {a.symbol} ↗</CompanyLink>
                </div>
              </div>
            </details>
          </li>
        );
      })}
    </ul>
  );
}

export function Overview({
  p,
  f,
  live,
  onNavigate,
  onSelectSymbol,
  onFilterSev,
}: {
  p: Payload;
  f: Filters;
  live?: LiveState | null;
  onNavigate: (tab: string) => void;
  onSelectSymbol?: (symbol: string) => void;
  onFilterSev?: (sev: Severity) => void;
}) {
  const [showAllMobileComps, setShowAllMobileComps] = useState(false);

  const onAlerts = () => onNavigate("canh-bao");
  const code = p.index?.code ?? p.meta.index_code;
  const lp = live?.pulse && live.pulse.index_code === code ? live.pulse : null;
  const score = lp ? lp.score : p.pulse?.score ?? null;
  const comps = useMemo(
    () => (lp ? lp.comps.map((c) => ({ key: c.k, name: c.n, weight: c.w, value: c.v })) : p.pulse?.components ?? []),
    [lp, p.pulse?.components]
  );
  const row = p.index?.row;
  const ixs: Ix[] = live?.tick
    ? ORDER.filter((c) => live.tick?.ix[c]).map((c) => ({ code: c, ...live.tick!.ix[c] }))
    : row ? [{ code, v: row.value, ch: row.change, pct: row.pct_change, adv: row.advances, dec: row.declines, nc: row.no_change }] : [];
  const liveAlerts: AlertItem[] = (lp ? live?.alerts ?? [] : []).map((a) => ({
    t: a.t,
    symbol: a.s,
    rule: a.rule,
    rule_name: p.alerts?.rule_names[a.rule] ?? a.rule,
    severity: a.sev,
    message: a.msg,
    value: null,
    threshold: null,
  }));
  const liveKeys = useMemo(() => new Set(liveAlerts.map((a) => `${a.t}|${a.symbol}|${a.rule}`)), [liveAlerts]);
  const { items: allAlerts, nHigh, hot } = alertDigest(liveAlerts, p.alerts?.items ?? [], p.alerts?.by_severity?.CAO, p.meta.last_update);
  const alerts = allAlerts.filter(
    (a) => SEV_ORDER.indexOf(a.severity) <= SEV_ORDER.indexOf(f.minSev) && (!f.sym || a.symbol.includes(f.sym.toUpperCase()))
  );
  const summary = p.pulse?.summary ?? [];
  const baseSeries = p.pulse?.series;
  const livePoints = live?.points[code];
  const series = useMemo(
    () => mergeSeries((baseSeries ?? []).map((r) => ({ t: r.t, value: r.index })), livePoints ?? []).map((q) => ({ time: q.t, value: q.v })),
    [baseSeries, livePoints]
  );
  const fs = p.foreign?.summary;

  // Hai thành phần tác động lớn nhất cho câu giải thích bằng lời thường
  const drivers = useMemo(
    () => comps.filter((c) => isNum(c.value)).sort((a, b) => Math.abs((b.value as number) * b.weight) - Math.abs((a.value as number) * a.weight)).slice(0, 2),
    [comps]
  );
  // 3 tín hiệu nổi bật cho mobile (ưu tiên thành phần có số liệu mạnh nhất; bổ sung nếu còn chỗ)
  const top3Keys = useMemo(() => {
    const ranked = [...comps].sort((a, b) => {
      const av = isNum(a.value) ? Math.abs(a.value * a.weight) : -1;
      const bv = isNum(b.value) ? Math.abs(b.value * b.weight) : -1;
      return bv - av;
    });
    return new Set(ranked.slice(0, 3).map((c) => c.key));
  }, [comps]);

  const missing = missingComponents(comps);
  const ix0 = ixs.find((x) => x.code === code);
  const otherIxs = ixs.filter((x) => x.code !== code);
  const dir0 = (ix0?.ch ?? 0) > 0 ? "up" : (ix0?.ch ?? 0) < 0 ? "down" : "flat";

  // Khoảng thời gian nội phiên thực tế đã ghi nhận (báo rõ nếu thiếu đầu phiên, ví dụ bắt đầu sau 09:20)
  const firstPoint = series[0]?.time ?? null;
  const lastPoint = series.at(-1)?.time ?? null;
  const firstHm = firstPoint ? hm(firstPoint) : null;
  const lastHm = lastPoint ? hm(lastPoint) : null;
  const lateStart = Boolean(firstHm && firstHm > "09:20");

  const handleEvidenceNav = (slug: string) => {
    if (slug === "tong-quan") {
      document.getElementById("market-chart")?.scrollIntoView({ behavior: "smooth" });
      document.getElementById("market-chart")?.focus({ preventScroll: true });
    } else {
      onNavigate(slug);
    }
  };

  const countMed = p.alerts?.by_severity?.["TRUNG BÌNH"] ?? allAlerts.filter((a) => a.severity === "TRUNG BÌNH").length;
  const countLow = p.alerts?.by_severity?.["THẤP"] ?? allAlerts.filter((a) => a.severity === "THẤP").length;

  return (
    <div className="panel-enter">
      {/* Dải phạm vi ngắn gọn — luôn hiện nguồn/mốc/khoảng ghi nhận mà không chiếm diện tích */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-xl border border-line/80 bg-surface px-3.5 py-2 text-xs text-muted">
        <p className="leading-relaxed">
          <b className="text-fg">Phạm vi:</b> chỉ số & độ rộng <b className="text-fg">{code}</b>; sổ lệnh & khối ngoại trên{" "}
          <b className="tnum text-fg">{p.meta.n_symbols_computed}</b> mã.{" "}
          {live ? "Giá & điểm nhịp cập nhật nhanh; bảng chi tiết theo mốc đầy đủ gần nhất. " : ""}
          Bản đầy đủ đến <b className="tnum text-fg">{p.meta.last_update ? dmyTime(p.meta.last_update) : "chưa xác định"}</b> (giờ VN).
        </p>
        {firstHm && lastHm ? (
          <span className={`tnum shrink-0 rounded-full px-2 py-0.5 font-medium ${lateStart ? "border border-fg/40 bg-surface2 text-fg" : "bg-surface2 text-muted"}`}>
            {lateStart ? `Thiếu đầu phiên · ghi từ ${firstHm}–${lastHm}` : `Chuỗi ghi nhận ${firstHm}–${lastHm}`}
          </span>
        ) : null}
      </div>

      {/* BÀN ĐIỀU KHIỂN 3 CỘT (PHƯƠNG ÁN B) — 1. Khỏe hay yếu? | 2. Vì sao? | 3. Bất thường? */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-12">
        {/* CỘT 1: 1 · KHỎE HAY YẾU? */}
        <section
          aria-labelledby="hero-title"
          className="card-elev flex min-w-0 flex-col justify-between rounded-2xl border border-line bg-surface p-4 lg:col-span-4"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-widest text-accent">1 · Khỏe hay yếu?</span>
              <Term k="pulse">Điểm nhịp</Term>
            </div>

            {/* Mobile: 2 số chính song song (Chỉ số | Điểm nhịp) ngay lập tức trên màn hình đầu */}
            <div className="mt-2.5 grid grid-cols-2 gap-2.5 lg:hidden">
              <div className="rounded-xl bg-surface2/60 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{code}</div>
                {ix0 ? (
                  <>
                    <div key={`${ix0.v}`} className={`tnum mt-0.5 rounded text-xl font-bold leading-tight ${TONE_CLASS[priceTone(ix0.ch)]} flash-${dir0}`}>
                      {num(ix0.v)}
                    </div>
                    <div className="mt-0.5 text-xs font-semibold"><Change value={ix0.pct} /></div>
                  </>
                ) : (
                  <div className="mt-1 text-sm text-muted">—</div>
                )}
              </div>
              <div className="rounded-xl bg-surface2/60 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">Điểm nhịp</div>
                <div className="tnum mt-0.5 text-xl font-bold leading-tight">
                  {isNum(score) ? num(score, 1) : "—"}
                  <span className="text-xs font-normal text-muted">/100</span>
                </div>
                <div className="mt-0.5 text-[11px] font-medium text-muted">
                  {comps.filter((c) => isNum(c.value)).length}/{comps.length} nhóm tín hiệu
                </div>
              </div>
            </div>

            {/* Desktop: Đồng hồ thu gọn + tận dụng khoảng trống cột trái */}
            <div className="mt-1 hidden lg:block">
              <Gauge score={score} label={scoreMeaning(score).replace(/\.$/, "")} compact />
            </div>

            <h2 id="hero-title" className="mt-2.5 text-base font-bold leading-snug lg:sr-only">
              {scoreMeaning(score).replace(/\.$/, "")}
            </h2>

            {/* Desktop: Chỉ số chính nổi bật ngay dưới đồng hồ */}
            {ix0 ? (
              <div className="mt-3 hidden items-baseline justify-between gap-2 border-t border-line/80 pt-3 lg:flex">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{ix0.code}</div>
                  <div key={`${ix0.v}`} className={`tnum rounded text-2xl font-bold leading-tight ${TONE_CLASS[priceTone(ix0.ch)]} flash-${dir0}`}>
                    {num(ix0.v)}
                  </div>
                </div>
                <div className="text-right">
                  <Change value={ix0.pct} className="text-base font-bold" />
                  {isNum(ix0.ch) ? (
                    <div className={`tnum text-xs ${TONE_CLASS[priceTone(ix0.ch)]}`}>{signed(ix0.ch)} điểm</div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {/* Thanh độ rộng trực quan */}
            {ix0 ? <BreadthBar adv={ix0.adv} nc={ix0.nc} dec={ix0.dec} /> : null}

            {/* Nhận định diễn biến bằng lời thường */}
            <p className="mt-2.5 text-xs leading-relaxed text-muted">
              {marketSummary(code, ix0?.pct, ix0?.adv, ix0?.dec)}
            </p>

            {/* Các chỉ số khác (khi đang live đa chỉ số) */}
            {otherIxs.length ? (
              <dl className="mt-2.5 grid grid-cols-2 gap-1.5 border-t border-line/70 pt-2.5">
                {otherIxs.map((x) => (
                  <div key={x.code} className="rounded-lg bg-surface2/60 px-2 py-1.5 text-xs">
                    <dt className="font-semibold text-muted">{x.code}</dt>
                    <dd className="tnum mt-0.5 flex items-baseline justify-between gap-1">
                      <span className={`font-semibold ${TONE_CLASS[priceTone(x.ch)]}`}>{num(x.v, 1)}</span>
                      <Change value={x.pct} d={1} className="text-[11px]" />
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>

          {/* Tận dụng đáy cột trái: độ phủ, phân kỳ, thiếu dữ liệu & độ nhạy trọng số */}
          <div className="mt-3 space-y-2 border-t border-line/80 pt-2.5">
            {p.pulse?.divergence ? (
              <p className="rounded-lg border border-fg/30 bg-surface2 px-2.5 py-1.5 text-xs font-medium text-fg">
                {p.pulse.divergence}
              </p>
            ) : null}
            {missing.length ? (
              <p className="rounded-lg bg-surface2 px-2.5 py-1.5 text-xs leading-relaxed text-muted">
                <b className="text-fg">Dữ liệu đang thiếu:</b>{" "}
                {missing.includes("Thanh khoản") ? "Chưa đủ phiên cùng giờ để so sánh thanh khoản. " : ""}
                {missing.filter((name) => name !== "Thanh khoản").length
                  ? `Chưa đủ dữ liệu cho: ${missing.filter((name) => name !== "Thanh khoản").join(", ")}. `
                  : ""}
                Điểm nhịp chưa tính phần này.
              </p>
            ) : null}
            <div className="hidden lg:block"><ComponentCoverage comps={comps} /></div>
            {!lp && p.pulse?.sensitivity && isNum(p.pulse.sensitivity.p05) ? (
              <details className="text-xs leading-relaxed text-muted">
                <summary className="cursor-pointer py-1 font-medium hover:text-fg">
                  Độ nhạy trọng số (±50%): <b className="tnum text-fg">{num(p.pulse.sensitivity.p05, 1)}–{num(p.pulse.sensitivity.p95, 1)}</b>
                </summary>
                <p className="mt-1">
                  <Term k="sensitivity">Độ nhạy trọng số</Term>: xáo trộn mỗi trọng số ±50%, khoảng điểm 5–95% là {num(p.pulse.sensitivity.p05, 1)}–{num(p.pulse.sensitivity.p95, 1)}; nhãn giữ nguyên {ratioPct(p.pulse.sensitivity.label_stability)} số lần thử. Không phải tỷ lệ dự báo đúng.
                </p>
              </details>
            ) : null}
          </div>
        </section>

        {/* CỘT 2: 2 · VÌ SAO? (NĂM GÓC NHÌN) */}
        <section
          aria-labelledby="why-title"
          className="card-elev flex min-w-0 flex-col justify-between rounded-2xl border border-line bg-surface p-4 lg:col-span-4"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-widest text-accent">2 · Vì sao?</span>
              <button
                type="button"
                onClick={() => onNavigate("vi-sao")}
                className="text-xs font-semibold text-accent underline-offset-4 hover:underline"
              >
                Phân tích chi tiết →
              </button>
            </div>
            <h2 id="why-title" className="mt-1 text-base font-bold">Năm góc nhìn cấu thành điểm nhịp</h2>

            {/* Câu giải thích bằng lời thường (điều kiện bắt buộc #1) */}
            <p className="mt-1.5 rounded-xl bg-surface2/60 px-3 py-2 text-xs leading-relaxed text-fg">
              {drivers.length
                ? drivers.map((c) => componentMeaning(c.key, c.value)).join(" ")
                : "Chưa đủ thành phần có dữ liệu để nêu yếu tố chi phối."}
            </p>

            {/* Ghi chú minh bạch: thành phần chuẩn hóa -1..+1, không phải % hay điểm đóng góp */}
            <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
              Các thanh dưới đây là <b className="text-fg">thành phần chuẩn hóa (−1…+1)</b> theo trọng số gốc —{" "}
              <b>không phải % tăng giá hay số điểm đóng góp</b>. Bấm ⓘ để tra cứu, bấm mũi tên để mở bảng bằng chứng.
            </p>

            {/* Nhãn rõ ràng cho chế độ thu gọn 3 tín hiệu trên mobile (điều kiện bắt buộc #3) */}
            <div className="mt-2 flex items-center justify-between lg:hidden">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                {showAllMobileComps ? `Đủ ${comps.length} tín hiệu` : "3 tín hiệu nổi bật"}
              </span>
              {comps.length > 3 ? (
                <button
                  type="button"
                  onClick={() => setShowAllMobileComps((v) => !v)}
                  aria-expanded={showAllMobileComps}
                  className="min-h-8 rounded-lg bg-surface2 px-2.5 text-xs font-semibold text-accent"
                >
                  {showAllMobileComps ? "Thu gọn ▴" : `Mở đủ ${comps.length} tín hiệu ▾`}
                </button>
              ) : null}
            </div>

            {/* Danh sách thành phần: Mobile hiện 3 tín hiệu nổi bật (hoặc đủ 5 khi bấm mở), Desktop luôn hiện đủ 5 */}
            <ul className="mt-1">
              {comps.map((c) => {
                const hiddenOnMobile = !showAllMobileComps && !top3Keys.has(c.key);
                return (
                  <ComponentRow
                    key={c.key}
                    c={c}
                    onNavigate={handleEvidenceNav}
                    className={hiddenOnMobile ? "hidden lg:block" : "block"}
                  />
                );
              })}
            </ul>
          </div>

          {/* Tóm tắt Khối ngoại trong rổ (luôn gọn ở chân cột 2) */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-surface2/70 px-3 py-2.5">
            <div>
              <div className="text-xs font-medium text-muted"><Term k="foreign">Khối ngoại trong rổ</Term></div>
              <div className="mt-0.5 text-base font-bold"><SignedMoney value={fs?.net_val ?? null} /></div>
            </div>
            <div className="text-right text-xs text-muted">
              {!isNum(fs?.net_val) ? (
                <span>Chưa đủ dữ liệu</span>
              ) : (
                <>
                  <div className="font-medium text-fg">
                    {fs.net_val > 0 ? "Mua ròng" : fs.net_val < 0 ? "Bán ròng" : "Cân bằng"}
                  </div>
                  <div className="tnum">
                    {num(fs?.n_net_buy ?? null, 0)} mua · {num(fs?.n_net_sell ?? null, 0)} bán
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        {/* CỘT 3: 3 · BẤT THƯỜNG? */}
        <section
          aria-labelledby="unusual-title"
          className="card-elev flex min-w-0 flex-col justify-between rounded-2xl border border-line bg-surface p-4 lg:col-span-4"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-widest text-accent">3 · Bất thường?</span>
              <button
                type="button"
                onClick={onAlerts}
                className="text-xs font-semibold text-accent underline-offset-4 hover:underline"
              >
                Mở toàn bộ ({p.alerts?.total ?? allAlerts.length}) →
              </button>
            </div>
            <h2 id="unusual-title" className="mt-1 text-base font-bold">Biến động đáng chú ý trong rổ</h2>

            {/* Bộ đếm mức cảnh báo — bấm để lọc nhanh */}
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {(
                [
                  ["CAO", `◆ ${nHigh} Cao`],
                  ["TRUNG BÌNH", `◇ ${countMed} Trung bình`],
                  ["THẤP", `· ${countLow} Thấp`],
                ] as [Severity, string][]
              ).map(([sev, txt]) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => (onFilterSev ? onFilterSev(sev) : onAlerts())}
                  aria-pressed={f.minSev === sev}
                  className={`ui-transition tnum rounded-lg px-2 py-1 text-xs font-semibold ${
                    f.minSev === sev
                      ? "bg-accent text-on-accent"
                      : "border border-line bg-surface2/70 text-fg hover:bg-surface2"
                  }`}
                >
                  {txt}
                </button>
              ))}
              {hot.length ? (
                <span className="ml-auto text-[11px] text-muted">
                  Nổi bật: <b className="text-fg">{hot.join(", ")}</b>
                </span>
              ) : null}
            </div>

            <p className="mt-2 text-[11px] leading-relaxed text-muted">
              {alerts.length} lượt khớp lọc ({f.minSev === "CAO" ? "chỉ mức Cao" : f.minSev === "TRUNG BÌNH" ? "từ Trung bình" : "tất cả"}); hiện tối đa 5 lượt gần nhất. Bấm mã để soi nội phiên.
            </p>

            <div className="mt-1.5">
              <AlertList items={alerts} limit={5} onSelectSymbol={onSelectSymbol} liveKeys={liveKeys} />
            </div>
          </div>

          <div className="mt-3 border-t border-line/80 pt-2.5">
            <button
              type="button"
              onClick={onAlerts}
              className="ui-transition min-h-10 w-full rounded-xl bg-surface2 px-3 text-xs font-semibold text-accent hover:bg-accent hover:text-on-accent"
            >
              Xem toàn bộ cảnh báo & lọc theo quy tắc →
            </button>
          </div>
        </section>
      </div>

      {/* BÊN DƯỚI BENTO: BIỂU ĐỒ DIỄN BIẾN GIÁ (CHIỀU CAO THOẢI MÁI, TẢI LƯỜI) */}
      <section aria-labelledby="market-chart" className="card-elev mt-6 rounded-2xl border border-line bg-surface p-4 sm:p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-accent">Diễn biến giá & xu hướng</p>
            <h3 id="market-chart" tabIndex={-1} className="scroll-mt-6 text-lg font-bold">
              Đặt tín hiệu vào diễn biến giá
            </h3>
          </div>
          <span className="text-xs text-muted">
            <Term k="ma">MA và EMA</Term> chỉ giúp nhìn xu hướng, không tham gia điểm nhịp.
          </span>
        </div>
        <figure className="mt-3">
          {series.length > 1 ? (
            <DeferredTechnicalChart key={code} symbol={code} intraday={series} intradayChart={p.chart} reference={row?.ref} />
          ) : (
            <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
              Chưa đủ điểm dữ liệu nội phiên để vẽ biểu đồ.
            </p>
          )}
          <figcaption className="mt-2 border-t border-line pt-2 text-xs text-muted">
            <b className="text-fg">Hình 1.</b> {code}: khung Phiên dùng dữ liệu nội phiên đã ghi; các khung ngày dùng giá đóng cửa từ Vietcap. Rê chuột hoặc chạm để đọc từng điểm; cuộn để thu phóng.
          </figcaption>
        </figure>
      </section>

      {/* NGÀNH KÉO / NGÀNH ĐÈ (ĐẦY ĐỦ CHIỀU RỘNG, KHÔNG BỊ ÉP) */}
      <section aria-labelledby="sector-overview-title" className="mt-6">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="sector-overview-title" className="text-lg font-bold">
            <Term k="sector">Đóng góp của các ngành vào chỉ số</Term>
          </h3>
          <span className="text-xs text-muted">Chạm vào một ngành để mở danh sách mã và soi chi tiết.</span>
        </div>
        <SectorCard sectors={p.sectors} live={lp?.sec ?? null} indexCode={code} onSelectSymbol={onSelectSymbol} />
      </section>

      {/* BẢN TÓM TẮT SỐ LIỆU ĐẦY ĐỦ */}
      {summary.length ? (
        <details className="card-elev mt-6 rounded-2xl border border-line bg-surface p-4">
          <summary className="cursor-pointer text-sm font-semibold">
            Bản tóm tắt số liệu đầy đủ{lp ? " (theo bản dữ liệu gần nhất)" : ""}
          </summary>
          <ul className="mt-2.5 max-w-[72ch] list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
            {summary.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
          <Note>Câu chữ dựng từ mẫu câu gắn với số liệu, không phải dự báo hay khuyến nghị.</Note>
        </details>
      ) : null}

      {/* TÓM TẮT KIỂM CHỨNG */}
      <ValidationSummary p={p} onNavigate={onNavigate} />
    </div>
  );
}
