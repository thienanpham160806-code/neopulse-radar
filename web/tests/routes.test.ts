import { describe, expect, it } from "vitest";
import { legacyMarketDestination } from "@/lib/routes";

describe("legacy market links", () => {
  it("keeps the bare domain and campaign links on the homepage", () => {
    expect(legacyMarketDestination({})).toBeNull();
    expect(legacyMarketDestination({ utm_source: "telegram" })).toBeNull();
  });
  it("preserves old market bookmarks including repeated and unknown parameters", () => {
    const target = legacyMarketDestination({ tab: "so-lenh", date: "2026-11-25", index: "VN30", sym: "MWG", extra: ["a b", "c&d"] });
    const url = new URL(target!, "https://example.test");
    expect(url.pathname).toBe("/thi-truong");
    expect(Object.fromEntries(url.searchParams)).toMatchObject({ tab: "so-lenh", date: "2026-11-25", index: "VN30", sym: "MWG" });
    expect(url.searchParams.getAll("extra")).toEqual(["a b", "c&d"]);
  });
  it.each(["tab", "date", "index", "sym"])("recognizes %s links even with an empty value", (key) => {
    expect(legacyMarketDestination({ [key]: "" })).toBe(`/thi-truong?${key}=`);
  });
});
