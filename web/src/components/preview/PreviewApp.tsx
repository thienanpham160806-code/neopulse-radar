"use client";

/** Hướng C "Ứng dụng": thẻ, ưu tiên điện thoại, ít số mỗi màn hình, chạm để đi sâu. */
import Link from "next/link";
import type { Loaded } from "@/lib/data";
import { clock, num, signed } from "@/lib/format";
import { bnLabel, priceTone, TONE_CLASS } from "@/lib/fmt";
import { formatAge } from "@/lib/status";
import { Change, Disclaimer, IndexLine, PreviewBar, scoreTone, SevTag } from "./shared";
import { usePreview, type PreviewModel, type PreviewState } from "./usePreview";

function Chevron() {
  return <svg viewBox="0 0 20 20" className="h-5 w-5 text-muted" aria-hidden><path d="M7 4l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>;
}

function Card({ href, title, children }: { href?: string; title: string; children: React.ReactNode }) {
  const body = (
    <>
      <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-muted">{title}</h2>{href ? <Chevron /> : null}</div>
      <div className="mt-2">{children}</div>
    </>
  );
  const cls = "block rounded-2xl bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.06),0_4px_16px_rgba(15,23,42,0.06)]";
  return href ? <Link href={href} className={`${cls} active:scale-[0.99] transition-transform`}>{body}</Link> : <section className={cls}>{body}</section>;
}

function StatusChip({ m }: { m: PreviewModel }) {
  const cfg = {
    live: ["bg-up", `Trực tiếp · trễ ${num(m.latencyS, 1)} giây${m.replay ? " · phát lại mô phỏng" : ""}`],
    snapshot: ["bg-accent", `Ảnh chụp ${clock(m.p.meta.snapshot_at ?? m.p.meta.last_update)} · cách đây ${formatAge(m.fresh.ageSeconds)}`],
    sim: ["bg-sim", `Mô phỏng · ảnh chụp ${clock(m.p.meta.snapshot_at ?? m.p.meta.last_update)}`],
    closed: ["bg-muted", "Phiên đã kết thúc"], stale: ["bg-warn", "Dữ liệu cũ"], error: ["bg-fg", "Lỗi dữ liệu"],
  }[m.kind];
  return (
    <div role="status" aria-live="polite" className="inline-flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-sm shadow-sm">
      <span className={`h-2.5 w-2.5 rounded-full ${cfg[0]}`} aria-hidden />{cfg[1]}
    </div>
  );
}

function Home({ m, q }: { m: PreviewModel; q: (t: string) => string }) {
  const main = m.indexes.find((x) => x.code === (m.p.index?.code ?? "VN30")) ?? m.indexes[0];
  const sev = { CAO: 0, "TRUNG BÌNH": 0, THẤP: 0 } as Record<string, number>;
  m.alerts.forEach((a) => (sev[a.severity] = (sev[a.severity] ?? 0) + 1));
  const lead = m.sectors[0];
  return (
    <div className="space-y-3">
      <Card title="Nhịp thị trường">
        <div className="flex items-end gap-3"><span className={`tnum text-6xl font-bold leading-none ${scoreTone(m.score)}`}>{num(m.score, 0)}</span>
          <span className="pb-1 text-lg font-medium">{m.label}</span></div>
      </Card>
      {main ? (
        <Card title={main.code} href={q("chi-so")}>
          <div key={`${main.v}`} className={`tnum rounded text-4xl font-semibold ${TONE_CLASS[priceTone(main.ch)]} flash-${(main.ch ?? 0) > 0 ? "up" : (main.ch ?? 0) < 0 ? "down" : "flat"}`}>{num(main.v)}</div>
          <div className="text-base"><Change value={main.pct} /></div>
        </Card>
      ) : null}
      <Card title="Cảnh báo" href={q("canh-bao")}>
        <div className="flex gap-4 text-base"><span><b className="tnum text-2xl">{sev.CAO}</b> mức cao</span><span className="text-muted"><b className="tnum text-2xl text-fg">{sev["TRUNG BÌNH"]}</b> trung bình</span></div>
      </Card>
      {lead ? (
        <Card title="Ngành ảnh hưởng nhất" href={q("nganh")}>
          <div className="text-xl font-semibold">{lead.sector}</div>
          <div className="text-base"><b className={`tnum ${TONE_CLASS[priceTone(lead.contrib)]}`}>{signed(lead.contrib, 1)} điểm</b> <span className="text-muted">(ước lượng)</span></div>
        </Card>
      ) : null}
      <Card title="Khối ngoại trong rổ">
        <div className={`tnum text-2xl font-semibold ${TONE_CLASS[priceTone(m.p.foreign?.summary?.net_val ?? null)]}`}>{bnLabel(m.p.foreign?.summary?.net_val ?? null)}</div>
      </Card>
    </div>
  );
}

function Detail({ m, tab }: { m: PreviewModel; tab: string }) {
  if (tab === "canh-bao") {
    return (
      <ul className="space-y-2">
        {m.alerts.slice(0, 40).map((a, i) => (
          <li key={`${a.t}${a.symbol}${a.rule}${i}`}>
            <details className="rounded-2xl bg-surface p-4 shadow-sm">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2">
                <span><b className="text-lg">{a.symbol}</b> <span className="text-muted">· {a.rule_name}</span></span><SevTag sev={a.severity} />
              </summary>
              <p className="mt-2 text-sm">{a.message}</p><p className="tnum mt-1 text-xs text-muted">Lúc {a.t.slice(11, 16)}</p>
            </details>
          </li>
        ))}
      </ul>
    );
  }
  if (tab === "nganh") {
    return (
      <ul className="space-y-2">{m.sectors.map((s) => (
        <li key={s.sector} className="flex items-center justify-between rounded-2xl bg-surface p-4 shadow-sm">
          <span><b>{s.sector}</b><br /><span className="text-sm"><span className="text-up">▲{s.up}</span> · <span className="text-down">▼{s.down}</span> · <Change value={s.pct} /></span></span>
          <b className={`tnum text-lg ${TONE_CLASS[priceTone(s.contrib)]}`}>{signed(s.contrib, 1)}</b>
        </li>))}
        <li className="px-1 text-xs text-muted">{m.p.sectors?.note}</li>
      </ul>
    );
  }
  return (
    <div className="space-y-3">
      <section className="rounded-2xl bg-surface p-4 shadow-sm"><IndexLine data={m.series} height={220} /></section>
      {m.indexes.map((x) => (
        <section key={x.code} className="flex items-center justify-between rounded-2xl bg-surface p-4 shadow-sm">
          <b>{x.code}</b><span className="text-right"><span className={`tnum text-lg font-semibold ${TONE_CLASS[priceTone(x.ch)]}`}>{num(x.v)}</span><br /><Change value={x.pct} className="text-sm" /></span>
        </section>
      ))}
    </div>
  );
}

const TITLES: Record<string, string> = { "canh-bao": "Cảnh báo", nganh: "Ngành trong phiên", "chi-so": "Chỉ số" };

export function PreviewApp({ initial, state, tab }: { initial: Loaded; state: PreviewState; tab: string | null }) {
  const m = usePreview(initial, state);
  const q = (t: string) => `?state=${state}${t ? `&tab=${t}` : ""}`;
  const active = tab && TITLES[tab] ? tab : "";
  return (
    <div data-skin="app" className="min-h-dvh bg-bg pb-24 text-fg">
      <PreviewBar variant="c" state={state} tab={tab} />
      <div className="mx-auto max-w-md px-4">
        <header className="flex items-center gap-2 pt-4 pb-3">
          {active ? <Link href={q("")} aria-label="Quay lại tổng quan" className="-ml-1 rounded-full p-1"><svg viewBox="0 0 20 20" className="h-6 w-6" aria-hidden><path d="M13 4l-6 6 6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg></Link> : null}
          <h1 className="text-2xl font-bold tracking-tight">{active ? TITLES[active] : "NeoPulse"}</h1>
        </header>
        <StatusChip m={m} />
        {m.p.meta.is_simulated ? <p className="mt-2 rounded-xl bg-sim/15 px-3 py-2 text-sm font-semibold text-sim">Dữ liệu MÔ PHỎNG, không phải thị trường thật.</p> : null}
        <main className="mt-3">
          {m.kind === "error"
            ? <div role="alert" className="rounded-2xl bg-surface p-6 text-center"><p className="text-lg font-semibold">Chưa có dữ liệu</p><p className="mt-1 text-sm text-muted">{m.p.meta.data_status.reason}</p></div>
            : active ? <Detail m={m} tab={active} /> : <Home m={m} q={q} />}
        </main>
        <footer className="mt-6 text-muted"><Disclaimer /></footer>
      </div>
      <nav aria-label="Điều hướng chính" className="fixed inset-x-0 bottom-0 border-t border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto grid max-w-md grid-cols-3">
          {[["", "Tổng quan"], ["canh-bao", "Cảnh báo"], ["nganh", "Ngành"]].map(([k, label]) => (
            <Link key={k} href={q(k)} aria-current={active === k ? "page" : undefined}
              className={`py-3 text-center text-sm ${active === k ? "font-semibold text-accent" : "text-muted"}`}>{label}</Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
