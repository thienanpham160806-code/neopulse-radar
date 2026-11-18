import { readFileSync } from "fs";
import path from "path";
import { describe, expect, it } from "vitest";
import { cookieValue, safeEqual } from "../src/lib/auth";
import { gateAllows } from "../src/lib/data";
import { dmy, money, num, pct } from "../src/lib/format";
import { ParseError, parseIndex, parsePayload } from "../src/lib/parse";

const sample = (rel: string) => JSON.parse(readFileSync(path.join(__dirname, "..", "public", "sample", rel), "utf-8"));

describe("parsePayload", () => {
  it("chấp nhận JSON mẫu do Python xuất và giữ nhãn MÔ PHỎNG", () => {
    const p = parsePayload(sample("latest.json"));
    expect(p.meta.is_simulated).toBe(true);
    expect(p.meta.source_label).toBe("MÔ PHỎNG");
    expect(p.pulse?.components.map((c) => c.key)).toEqual(["breadth", "momentum", "book", "foreign", "liquidity"]);
    expect(p.meta.disclaimer).toContain("lời khuyên đầu tư");
  });
  it("JSON mẫu không chứa NaN/Infinity (đã là null) và không có bí mật", () => {
    const text = readFileSync(path.join(__dirname, "..", "public", "sample", "latest.json"), "utf-8");
    expect(text).not.toMatch(/\bNaN\b|\bInfinity\b/);
    expect(text.toLowerCase()).not.toMatch(/password|secret|api_key|authorization|blob_read_write/);
  });
  it("không có sổ lệnh thô từng tick", () => {
    const text = readFileSync(path.join(__dirname, "..", "public", "sample", "latest.json"), "utf-8");
    expect(text).not.toMatch(/bid1|ask1|bid_vol|ask_vol/);
  });
  it("từ chối thiếu meta / sai phiên bản / thiếu trường", () => {
    expect(() => parsePayload({})).toThrow(ParseError);
    expect(() => parsePayload(null)).toThrow(ParseError);
    const p = sample("latest.json");
    expect(() => parsePayload({ ...p, meta: { ...p.meta, schema_version: 2 } })).toThrow(/chưa được hỗ trợ/);
    expect(() => parsePayload({ ...p, meta: { ...p.meta, is_simulated: "có" } })).toThrow(/thiếu trường/);
    expect(() => parsePayload({ ...p, meta: { ...p.meta, data_status: { state: "lạ" } } })).toThrow(/data_status/);
  });
  it("payload chỉ có meta (không dữ liệu) vẫn hợp lệ để hiện trạng thái lỗi", () => {
    const p = sample("latest.json");
    const out = parsePayload({ meta: { ...p.meta, data_status: { ...p.meta.data_status, state: "error", reason: "Chưa có dữ liệu" } } });
    expect(out.pulse).toBeUndefined();
  });
});

describe("parseIndex", () => {
  it("đọc index.json mẫu: có nhiều phiên và hai chỉ số", () => {
    const idx = parseIndex(sample("index.json"));
    expect(new Set(idx.sessions.map((s) => s.index_code))).toEqual(new Set(["VN30", "VNINDEX"]));
    expect(idx.sessions.every((s) => s.is_simulated)).toBe(true);
  });
  it("từ chối cấu trúc sai", () => expect(() => parseIndex({ sessions: 3 })).toThrow(ParseError));
});

describe("cổng dữ liệu thật", () => {
  const sim = parsePayload(sample("latest.json"));
  const real = { ...sim, meta: { ...sim.meta, is_simulated: false } };
  it("không đặt mật khẩu: chỉ cho dữ liệu mô phỏng", () => {
    expect(gateAllows(sim, false)).toBe(true);
    expect(gateAllows(real, false)).toBe(false);
  });
  it("đã đặt mật khẩu: cho cả hai", () => expect(gateAllows(real, true)).toBe(true));
});

describe("auth", () => {
  it("cookie là băm, không chứa mật khẩu, ổn định và đổi theo mật khẩu", async () => {
    const a = await cookieValue("mat-khau-bi-mat");
    expect(a).toMatch(/^[0-9a-f]{64}$/);
    expect(a).not.toContain("mat-khau");
    expect(await cookieValue("mat-khau-bi-mat")).toBe(a);
    expect(await cookieValue("khac")).not.toBe(a);
  });
  it("safeEqual", () => {
    expect(safeEqual("abc", "abc")).toBe(true);
    expect(safeEqual("abc", "abd")).toBe(false);
    expect(safeEqual("abc", "abcd")).toBe(false);
  });
});

describe("định dạng", () => {
  it("null -> dấu gạch, không hiện NaN", () => {
    expect(num(null)).toBe("—");
    expect(pct(null)).toBe("—");
    expect(money(null)).toBe("—");
    expect(dmy(null)).toBe("—");
  });
  it("tiền theo tỷ/triệu và ngày dd/mm/yyyy", () => {
    expect(money(2.5e9)).toBe("2,5 tỷ");
    expect(money(3.2e6)).toBe("3,2 triệu");
    expect(money(-1.5e12)).toContain("nghìn tỷ");
    expect(dmy("2026-11-19")).toBe("19/11/2026");
    expect(pct(1.234)).toBe("+1,23%");
  });
});
