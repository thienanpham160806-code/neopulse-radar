import { readFileSync } from "node:fs";
import path from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Overview } from "../src/components/Overview";
import { StatusBar } from "../src/components/StatusBar";
import type { Payload } from "../src/lib/types";

const fixture = (): Payload => JSON.parse(readFileSync(path.join(__dirname, "../public/sample/latest.json"), "utf8"));

describe("UX refine: Radar Cockpit Option B + 4 approved conditions", () => {
  it("explains Why in plain Vietnamese and explicitly marks bars as normalized components (not % or point contribution)", () => {
    const p = fixture();
    const html = renderToStaticMarkup(createElement(Overview, { p, f: { sym: "", minSev: "TRUNG BÌNH" }, onNavigate: () => {} }));
    expect(html).toContain("thành phần chuẩn hóa (−1…+1)");
    expect(html).toContain("không phải % tăng giá hay số điểm đóng góp");
    expect(html).toContain("3 tín hiệu nổi bật");
    expect(html).toContain("Mở đủ 5 tín hiệu");
  });

  it("flags late intraday session start when morning data is missing", () => {
    const p = fixture();
    p.pulse!.series = [
      { t: "2026-11-23T10:45:00+07:00", index: 1920, score: 52 },
      { t: "2026-11-23T11:25:00+07:00", index: 1933, score: 58 },
    ];
    const html = renderToStaticMarkup(createElement(Overview, { p, f: { sym: "", minSev: "TRUNG BÌNH" }, onNavigate: () => {} }));
    expect(html).toContain("Thiếu đầu phiên");
    expect(html).toContain("10:45–11:25");
  });

  it("deduplicates MÔ PHỎNG label in StatusBar while keeping source, timestamp, and disclaimer clear", () => {
    const p = fixture();
    p.meta.is_simulated = true;
    p.meta.source_label = "MÔ PHỎNG";
    const html = renderToStaticMarkup(createElement(StatusBar, { meta: p.meta, nowMs: Date.now(), notice: null, pollError: null }));
    expect(html).toContain("DỮ LIỆU MÔ PHỎNG");
    // Không còn lặp 2 lần chữ MÔ PHỎNG cạnh nhau ở summary
    expect(html).not.toMatch(/MÔ PHỎNG<\/span>\s*<span[^>]*>MÔ PHỎNG/);
  });
});
