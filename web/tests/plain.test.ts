import { describe, expect, it } from "vitest";
import { alertDigest, componentMeaning, GLOSSARY, missingComponents, RULE_PLAIN, scoreMeaning } from "../src/lib/plain";
import type { AlertItem } from "../src/lib/types";

const al = (t: string, symbol: string, severity: AlertItem["severity"] = "CAO", rule = "volume_spike"): AlertItem =>
  ({ t, symbol, rule, rule_name: rule, severity, value: null, threshold: null, message: "" });

describe("luận giải bằng lời thường", () => {
  it("ý nghĩa điểm theo đúng ranh giới nhãn 35/45/55/65, chỉ nói mức nghiêng", () => {
    expect(scoreMeaning(70)).toMatch(/nghiêng rõ về phía tích cực/);
    expect(scoreMeaning(58.7)).toMatch(/nghiêng nhẹ về phía tích cực/);
    expect(scoreMeaning(50)).toMatch(/cân bằng/);
    expect(scoreMeaning(40)).toMatch(/nghiêng nhẹ về phía tiêu cực/);
    expect(scoreMeaning(20)).toMatch(/nghiêng rõ về phía tiêu cực/);
    expect(scoreMeaning(null)).toMatch(/Chưa đủ/);
  });
  it("CX-013: điểm cao không khẳng định độ rộng, dòng tiền hay lệnh mua", () => {
    for (const s of [82, 67.3, 20]) expect(scoreMeaning(s)).not.toMatch(/đa số|cổ phiếu|tiền|lệnh mua|bán lan rộng/i);
    expect(componentMeaning("breadth", -0.2)).toBe("Số mã giảm áp đảo số mã tăng (mức vừa).");
    expect(componentMeaning("foreign", 0)).toBe("Khối ngoại mua và bán gần cân bằng.");
    expect(missingComponents([{ name: "Độ rộng", value: -0.2 }, { name: "Sổ lệnh", value: null }, { name: "Khối ngoại", value: null }]))
      .toEqual(["Sổ lệnh", "Khối ngoại"]);
  });
  it("thành phần: chiều theo dấu, mức theo độ lớn", () => {
    expect(componentMeaning("breadth", 0.6)).toBe("Số mã tăng áp đảo số mã giảm (mức rõ).");
    expect(componentMeaning("foreign", -0.25)).toBe("Khối ngoại đang bán ròng (mức vừa).");
    expect(componentMeaning("book", 0.01)).toBe("Lệnh chờ mua và bán gần cân bằng.");
    expect(componentMeaning("momentum", null)).toMatch(/Chưa đủ/);
  });
  it("CX-014: cảnh báo live trùng snapshot không bị đếm hai lần; tổng dùng by_severity", () => {
    const snap = [al("2026-11-18T10:00:00", "AAA")];
    const d = alertDigest([al("2026-11-18T10:00:00", "AAA")], snap, 1);
    expect(d.items).toHaveLength(1);
    expect(d.nHigh).toBe(1);
    // snapshot bị cắt MAX_ALERTS: tổng phiên lấy từ Python; live mới hơn snapshot được cộng thêm
    const d2 = alertDigest([al("2026-11-18T10:05:00", "BBB"), al("2026-11-18T10:06:00", "BBB")], snap, 25);
    expect(d2.nHigh).toBe(27);
    expect(d2.hot[0]).toBe("BBB"); // xếp theo tần suất, không theo thứ tự xuất hiện
  });
  it("mọi thành phần và quy tắc cảnh báo đều có lời giải thích", () => {
    for (const k of ["pulse", "breadth", "momentum", "book", "foreign", "liquidity", "basis", "rvol", "sector"]) expect(GLOSSARY[k].body.length).toBeGreaterThan(20);
    for (const r of ["volume_spike", "spread_blowout", "price_jump", "foreign_flow", "book_pressure", "near_limit"]) expect(RULE_PLAIN[r]).toBeTruthy();
  });
  it("loại trùng cả trong live và chuẩn hóa múi giờ; không cộng sự kiện cũ ngoài danh sách snapshot bị cắt", () => {
    const a = al("2026-11-18T10:00:00+07:00", "AAA");
    expect(alertDigest([a, { ...a, t: "2026-11-18T03:00:00Z" }], [], 0).nHigh).toBe(1);
    expect(alertDigest([a], [], 500, "2026-11-18T11:00:00+07:00").nHigh).toBe(500);
  });
});
