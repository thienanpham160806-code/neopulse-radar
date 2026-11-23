"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Loaded } from "@/lib/data";
import { clock, dmy } from "@/lib/format";
import { liveForSnapshot, liveMode } from "@/lib/live";
import { SiteHeader } from "./SiteHeader";
import { StatusBar } from "./StatusBar";
import { GlossaryButton, GlossaryProvider } from "./Glossary";
import { GuideButton } from "./Explain";
import { useLive } from "./useLive";
import { Overview } from "./Overview";
import { TabSkeleton } from "./ui";
import type { Filters, MethodSub, WhySub } from "./tabs";

// Các tab phụ (và Recharts) tải lười kèm khung skeleton chống giật bố cục (CLS)
const loading = () => <TabSkeleton />;
const WhyTab = dynamic(() => import("./tabs").then((m) => m.WhyTab), { loading });
const Alerts = dynamic(() => import("./tabs").then((m) => m.Alerts), { loading });
const StockDetailTab = dynamic(() => import("./tabs").then((m) => m.StockDetailTab), { loading });
const MethodTab = dynamic(() => import("./tabs").then((m) => m.MethodTab), { loading });

const TABS = ["Tổng quan", "Vì sao?", "Bất thường", "Chi tiết mã", "Phương pháp"] as const;
type Tab = (typeof TABS)[number];

const SLUGS: Record<Tab, string> = {
  "Tổng quan": "tong-quan",
  "Vì sao?": "vi-sao",
  "Bất thường": "canh-bao",
  "Chi tiết mã": "chi-tiet-ma",
  "Phương pháp": "phuong-phap",
};

const MOBILE_LABEL: Record<Tab, string> = {
  "Tổng quan": "Tổng quan",
  "Vì sao?": "Vì sao",
  "Bất thường": "Cảnh báo",
  "Chi tiết mã": "Chi tiết mã",
  "Phương pháp": "Phương pháp",
};

interface ResolvedRoute {
  tab: Tab;
  whySub?: WhySub;
  methodSub?: MethodSub;
}

/** Ánh xạ tương thích ngược cả 5 slug mới lẫn 8 slug cũ (?tab=so-lenh, khoi-ngoai, phai-sinh, xep-hang, kiem-chung). */
function resolveSlug(slug: string | null): ResolvedRoute {
  switch (slug) {
    case "vi-sao":
    case "nganh":
      return { tab: "Vì sao?", whySub: "nganh" };
    case "so-lenh":
      return { tab: "Vì sao?", whySub: "so-lenh" };
    case "khoi-ngoai":
      return { tab: "Vì sao?", whySub: "khoi-ngoai" };
    case "phai-sinh":
      return { tab: "Vì sao?", whySub: "phai-sinh" };
    case "canh-bao":
      return { tab: "Bất thường" };
    case "chi-tiet-ma":
    case "xep-hang":
      return { tab: "Chi tiết mã" };
    case "kiem-chung":
      return { tab: "Phương pháp", methodSub: "kiem-chung" };
    case "phuong-phap":
      return { tab: "Phương pháp", methodSub: "phuong-phap" };
    default:
      return { tab: "Tổng quan" };
  }
}

function TabIcon({ tab }: { tab: Tab }) {
  const cls = "h-5 w-5";
  switch (tab) {
    case "Tổng quan":
      return (
        <svg aria-hidden viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9" rx="1.5" />
          <rect x="14" y="3" width="7" height="5" rx="1.5" />
          <rect x="14" y="12" width="7" height="9" rx="1.5" />
          <rect x="3" y="16" width="7" height="5" rx="1.5" />
        </svg>
      );
    case "Vì sao?":
      return (
        <svg aria-hidden viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19h16" />
          <path d="M7 15v-5" />
          <path d="M12 15V7" />
          <path d="M17 15v-3" />
        </svg>
      );
    case "Bất thường":
      return (
        <svg aria-hidden viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3 3 19h18L12 3Z" />
          <path d="M12 10v4" />
          <path d="M12 17h.01" />
        </svg>
      );
    case "Chi tiết mã":
      return (
        <svg aria-hidden viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      );
    case "Phương pháp":
      return (
        <svg aria-hidden viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5v-13Z" />
          <path d="M8 8h8M8 12h6" />
        </svg>
      );
  }
}

const POLL_MS = 20_000;

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export function Dashboard({
  initial,
  requestedDate,
  requestedIndex,
  initialTab,
  initialSym = null,
}: {
  initial: Loaded;
  requestedDate: string | null;
  requestedIndex: string | null;
  initialTab: string | null;
  initialSym?: string | null;
}) {
  const router = useRouter();
  const now = useNow();
  const initRoute = resolveSlug(initialTab);

  const [loaded, setLoaded] = useState<Loaded>(initial);
  const [pollError, setPollError] = useState<string | null>(null);
  const [tab, setTabState] = useState<Tab>(initRoute.tab);
  const [whySub, setWhySub] = useState<WhySub>(initRoute.whySub ?? "nganh");
  const [methodSub, setMethodSub] = useState<MethodSub>(initRoute.methodSub ?? "phuong-phap");
  const [selectedSymbol, setSelectedSymbol] = useState<string>(initialSym?.toUpperCase() ?? "");
  const [filters, setFilters] = useState<Filters>({ sym: "", minSev: "TRUNG BÌNH" });

  useEffect(() => setLoaded(initial), [initial]);

  const updateUrl = useCallback((nextSlug: string, sym?: string) => {
    const u = new URL(window.location.href);
    u.searchParams.set("tab", nextSlug);
    if (sym) u.searchParams.set("sym", sym);
    else u.searchParams.delete("sym");
    window.history.replaceState(null, "", u);
  }, []);

  const setTab = useCallback(
    (t: Tab) => {
      setTabState(t);
      const slug =
        t === "Vì sao?" ? (whySub === "nganh" ? "vi-sao" : whySub)
        : t === "Phương pháp" ? methodSub
        : SLUGS[t];
      updateUrl(slug, t === "Chi tiết mã" ? selectedSymbol || undefined : undefined);
    },
    [whySub, methodSub, selectedSymbol, updateUrl]
  );

  const navigateSlug = useCallback(
    (slug: string) => {
      const r = resolveSlug(slug);
      setTabState(r.tab);
      if (r.whySub) setWhySub(r.whySub);
      if (r.methodSub) setMethodSub(r.methodSub);
      updateUrl(slug);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [updateUrl]
  );

  const openStockDetail = useCallback(
    (symbol: string) => {
      const sym = symbol.toUpperCase();
      setSelectedSymbol(sym);
      setTabState("Chi tiết mã");
      updateUrl("chi-tiet-ma", sym);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [updateUrl]
  );

  // Làm mới định kỳ khi đang xem phiên mới nhất; tạm dừng khi tab trình duyệt ẩn
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

  const live = useLive(!requestedDate);
  const mode = liveMode(live.state, now, live.connected, live.error);
  const liveOn = mode.live ? liveForSnapshot(live.state, loaded.payload.meta) : null;

  useEffect(() => {
    if (requestedDate) return;
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
  }, [liveDay, requestedDate, refresh, loaded.payload.meta.trading_date]);

  const { payload: p, index } = loaded;
  const meta = p.meta;
  const dates = useMemo(
    () => Array.from(new Set(index.sessions.filter((s) => s.source === meta.source).map((s) => s.trading_date))).sort().reverse(),
    [index, meta.source]
  );
  const codes = useMemo(() => Array.from(new Set(index.sessions.map((s) => s.index_code))), [index]);

  const go = (date: string | null, code: string | null) => {
    const qs = new URLSearchParams();
    if (date) qs.set("date", date);
    if (code) qs.set("index", code);
    qs.set("tab", SLUGS[tab]);
    if (tab === "Chi tiết mã" && selectedSymbol) qs.set("sym", selectedSymbol);
    router.push(`/?${qs}`);
  };

  const highAlertCount = p.alerts?.by_severity?.CAO ?? 0;
  const empty = meta.data_status.state === "error" || !p.pulse;
  const showContextualSymFilter =
    (tab === "Vì sao?" && (whySub === "so-lenh" || whySub === "khoi-ngoai")) ||
    tab === "Bất thường" ||
    tab === "Chi tiết mã";

  return (
    <GlossaryProvider onNavigate={navigateSlug}>
      <SiteHeader area="market" compact />
      <StatusBar
        meta={meta}
        nowMs={now}
        notice={loaded.notice}
        pollError={pollError}
        live={
          liveOn
            ? {
                ts: (liveOn.tick ?? liveOn.pulse ?? liveOn.status)?.ts ?? null,
                latencyMs: liveOn.latencyMs,
                simulated: (liveOn.tick ?? liveOn.pulse)?.is_simulated ?? false,
              }
            : null
        }
        liveNote={live.available && !mode.live && live.state.lastMsgAt !== null ? `${mode.reason} — đang hiển thị snapshot.` : null}
      />

      {/* Thanh điều khiển tích hợp: 5 tab chính + Phiên / Chỉ số / Tra cứu ⓘ / Cách đọc (loại bỏ hero 162-245px) */}
      <div className="mx-auto max-w-6xl px-3 pt-3 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-line bg-surface p-1.5 shadow-xs">
          {/* Desktop: 5 tab rõ hành trình */}
          <nav aria-label="Các mục thị trường" className="hidden min-w-0 md:block">
            <div role="tablist" className="flex items-center gap-1">
              {TABS.map((t, i) => (
                <button
                  key={t}
                  id={`tab-${SLUGS[t]}`}
                  type="button"
                  role="tab"
                  aria-selected={tab === t}
                  aria-controls="tabpanel"
                  tabIndex={tab === t ? 0 : -1}
                  onClick={() => setTab(t)}
                  onKeyDown={(e) => {
                    const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
                    if (k === undefined) return;
                    e.preventDefault();
                    const next = TABS[(k + TABS.length) % TABS.length];
                    setTab(next);
                    document.getElementById(`tab-${SLUGS[next]}`)?.focus();
                  }}
                  className={`ui-transition inline-flex min-h-9 items-center gap-1.5 whitespace-nowrap rounded-xl px-3 text-sm ${
                    tab === t
                      ? "bg-accent font-semibold text-on-accent"
                      : "font-medium text-muted hover:bg-surface2 hover:text-fg"
                  }`}
                >
                  <span>{t}</span>
                  {t === "Bất thường" && highAlertCount > 0 ? (
                    <span
                      className={`tnum rounded-full px-1.5 py-0.2 text-[11px] font-bold ${
                        tab === t ? "bg-on-accent/20 text-on-accent" : "bg-fg text-bg"
                      }`}
                    >
                      {highAlertCount}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          </nav>

          {/* Bộ điều khiển toàn cục gọn (luôn thấy trên cả desktop & mobile trong 1 hàng) */}
          <div className="flex w-full flex-wrap items-center justify-between gap-1.5 md:w-auto md:justify-end">
            <div className="flex flex-wrap items-center gap-1.5">
              <select
                aria-label="Chọn chỉ số"
                className="min-h-9 rounded-lg border border-line bg-bg px-2 text-xs font-semibold text-fg sm:text-sm"
                value={requestedIndex ?? meta.index_code}
                onChange={(e) => go(requestedDate, e.target.value)}
              >
                {(codes.length ? codes : [meta.index_code]).map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <select
                aria-label="Chọn phiên giao dịch"
                className="min-h-9 rounded-lg border border-line bg-bg px-2 text-xs text-fg sm:text-sm"
                value={requestedDate ?? ""}
                onChange={(e) => go(e.target.value || null, requestedIndex ?? meta.index_code)}
              >
                <option value="">Mới nhất{meta.trading_date ? ` (${dmy(meta.trading_date)})` : ""}</option>
                {dates.map((d) => (
                  <option key={d} value={d}>{dmy(d)}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <GlossaryButton compact />
              <GuideButton />
            </div>
          </div>
        </div>

        {/* Bộ lọc ngữ cảnh — chỉ xuất hiện khi tab hiện tại thực sự dùng bộ lọc mã / mức cảnh báo */}
        {showContextualSymFilter ? (
          <div className="mt-2.5 flex flex-wrap items-center gap-2 text-xs sm:text-sm">
            <label className="flex items-center gap-1.5">
              <span className="sr-only">Lọc theo mã cổ phiếu</span>
              <input
                aria-label="Lọc theo mã"
                placeholder="Lọc mã (VD: FPT, VCB)…"
                value={filters.sym}
                onChange={(e) => setFilters({ ...filters, sym: e.target.value.trim().toUpperCase() })}
                className="min-h-9 w-44 rounded-xl border border-line bg-surface px-3 text-xs sm:text-sm"
              />
            </label>
            {filters.sym ? (
              <button
                type="button"
                onClick={() => setFilters({ ...filters, sym: "" })}
                className="ui-transition inline-flex min-h-8 items-center gap-1 rounded-full bg-surface2 px-2.5 text-xs font-medium text-fg hover:bg-line"
              >
                <span>Mã: {filters.sym}</span>
                <span aria-hidden>×</span>
              </button>
            ) : null}
            {tab === "Bất thường" && filters.minSev !== "TRUNG BÌNH" ? (
              <button
                type="button"
                onClick={() => setFilters({ ...filters, minSev: "TRUNG BÌNH" })}
                className="ui-transition inline-flex min-h-8 items-center gap-1 rounded-full bg-surface2 px-2.5 text-xs font-medium text-fg hover:bg-line"
              >
                <span>Mức: {filters.minSev === "CAO" ? "Chỉ Cao" : "Tất cả"}</span>
                <span aria-hidden>×</span>
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      <main className="mx-auto min-w-0 max-w-6xl px-3 pb-24 pt-3.5 sm:px-6 md:pb-10">
        <h1 className="sr-only">Nhịp thị trường {meta.index_code} — {tab}</h1>
        <div id="tabpanel" tabIndex={-1} role="tabpanel" aria-labelledby={`tab-${SLUGS[tab]}`}>
          {empty && tab !== "Phương pháp" ? (
            <div role="alert" className="card-elev mx-auto max-w-xl rounded-2xl border border-line bg-surface p-6 text-center">
              <p className="text-lg font-semibold">Chưa có dữ liệu để hiển thị</p>
              <p className="mt-1.5 text-sm text-muted">{meta.data_status.reason}</p>
              {meta.last_update ? (
                <p className="mt-1 text-sm text-muted">
                  Dữ liệu tốt gần nhất: {clock(meta.last_update)} · {dmy(meta.trading_date)}.
                </p>
              ) : null}
              <div className="mt-4 flex justify-center gap-2">
                <button type="button" onClick={() => window.location.reload()} className="min-h-10 rounded-xl bg-accent px-4 text-sm font-medium text-on-accent">
                  Tải lại
                </button>
                <button type="button" onClick={() => setTab("Phương pháp")} className="min-h-10 rounded-xl border border-line px-4 text-sm">
                  Đọc phương pháp
                </button>
              </div>
            </div>
          ) : tab === "Tổng quan" ? (
            <Overview
              p={p}
              f={filters}
              live={liveOn}
              onNavigate={navigateSlug}
              onSelectSymbol={openStockDetail}
              onFilterSev={(sev) => setFilters((prev) => ({ ...prev, minSev: sev }))}
            />
          ) : tab === "Vì sao?" ? (
            <WhyTab
              p={p}
              f={filters}
              sub={whySub}
              onSub={(next) => {
                setWhySub(next);
                updateUrl(next === "nganh" ? "vi-sao" : next);
              }}
              onSelectSymbol={openStockDetail}
              onSwitchIndex={(code) => go(requestedDate, code)}
            />
          ) : tab === "Bất thường" ? (
            <Alerts
              p={p}
              f={filters}
              onSelectSymbol={openStockDetail}
              onFilterSev={(sev) => setFilters((prev) => ({ ...prev, minSev: sev }))}
            />
          ) : tab === "Chi tiết mã" ? (
            <StockDetailTab
              p={p}
              f={filters}
              selectedSymbol={selectedSymbol}
              onSelectSymbol={(sym) => {
                setSelectedSymbol(sym);
                updateUrl("chi-tiet-ma", sym);
              }}
            />
          ) : (
            <MethodTab
              p={p}
              sub={methodSub}
              onSub={(next) => {
                setMethodSub(next);
                updateUrl(next);
              }}
            />
          )}
        </div>
      </main>

      {/* Điều hướng đáy mobile: 5 mục cố định, icon + nhãn 1 dòng, bỏ ngăn kéo "Thêm" */}
      <nav
        aria-label="Điều hướng chính"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur md:hidden"
      >
        <div className="grid grid-cols-5">
          {TABS.map((t) => {
            const active = tab === t;
            return (
              <button
                key={t}
                type="button"
                onClick={() => {
                  setTab(t);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                aria-current={active ? "page" : undefined}
                className={`ui-transition relative flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 text-[11px] leading-tight ${
                  active ? "font-bold text-accent" : "text-muted"
                }`}
              >
                <span className="relative inline-flex">
                  <TabIcon tab={t} />
                  {t === "Bất thường" && highAlertCount > 0 ? (
                    <span className="tnum absolute -right-2.5 -top-1 rounded-full bg-fg px-1 text-[9px] font-bold leading-4 text-bg">
                      {highAlertCount > 99 ? "99+" : highAlertCount}
                    </span>
                  ) : null}
                </span>
                <span className="truncate">{MOBILE_LABEL[t]}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </GlossaryProvider>
  );
}
