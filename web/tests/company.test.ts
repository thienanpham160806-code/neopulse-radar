import { afterEach, describe, expect, it, vi } from "vitest";
import { promises as fs } from "fs";
import { companyIndex, companyReport, companyUniverse } from "../src/lib/company";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CompanyLink } from "../src/components/CompanyLink";

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
    const read = vi.spyOn(fs, "readFile").mockResolvedValueOnce(JSON.stringify({ symbols: [{ symbol: "MWG", name: "MWG" }, { symbol: "../escape" }] }));
    expect((await companyIndex()).map((e) => e.symbol)).toEqual(["MWG"]);
    read.mockRejectedValueOnce(new Error("missing"));
    expect(await companyIndex()).toEqual([]);
  });
});
