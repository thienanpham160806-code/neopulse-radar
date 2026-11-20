"use client";

import { useRouter } from "next/navigation";
import { SiteHeader } from "./SiteHeader";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Loaded } from "@/lib/data";
import { clock, dmy } from "@/lib/format";
import type { Severity } from "@/lib/types";
import { liveForSnapshot, liveMode } from "@/lib/live";
import { StatusBar } from "./StatusBar";

import { useLive } from "./useLive";
import { Overview } from "./Overview";
import dynamic from "next/dynamic";
import type { Filters } from "./tabs";

// các tab phụ (và Recharts) tải lười khi mở, không nằm trong gói JS của lần tải đầu
const loading = () => <p className="text-sm text-muted">Đang tải…</p>;
const Alerts = dynamic(() => import("./tabs").then((m) => m.Alerts), { loading });
const Book = dynamic(() => import("./tabs").then((m) => m.Book), { loading });
const Foreign = dynamic(() => import("./tabs").then((m) => m.Foreign), { loading });
const Futures = dynamic(() => import("./tabs").then((m) => m.Futures), { loading });
const Method = dynamic(() => import("./tabs").then((m) => m.Method), { loading });
const Ranking = dynamic(() => import("./tabs").then((m) => m.Ranking), { loading });
const Validation = dynamic(() => import("./tabs").then((m) => m.Validation), { loading });

const TABS = ["Tổng quan", "Sổ lệnh & thanh khoản", "Khối ngoại", "Phái sinh", "Cảnh báo", "Xếp hạng", "Kiểm chứng & dữ liệu", "Phương pháp & giới hạn"] as const;
type Tab = (typeof TABS)[number];
const SLUGS: Record<Tab, string> = {
  "Tổng quan": "tong-quan", "Sổ lệnh & thanh khoản": "so-lenh", "Khối ngoại": "khoi-ngoai", "Phái sinh": "phai-sinh",
  "Cảnh báo": "canh-bao", "Xếp hạng": "xep-hang", "Kiểm chứng & dữ liệu": "kiem-chung", "Phương pháp & giới hạn": "phuong-phap",
};
const tabFromSlug = (slug: string | null): Tab => TABS.find((t) => SLUGS[t] === slug) ?? "Tổng quan";
const POLL_MS = 20_000;
const PRIMARY: Tab[] = ["Tổng quan", "Cảnh báo", "Khối ngoại"];
const SHORT: Partial<Record<Tab, string>> = { "Tổng quan": "Tổng quan", "Cảnh báo": "Cảnh báo", "Khối ngoại": "Khối ngoại" };

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export function Dashboard({ initial, requestedDate, requestedIndex, initialTab }: { initial: Loaded; requestedDate: string | null; requestedIndex: string | null; initialTab: string | null }) {
  const router = useRouter();
  const now = useNow();
  const [loaded, setLoaded] = useState<Loaded>(initial);
  const [pollError, setPollError] = useState<string | null>(null);
  const [tab, setTabState] = useState<Tab>(tabFromSlug(initialTab));
  const setTab = (t: Tab) => {
    setTabState(t);
    const u = new URL(window.location.href);
    u.searchParams.set("tab", SLUGS[t]);
    window.history.replaceState(null, "", u);
  };
  const [filters, setFilters] = useState<Filters>({ sym: "", minSev: "TRUNG BÌNH" });
  const [moreOpen, setMoreOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => setLoaded(initial), [initial]);

  // làm mới định kỳ khi đang xem phiên mới nhất; tạm dừng khi tab trình duyệt bị ẩn
  const refresh = useCallback(async () => {
    try {
      const qs = new URLSearchParams();
      if (requestedDate) qs.set("date", requestedDate);
      if (requestedIndex) qs.set("index", requestedIndex);
      const r = await fetch(`/api/data?${qs}`, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status === 401 ? "hết phiên đăng nhập" : `HTTP ${r.status}`);
      setLoaded((await r.json()) as Loaded);
      setPollError(null);
    } catch (e) {
      setPollError(e instanceof Error ? e.message : "lỗi mạng");
    }
  }, [requestedDate, requestedIndex]);

  const live = useLive(!requestedDate); // chỉ khi xem phiên mới nhất
  const mode = liveMode(live.state, now, live.connected, live.error);
  const liveOn = mode.live ? liveForSnapshot(live.state, loaded.payload.meta) : null;
  useEffect(() => {
    if (requestedDate) return; // Historical sessions remain fixed; latest must discover the next session.
    const tick = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const id = setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [refresh, requestedDate]);

  const liveDay = live.state.tick?.day ?? live.state.pulse?.day;
  useEffect(() => {
    if (!requestedDate && liveDay && liveDay > (loaded.payload.meta.trading_date ?? "")) void refresh();
    // Refresh once on session rollover; the interval retries if its full payload is still being published.
  }, [liveDay, requestedDate, refresh, loaded.payload.meta.trading_date]);

  const { payload: p, index } = loaded;
  const meta = p.meta;
  const dates = useMemo(() => Array.from(new Set(index.sessions.filter((s) => s.source === meta.source).map((s) => s.trading_date))).sort().reverse(), [index, meta.source]);
  const codes = useMemo(() => Array.from(new Set(index.sessions.map((s) => s.index_code))), [index]);

  const go = (date: string | null, code: string | null) => {
    const qs = new URLSearchParams();
    if (date) qs.set("date", date);
    if (code) qs.set("index", code);
    qs.set("tab", SLUGS[tab]);
    router.push(`/?${qs}`);
  };

  const empty = meta.data_status.state === "error" || !p.pulse;
  return (
    <>
      <SiteHeader area="market" crumbs={[{ label: "Nhịp thị trường", ...(tab !== "Tổng quan" ? { href: `/?${new URLSearchParams({ ...(requestedDate ? { date: requestedDate } : {}), ...(requestedIndex ? { index: requestedIndex } : {}), tab: "tong-quan" })}`, onClick: () => setTab("Tổng quan") } : {}) }, ...(tab !== "Tổng quan" ? [{ label: tab }] : [])]} />
      <StatusBar
        meta={meta}
        nowMs={now}
        notice={loaded.notice}
        pollError={pollError}
        live={liveOn ? { ts: (liveOn.tick ?? liveOn.pulse ?? liveOn.status)?.ts ?? null, latencyMs: liveOn.latencyMs,
          simulated: (liveOn.tick ?? liveOn.pulse)?.is_simulated ?? false } : null}
        liveNote={live.available && !mode.live && live.state.lastMsgAt !== null ? `${mode.reason} — đang hiển thị snapshot.` : null}
      />
      <header className="mx-auto max-w-6xl px-4 pt-5 sm:px-6">
        <div className="feature-hero rounded-3xl px-6 py-6 sm:px-8 sm:py-7">
          <p className="hero-kicker">THỊ TRƯỜNG VIỆT NAM / {meta.index_code}</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Nhịp thị trường<span className="hero-highlight">.</span></h1>
          <p className="hero-description mt-3 max-w-xl text-sm leading-relaxed">Theo dõi dòng tiền, đọc độ rộng và nhận diện những chuyển động đáng chú ý trong phiên.</p>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <button type="button" onClick={() => setFiltersOpen(!filtersOpen)} aria-expanded={filtersOpen} aria-controls="filters"
          className="mt-3 flex min-h-10 w-full items-center justify-between rounded-md border border-line bg-surface px-3 text-sm md:hidden">
          <span>Bộ lọc · {meta.index_code}{requestedDate ? ` · ${dmy(requestedDate)}` : " · mới nhất"}</span><span aria-hidden className="text-muted">{filtersOpen ? "▴" : "▾"}</span>
        </button>
          <div id="filters" className={`mt-2 flex-wrap items-center gap-2 text-sm md:mt-5 md:flex ${filtersOpen ? "flex" : "hidden"}`}>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">Phiên</span>
              <select aria-label="Chọn phiên giao dịch" className="min-h-10 rounded-md border border-line bg-surface px-2"
                value={requestedDate ?? ""} onChange={(e) => go(e.target.value || null, requestedIndex ?? meta.index_code)}>
                <option value="">Mới nhất{meta.trading_date ? ` (${dmy(meta.trading_date)})` : ""}</option>
                {dates.map((d) => <option key={d} value={d}>{dmy(d)}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">Chỉ số</span>
              <select aria-label="Chọn chỉ số" className="min-h-10 rounded-md border border-line bg-surface px-2"
                value={requestedIndex ?? meta.index_code} onChange={(e) => go(requestedDate, e.target.value)}>
                {(codes.length ? codes : [meta.index_code]).map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <input aria-label="Lọc theo mã" placeholder="Lọc mã…" value={filters.sym}
              onChange={(e) => setFilters({ ...filters, sym: e.target.value.trim() })}
              className="min-h-10 w-28 rounded-md border border-line bg-surface px-2" />
            <label className="flex items-center gap-1.5">
              <span className="text-muted">Cảnh báo từ</span>
              <select aria-label="Ngưỡng mức cảnh báo" className="min-h-10 rounded-md border border-line bg-surface px-2"
                value={filters.minSev} onChange={(e) => setFilters({ ...filters, minSev: e.target.value as Severity })}>
                <option value="CAO">Mức cao</option>
                <option value="TRUNG BÌNH">Trung bình trở lên</option>
                <option value="THẤP">Tất cả</option>
              </select>
            </label>

          </div>

        {/* desktop: mục lục kiểu chuyên mục báo; điện thoại dùng thanh tab đáy */}
        <nav aria-label="Các mục" className="mt-4 hidden rounded-2xl bg-surface p-1 shadow-sm md:block">
          <div role="tablist" className="scroll-x flex gap-1 py-1">
            {TABS.map((t, i) => (
              <button key={t} id={`tab-${SLUGS[t]}`} role="tab" aria-selected={tab === t} aria-controls="tabpanel"
                tabIndex={tab === t ? 0 : -1} onClick={() => setTab(t)}
                onKeyDown={(e) => {
                  // mẫu tablist WAI-ARIA: mũi tên trái/phải, Home/End
                  const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
                  if (k === undefined) return;
                  e.preventDefault();
                  const next = TABS[(k + TABS.length) % TABS.length];
                  setTab(next);
                  document.getElementById(`tab-${SLUGS[next]}`)?.focus();
                }}
                className={`min-h-10 whitespace-nowrap px-3 text-sm ${tab === t ? "rounded-xl bg-surface2 font-semibold text-accent" : "text-muted hover:text-fg"}`}>
                {t}
              </button>
            ))}
          </div>
        </nav>
      </div>

      <main className="mx-auto min-w-0 max-w-6xl px-4 pb-28 pt-6 sm:px-6 md:pb-10">
        <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${SLUGS[tab]}`}>
        <h2 className="sr-only md:hidden">{tab}</h2>
        {empty && tab !== "Phương pháp & giới hạn" ? (
          <div role="alert" className="mx-auto max-w-xl rounded-xl border border-line bg-surface p-6 text-center">
            <p className="text-lg font-semibold">Chưa có dữ liệu để hiển thị</p>
            <p className="mt-1 text-sm text-muted">{meta.data_status.reason}</p>
            {meta.last_update ? <p className="mt-1 text-sm text-muted">Dữ liệu tốt gần nhất: {clock(meta.last_update)} · {dmy(meta.trading_date)}.</p> : null}
            <div className="mt-4 flex justify-center gap-2">
              <button onClick={() => window.location.reload()} className="min-h-10 rounded-md bg-accent px-4 font-medium text-on-accent">Tải lại</button>
              <button onClick={() => setTab("Phương pháp & giới hạn")} className="min-h-10 rounded-md border border-line px-4">Đọc phương pháp</button>
            </div>
          </div>
        ) : tab === "Tổng quan" ? <Overview p={p} f={filters} live={liveOn} onAlerts={() => setTab("Cảnh báo")} />
          : tab === "Sổ lệnh & thanh khoản" ? <Book p={p} f={filters} />
          : tab === "Khối ngoại" ? <Foreign p={p} f={filters} />
          : tab === "Phái sinh" ? <Futures p={p} />
          : tab === "Cảnh báo" ? <Alerts p={p} f={filters} />
          : tab === "Xếp hạng" ? <Ranking p={p} f={filters} />
          : tab === "Kiểm chứng & dữ liệu" ? <Validation p={p} />
          : <Method />}
        </div>
      </main>

      {/* điện thoại (ghép hướng C): thanh tab đáy 4 mục + "Thêm" mở danh sách các mục còn lại */}
      <nav aria-label="Điều hướng chính" className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur md:hidden">
        {moreOpen ? (
          <ul className="grid grid-cols-2 gap-1 border-b border-line p-2">
            {TABS.filter((t) => !PRIMARY.includes(t)).map((t) => (
              <li key={t}><button onClick={() => { setTab(t); setMoreOpen(false); }} aria-current={tab === t ? "page" : undefined}
                className={`min-h-11 w-full rounded-md px-2 text-left text-sm ${tab === t ? "bg-surface2 font-semibold" : ""}`}>{t}</button></li>
            ))}
          </ul>
        ) : null}
        <div className="grid grid-cols-4">
          {PRIMARY.map((t) => (
            <button key={t} onClick={() => { setTab(t); setMoreOpen(false); }} aria-current={tab === t ? "page" : undefined}
              className={`min-h-14 px-1 text-xs ${tab === t ? "font-bold text-accent" : "text-muted"}`}>{SHORT[t] ?? t}</button>
          ))}
          <button onClick={() => setMoreOpen(!moreOpen)} aria-expanded={moreOpen}
            className={`min-h-14 px-1 text-xs ${!PRIMARY.includes(tab) ? "font-bold text-accent" : "text-muted"}`}>Thêm</button>
        </div>
      </nav>

    </>
  );
}
