"use client";

import { useEffect, useState } from "react";
import { applyLive, emptyLive, parseLive, type LiveState } from "@/lib/live";
import { sseUrl, nextBackoffMs, type TokenDetails } from "@/lib/liveTransport";

/**
 * Kết nối kênh trực tiếp qua Server-Sent Events của Ably (EventSource có sẵn trong trình duyệt, không cần SDK).
 * Token lấy từ /api/ably-token (chỉ subscribe, hạn ngắn); chưa cấu hình/bị khóa thì im lặng ở chế độ snapshot.
 * Mất kết nối hoặc token sắp hết hạn: đóng và nối lại với token mới, lùi dần 2 giây -> 60 giây.
 */
export function useLive(enabled: boolean): { state: LiveState; connected: boolean; error: string | null; available: boolean } {
  const [state, setState] = useState<LiveState>(emptyLive);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let es: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let failures = 0;

    const schedule = (ms: number) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => void connect(), ms);
    };

    const connect = async () => {
      es?.close();
      if (stopped) return;
      let tok: TokenDetails;
      try {
        const r = await fetch("/api/ably-token", { cache: "no-store" });
        if (r.status === 503 || r.status === 403 || r.status === 401) return; // không có kênh trực tiếp: dùng snapshot
        if (!r.ok) throw new Error(`token HTTP ${r.status}`);
        tok = (await r.json()) as TokenDetails;
      } catch (e) {
        setError(e instanceof Error ? e.message : "không mở được kênh trực tiếp");
        failures += 1;
        schedule(nextBackoffMs(failures));
        return;
      }
      if (stopped) return;
      setAvailable(true);
      es = new EventSource(sseUrl(tok.token));
      es.onopen = () => {
        failures = 0;
        setConnected(true);
        setError(null);
      };
      es.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as { name?: string; data?: unknown };
          const m = parseLive(msg.name ?? "", msg.data);
          if (m) setState((s) => applyLive(s, m, Date.now()));
        } catch {
          /* bỏ khung hỏng */
        }
      };
      es.onerror = () => {
        setConnected(false);
        es?.close();
        failures += 1;
        schedule(nextBackoffMs(failures));
      };
      // nối lại chủ động 60 giây trước khi token hết hạn
      schedule(Math.max(30_000, tok.expires - Date.now() - 60_000));
    };

    void connect();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      es?.close();
    };
  }, [enabled]);

  return { state, connected, error, available };
}
