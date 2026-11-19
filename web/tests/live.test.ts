import { describe, expect, it } from "vitest";
import { applyLive, emptyLive, liveForSnapshot, liveMode, MAX_POINTS, mergeSeries, parseLive, type LiveMessage } from "../src/lib/live";

// 2026-11-19 (thứ Năm) 10:00 giờ VN
const T0 = Date.UTC(2026, 10, 19, 3, 0, 0);
const iso = (ms: number) => new Date(ms + 7 * 3600_000).toISOString().replace("Z", "+07:00");

function tick(seq: number, ms: number, v = 1800, sim = false): LiveMessage {
  return {
    name: "tick",
    data: {
      ts: iso(ms), source: sim ? "sim" : "ssi", is_simulated: sim, seq, day: "2026-11-19", basis: null,
      ix: { VN30: { v, ch: 1, pct: 0.1, adv: 10, dec: 15, nc: 5, ce: 0, fl: 0 } },
    },
  };
}
const status = (seq: number, ms: number, event: "start" | "end" | "data_gap"): LiveMessage => ({
  name: "status", data: { ts: iso(ms), source: "ssi", is_simulated: false, seq, event },
});

describe("parseLive", () => {
  it("đọc chuỗi JSON từ Ably và từ chối dữ liệu hỏng", () => {
    const raw = JSON.stringify(tick(1, T0).data);
    expect(parseLive("tick", raw)?.data.seq).toBe(1);
    expect(parseLive("tick", "{không phải json")).toBeNull();
    expect(parseLive("tick", JSON.stringify({ ts: "x" }))).toBeNull(); // thiếu seq
    expect(parseLive("lạ", raw)).toBeNull();
    expect(parseLive("status", JSON.stringify({ ts: iso(T0), seq: 2, event: "start" }))?.name).toBe("status");
  });
});

describe("applyLive: thứ tự seq, độ trễ, chuỗi điểm", () => {
  it("tính độ trễ = giờ nhận - ts", () => {
    const s = applyLive(emptyLive(), tick(1, T0), T0 + 1500);
    expect(s.latencyMs).toBe(1500);
    expect(s.tick?.ix.VN30.v).toBe(1800);
  });
  it("bỏ tin đến muộn hoặc trùng (seq không tăng)", () => {
    let s = applyLive(emptyLive(), tick(5, T0, 1801), T0);
    s = applyLive(s, tick(4, T0 - 1000, 1799), T0 + 10); // đến muộn
    s = applyLive(s, tick(5, T0, 1801), T0 + 20); // trùng
    expect(s.tick?.ix.VN30.v).toBe(1801);
    expect(s.dropped).toBe(2);
    expect(s.points.VN30).toHaveLength(1);
  });
  it("run mới reset dữ liệu; run cũ đến muộn bị bỏ", () => {
    const first = tick(900, T0);
    first.data.run = "run1";
    let s = applyLive(emptyLive(), first, T0);
    const start = status(1, T0 + 1000, "start");
    start.data.run = "run2";
    s = applyLive(s, start, T0 + 1000);
    expect(s.lastSeq).toBe(1);
    expect(s.tick).toBeNull();
    expect(s.points).toEqual({});
    const second = tick(2, T0 + 2000, 1810);
    second.data.run = "run2";
    s = applyLive(s, second, T0 + 2000);
    expect(s.tick?.ix.VN30.v).toBe(1810);
    s = applyLive(s, first, T0 + 3000);
    expect(s.run).toBe("run2");
    expect(s.tick?.ix.VN30.v).toBe(1810);
    expect(s.dropped).toBe(1);
  });
  it("seq lùi hơn 50 không phải restart khi thiếu run", () => {
    let s = applyLive(emptyLive(), tick(100, T0), T0);
    s = applyLive(s, tick(2, T0 - 10_000, 1700), T0 + 10);
    expect(s.lastSeq).toBe(100);
    expect(s.tick?.ix.VN30.v).toBe(1800);
    expect(s.dropped).toBe(1);
  });
  it("run mới cần timestamp hợp lệ và mới hơn", () => {
    const first = tick(100, T0);
    first.data.run = "run1";
    const s = applyLive(emptyLive(), first, T0);
    const bad = tick(1, T0);
    bad.data.run = "run2";
    expect(applyLive(s, bad, T0 + 10).run).toBe("run1");
    bad.data.ts = "invalid";
    expect(applyLive(s, bad, T0 + 20).run).toBe("run1");
  });
  it("start phiên mới trong cùng run xóa dữ liệu phiên trước", () => {
    const s = applyLive(emptyLive(), tick(1, T0), T0);
    const next = applyLive(s, status(2, T0 + 1000, "start"), T0 + 1000);
    expect(next.tick).toBeNull();
    expect(next.points).toEqual({});
  });
  it("chuỗi điểm trực tiếp giới hạn MAX_POINTS", () => {
    let s = emptyLive();
    for (let i = 1; i <= MAX_POINTS + 20; i++) s = applyLive(s, tick(i, T0 + i * 1000, 1800 + i), T0 + i * 1000);
    expect(s.points.VN30).toHaveLength(MAX_POINTS);
    expect(s.points.VN30[MAX_POINTS - 1].v).toBe(1800 + MAX_POINTS + 20);
  });
  it("cảnh báo mới từ pulse dồn lên đầu", () => {
    const p = (seq: number, s: string): LiveMessage => ({
      name: "pulse",
      data: { ts: iso(T0), source: "ssi", is_simulated: false, seq, score: 40, label: "x", comps: [], up: [], down: [],
        alerts: [{ t: iso(T0), s, rule: "volume_spike", sev: "CAO", msg: "m" }], n_alerts: 1, index_code: "VN30" },
    });
    let st = applyLive(emptyLive(), p(1, "AAA"), T0);
    st = applyLive(st, p(2, "BBB"), T0);
    expect(st.alerts.map((a) => a.s)).toEqual(["BBB", "AAA"]);
  });
});

describe("liveMode: khi nào hiện TRỰC TIẾP, khi nào quay về snapshot", () => {
  const s = applyLive(emptyLive(), tick(1, T0), T0);
  it("trực tiếp khi kết nối tốt, tin < 60 giây, trong giờ", () => {
    expect(liveMode(s, T0 + 59_000, true, null).live).toBe(true);
  });
  it("quá 60 giây không có tin -> snapshot", () => {
    expect(liveMode(s, T0 + 61_000, true, null)).toEqual({ live: false, reason: "Quá 60 giây không có tin trực tiếp" });
  });
  it("lỗi Ably hoặc chưa kết nối -> snapshot", () => {
    expect(liveMode(s, T0 + 1000, true, "token").live).toBe(false);
    expect(liveMode(s, T0 + 1000, false, null).live).toBe(false);
    expect(liveMode(emptyLive(), T0, true, null).live).toBe(false);
  });
  it("ngoài giờ giao dịch -> snapshot; mô phỏng phát lại thì được miễn giờ", () => {
    const night = Date.UTC(2026, 10, 19, 13, 0, 0); // 20:00 giờ VN
    const real = applyLive(emptyLive(), tick(1, night), night);
    expect(liveMode(real, night + 1000, true, null).live).toBe(false);
    const sim = applyLive(emptyLive(), tick(1, night, 1800, true), night);
    expect(liveMode(sim, night + 1000, true, null).live).toBe(true);
  });
  it("relay báo kết thúc phiên -> snapshot", () => {
    const e = applyLive(s, status(2, T0 + 1000, "end"), T0 + 1000);
    expect(liveMode(e, T0 + 2000, true, null).live).toBe(false);
  });
  it("pulse vẫn tới không xóa data_gap; data_ok mới phục hồi", () => {
    let st = applyLive(s, status(2, T0 + 61_000, "data_gap"), T0 + 61_000);
    const pulse: LiveMessage = { name: "pulse", data: {
      ts: iso(T0 + 70_000), source: "ssi", is_simulated: false, seq: 3, score: 50, label: "x",
      comps: [], up: [], down: [], alerts: [], n_alerts: 0, index_code: "VN30",
    } };
    st = applyLive(st, pulse, T0 + 70_000);
    expect(liveMode(st, T0 + 71_000, true, null).live).toBe(false);
    const ok: LiveMessage = { name: "status", data: { ts: iso(T0 + 72_000), source: "ssi", is_simulated: false, seq: 4, event: "data_ok" } };
    st = applyLive(st, ok, T0 + 72_000);
    expect(liveMode(st, T0 + 72_000, true, null).live).toBe(true);
    pulse.data.data_gap = true;
    expect(liveMode(applyLive(emptyLive(), pulse, T0 + 70_000), T0 + 71_000, true, null).live).toBe(false);
  });
});

describe("liveForSnapshot: không trộn nguồn, phiên hay chỉ số", () => {
  const meta = { source: "ssi", trading_date: "2026-11-19", index_code: "VN30" };
  it("khác nguồn/ngày thì giữ snapshot", () => {
    const s = applyLive(emptyLive(), tick(1, T0), T0);
    expect(liveForSnapshot(s, { ...meta, source: "sim" })).toBeNull();
    expect(liveForSnapshot(s, { ...meta, trading_date: "2026-11-18" })).toBeNull();
    expect(liveForSnapshot(s, meta)?.tick?.ix.VN30.v).toBe(1800);
  });
  it("pulse/cảnh báo VN30 không được áp lên VNINDEX", () => {
    const s = applyLive(emptyLive(), tick(1, T0), T0);
    const pulse: LiveMessage = { name: "pulse", data: {
      ts: iso(T0), source: "ssi", is_simulated: false, seq: 2, day: meta.trading_date,
      score: 12.3, label: "VN30", comps: [], up: [], down: [],
      alerts: [{ t: iso(T0), s: "AAA", rule: "volume_spike", sev: "CAO", msg: "m" }], n_alerts: 1, index_code: "VN30",
    } };
    const st = applyLive(s, pulse, T0);
    expect(liveForSnapshot(st, { ...meta, index_code: "VNINDEX" })?.pulse).toBeNull();
    expect(liveForSnapshot(st, { ...meta, index_code: "VNINDEX" })?.alerts).toEqual([]);
    expect(liveForSnapshot(st, meta)?.pulse?.score).toBe(12.3);
  });
});

describe("mergeSeries", () => {
  it("nối điểm trực tiếp sau điểm nền cuối, bỏ điểm trùng thời gian nền, bỏ null", () => {
    const base = [{ t: iso(T0), value: 1800 }, { t: iso(T0 + 60_000), value: null }, { t: iso(T0 + 120_000), value: 1802 }];
    const live = [{ t: iso(T0 + 60_000), v: 1801 }, { t: iso(T0 + 125_000), v: 1803 }];
    expect(mergeSeries(base, live).map((p) => p.v)).toEqual([1800, 1802, 1803]);
  });
  it("giới hạn số điểm, giữ phần mới nhất", () => {
    const live = Array.from({ length: 30 }, (_, i) => ({ t: iso(T0 + i * 1000), v: i }));
    const out = mergeSeries([], live, 10);
    expect(out).toHaveLength(10);
    expect(out[9].v).toBe(29);
  });
});

import { nextBackoffMs, sseUrl } from "../src/lib/liveTransport";

describe("đường truyền SSE", () => {
  it("địa chỉ SSE mã hóa kênh và token, không chứa khóa gốc", () => {
    const u = new URL(sseUrl("tok.en/+="));
    expect(u.origin).toBe("https://realtime.ably.io");
    expect(u.searchParams.get("channels")).toBe("neopulse:live");
    expect(u.searchParams.get("accessToken")).toBe("tok.en/+=");
    expect(u.searchParams.has("key")).toBe(false);
  });
  it("lùi dần 2s, 4s, ... tối đa 60s", () => {
    expect([1, 2, 3, 6, 10].map(nextBackoffMs)).toEqual([2000, 4000, 8000, 60000, 60000]);
  });
});
