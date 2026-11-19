import { promises as fs } from "fs";
import path from "path";
import type { Loaded } from "@/lib/data";
import { parseIndex, parsePayload } from "@/lib/parse";

/**
 * Bản xem trước giao diện LUÔN dùng dữ liệu MẪU MÔ PHỎNG (public/sample), không đọc snapshot thật trong public/data:
 * - để cả ba hướng chạy cùng một bộ dữ liệu và cùng luồng phát lại mô phỏng (cùng nguồn "sim");
 * - để link preview gửi đi không làm lộ dữ liệu SSI thật.
 */
export async function loadSample(): Promise<Loaded> {
  const dir = path.join(process.cwd(), "public", "sample");
  const read = async (rel: string) => JSON.parse(await fs.readFile(path.join(dir, rel), "utf-8"));
  return {
    payload: parsePayload(await read("latest.json")),
    index: parseIndex(await read("index.json")),
    origin: "sample",
    notice: null,
  };
}
