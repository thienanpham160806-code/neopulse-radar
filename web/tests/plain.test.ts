import { describe, expect, it } from "vitest";
import { componentMeaning, GLOSSARY, RULE_PLAIN, scoreMeaning } from "../src/lib/plain";

describe("luận giải bằng lời thường", () => {
  it("ý nghĩa điểm theo đúng ranh giới nhãn 35/45/55/65", () => {
    expect(scoreMeaning(70)).toMatch(/lan tỏa/);
    expect(scoreMeaning(58.7)).toMatch(/nghiêng về phía tích cực/);
    expect(scoreMeaning(50)).toMatch(/giằng co/);
    expect(scoreMeaning(40)).toMatch(/tiêu cực/);
    expect(scoreMeaning(20)).toMatch(/bán lan rộng/);
    expect(scoreMeaning(null)).toMatch(/Chưa đủ/);
  });
  it("thành phần: chiều theo dấu, mức theo độ lớn", () => {
    expect(componentMeaning("breadth", 0.6)).toBe("Số mã tăng áp đảo số mã giảm (mức rõ).");
    expect(componentMeaning("foreign", -0.25)).toBe("Khối ngoại đang bán ròng (mức vừa).");
    expect(componentMeaning("book", 0.01)).toBe("Lệnh chờ mua và bán gần cân bằng.");
    expect(componentMeaning("momentum", null)).toMatch(/Chưa đủ/);
  });
  it("mọi thành phần và quy tắc cảnh báo đều có lời giải thích", () => {
    for (const k of ["pulse", "breadth", "momentum", "book", "foreign", "liquidity", "basis", "rvol", "sector"]) expect(GLOSSARY[k].body.length).toBeGreaterThan(20);
    for (const r of ["volume_spike", "spread_blowout", "price_jump", "foreign_flow", "book_pressure", "near_limit"]) expect(RULE_PLAIN[r]).toBeTruthy();
  });
});
