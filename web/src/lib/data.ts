import { promises as fs } from "fs";
import path from "path";
import { ParseError, parseIndex, parsePayload } from "./parse";
import type { Payload, SessionIndex } from "./types";

export interface Loaded {
  payload: Payload;
  index: SessionIndex;
  /** static = snapshot tĩnh trong public/data (`neopulse publish-static`); blob = tùy chọn (`neopulse publish`);
   *  sample = dữ liệu MÔ PHỎNG đi kèm mã nguồn */
  origin: "static" | "blob" | "sample";
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
  const base = blobBase();
  if (base) {
    try {
      return { ...(await loadFrom((rel) => fetchJson(base, rel), date, code)), origin: "blob", notice: null };
    } catch (e) {
      notice = `Không đọc được Blob (${e instanceof Error ? e.message : "lỗi không xác định"}).`;
    }
  }
  if (await hasStatic()) {
    try {
      return { ...(await loadFrom(readStatic, date, code)), origin: "static", notice };
    } catch (e) {
      notice = `${notice ?? ""} Không đọc được snapshot tĩnh (${e instanceof Error ? e.message : "lỗi không xác định"}).`.trim();
    }
  }
  const r = await loadFrom(readSample, date, code);
  return {
    ...r,
    origin: "sample",
    notice: `${notice ? notice + " " : ""}Chưa có snapshot dữ liệu thật (public/data trống): đang hiển thị dữ liệu MẪU MÔ PHỎNG đi kèm mã nguồn.`,
  };
}
