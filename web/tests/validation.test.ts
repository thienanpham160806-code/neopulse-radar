import { readFileSync } from "node:fs";
import path from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { Validation } from "../src/components/tabs";
import type { Payload } from "../src/lib/types";

it("explains limited session history separately from the computed validation result", () => {
  const payload: Payload = JSON.parse(readFileSync(path.join(__dirname, "../public/sample/latest.json"), "utf8"));
  payload.validation = {
    generated_at: "2026-11-20T12:10:00+07:00", data_until: "2026-11-20T11:30:00+07:00",
    ic: { train: ["2026-11-19"], test: ["2026-11-20"], table: [], note: null },
    ic_by_session: [], simulated_signals_are_planted: false,
    data_quality: { n_quotes: 100, n_sessions: 2, n_symbols: 30, n_gaps: 0, issues: {}, runs: [] },
  };
  const html = renderToStaticMarkup(createElement(Validation, { p: payload }));
  expect(html).toContain("Mới ghi nhận 2 phiên");
  expect(html).toContain("Dữ liệu đến");
  expect(html).toContain("khoảng 10 phút một lần");
  expect(html).toContain("Chất lượng dữ liệu");
});
