"use client";

/** Hướng B "Bản tin": nền sáng kiểu báo tài chính, kể chuyện bằng tiêu đề + chú thích; hợp demo và đọc trên điện thoại. */
import Link from "next/link";
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { Loaded } from "@/lib/data";
import { clock, dmy, num, signed } from "@/lib/format";
import { bnLabel, priceTone, TONE_CLASS } from "@/lib/fmt";
import { formatAge } from "@/lib/status";
import { Change, Disclaimer, IndexLine, PreviewBar, scoreTone, SevTag } from "./shared";
import { usePreview, type PreviewModel, type PreviewState } from "./usePreview";

const WEEKDAY = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

function Dateline({ m }: { m: PreviewModel }) {
  const d = m.p.meta.trading_date ? new Date(`${m.p.meta.trading_date}T12:00:00+07:00`) : null;
  const status = m.kind === "live"
    ? <><span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-up align-middle" aria-hidden /><b>Đang cập nhật trực tiếp</b> · tin lúc {clock(m.liveTs)}, trễ {num(m.latencyS, 1)} giây{m.replay ? " (phát lại mô phỏng)" : ""}</>
    : m.kind === "error" ? <b>Chưa có bản tin: {m.p.meta.data_status.reason}</b>
    : <><b>Ảnh chụp lúc {clock(m.p.meta.snapshot_at ?? m.p.meta.last_update)}</b> · cách đây {formatAge(m.fresh.ageSeconds)} · không phải thời gian thực</>;
  return (
    <div className="border-y-2 border-fg py-2 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <span>{d ? `${WEEKDAY[d.getUTCDay()]}, ${dmy(m.p.meta.trading_date)}` : "—"} · Nguồn: <b className={m.p.meta.is_simulated ? "text-sim" : ""}>{m.p.meta.source_label}</b></span>
        <span role="status" aria-live="polite">{status}</span>
      </div>
      {m.p.meta.is_simulated ? <p className="mt-1 font-semibold text-sim">Số liệu MÔ PHỎNG để trình diễn, không phản ánh thị trường thật.</p> : null}
    </div>
  );
}

function Story({ m }: { m: PreviewModel }) {
  const lines = m.p.pulse?.summary ?? [];
  const top = m.alerts.filter((a) => a.severity === "CAO").slice(0, 4);
  const lead = m.sectors.slice().sort((a, b) => Math.abs(b.contrib ?? 0) - Math.abs(a.contrib ?? 0)).slice(0, 3);
  return (
    <article className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <h2 className="text-[clamp(1.6rem,4.5vw,2.6rem)] font-bold leading-tight tracking-tight [text-wrap:balance]">
          Thị trường {m.label.toLowerCase()}: điểm nhịp <span className={scoreTone(m.score)}>{num(m.score, 1)}</span>/100
        </h2>
        <p className="mt-3 max-w-[68ch] text-lg leading-relaxed text-muted">
          {m.live && m.indexes[0]
            ? m.indexes.map((x) => `${x.code} ${num(x.v)} (${signed(x.pct)}%), ${num(x.adv, 0)} mã tăng / ${num(x.dec, 0)} mã giảm`).join("; ") + "."
            : lines[1] ?? lines[0] ?? "Chưa có nhận định."}
        </p>
        <figure className="mt-6">
          <IndexLine data={m.series} height={240} color="var(--fg)" />
          <figcaption className="mt-1 border-t border-line pt-1 text-sm text-muted"><b className="text-fg">Hình 1.</b> {m.p.index?.code ?? "VN30"} trong phiên, theo phút (ảnh chụp lúc {clock(m.p.meta.snapshot_at ?? m.p.meta.last_update)}).{m.live ? "" : ` ${lines[0] ?? ""}`}</figcaption>
        </figure>
        <h3 className="mt-8 text-xl font-bold">Ngành nào kéo, ngành nào đè</h3>
        <ul className="mt-2 space-y-2 text-base leading-relaxed">
          {lead.map((s) => (
            <li key={s.sector} className="max-w-[68ch]"><b>{s.sector}</b>: <Change value={s.pct} /> bình quân, đóng góp ước lượng{" "}
              <b className={`tnum ${TONE_CLASS[priceTone(s.contrib)]}`}>{signed(s.contrib, 2)} điểm</b> ({s.up} mã tăng, {s.down} mã giảm).</li>
          ))}
        </ul>
        <p className="mt-2 text-sm text-muted">{m.p.sectors?.note}</p>
        <h3 className="mt-8 text-xl font-bold">Điều gì bất thường</h3>
        {top.length ? (
          <ul className="mt-2 divide-y divide-line">
            {top.map((a, i) => (
              <li key={`${a.t}${a.symbol}${i}`} className="py-2"><span className="tnum text-sm text-muted">{a.t.slice(11, 16)}</span> · <b>{a.symbol}</b> — {a.message} <SevTag sev={a.severity} /></li>
            ))}
          </ul>
        ) : <p className="mt-2 text-muted">Chưa có cảnh báo mức cao.</p>}
        <Link href="?state=live&tab=khoi-ngoai" className="mt-4 inline-block font-semibold text-accent underline underline-offset-4">Đọc tiếp: khối ngoại hôm nay →</Link>
      </div>
      <aside className="space-y-4 lg:border-l lg:border-line lg:pl-6">
        <h3 className="text-sm font-bold uppercase tracking-wide">Bảng chỉ số</h3>
        <dl className="divide-y divide-line">
          {m.indexes.map((x) => (
            <div key={x.code} className="flex items-baseline justify-between py-2"><dt className="font-semibold">{x.code}</dt>
              <dd key={`${x.v}`} className={`rounded text-right flash-${(x.ch ?? 0) > 0 ? "up" : (x.ch ?? 0) < 0 ? "down" : "flat"}`}><span className={`tnum text-lg font-semibold ${TONE_CLASS[priceTone(x.ch)]}`}>{num(x.v)}</span><br /><Change value={x.pct} className="text-sm" /></dd></div>
          ))}
        </dl>
        <h3 className="pt-2 text-sm font-bold uppercase tracking-wide">Thành phần điểm nhịp</h3>
        <ul className="space-y-1 text-sm">{m.comps.map((c) => <li key={c.key} className="flex justify-between"><span>{c.name}</span><span className={`tnum ${TONE_CLASS[priceTone(c.value)]}`}>{signed(c.value)}</span></li>)}</ul>
      </aside>
    </article>
  );
}

function ForeignStory({ m }: { m: PreviewModel }) {
  const rows = (m.p.foreign?.rows ?? []).filter((r) => r.net !== null);
  const bars = [...rows.slice(0, 6), ...rows.slice(-6)].map((r) => ({ s: r.symbol, v: (r.net ?? 0) / 1e9 }));
  const fs = m.p.foreign?.summary;
  return (
    <article className="max-w-3xl">
      <h2 className="text-[clamp(1.5rem,4vw,2.3rem)] font-bold leading-tight tracking-tight [text-wrap:balance]">
        Khối ngoại {(fs?.net_val ?? 0) >= 0 ? "mua ròng" : "bán ròng"} <span className={TONE_CLASS[priceTone(fs?.net_val ?? null)]}>{bnLabel(Math.abs(fs?.net_val ?? 0))}</span> trong rổ theo dõi
      </h2>
      <p className="mt-3 text-lg text-muted">{num(fs?.n_net_buy ?? null, 0)} mã mua ròng, {num(fs?.n_net_sell ?? null, 0)} mã bán ròng.</p>
      <figure className="mt-6">
        <div className="h-[360px]" role="img" aria-label="Giá trị mua bán ròng của khối ngoại theo mã">
          <ResponsiveContainer><BarChart data={bars} layout="vertical" margin={{ left: 4, right: 12 }}>
            <XAxis type="number" tickFormatter={(v: number) => `${num(v, 0)} tỷ`} /><YAxis type="category" dataKey="s" width={40} interval={0} />
            <ReferenceLine x={0} stroke="var(--muted)" />
            <Bar dataKey="v" isAnimationActive={false}>{bars.map((b) => <Cell key={b.s} fill={b.v >= 0 ? "var(--up)" : "var(--down)"} />)}</Bar>
          </BarChart></ResponsiveContainer>
        </div>
        <figcaption className="border-t border-line pt-1 text-sm text-muted"><b className="text-fg">Hình 2.</b> Giá trị ròng (tỷ đồng) của 6 mã mua ròng và 6 mã bán ròng mạnh nhất.</figcaption>
      </figure>
      <Link href="?state=live" className="mt-6 inline-block font-semibold text-accent underline underline-offset-4">← Về bản tin chính</Link>
    </article>
  );
}

export function PreviewNews({ initial, state, tab }: { initial: Loaded; state: PreviewState; tab: string | null }) {
  const m = usePreview(initial, state);
  return (
    <div data-skin="news" className="min-h-dvh bg-bg text-fg">
      <PreviewBar variant="b" state={state} tab={tab} />
      <div className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
        <header className="pt-6 pb-3 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Bản tin Nhịp Thị Trường</h1>
          <p className="mt-1 text-sm text-muted">NeoPulse Radar · đọc trong 2 phút</p>
        </header>
        <Dateline m={m} />
        <main className="pt-6">
          {m.kind === "error" ? <p role="alert" className="text-lg">Bản tin sẽ xuất hiện khi có dữ liệu. {m.p.meta.data_status.reason}</p>
            : tab === "khoi-ngoai" ? <ForeignStory m={m} /> : <Story m={m} />}
        </main>
        <footer className="mt-10 border-t border-line pt-3 text-muted"><Disclaimer /></footer>
      </div>
    </div>
  );
}
