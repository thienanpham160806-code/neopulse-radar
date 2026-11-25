export type RouteQuery = Record<string, string | string[] | undefined>;

/** Old market bookmarks and Telegram messages keep every query parameter. */
export function legacyMarketDestination(query: RouteQuery): string | null {
  if (!["tab", "date", "index", "sym"].some((key) => query[key] !== undefined)) return null;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) {
      params.append(key, item);
    }
  }
  return `/thi-truong?${params}`;
}
