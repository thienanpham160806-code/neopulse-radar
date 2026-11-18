import { promises as fs } from "fs";
import path from "path";
import { ParseError, parseIndex, parsePayload } from "./parse";
import type { Payload, SessionIndex } from "./types";

export interface Loaded {
  payload: Payload;
  index: SessionIndex;
  /** blob = dữ liệu do `neopulse publish` đẩy lên; sample = dữ liệu MÔ PHỎNG đi kèm mã nguồn */
  origin: "blob" | "sample";
  notice: string | null;
}

export const REVALIDATE_S = 15;

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

async function readSample(rel: string): Promise<unknown> {
  const text = await fs.readFile(path.join(process.cwd(), "public", "sample", rel), "utf-8");
  return JSON.parse(text);
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
  let rel = code && code !== "VN30" ? `latest_${code}.json` : "latest.json";
  if (date) {
    const e = index.sessions.find((s) => s.trading_date === date && (!code || s.index_code === code));
    if (!e) throw new ParseError(`Không có phiên ${date}${code ? ` (${code})` : ""} trong danh sách đã xuất.`);
    rel = e.path;
  }
  return { payload: parsePayload(await read(rel)), index };
}

/** Đọc dữ liệu cho trang. Không cấu hình Blob -> dữ liệu mẫu MÔ PHỎNG; Blob lỗi -> báo rõ và rơi về mẫu. */
export async function loadData(date?: string | null, code?: string | null): Promise<Loaded> {
  const base = blobBase();
  if (base) {
    try {
      const r = await loadFrom((rel) => fetchJson(base, rel), date, code);
      return { ...r, origin: "blob", notice: null };
    } catch (e) {
      const why = e instanceof Error ? e.message : "lỗi không xác định";
      const r = await loadFrom(readSample, date, code);
      return {
        ...r,
        origin: "sample",
        notice: `Không đọc được dữ liệu trực tiếp (${why}). Đang hiển thị dữ liệu MẪU MÔ PHỎNG đi kèm.`,
      };
    }
  }
  const r = await loadFrom(readSample, date, code);
  return { ...r, origin: "sample", notice: "Chưa cấu hình BLOB_READ_URL: đang hiển thị dữ liệu MẪU MÔ PHỎNG đi kèm mã nguồn." };
}

/** Nếu chưa đặt SITE_PASSWORD, chỉ cho phép dữ liệu mô phỏng. */
export function gateAllows(payload: Payload, hasPassword: boolean): boolean {
  return hasPassword || payload.meta.is_simulated;
}
