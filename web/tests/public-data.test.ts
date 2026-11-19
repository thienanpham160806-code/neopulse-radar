import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, expect, it, vi } from "vitest";
import { GET } from "../src/app/api/data/route";
import { loadData } from "../src/lib/data";

vi.mock("../src/lib/data", () => ({ loadData: vi.fn() }));

afterEach(() => {
  vi.resetAllMocks();
  vi.unstubAllEnvs();
});

it.each([undefined, "leftover-password"])("trả dữ liệu SSI không cần cookie dù SITE_PASSWORD=%s", async (password) => {
  vi.stubEnv("SITE_PASSWORD", password);
  const payload = JSON.parse(readFileSync(path.join(__dirname, "../public/sample/latest.json"), "utf-8"));
  payload.meta = { ...payload.meta, source: "ssi", is_simulated: false };
  vi.mocked(loadData).mockResolvedValue({ payload, index: { schema_version: 1, generated_at: "", sessions: [] }, origin: "static", notice: null });
  const response = await GET(new Request("http://localhost/api/data?index=VNINDEX"));
  expect(response.status).toBe(200);
  expect((await response.json()).payload.meta.source).toBe("ssi");
  expect(loadData).toHaveBeenCalledWith(null, "VNINDEX");
  expect(response.headers.get("Cache-Control")).toBe("no-store");
});
