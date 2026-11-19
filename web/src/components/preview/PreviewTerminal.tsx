"use client";

/** Hướng A "Terminal": nền tối, mật độ cao, mọi số quan trọng trên một màn hình, cho người theo dõi liên tục. */
import Link from "next/link";
import type { Loaded } from "@/lib/data";
import { clock, dmy, num, signed } from "@/lib/format";
import { bnLabel, priceTone, TONE_CLASS } from "@/lib/fmt";
import { formatAge } from "@/lib/status";
import { Change, Disclaimer, IndexLine, PreviewBar, scoreTone, SevTag } from "./shared";
import { usePreview, type PreviewModel, type PreviewState } from "./usePreview";

function Status({ m }: { m: PreviewModel }) {
  const dot = { live: "bg-up", snapshot: "bg-accent", sim: "bg-sim", error: "bg-fg", closed: "bg-muted", stale: "bg-warn" }[m.kind];
  const text = m.kind === "live"
    ? <>TRỰC TIẾP · tin {clock(m.liveTs)} · trễ {num(m.latencyS, 1)} s{m.replay ? " · phát lại mô phỏng" : ""}</>
    : m.kind === "error" ? <>LỖI DỮ LIỆU · {m.p.meta.data_status.reason}</>
    : <>SNAPSHOT {clock(m.p.meta.snapshot_at ?? m.p.meta.last_update)} · cách đây {formatAge(m.fresh.ageSeconds)} · không phải thời gian thực</>;
  return (
    <div role="status" aria-live="polite" className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-3 py-1.5 text-xs">
      <span className="flex items-center gap-1.5 font-semibold"><span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />{text}</span>
      <span className="text-muted">Nguồn <b className={m.p.meta.is_simulated ? "text-sim" : "text-fg"}>{m.p.meta.source_label}</b></span>
      <span className="text-muted">Phiên <b className="text-fg">{dmy(m.p.meta.trading_date)}</b></span>
      <span className="text-muted">Mã tính/loại <b className="tnum text-fg">{m.p.meta.n_symbols_computed}/{m.p.meta.n_symbols_excluded}</b></span>
      {m.p.meta.is_simulated ? <span className="rounded bg-sim px-1.5 font-bold text-bg">MÔ PHỎNG</span> : null}
    </div>
  );
}

function Panel({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 border border-line bg-surface ${className}`}>
      <h2 className="border-b border-line px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-muted">{title}</h2>
      <div className="p-2.5">{children}</div>
    </section>
  );
}

function Overview({ m }: { m: PreviewModel }) {
  return (
    <div className="grid grid-cols-1 gap-2 lg:grid-cols-12">
      <div className={`grid grid-cols-2 gap-px border border-line bg-line lg:col-span-12 ${m.indexes.length >= 4 ? "md:grid-cols-4" : m.indexes.length === 3 ? "md:grid-cols-3" : ""}`}>
        {m.indexes.map((x) => (
          <div key={x.code} className="bg-surface px-3 py-2">
            <div className="flex items-baseline justify-between text-xs text-muted"><span className="font-semibold text-fg">{x.code}</span>
              <span className="tnum"><span className="text-up">▲{num(x.adv, 0)}</span> <span className="text-refc">■{num(x.nc, 0)}</span> <span className="text-down">▼{num(x.dec, 0)}</span></span></div>
            <div key={`${x.v}`} className={`tnum rounded text-2xl font-semibold ${TONE_CLASS[priceTone(x.ch)]} flash-${(x.ch ?? 0) > 0 ? "up" : (x.ch ?? 0) < 0 ? "down" : "flat"}`}>{num(x.v)}</div>
            <div className="text-xs"><Change value={x.ch} unit=" đ" /> · <Change value={x.pct} /></div>
          </div>
        ))}
      </div>
      <Panel title="Điểm nhịp" className="lg:col-span-3">
        <div className="flex items-end gap-2"><span className={`tnum text-5xl font-bold leading-none ${scoreTone(m.score)}`}>{num(m.score, 1)}</span><span className="pb-1 text-sm">/100 · {m.label}</span></div>
        <ul className="mt-3 space-y-1.5 text-xs">
          {m.comps.map((c) => (
            <li key={c.key} className="grid grid-cols-[1fr_auto] items-center gap-2">
              <span>{c.name} <span className="text-muted">{Math.round(c.weight * 100)}%</span></span>
              <span className={`tnum ${TONE_CLASS[priceTone(c.value)]}`}>{signed(c.value)}</span>
              <div className="col-span-2 h-1 bg-surface2"><div className="h-1" style={{ width: `${Math.abs(c.value ?? 0) * 100}%`, background: (c.value ?? 0) >= 0 ? "var(--up)" : "var(--down)" }} /></div>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title={`${m.p.index?.code ?? "VN30"} trong phiên`} className="lg:col-span-5"><IndexLine data={m.series} height={210} /></Panel>
      <Panel title={`Cảnh báo · ${m.alerts.length}`} className="lg:col-span-4">
        <ul className="max-h-[220px] space-y-1 overflow-y-auto text-xs">
          {m.alerts.slice(0, 14).map((a, i) => (
            <li key={`${a.t}${a.symbol}${a.rule}${i}`} className="grid grid-cols-[3rem_2.6rem_1fr_auto] items-center gap-1.5 border-b border-line pb-1">
              <time className="tnum text-muted">{a.t.slice(11, 16)}</time><b>{a.symbol}</b><span className="truncate">{a.rule_name}</span><SevTag sev={a.severity} />
            </li>
          ))}
        </ul>
        <Link href="?state=live&tab=canh-bao" className="mt-2 inline-block text-xs text-accent underline-offset-2 hover:underline">Xem tất cả cảnh báo →</Link>
      </Panel>
      <Panel title="Ngành · đóng góp điểm (ước lượng)" className="lg:col-span-6">
        <table className="w-full text-xs"><tbody>
          {m.sectors.map((s) => (
            <tr key={s.sector} className="border-b border-line">
              <td className="py-1">{s.sector}</td>
              <td className="tnum py-1 text-right"><span className="text-up">▲{s.up}</span> <span className="text-down">▼{s.down}</span></td>
              <td className="py-1 text-right"><Change value={s.pct} /></td>
              <td className={`tnum py-1 text-right font-semibold ${TONE_CLASS[priceTone(s.contrib)]}`}>{signed(s.contrib, 2)}</td>
            </tr>
          ))}
        </tbody></table>
      </Panel>
      <Panel title="Tăng / giảm mạnh nhất trong rổ" className="lg:col-span-3">
        <div className="grid grid-cols-2 gap-2 text-xs">
          {(["up", "down"] as const).map((k) => (
            <ul key={k} className="space-y-1">{m.movers[k].map((r) => <li key={r.s} className="flex justify-between"><b>{r.s}</b><Change value={r.pct} /></li>)}</ul>
          ))}
        </div>
      </Panel>
      <Panel title="Khối ngoại (rổ)" className="lg:col-span-3">
        <div className={`tnum text-xl font-semibold ${TONE_CLASS[priceTone(m.p.foreign?.summary?.net_val ?? null)]}`}>{bnLabel(m.p.foreign?.summary?.net_val ?? null)}</div>
        <p className="text-xs text-muted">{num(m.p.foreign?.summary?.n_net_buy ?? null, 0)} mã mua ròng · {num(m.p.foreign?.summary?.n_net_sell ?? null, 0)} mã bán ròng</p>
        {m.p.futures?.state ? <p className="mt-2 text-xs">Basis {m.p.futures.state.symbol}: <b className="tnum">{signed(m.p.futures.state.basis)} điểm</b></p> : null}
      </Panel>
    </div>
  );
}

function AlertsScreen({ m }: { m: PreviewModel }) {
  return (
    <Panel title={`Tất cả cảnh báo · ${m.alerts.length}`}>
      <div className="scroll-x"><table className="w-full min-w-[640px] text-xs">
        <thead><tr className="text-left text-muted"><th className="py-1 font-medium">Giờ</th><th className="font-medium">Mã</th><th className="font-medium">Mức</th><th className="font-medium">Loại</th><th className="font-medium">Nội dung</th></tr></thead>
        <tbody>{m.alerts.map((a, i) => (
          <tr key={`${a.t}${a.symbol}${a.rule}${i}`} className="border-t border-line"><td className="tnum py-1 text-muted">{a.t.slice(11, 16)}</td><td className="font-semibold">{a.symbol}</td><td><SevTag sev={a.severity} /></td><td>{a.rule_name}</td><td className="text-muted">{a.message}</td></tr>
        ))}</tbody>
      </table></div>
    </Panel>
  );
}

export function PreviewTerminal({ initial, state, tab }: { initial: Loaded; state: PreviewState; tab: string | null }) {
  const m = usePreview(initial, state);
  return (
    <div data-skin="terminal" className="min-h-dvh bg-bg text-fg">
      <PreviewBar variant="a" state={state} tab={tab} />
      <header className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <h1 className="text-base font-bold tracking-tight">NeoPulse Radar <span className="font-normal text-muted">· nhịp thị trường trong phiên</span></h1>
        <nav aria-label="Màn hình" className="flex gap-1 text-xs">
          {[["", "Tổng quan"], ["canh-bao", "Cảnh báo"]].map(([k, label]) => (
            <Link key={k} href={k ? `?state=${state}&tab=${k}` : `?state=${state}`} aria-current={(tab ?? "") === k ? "page" : undefined}
              className={`border px-2 py-1 ${(tab ?? "") === k ? "border-accent text-accent" : "border-line text-muted hover:text-fg"}`}>{label}</Link>
          ))}
        </nav>
      </header>
      <Status m={m} />
      <main className="p-2">
        {m.kind === "error" ? (
          <div role="alert" className="border border-line bg-surface p-6 text-sm"><b>Không có dữ liệu để hiển thị.</b> {m.p.meta.data_status.reason}</div>
        ) : tab === "canh-bao" ? <AlertsScreen m={m} /> : <Overview m={m} />}
      </main>
      <footer className="px-3 pb-4 text-muted"><Disclaimer /></footer>
    </div>
  );
}
