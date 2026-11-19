import type { Payload, SessionIndex } from "./types";

const SUPPORTED_SCHEMA = 1;
export class ParseError extends Error {}

function isObj(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

/** Kiểm tra tối thiểu hình dạng JSON trước khi vẽ; thiếu/sai phiên bản -> ParseError (web hiện lỗi rõ ràng). */
export function parsePayload(raw: unknown): Payload {
  if (!isObj(raw) || !isObj(raw.meta)) throw new ParseError("JSON không có khối meta.");
  const m = raw.meta;
  if (m.schema_version !== SUPPORTED_SCHEMA) {
    throw new ParseError(`Phiên bản schema ${String(m.schema_version)} chưa được hỗ trợ (cần ${SUPPORTED_SCHEMA}).`);
  }
  if (typeof m.generated_at !== "string" || typeof m.source !== "string" || typeof m.is_simulated !== "boolean") {
    throw new ParseError("meta thiếu trường bắt buộc (generated_at, source, is_simulated).");
  }
  const ds = m.data_status;
  if (!isObj(ds) || !["fresh", "stale", "error", "closed"].includes(String(ds.state))) {
    throw new ParseError("meta.data_status không hợp lệ.");
  }
  return raw as unknown as Payload;
}

export function parseIndex(raw: unknown): SessionIndex {
  if (!isObj(raw) || !Array.isArray(raw.sessions)) throw new ParseError("index.json không hợp lệ.");
  return raw as unknown as SessionIndex;
}
