import { promises as fs } from "fs";
import path from "path";
import { ParseError, parseIndex, parsePayload } from "./parse";
import type { Payload, SessionIndex } from "./types";

export interface Loaded {
  payload: Payload;
  index: SessionIndex;
  /** static = snapshot tĩnh trong public/data (`neopulse publish-static`); blob = tùy chọn (`neopulse publish`);
   *  sample = dữ liệu MÔ PHỎNG đi kèm mã nguồn */
  origin: "static" | "blob" | "sample" | "cloud";
  notice: string | null;
}

const REVALIDATE_S = 15;

function blobBase(): string {
  return (process.env.BLOB_READ_URL ?? "").trim().replace(/\/+$/, "");
}

async function fetchJson(base: string, rel: string): Promise<unknown> {
  // tham số v đổi mỗi REVALIDATE_S giây để vượt cache CDN của Blob khi tệp được ghi đè cùng đường dẫn
  const v = Math.floor(Date.now() / (REVALIDATE_S * 1000));
  const res = await fetch(`${base}/${rel}?v=${v}`, { next: { revalidate: REVALIDATE_S } });
  if (!res.ok) throw new Error(`HTTP ${res.status} khi đọc ${rel}`);
  return res.json();
}

const publicDir = (sub: "data" | "sample") => path.join(process.cwd(), "public", sub);

async function readFrom(sub: "data" | "sample", rel: string): Promise<unknown> {
  return JSON.parse(await fs.readFile(path.join(publicDir(sub), rel), "utf-8"));
}
const readSample = (rel: string) => readFrom("sample", rel);
const readStatic = (rel: string) => readFrom("data", rel);

async function hasStatic(): Promise<boolean> {
  try {
    await fs.access(path.join(publicDir("data"), "latest.json"));
    return true;
  } catch {
    return false;
  }
}

async function loadFrom(
  read: (rel: string) => Promise<unknown>,
  date?: string | null,
  code?: string | null,
): Promise<{ payload: Payload; index: SessionIndex }> {
  let index: SessionIndex = { schema_version: 1, generated_at: "", sessions: [] };
  try {
    index = parseIndex(await read("index.json"));
  } catch {
    // index.json chỉ được ghi khi kết thúc phiên: giữa phiên vẫn xem được latest.json
  }
  // latest_<MÃ>.json luôn có cho mọi chỉ số; latest.json chỉ là bí danh của chỉ số chính (có thể không phải VN30)
  let rel = code ? `latest_${code}.json` : "latest.json";
  if (date) {
    const e = index.sessions.find((s) => s.trading_date === date && (!code || s.index_code === code));
    if (!e) throw new ParseError(`Không có phiên ${date}${code ? ` (${code})` : ""} trong danh sách đã xuất.`);
    rel = e.path;
  }
  return { payload: parsePayload(await read(rel)), index };
}

/**
 * Đọc dữ liệu cho trang. Thứ tự ưu tiên:
 *  1. BLOB_READ_URL (tùy chọn, tốn hạn mức) nếu được đặt;
 *  2. snapshot tĩnh `public/data/` (do `neopulse publish-static` sinh, không vào git);
 *  3. dữ liệu MẪU MÔ PHỎNG `public/sample/` (kèm thông báo rõ).
 * Lỗi ở bước trên được báo rõ rồi rơi xuống bước dưới.
 */
export async function loadData(date?: string | null, code?: string | null): Promise<Loaded> {
  let notice: string | null = null;
  const kvUrl = process.env.KV_REST_API_URL, kvToken = process.env.KV_REST_API_TOKEN;
  if (kvUrl && kvToken && (!code || ["VN30", "VNINDEX", "HNXINDEX", "UPCOMINDEX"].includes(code)) && (!date || /^\d{4}-\d{2}-\d{2}$/.test(date))) {
    try {
      const key = date ? `neopulse:market:session:${date}:${code ?? "VN30"}` : `neopulse:market:latest:${code ?? "VN30"}`;
      const response = await fetch(kvUrl, { method: "POST", headers: { Authorization: `Bearer ${kvToken}`, "Content-Type": "application/json" }, body: JSON.stringify(["GET", key]), next: { revalidate: REVALIDATE_S }, signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error("cloud unavailable");
      const stored = await response.json();
      if (stored.error) throw new Error("cloud unavailable");
      if (stored.result) {
        const payload = parsePayload(JSON.parse(stored.result));
        if (payload.meta.is_simulated || payload.meta.source !== "ssi" || payload.meta.index_code !== (code ?? "VN30") || (date && payload.meta.trading_date !== date)) throw new Error("invalid cloud session");
        let index: SessionIndex = { schema_version: 1, generated_at: payload.meta.generated_at, sessions: [] };
        try { index = parseIndex(await readStatic("index.json")); } catch { /* The cloud session can bootstrap without local data. */ }
        const meta = payload.meta;
        if (meta.trading_date && !index.sessions.some((s) => s.trading_date === meta.trading_date && s.index_code === meta.index_code && s.source === meta.source)) {
          index.sessions.unshift({ source: meta.source, is_simulated: false, trading_date: meta.trading_date, index_code: meta.index_code, path: `sessions/${meta.source}_${meta.trading_date}_${meta.index_code}.json`, generated_at: meta.generated_at, pulse_score: payload.pulse?.score ?? null, n_symbols: meta.n_symbols_computed });
        }
        return { payload, index, origin: "cloud", notice: null };
      }
    } catch { notice = "Không tải được phiên mới nhất; trang đang dùng dữ liệu đã lưu. Xem thời điểm cập nhật trên thanh trạng thái."; }
  }
  const base = blobBase();
  if (base) {
    try {
      return { ...(await loadFrom((rel) => fetchJson(base, rel), date, code)), origin: "blob", notice: null };
    } catch (e) {
      notice = `Không đọc được dữ liệu đã xuất bản (${e instanceof Error ? e.message : "lỗi không xác định"}).`;
    }
  }
  if (await hasStatic()) {
    try {
      return { ...(await loadFrom(readStatic, date, code)), origin: "static", notice };
    } catch (e) {
      notice = `${notice ?? ""} Không đọc được bản dữ liệu tĩnh (${e instanceof Error ? e.message : "lỗi không xác định"}).`.trim();
    }
  }
  const r = await loadFrom(readSample, date, code);
  return {
    ...r,
    origin: "sample",
    notice: `${notice ? notice + " " : ""}Chưa có dữ liệu thị trường thật. Trang đang hiển thị dữ liệu MÔ PHỎNG đi kèm mã nguồn.`,
  };
}
