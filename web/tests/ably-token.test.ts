import { afterEach, expect, it, vi } from "vitest";
import { GET } from "../src/app/api/ably-token/route";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

it("cấp token có định danh, chỉ subscribe và không trả khóa gốc", async () => {
  vi.stubEnv("SITE_PASSWORD", "test-password");
  vi.stubEnv("ABLY_API_KEY", "test.key:fake-secret");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    token: "fake-token", issued: 1000, expires: 901000,
    capability: JSON.stringify({ "neopulse:live": ["subscribe"] }), keyName: "test.key",
  }), { status: 201 }));
  const response = await GET();
  expect(response.status).toBe(200);
  const body = JSON.parse(String(fetch.mock.calls[0][1]?.body));
  expect(body.clientId).toBe("neopulse-web");
  expect(body.ttl).toBe(900000);
  expect(JSON.parse(body.capability)).toEqual({ "neopulse:live": ["subscribe"] });
  expect(response.headers.get("Cache-Control")).toBe("no-store");
  expect(await response.text()).not.toContain("fake-secret");
});
