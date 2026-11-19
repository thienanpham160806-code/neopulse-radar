"use client";

/**
 * Lớp dữ liệu DÙNG CHUNG cho 3 bản xem trước giao diện: cùng snapshot, cùng luồng trực tiếp, cùng logic trạng thái.
 * Ba hướng chỉ khác lớp trình bày. Không tính chỉ báo: mọi số lấy từ JSON/tin do Python tạo.
 *
 * Trạng thái minh họa (`?state=`): live = phát lại luồng MÔ PHỎNG do live-relay sinh (public/sample/live_replay.json),
 * hoặc luồng Ably thật nếu đã cấu hình; snapshot = chỉ snapshot; error = giả lập lỗi dữ liệu để xem trạng thái lỗi.
 */
import { useEffect, useMemo, useState } from "react";
import type { Loaded } from "@/lib/data";
import { applyLive, emptyLive, liveMode, parseLive, type LiveMessage, type LiveState, type TickData } from "@/lib/live";
import { freshness, type Freshness } from "@/lib/status";
import type { AlertItem, Num, Payload } from "@/lib/types";
import { useLive } from "../useLive";

export type PreviewState = "live" | "snapshot" | "error";
export type Kind = "live" | "snapshot" | "sim" | "error" | "closed" | "stale";

export interface IndexView { code: string; v: Num; ch: Num; pct: Num; adv: Num; dec: Num; nc: Num; ce: Num; fl: Num }

export interface PreviewModel {
  p: Payload;
  now: number;
  kind: Kind;
  fresh: Freshness;
  live: LiveState | null;
  latencyS: number | null;
  liveTs: string | null;
  replay: boolean;
  /** 4 chỉ số: tick trực tiếp nếu có, không thì dòng chỉ số của snapshot (chỉ có chỉ số đang xem) */
  indexes: IndexView[];
  score: Num;
  label: string;
  comps: { key: string; name: string; weight: number; value: Num }[];
  alerts: AlertItem[];
  sectors: { sector: string; up: number; down: number; pct: Num; contrib: Num }[];
  movers: { up: { s: string; pct: Num; last: Num }[]; down: { s: string; pct: Num; last: Num }[] };
  series: { t: string; v: number }[];
}

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

/** Phát lại tin mô phỏng 1 tin/giây; đổi ts thành "bây giờ" để độ trễ hiển thị như luồng thật (ghi rõ là phát lại). */
function useReplay(enabled: boolean): LiveState | null {
  const [state, setState] = useState<LiveState | null>(null);
  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    (async () => {
      const r = await fetch("/sample/live_replay.json", { cache: "force-cache" });
      if (!r.ok || stop) return;
      const all = (await r.json()).messages as { name: string; data: Record<string, unknown> }[];
      // Phát lại tăng tốc 30x nên relay thấy "khoảng trống" giả giữa các tick mô phỏng: bỏ cờ/tin mất dữ liệu đó
      // (chỉ trong bản xem trước) và bắt đầu từ tick hợp lệ đầu tiên. Luồng thật vẫn giữ nguyên logic CX-007.
      const messages = all
        .filter((m) => !(m.name === "status" && (m.data.event === "data_gap" || m.data.event === "data_ok")))
        .map((m) => ({ ...m, data: { ...m.data, data_gap: false } }));
      let i = Math.max(0, messages.findIndex((m) => m.name === "tick"));
      let loop = 0;
      let s = emptyLive();
      const step = () => {
        if (stop) return;
        if (i >= messages.length) {
          i = 0;
          loop += 1;
        }
        const raw = messages[i++];
        const m = parseLive(raw.name, raw.data);
        if (m) {
          const recv = Date.now();
          const d = { ...m.data, ts: new Date(recv - 400 + 7 * 3600_000).toISOString().replace("Z", "+07:00"),
            run: `replay-${loop}`, seq: i + loop * messages.length };
          s = applyLive(s, { ...m, data: d } as LiveMessage, recv);
          setState(s);
        }
        timer = setTimeout(step, m?.name === "tick" ? 1000 : 150);
      };
      step();
    })().catch(() => undefined);
    return () => {
      stop = true;
      if (timer) clearTimeout(timer);
    };
  }, [enabled]);
  return state;
}

function errorPayload(p: Payload): Payload {
  return { meta: { ...p.meta, data_status: { ...p.meta.data_status, state: "error",
    reason: "Không đọc được dữ liệu: tệp snapshot hỏng hoặc bộ ghi chưa chạy (trạng thái minh họa)." } } };
}

const ORDER = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"];

export function usePreview(initial: Loaded, state: PreviewState): PreviewModel {
  const now = useNow();
  const real = useLive(state === "live");
  const replay = useReplay(state === "live" && !real.available);
  const p = state === "error" ? errorPayload(initial.payload) : initial.payload;

  const liveState = real.available ? real.state : replay;
  const mode = liveState ? liveMode(liveState, now, real.available ? real.connected : true, real.available ? real.error : null) : null;
  const src = liveState ? (liveState.tick ?? liveState.pulse ?? liveState.status)?.source : undefined;
  const live = state === "live" && mode?.live && src === p.meta.source ? liveState : null;

  return useMemo(() => {
    const fresh = freshness(p.meta, now);
    const kind: Kind = p.meta.data_status.state === "error" ? "error"
      : live ? "live"
      : p.meta.is_simulated ? "sim"
      : fresh.level === "closed" ? "closed"
      : fresh.level === "red" ? "stale" : "snapshot";
    const tick: TickData | null = live?.tick ?? null;
    const code = p.index?.code ?? p.meta.index_code;
    const indexes: IndexView[] = tick
      ? ORDER.filter((c) => tick.ix[c]).map((c) => ({ code: c, ...tick.ix[c] }))
      : p.index?.row ? [{ code, v: p.index.row.value, ch: p.index.row.change, pct: p.index.row.pct_change,
          adv: p.index.row.advances, dec: p.index.row.declines, nc: p.index.row.no_change, ce: p.index.row.n_ceiling,
          fl: p.index.row.n_floor }] : [];
    const lp = live?.pulse && live.pulse.index_code === code ? live.pulse : null;
    const liveAlerts: AlertItem[] = (live?.alerts ?? []).map((a) => ({ t: a.t, symbol: a.s, rule: a.rule,
      rule_name: p.alerts?.rule_names[a.rule] ?? a.rule, severity: a.sev, message: a.msg, value: null, threshold: null }));
    const rank = p.ranking ?? [];
    const byPct = [...rank].filter((r) => r.pct_change !== null).sort((a, b) => (b.pct_change ?? 0) - (a.pct_change ?? 0));
    const base = (p.pulse?.series ?? []).filter((r) => r.index !== null).map((r) => ({ t: r.t, v: r.index as number }));
    // phát lại mô phỏng: điểm lấy từ giữa phiên nhưng giờ đã đổi thành "bây giờ" -> không nối vào đồ thị (tránh gãy giả)
    const pts = live && !real.available ? [] : live?.points[code] ?? [];
    const lastBase = base.length ? Date.parse(base[base.length - 1].t) : -Infinity;
    return {
      p, now, kind, fresh, live,
      latencyS: live?.latencyMs != null ? live.latencyMs / 1000 : null,
      liveTs: (live?.tick ?? live?.pulse)?.ts ?? null,
      replay: Boolean(live && !real.available),
      indexes,
      score: lp ? lp.score : p.pulse?.score ?? null,
      label: lp ? lp.label : p.pulse?.label ?? "Không đủ dữ liệu",
      comps: lp ? lp.comps.map((c) => ({ key: c.k, name: c.n, weight: c.w, value: c.v })) : p.pulse?.components ?? [],
      alerts: [...liveAlerts, ...(p.alerts?.items ?? [])],
      sectors: lp?.sec?.length
        ? lp.sec.map((r) => ({ sector: r.n, up: r.u, down: r.d, pct: r.p, contrib: r.c }))
        : (p.sectors?.rows ?? []).map((r) => ({ sector: r.sector, up: r.n_up, down: r.n_down, pct: r.pct_cap, contrib: r.contrib_pts })),
      movers: lp ? { up: lp.up, down: lp.down } : {
        up: byPct.slice(0, 5).map((r) => ({ s: r.symbol, pct: r.pct_change, last: r.last })),
        down: byPct.slice(-5).reverse().map((r) => ({ s: r.symbol, pct: r.pct_change, last: r.last })),
      },
      series: [...base, ...pts.filter((q) => Date.parse(q.t) > lastBase)],
    };
  }, [p, now, live, real.available]);
}
