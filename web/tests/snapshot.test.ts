import { describe, expect, it } from "vitest";
import { decide } from "../src/lib/auth";
import { freshness, snapshotFreshness } from "../src/lib/status";
import type { Meta } from "../src/lib/types";

// 2026-11-19 là thứ Năm; 15:30 giờ VN = 08:30 UTC.
const at = (hh: number, mm: number, day = 19) => Date.UTC(2026, 10, day, hh - 7, mm, 0);
const iso = (ms: number) => new Date(ms + 7 * 3600_000).toISOString().replace("Z", "+07:00");

function snap(over: Partial<Meta> = {}, snapAt = at(15, 30), kind: Meta["snapshot_kind"] = "end_of_session"): Meta {
  return {
    schema_version: 1, source: "ssi", source_label: "SSI FastConnect (dữ liệu thật)", is_simulated: false,
    generated_at: iso(snapAt), last_update: iso(at(15, 0)), trading_date: "2026-11-19", index_code: "VN30",
    data_status: { state: "closed", reason: "Phiên đã kết thúc.", phase: "closed", age_seconds: 1800, stale_after_seconds: 120 },
    n_symbols_computed: 30, n_symbols_excluded: 0, excluded_reason: null, n_sessions: 5, n_history_sessions: 4,
    available_dates: [], order_value_vnd: 5e8, disclaimer: "d",
    snapshot_at: iso(snapAt), snapshot_kind: kind,
    snapshot_label: kind === "end_of_session" ? "Snapshot cuối phiên" : "Snapshot giữa phiên", snapshot_realtime: false,
    ...over,
  };
}

describe("trạng thái snapshot tĩnh", () => {
  it("cuối phiên: chấm 'snapshot', không bao giờ đỏ dù cũ nhiều ngày", () => {
    for (const days of [0, 1, 7, 60]) {
      const f = freshness(snap(), at(15, 30) + days * 86_400_000);
      expect(f.level).toBe("snapshot");
      expect(f.label).toBe("Snapshot cuối phiên");
      expect(f.detail).toMatch(/Không phải thời gian thực/);
    }
  });
  it("cuối phiên: giữa giờ giao dịch hôm sau vẫn không đỏ", () => {
    expect(freshness(snap(), at(10, 0, 20)).level).toBe("snapshot");
  });
  it("tuổi snapshot tính từ snapshot_at", () => {
    expect(freshness(snap(), at(15, 30) + 90_000).ageSeconds).toBe(90);
  });
  it("giữa phiên: cam (không xanh, không đỏ) và nhắc thị trường đã đi tiếp", () => {
    const m = snap({}, at(10, 30), "intraday");
    for (const later of [at(10, 31), at(14, 0), at(10, 30) + 3 * 86_400_000]) {
      const f = freshness(m, later);
      expect(f.level).toBe("amber");
      expect(f.detail).toMatch(/Thị trường có thể đã thay đổi/);
    }
  });
  it("MÔ PHỎNG vẫn giữ nhãn MÔ PHỎNG dù là snapshot", () => {
    const f = freshness(snap({ is_simulated: true, source: "sim", source_label: "MÔ PHỎNG" }), at(16, 0));
    expect(f.level).toBe("sim");
    expect(f.label).toBe("MÔ PHỎNG");
  });
  it("lỗi dữ liệu vẫn là lỗi dù là snapshot", () => {
    const m = snap();
    m.data_status = { ...m.data_status, state: "error", reason: "Chưa có dữ liệu" };
    expect(freshness(m, at(16, 0)).level).toBe("error");
  });
  it("không có snapshot_at => dùng logic thời gian thực cũ (không bị nhầm là snapshot)", () => {
    const m = snap();
    delete m.snapshot_at;
    expect(freshness(m, at(16, 0)).level).toBe("closed");
  });
  it("snapshotFreshness mặc định (thiếu kind) coi là cuối phiên", () => {
    const m = snap();
    delete m.snapshot_kind;
    expect(snapshotFreshness(m, at(16, 0)).level).toBe("snapshot");
  });
});

describe("quyết định truy cập", () => {
  it("chưa đặt mật khẩu: /data/* bị chặn hẳn, trang vẫn vào (dữ liệu thật bị khóa ở tầng gate)", () => {
    expect(decide("/data/latest.json", false, false)).toBe("forbidden");
    expect(decide("/data/sessions/ssi_2026-11-19_VN30.json", false, false)).toBe("forbidden");
    expect(decide("/", false, false)).toBe("next");
    expect(decide("/sample/latest.json", false, false)).toBe("next");
  });
  it("đã đặt mật khẩu, chưa đăng nhập: trang -> login, API và dữ liệu -> 401", () => {
    expect(decide("/", true, false)).toBe("login");
    expect(decide("/api/data", true, false)).toBe("unauthorized");
    expect(decide("/data/latest.json", true, false)).toBe("unauthorized");
  });
  it("đã đăng nhập: cho qua mọi đường dẫn", () => {
    for (const p of ["/", "/api/data", "/data/latest.json"]) expect(decide(p, true, true)).toBe("next");
  });
});
