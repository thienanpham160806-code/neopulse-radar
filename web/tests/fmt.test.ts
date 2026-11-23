import { describe, expect, it } from "vitest";
import { bnLabel, cls, dmyTime, priceTone, TONE_MARK } from "../src/lib/fmt";

describe("fmt (tái sử dụng từ invest-system-phase2, có bổ sung trần/sàn)", () => {
  it("màu theo quy ước bảng giá VN: trần tím, sàn xanh lơ, tham chiếu vàng", () => {
    expect(priceTone(1.2)).toBe("up");
    expect(priceTone(-0.4)).toBe("down");
    expect(priceTone(0)).toBe("ref");
    expect(priceTone(null)).toBe("ref");
    expect(priceTone(6.9, 50200, 50200, 43700)).toBe("ceil"); // chạm trần ưu tiên hơn "tăng"
    expect(priceTone(-6.9, 43700, 50200, 43700)).toBe("floor");
    expect(cls(-1)).toBe("text-down");
  });
  it("có ký hiệu không phụ thuộc màu", () => {
    expect(new Set(Object.values(TONE_MARK)).size).toBe(5);
  });
  it("tiền và ngày kiểu Việt Nam", () => {
    expect(bnLabel(1.6853e12)).toBe("1,7 nghìn tỷ đồng");
    expect(bnLabel(345e9)).toBe("345 tỷ đồng");
    expect(bnLabel(null)).toBe("—");
    expect(dmyTime("2026-11-19T10:05:30+07:00")).toBe("10:05, 19/11/2026");
    expect(dmyTime("2026-11-19")).toBe("19/11/2026");
  });
});
