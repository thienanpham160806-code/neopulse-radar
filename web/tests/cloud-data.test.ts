import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, expect, it, vi } from "vitest";
import { loadData } from "../src/lib/data";

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });
function cloud() {
  vi.stubEnv("KV_REST_API_URL", "https://kv.test");
  vi.stubEnv("KV_REST_API_TOKEN", "server-only-secret");
  vi.stubEnv("BLOB_READ_URL", "");
  const p = JSON.parse(readFileSync(path.join(__dirname, "../public/sample/latest.json"), "utf8"));
  p.meta = { ...p.meta, source: "ssi", is_simulated: false, trading_date: "2026-11-20", index_code: "VN30" };
  return p;
}

it("boots the current cloud session over yesterday's static deployment", async () => {
  const payload = cloud();
  const fetcher = vi.fn().mockResolvedValue(Response.json({ result: JSON.stringify(payload) }));
  vi.stubGlobal("fetch", fetcher);
  const data = await loadData(null, "VN30");
  expect(data.origin).toBe("cloud");
  expect(data.payload.meta.trading_date).toBe("2026-11-20");
  expect(data.index.sessions.some((s) => s.trading_date === "2026-11-20" && s.index_code === "VN30")).toBe(true);
  expect(fetcher.mock.calls[0][1].body).toBe(JSON.stringify(["GET", "neopulse:market:latest:VN30"]));
  expect(JSON.stringify(data)).not.toContain("server-only-secret");
});

it("historical selection reads its own day instead of the live latest key", async () => {
  const payload = cloud();
  const fetcher = vi.fn().mockResolvedValue(Response.json({ result: JSON.stringify(payload) }));
  vi.stubGlobal("fetch", fetcher);
  expect((await loadData("2026-11-20", "VN30")).origin).toBe("cloud");
  expect(fetcher.mock.calls[0][1].body).toBe(JSON.stringify(["GET", "neopulse:market:session:2026-11-20:VN30"]));
});

it("cloud failure falls back with an explicit notice", async () => {
  cloud();
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  const data = await loadData();
  expect(data.origin).not.toBe("cloud");
  expect(data.notice).toContain("phiên mới nhất");
});
