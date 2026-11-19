/**
 * Chế độ TRỰC TIẾP (Ably kênh `neopulse:live`): xử lý tin tick/pulse/status do `neopulse live-relay` phát.
 * Hàm thuần để kiểm thử; mọi con số đã do Python tính, ở đây chỉ chọn tin mới nhất và nối chuỗi.
 */
import { sessionPhase } from "./status";
import type { Num } from "./types";

export const LIVE_STALE_MS = 60_000;
export const MAX_POINTS = 5_000;

export interface Envelope {
  ts: string;
  source: string;
  is_simulated: boolean;
  seq: number;
}
export interface IndexTick { v: Num; ch: Num; pct: Num; adv: Num; dec: Num; nc: Num; ce: Num; fl: Num }
export interface TickData extends Envelope {
  day: string;
  ix: Record<string, IndexTick>;
  basis: { sym: string; f: Num; s: Num; b: Num; bp: Num; dtm: Num } | null;
}
export interface LiveAlert { t: string; s: string; rule: string; sev: "CAO" | "TRUNG BÌNH" | "THẤP"; msg: string }
export interface PulseData extends Envelope {
  score: Num;
  label: string;
  comps: { k: string; n: string; w: number; v: Num }[];
  up: { s: string; pct: Num; last: Num }[];
  down: { s: string; pct: Num; last: Num }[];
  alerts: LiveAlert[];
  n_alerts: number;
  index_code: string;
}
export interface StatusData extends Envelope {
  event: "start" | "end" | "phase" | "data_gap" | "data_ok";
  phase?: string;
  age_s?: Num;
  day?: string;
}
export type LiveMessage =
  | { name: "tick"; data: TickData }
  | { name: "pulse"; data: PulseData }
  | { name: "status"; data: StatusData };

export interface Point { t: string; v: number }

export interface LiveState {
  lastSeq: number;
  tick: TickData | null;
  pulse: PulseData | null;
  status: StatusData | null;
  alerts: LiveAlert[];
  /** chuỗi điểm trực tiếp theo mã chỉ số, tối đa MAX_POINTS mỗi mã */
  points: Record<string, Point[]>;
  lastMsgAt: number | null;
  latencyMs: number | null;
  dropped: number;
}

export const emptyLive = (): LiveState => ({
  lastSeq: 0, tick: null, pulse: null, status: null, alerts: [], points: {}, lastMsgAt: null, latencyMs: null, dropped: 0,
});

/** Ably trả `data` là chuỗi JSON (relay gửi chuỗi); chấp nhận cả object. Sai định dạng -> null. */
export function parseLive(name: string, raw: unknown): LiveMessage | null {
  let data: unknown = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (typeof data !== "object" || data === null) return null;
  const d = data as Record<string, unknown>;
  if (typeof d.seq !== "number" || typeof d.ts !== "string") return null;
  if (name === "tick" && typeof d.ix === "object" && d.ix !== null) return { name, data: d as unknown as TickData };
  if (name === "pulse") return { name, data: d as unknown as PulseData };
  if (name === "status" && typeof d.event === "string") return { name, data: d as unknown as StatusData };
  return null;
}

/**
 * Áp một tin vào trạng thái. seq tăng dần trên toàn kênh: tin đến muộn (seq <= đã thấy) bị bỏ, đếm vào `dropped`.
 * Relay khởi động lại thì seq về 1: nhận ra qua tin status "start" hoặc seq lùi hẳn (> 50) và đặt lại.
 */
export function applyLive(s: LiveState, m: LiveMessage, recvMs: number): LiveState {
  const seq = m.data.seq;
  const restart = (m.name === "status" && m.data.event === "start") || seq < s.lastSeq - 50;
  if (!restart && seq <= s.lastSeq) return { ...s, dropped: s.dropped + 1 };
  const sent = Date.parse(m.data.ts);
  const next: LiveState = {
    ...s,
    lastSeq: seq,
    lastMsgAt: recvMs,
    latencyMs: Number.isNaN(sent) ? s.latencyMs : Math.max(0, recvMs - sent),
  };
  if (m.name === "tick") {
    next.tick = m.data;
    const points = { ...s.points };
    for (const [code, ix] of Object.entries(m.data.ix)) {
      if (ix.v === null) continue;
      const arr = [...(points[code] ?? []), { t: m.data.ts, v: ix.v }];
      points[code] = arr.length > MAX_POINTS ? arr.slice(arr.length - MAX_POINTS) : arr;
    }
    next.points = points;
  } else if (m.name === "pulse") {
    next.pulse = m.data;
    if (m.data.alerts.length) next.alerts = [...m.data.alerts.slice().reverse(), ...s.alerts].slice(0, 200);
  } else {
    next.status = m.data;
  }
  return next;
}

export type LiveMode = { live: true; reason: string } | { live: false; reason: string };

/** Hiện TRỰC TIẾP chỉ khi: kết nối tốt, có tin trong 60 giây, đang giờ giao dịch (mô phỏng phát lại được miễn giờ). */
export function liveMode(s: LiveState, nowMs: number, connected: boolean, error: string | null): LiveMode {
  if (error) return { live: false, reason: `Lỗi kết nối trực tiếp: ${error}` };
  if (!connected) return { live: false, reason: "Chưa kết nối kênh trực tiếp" };
  if (s.lastMsgAt === null) return { live: false, reason: "Chưa nhận tin trực tiếp nào" };
  if (nowMs - s.lastMsgAt > LIVE_STALE_MS) return { live: false, reason: "Quá 60 giây không có tin trực tiếp" };
  const sim = (s.tick ?? s.pulse ?? s.status)?.is_simulated ?? false;
  if (!sim && sessionPhase(nowMs) !== "open") return { live: false, reason: "Ngoài giờ giao dịch" };
  if (s.status?.event === "end") return { live: false, reason: "Bộ phát đã kết thúc phiên" };
  return { live: true, reason: "Đang nhận tin trực tiếp" };
}

/** Chuỗi nền (snapshot, theo phút) + điểm trực tiếp sau điểm nền cuối; tối đa `max` điểm (giữ phần mới nhất). */
export function mergeSeries(base: { t: string; value: Num }[], live: Point[], max = MAX_POINTS): Point[] {
  const b: Point[] = base.filter((p) => p.value !== null).map((p) => ({ t: p.t, v: p.value as number }));
  const lastBase = b.length ? Date.parse(b[b.length - 1].t) : -Infinity;
  const tail = live.filter((p) => Date.parse(p.t) > lastBase);
  const all = [...b, ...tail];
  return all.length > max ? all.slice(all.length - max) : all;
}
