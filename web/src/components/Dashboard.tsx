"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Loaded } from "@/lib/data";
import { dmy } from "@/lib/format";
import type { Severity } from "@/lib/types";
import { liveForSnapshot, liveMode } from "@/lib/live";
import { StatusBar } from "./StatusBar";
import { useLive } from "./useLive";
import { Alerts, Book, Foreign, Futures, Method, Overview, Ranking, Validation, type Filters } from "./tabs";
import { Empty } from "./ui";

const TABS = ["Tổng quan", "Sổ lệnh & thanh khoản", "Khối ngoại", "Phái sinh", "Cảnh báo", "Xếp hạng", "Kiểm chứng & dữ liệu", "Phương pháp & giới hạn"] as const;
type Tab = (typeof TABS)[number];
const SLUGS: Record<Tab, string> = {
  "Tổng quan": "tong-quan", "Sổ lệnh & thanh khoản": "so-lenh", "Khối ngoại": "khoi-ngoai", "Phái sinh": "phai-sinh",
  "Cảnh báo": "canh-bao", "Xếp hạng": "xep-hang", "Kiểm chứng & dữ liệu": "kiem-chung", "Phương pháp & giới hạn": "phuong-phap",
};
const tabFromSlug = (slug: string | null): Tab => TABS.find((t) => SLUGS[t] === slug) ?? "Tổng quan";
const POLL_MS = 20_000;

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState("auto");
  useEffect(() => {
    try {
      const t = localStorage.getItem("np-theme");
      if (t === "light" || t === "dark") {
        setTheme(t);
        document.documentElement.dataset.theme = t;
      }
    } catch {
      /* localStorage có thể bị chặn: bỏ qua */
    }
  }, []);
  const toggle = () => {
    const dark = theme === "dark" || (theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("np-theme", next);
    } catch {
      /* bỏ qua */
    }
  };
  return [theme, toggle];
}

export function Dashboard({ initial, requestedDate, requestedIndex, initialTab }: { initial: Loaded; requestedDate: string | null; requestedIndex: string | null; initialTab: string | null }) {
  const router = useRouter();
  const now = useNow();
  const [theme, toggleTheme] = useTheme();
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

  const isSnapshot = Boolean(loaded.payload.meta.snapshot_at);
  const live = useLive(!requestedDate); // chỉ khi xem phiên mới nhất
  const mode = liveMode(live.state, now, live.connected, live.error);
  const liveOn = mode.live ? liveForSnapshot(live.state, loaded.payload.meta) : null;
  useEffect(() => {
    if (requestedDate || isSnapshot) return; // phiên lịch sử và snapshot tĩnh không đổi: không poll
    const tick = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const id = setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [refresh, requestedDate, isSnapshot]);

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
      <StatusBar
        meta={meta}
        nowMs={now}
        notice={loaded.notice}
        pollError={pollError}
        live={liveOn ? { ts: (liveOn.tick ?? liveOn.pulse ?? liveOn.status)?.ts ?? null, latencyMs: liveOn.latencyMs,
          simulated: (liveOn.tick ?? liveOn.pulse)?.is_simulated ?? false } : null}
        liveNote={live.available && !mode.live && live.state.lastMsgAt !== null ? `${mode.reason} — đang hiển thị snapshot.` : null}
      />
      <header className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-3 px-4 pb-2 pt-4">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight sm:text-2xl">
            <svg viewBox="0 0 32 32" className="h-7 w-7 shrink-0" aria-hidden>
              <rect width="32" height="32" rx="7" fill="var(--accent)" />
              <path d="M6 20a10 10 0 0 1 20 0M16 20l5-8" stroke="var(--on-accent)" strokeWidth="3" fill="none" strokeLinecap="round" />
            </svg>
            NeoPulse Radar
          </h1>
          <p className="text-xs text-muted sm:text-sm">Nhịp thị trường · áp lực sổ lệnh · cảnh báo bất thường nội phiên</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label className="flex items-center gap-1.5">
            <span className="text-muted">Phiên</span>
            <select
              aria-label="Chọn phiên giao dịch"
              className="rounded-md border border-line bg-surface px-2 py-1"
              value={requestedDate ?? ""}
              onChange={(e) => go(e.target.value || null, requestedIndex ?? meta.index_code)}
            >
              <option value="">Mới nhất{meta.trading_date ? ` (${dmy(meta.trading_date)})` : ""}</option>
              {dates.map((d) => <option key={d} value={d}>{dmy(d)}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <span className="text-muted">Chỉ số</span>
            <select
              aria-label="Chọn chỉ số"
              className="rounded-md border border-line bg-surface px-2 py-1"
              value={requestedIndex ?? meta.index_code}
              onChange={(e) => go(requestedDate, e.target.value)}
            >
              {(codes.length ? codes : [meta.index_code]).map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <input
            aria-label="Lọc theo mã"
            placeholder="Lọc mã…"
            value={filters.sym}
            onChange={(e) => setFilters({ ...filters, sym: e.target.value.trim() })}
            className="w-24 rounded-md border border-line bg-surface px-2 py-1"
          />
          <label className="flex items-center gap-1.5">
            <span className="text-muted">Cảnh báo từ</span>
            <select
              aria-label="Ngưỡng mức cảnh báo"
              className="rounded-md border border-line bg-surface px-2 py-1"
              value={filters.minSev}
              onChange={(e) => setFilters({ ...filters, minSev: e.target.value as Severity })}
            >
              <option value="CAO">Mức CAO</option>
              <option value="TRUNG BÌNH">Trung bình trở lên</option>
              <option value="THẤP">Tất cả</option>
            </select>
          </label>
          <button onClick={toggleTheme} className="rounded-md border border-line bg-surface px-2 py-1" aria-label="Đổi giao diện sáng/tối" title={`Giao diện: ${theme}`}>
            <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
              <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M10 3a7 7 0 0 1 0 14z" fill="currentColor" />
            </svg>
          </button>
        </div>
      </header>

      <nav aria-label="Các mục" className="border-y border-line bg-bg">
        <div role="tablist" className="scroll-x mx-auto flex max-w-7xl gap-1 px-4 py-1.5">
          {TABS.map((t, i) => (
            <button
              key={t}
              id={`tab-${SLUGS[t]}`}
              role="tab"
              aria-selected={tab === t}
              aria-controls="tabpanel"
              tabIndex={tab === t ? 0 : -1}
              onClick={() => setTab(t)}
              onKeyDown={(e) => {
                // mẫu tablist WAI-ARIA: mũi tên trái/phải chuyển tab, Home/End về đầu/cuối
                const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
                if (k === undefined) return;
                e.preventDefault();
                const next = TABS[(k + TABS.length) % TABS.length];
                setTab(next);
                document.getElementById(`tab-${SLUGS[next]}`)?.focus();
              }}
              className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm ${tab === t ? "bg-accent font-semibold text-on-accent" : "text-muted hover:bg-surface2 hover:text-fg"}`}
            >
              {t}
            </button>
          ))}
        </div>
      </nav>

      <main id="tabpanel" role="tabpanel" aria-labelledby={`tab-${SLUGS[tab]}`} className="mx-auto min-w-0 max-w-7xl px-4 py-4">
        {empty && tab !== "Phương pháp & giới hạn" ? (
          <Empty>
            <p className="mb-1 font-medium text-fg">Chưa có dữ liệu để hiển thị</p>
            {meta.data_status.reason}
          </Empty>
        ) : tab === "Tổng quan" ? <Overview p={p} f={filters} live={liveOn} />
          : tab === "Sổ lệnh & thanh khoản" ? <Book p={p} f={filters} />
          : tab === "Khối ngoại" ? <Foreign p={p} f={filters} />
          : tab === "Phái sinh" ? <Futures p={p} />
          : tab === "Cảnh báo" ? <Alerts p={p} f={filters} />
          : tab === "Xếp hạng" ? <Ranking p={p} f={filters} />
          : tab === "Kiểm chứng & dữ liệu" ? <Validation p={p} />
          : <Method />}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-2 text-xs text-muted">
        <p className="font-medium text-fg">{meta.disclaimer}</p>
        <p className="mt-1">
          Đồ án học phần Gói phần mềm ứng dụng cho tài chính 1 (UEL). Nguồn: {meta.source_label}. Bản JSON schema v{meta.schema_version}; Python tính, web chỉ hiển thị.
        </p>
      </footer>
    </>
  );
}
