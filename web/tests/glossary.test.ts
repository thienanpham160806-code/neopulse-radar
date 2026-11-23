import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { GLOSSARY, searchGlossary } from "../src/lib/glossary";
import { AlertDetail } from "../src/components/AlertDetail";
import { MarketEvidence, ValidationSummary } from "../src/components/MarketEvidence";
import { Overview } from "../src/components/Overview";
import type { AlertItem, Payload } from "../src/lib/types";

const fixture = (): Payload => JSON.parse(readFileSync(path.join(__dirname, "../public/sample/latest.json"), "utf8"));

describe("one contextual market dictionary", () => {
  it("finds Vietnamese without accents, abbreviations, subscripts and multiple words", () => {
    expect(searchGlossary("do rong").map(([k]) => k)).toContain("breadth");
    expect(searchGlossary("khOI ngoai").map(([k]) => k)).toContain("foreign");
    expect(searchGlossary("OBI₃").map(([k]) => k)).toContain("book");
    expect(searchGlossary("ic mean").map(([k]) => k)).toContain("ic");
    expect(searchGlossary("OBIw").map(([k]) => k)).toContain("obi_w");
    expect(searchGlossary("IC")[0][0]).toBe("ic");
    expect(searchGlossary("MA")[0][0]).toBe("ma");
    expect(searchGlossary("not-a-real-metric")).toEqual([]);
    expect(searchGlossary("   ")).toHaveLength(Object.keys(GLOSSARY).length);
  });
  it("every contextual label resolves to an entry with project role, units, example and limits", () => {
    const dir = path.join(__dirname, "../src/components");
    for (const file of readdirSync(dir).filter((f) => f.endsWith(".tsx"))) {
      for (const match of readFileSync(path.join(dir, file), "utf8").matchAll(/<Term k="([^"]+)"/g)) {
        expect(GLOSSARY[match[1]], `${file}: ${match[1]}`).toBeDefined();
      }
    }
    for (const g of Object.values(GLOSSARY)) {
      for (const field of [g.body, g.reading, g.example, g.role, g.formula, g.limit]) expect(field.trim().length).toBeGreaterThan(0);
      expect(g.unit).toBeTruthy();
      expect(["tong-quan", "so-lenh", "khoi-ngoai", "phai-sinh", "canh-bao", "xep-hang", "kiem-chung"]).toContain(g.tab);
    }
    expect(GLOSSARY.basis.limit).toContain("không tự chứng minh");
    expect(GLOSSARY.sensitivity.limit).toContain("không kiểm chứng");
  });
});

it("keeps missing components empty and labels normalized units and original weights", () => {
  const html = renderToStaticMarkup(createElement(MarketEvidence, {
    comps: [{ key: "liquidity", name: "Thanh khoản", weight: 0.1, value: null }], onNavigate: () => {},
  }));
  expect(html).toContain("Chưa đủ dữ liệu");
  expect(html).toContain("—");
  expect(html).toContain("trọng số gốc 10%");
  expect(html).toContain("không phải % tăng giá");
});

it("never invents the measurement or baseline of a fast live alert", () => {
  const a: AlertItem = { t: "2026-11-23T10:00:00+07:00", symbol: "FPT", rule: "volume_spike", rule_name: "Bùng nổ khối lượng", severity: "CAO", message: "Khối lượng khác thường", value: null, threshold: null };
  const fast = renderToStaticMarkup(createElement(AlertDetail, { a }));
  expect(fast).toContain("chưa kèm giá trị và ngưỡng");
  expect(fast).not.toContain("Giá trị kiểm tra:");
  const full = renderToStaticMarkup(createElement(AlertDetail, { a: { ...a, value: 4.2, threshold: 3 } }));
  expect(full).toContain("4,20");
  expect(full).toContain("3,00");
  expect(full).not.toContain("chưa kèm");
});

it("a high composite score does not override observed declines or missing foreign data", () => {
  const p = fixture();
  p.meta.data_status.state = "stale";
  p.meta.is_simulated = false;
  p.pulse!.score = 70;
  p.pulse!.components = [{ key: "breadth", name: "Độ rộng", weight: 0.3, value: -0.5 }, { key: "foreign", name: "Khối ngoại", weight: 0.15, value: null }];
  p.index!.row!.pct_change = -1;
  p.index!.row!.advances = 5;
  p.index!.row!.declines = 25;
  p.foreign = { rows: [], summary: null };
  const html = renderToStaticMarkup(createElement(Overview, { p, f: { sym: "", minSev: "CAO" }, onNavigate: () => {} }));
  expect(html).toContain("Tín hiệu chung đang khá tích cực");
  expect(html).toContain("đang giảm 1,00%");
  expect(html).toContain("25 mã giảm và 5 mã tăng");
  expect(html).toContain("Chưa đủ dữ liệu cho: Khối ngoại");
  expect(html).not.toContain("Mua ròng ·");
  expect(html.indexOf("Năm góc nhìn")).toBeLessThan(html.indexOf("Biến động đáng chú ý"));
  expect(html.indexOf("Biến động đáng chú ý")).toBeLessThan(html.indexOf("Đặt tín hiệu vào diễn biến giá"));
});

it("five sessions is a collection milestone, not a predictive certificate; no validation means no invented result", () => {
  const p = fixture();
  p.validation = undefined;
  expect(renderToStaticMarkup(createElement(ValidationSummary, { p, onNavigate: () => {} }))).toContain("chưa có kết quả kiểm chứng");
  p.validation = { ic: { train: [], test: [], table: [], note: null }, ic_by_session: [], simulated_signals_are_planted: false,
    data_quality: { n_quotes: 200, n_sessions: 5, n_symbols: 30, n_gaps: 0, issues: {}, runs: [] } };
  const html = renderToStaticMarkup(createElement(ValidationSummary, { p, onNavigate: () => {} }));
  expect(html).toContain("vẫn cần nhiều phiên hơn");
  expect(html).toContain("chưa chứng minh lợi nhuận sau phí");
});
