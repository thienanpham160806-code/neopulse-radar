import { promises as fs } from "fs";
import path from "path";

export interface CompanyEntry { symbol: string; name: string | null; industry: string | null; exchange?: string; has_report?: boolean }
type N = number | null;
export interface CompanyReport {
  schema: number; symbol: string; kind: string; source: string; fetched_at: string | null;
  profile: { name: string | null; short_name: string | null; about: string | null; exchange: string | null; industry: string | null; listing_date: string | null; shares: N; foreign_pct: N; foreign_room: N; state_pct: N; free_float_pct: N };
  shareholders: { name: string; pct: N }[]; officers: { name: string; position: string }[];
  events: { date: string; title: string; type?: string | null }[]; news: { date: string; title: string; url?: string; source?: string }[];
  price: { last: N; date: string | null; high_52w: N; low_52w: N; n_sessions?: number; series: [string, number, number][]; returns: Record<string, { stock: N; index: N }> };
  valuation: { market_cap: N; pe: N; pb: N; ev_ebitda: N };
  years: string[]; tables: Record<string, { label: string; values: N[] }[]>;
  ratios: Record<string, Record<string, N>>;
  peers: { basis: string; rows: ({ symbol: string; year: string | null } & Record<string, string | N>)[]; median: Record<string, N> };
  summary: string[]; notes: string[];
  technical?: import("@/components/TechnicalChart").ChartData;
  dcf?: { reason?: string; base_fcff: N; tax_rate?: number; cases: { wacc: number; growth: number; value: N }[] };
}

export const validSymbol = (s: string) => /^[A-Z][A-Z0-9]{1,9}$/.test(s);
const dir = () => path.join(process.cwd(), "public", "data", "company");
export async function companyVN100(): Promise<{ symbols: string[]; date: string | null }> {
  try {
    const data = JSON.parse(await fs.readFile(path.join(dir(), "vn100.json"), "utf8"));
    const symbols = [...new Set<string>((Array.isArray(data.symbols) ? data.symbols : []).filter((s: unknown) => typeof s === "string" && validSymbol(s)))].sort();
    if (symbols.length === 100) return { symbols, date: typeof data.as_of === "string" ? data.as_of : null };
  } catch { /* An incomplete basket must not be presented as the VN100. */ }
  return { symbols: [], date: null };
}
/** Rổ thực sự có trong snapshot VN30; không dùng danh sách tham chiếu chứa cả mã cũ. */
export async function companyUniverse(): Promise<{ symbols: string[]; date: string | null }> {
  for (const file of ["latest_VN30.json", "latest.json"]) {
    try {
      const p = JSON.parse(await fs.readFile(path.join(process.cwd(), "public", "data", file), "utf8"));
      if (p.meta?.index_code !== "VN30" || p.meta?.is_simulated !== false) continue;
      const symbols = [...new Set<string>((p.book?.rows ?? []).map((r: { symbol: string }) => r.symbol))].filter(validSymbol).sort();
      if (symbols.length === 30) return { symbols, date: p.meta.trading_date ?? null };
    } catch { /* Thử snapshot tiếp theo. */ }
  }
  return { symbols: [], date: null };
}
export async function companyIndex(): Promise<CompanyEntry[]> {
  try {
    const data = JSON.parse(await fs.readFile(path.join(dir(), "index.json"), "utf8"));
    const ready: CompanyEntry[] = Array.isArray(data.symbols) ? data.symbols.filter((e: CompanyEntry) => typeof e.symbol === "string" && validSymbol(e.symbol)).map((e: CompanyEntry) => ({ ...e, has_report: true })) : [];
    try {
      const catalog = JSON.parse(await fs.readFile(path.join(dir(), "catalog.json"), "utf8"));
      if (!Array.isArray(catalog.symbols)) return ready;
      const cached = new Map(ready.map((e) => [e.symbol, e]));
      return catalog.symbols.filter((e: CompanyEntry) => e && validSymbol(e.symbol)).map((e: CompanyEntry) => ({ ...e, has_report: cached.has(e.symbol) }));
    } catch { return ready; }
  } catch { return []; }
}
export async function companyReport(symbol: string): Promise<CompanyReport | null> {
  if (!validSymbol(symbol)) return null;
  try {
    const data = JSON.parse(await fs.readFile(path.join(dir(), `${symbol}.json`), "utf8"));
    if (data.schema !== 1 || data.symbol !== symbol || !data.profile || !Array.isArray(data.years) || !data.tables || !data.ratios || !data.price || !data.valuation || !data.peers) return null;
    return data;
  } catch { return null; }
}
