import { afterEach, describe, expect, it, vi } from "vitest";
import { promises as fs } from "fs";
import { companyIndex, companyReport, companyUniverse, companyVN100 } from "../src/lib/company";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CompanyLink } from "../src/components/CompanyLink";
import { CompanyDirectory } from "../src/components/CompanyDirectory";

afterEach(() => vi.restoreAllMocks());
describe("hồ sơ doanh nghiệp", () => {
  it("rổ VN30 lấy từ snapshot thật đủ 30 mã, không dùng snapshot mô phỏng", async () => {
    const rows = Array.from({ length: 30 }, (_, i) => ({ symbol: `A${i}` }));
    const read = vi.spyOn(fs, "readFile").mockResolvedValue(JSON.stringify({ meta: { index_code: "VN30", is_simulated: false, trading_date: "2026-11-19" }, book: { rows } }));
    expect((await companyUniverse()).symbols).toHaveLength(30);
    read.mockResolvedValue(JSON.stringify({ meta: { index_code: "VN30", is_simulated: true }, book: { rows } }));
    expect((await companyUniverse()).symbols).toEqual([]);
  });
  it("mã trên bảng là đường dẫn thật tới hồ sơ", () => {
    expect(renderToStaticMarkup(createElement(CompanyLink, { symbol: "MWG" }))).toContain('href="/doanh-nghiep/MWG"');
  });
  it("không đọc file khi mã chứa đường dẫn", async () => {
    const read = vi.spyOn(fs, "readFile");
    expect(await companyReport("../MWG")).toBeNull();
    expect(read).not.toHaveBeenCalled();
  });
  it("file thiếu hoặc sai mã không được trả thành hồ sơ khác", async () => {
    const read = vi.spyOn(fs, "readFile").mockRejectedValueOnce(new Error("ENOENT"));
    expect(await companyReport("MWG")).toBeNull();
    read.mockResolvedValueOnce(JSON.stringify({ schema: 1, symbol: "VCB" }));
    expect(await companyReport("MWG")).toBeNull();
  });
  it("danh sách chỉ dùng mã hợp lệ và chịu được dữ liệu thiếu", async () => {
    const read = vi.spyOn(fs, "readFile").mockResolvedValueOnce(JSON.stringify({ symbols: [{ symbol: "MWG", name: "MWG" }, { symbol: "../escape" }] })).mockRejectedValueOnce(new Error("missing catalog"));
    expect((await companyIndex()).map((e) => e.symbol)).toEqual(["MWG"]);
    read.mockRejectedValueOnce(new Error("missing"));
    expect(await companyIndex()).toEqual([]);
  });
  it("toàn thị trường phân biệt báo cáo có sẵn và mã tải khi mở", async () => {
    vi.spyOn(fs, "readFile")
      .mockResolvedValueOnce(JSON.stringify({ symbols: [{ symbol: "MWG" }] }))
      .mockResolvedValueOnce(JSON.stringify({ symbols: [{ symbol: "MWG", exchange: "HOSE" }, { symbol: "VND", exchange: "HOSE" }, { symbol: "../bad" }] }));
    expect(await companyIndex()).toEqual([{ symbol: "MWG", exchange: "HOSE", has_report: true }, { symbol: "VND", exchange: "HOSE", has_report: false }]);
  });
  it("VN100 chỉ chấp nhận rổ có đúng 100 mã duy nhất", async () => {
    const symbols = Array.from({ length: 100 }, (_, i) => `A${i}`);
    const read = vi.spyOn(fs, "readFile").mockResolvedValueOnce(JSON.stringify({ symbols, as_of: "2026-11-20" }));
    expect((await companyVN100()).symbols).toHaveLength(100);
    read.mockResolvedValueOnce(JSON.stringify({ symbols: [...symbols.slice(0, 99), symbols[0]] }));
    expect((await companyVN100()).symbols).toEqual([]);
  });
  it("đếm báo cáo VN100 theo thành viên thật, không cộng báo cáo ngoài rổ", () => {
    const entries = [{ symbol: "MWG", name: "MWG", industry: null, has_report: true }, { symbol: "VND", name: "VND", industry: null, has_report: true }];
    const html = renderToStaticMarkup(createElement(CompanyDirectory, { entries, vn100: ["MWG", "FPT"] }));
    expect(html).toContain("VN100 · báo cáo sẵn (1/100)");
  });
  it("cho chọn trực tiếp mọi trang, tự đổi tổng trang theo bộ dữ liệu", () => {
    const entries = Array.from({ length: 1519 }, (_, i) => ({ symbol: `A${i}`, name: null, industry: null }));
    const render = (rows: typeof entries) => renderToStaticMarkup(createElement(CompanyDirectory, { entries: rows })).match(/<select aria-label="Đi đến trang doanh nghiệp"[\s\S]*?<\/select>/)?.[0] ?? "";
    const menu = render(entries);
    expect(menu.match(/<option /g)).toHaveLength(64);
    expect(menu).toContain('value="20">20/64');
    expect(menu).toContain('value="64">64/64');
    expect(render(entries.slice(0, 100))).toContain('value="5">05/05');
    expect(render([])).toContain('value="1" selected="">01/01');
  });
});
