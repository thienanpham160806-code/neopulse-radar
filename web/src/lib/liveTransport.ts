/** Đường truyền SSE của Ably (không SDK): địa chỉ luồng và nhịp lùi khi nối lại. */
export const LIVE_CHANNEL = "neopulse:live";

export interface TokenDetails {
  token: string;
  expires: number;
  issued: number;
  capability: string;
  keyName: string;
}

/** https://realtime.ably.io/sse?v=1.2&channels=<kênh>&accessToken=<token> ; mỗi sự kiện là JSON {name, data, ...}. */
export function sseUrl(token: string, channel = LIVE_CHANNEL): string {
  const q = new URLSearchParams({ v: "1.2", channels: channel, accessToken: token });
  return `https://realtime.ably.io/sse?${q.toString()}`;
}

/** Lùi dần 2, 4, 8 ... giây, tối đa 60 giây. */
export function nextBackoffMs(failures: number): number {
  return Math.min(60_000, 1000 * 2 ** Math.max(1, failures));
}
