import { describe, expect, it } from "vitest";
import { ageSince, formatAge, freshness, sessionPhase } from "../src/lib/status";
import type { Meta } from "../src/lib/types";

// 2026-11-19 là thứ Năm. 10:00 giờ VN = 03:00 UTC.
const at = (hh: number, mm: number, ss = 0, day = 19) => Date.UTC(2026, 10, day, hh - 7, mm, ss);
const iso = (ms: number) => new Date(ms + 7 * 3600_000).toISOString().replace("Z", "+07:00");

function meta(over: Partial<Meta> & { state?: Meta["data_status"]["state"] } = {}, lastUpdate?: number, generated?: number): Meta {
  const { state = "fresh", ...rest } = over;
  return {
    schema_version: 1, source: "ssi", source_label: "SSI FastConnect (dữ liệu thật)", is_simulated: false,
    generated_at: iso(generated ?? at(10, 0)), last_update: iso(lastUpdate ?? at(10, 0)), trading_date: "2026-11-19",
    index_code: "VN30", data_status: { state, reason: "x", phase: "open", age_seconds: 0, stale_after_seconds: 120 },
    n_symbols_computed: 30, n_symbols_excluded: 0, excluded_reason: null, n_sessions: 5, n_history_sessions: 4,
    available_dates: [], order_value_vnd: 5e8, disclaimer: "d", ...rest,
  };
}

describe("sessionPhase (giờ VN)", () => {
  it("nhận diện các pha trong ngày", () => {
    expect(sessionPhase(at(8, 59))).toBe("pre");
    expect(sessionPhase(at(9, 0))).toBe("open");
    expect(sessionPhase(at(11, 29))).toBe("open");
    expect(sessionPhase(at(11, 30))).toBe("lunch");
    expect(sessionPhase(at(13, 0))).toBe("open");
    expect(sessionPhase(at(15, 5))).toBe("open");
    expect(sessionPhase(at(15, 6))).toBe("closed");
  });
  it("cuối tuần luôn đóng", () => {
    expect(sessionPhase(at(10, 0, 0, 21))).toBe("closed"); // thứ Bảy
    expect(sessionPhase(at(10, 0, 0, 22))).toBe("closed"); // Chủ nhật
  });
});

describe("freshness: xanh < 60 s, cam < 5 phút, còn lại đỏ", () => {
  const upd = at(10, 0);
  it("xanh khi 59 giây", () => expect(freshness(meta({}, upd), upd + 59_000).level).toBe("green"));
  it("cam khi đúng 60 giây", () => expect(freshness(meta({}, upd), upd + 60_000).level).toBe("amber"));
  it("cam khi 299 giây", () => expect(freshness(meta({}, upd), upd + 299_000).level).toBe("amber"));
  it("đỏ khi 300 giây", () => expect(freshness(meta({}, upd), upd + 300_000).level).toBe("red"));
  it("tính lại từ đồng hồ: JSON nói fresh nhưng đã cũ -> đỏ", () => {
    const f = freshness(meta({ state: "fresh" }, upd, upd), upd + 600_000);
    expect(f.level).toBe("red");
    expect(f.ageSeconds).toBe(600);
  });
});

describe("freshness: các trạng thái đặc biệt", () => {
  it("lỗi dữ liệu -> error, có lý do", () => {
    const f = freshness(meta({ state: "error" }), at(10, 0));
    expect(f.level).toBe("error");
    expect(f.detail).toBe("x");
  });
  it("MÔ PHỎNG luôn gắn nhãn, không báo cũ", () => {
    const f = freshness(meta({ is_simulated: true }, at(9, 0)), at(14, 0));
    expect(f.level).toBe("sim");
    expect(f.label).toBe("MÔ PHỎNG");
  });
  it("sau giờ đóng cửa: 'phiên đã kết thúc', không phải lỗi", () => {
    const f = freshness(meta({ state: "closed" }, at(15, 0)), at(16, 30));
    expect(f.level).toBe("closed");
    expect(f.label).toBe("Phiên đã kết thúc");
  });
  it("JSON còn nhãn fresh nhưng đã sau 15:05 -> vẫn 'phiên đã kết thúc'", () => {
    expect(freshness(meta({ state: "fresh" }, at(15, 1)), at(17, 0)).level).toBe("closed");
  });
  it("nghỉ trưa -> closed với nhãn nghỉ trưa", () => {
    expect(freshness(meta({ state: "fresh" }, at(11, 29)), at(12, 0)).label).toBe("Nghỉ trưa");
  });
  it("trong giờ mà bản đẩy lên đã cũ > 5 phút dù JSON ghi closed -> đỏ", () => {
    const f = freshness(meta({ state: "closed" }, at(10, 0), at(10, 0)), at(10, 20));
    expect(f.level).toBe("red");
  });
  it("cuối tuần -> closed", () => {
    expect(freshness(meta({ state: "closed" }, at(15, 0, 0, 20)), at(10, 0, 0, 21)).level).toBe("closed");
  });
});

describe("tiện ích thời gian", () => {
  it("ageSince xử lý null và chuỗi sai", () => {
    expect(ageSince(null, 1)).toBeNull();
    expect(ageSince("không phải ngày", 1)).toBeNull();
    expect(ageSince(iso(at(10, 0)), at(10, 0, 30))).toBe(30);
  });
  it("formatAge", () => {
    expect(formatAge(null)).toBe("—");
    expect(formatAge(45)).toBe("45 giây");
    expect(formatAge(180)).toBe("3 phút");
    expect(formatAge(7200)).toBe("2.0 giờ");
  });
});
