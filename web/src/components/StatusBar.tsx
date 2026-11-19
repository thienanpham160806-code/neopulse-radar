"use client";

import { clock, dmy } from "@/lib/format";
import { ageSince, formatAge, freshness, type Level } from "@/lib/status";
import type { Meta } from "@/lib/types";

const DOT: Record<Level, string> = {
  green: "bg-up",
  amber: "bg-warn",
  red: "bg-down",
  error: "bg-down",
  closed: "bg-muted",
  sim: "bg-sim",
  snapshot: "bg-accent",
};

/** Thanh trạng thái luôn hiện: nguồn · giờ cập nhật · tuổi dữ liệu · số mã tính/loại. */
export interface LiveInfo {
  ts: string | null;
  latencyMs: number | null;
  simulated: boolean;
}

export function StatusBar({ meta, nowMs, notice, pollError, live = null, liveNote = null }: {
  meta: Meta; nowMs: number; notice: string | null; pollError: string | null; live?: LiveInfo | null; liveNote?: string | null;
}) {
  const f = live
    ? { level: "green" as Level, label: "TRỰC TIẾP", detail: "", ageSeconds: null }
    : freshness(meta, nowMs);
  const excluded = meta.n_symbols_excluded;
  return (
    <div className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 text-xs sm:text-sm" role="status" aria-live="polite">
        <span className="flex items-center gap-2 font-semibold">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${DOT[f.level]}`} aria-hidden />
          {f.label}
        </span>
        <span>
          <span className="text-muted">Nguồn: </span>
          <b className={meta.is_simulated ? "text-sim" : ""}>{meta.source_label}</b>
        </span>
        {live ? (
          <>
            <span className="tnum">
              <span className="text-muted">Tin lúc: </span>
              {clock(live.ts)} <span className="text-muted">(giờ VN)</span>
            </span>
            <span className="tnum">
              <span className="text-muted">Độ trễ: </span>
              {live.latencyMs === null ? "—" : `${(live.latencyMs / 1000).toFixed(1)} giây`}
            </span>
          </>
        ) : meta.snapshot_at ? (
          <>
            <span className="tnum">
              <span className="text-muted">Snapshot lúc: </span>
              {clock(meta.snapshot_at)} · {dmy(meta.snapshot_at.slice(0, 10))} <span className="text-muted">(giờ VN)</span>
            </span>
            <span className="tnum">
              <span className="text-muted">Cách đây: </span>
              {formatAge(ageSince(meta.snapshot_at, nowMs))}
            </span>
            <span className="rounded bg-surface2 px-1.5 py-0.5 text-xs font-semibold">Không phải thời gian thực</span>
            <span className="tnum hidden sm:inline">
              <span className="text-muted">Số liệu đến: </span>
              {clock(meta.last_update)} · {dmy(meta.trading_date)}
            </span>
          </>
        ) : (
          <>
            <span className="tnum">
              <span className="text-muted">Cập nhật: </span>
              {clock(meta.last_update)} · {dmy(meta.trading_date)} <span className="text-muted">(giờ VN)</span>
            </span>
            {f.ageSeconds !== null ? (
              <span className="tnum">
                <span className="text-muted">Cách đây: </span>
                {formatAge(f.ageSeconds)}
              </span>
            ) : null}
          </>
        )}
        <span className="tnum">
          <span className="text-muted">Mã tính / loại: </span>
          {meta.n_symbols_computed} / {excluded}
        </span>
        <span className="tnum hidden sm:inline">
          <span className="text-muted">Số phiên đã lưu: </span>
          {meta.n_sessions}
        </span>
      </div>
      {meta.is_simulated || live?.simulated ? (
        <div className="bg-sim/15 px-4 py-1.5 text-center text-xs font-semibold text-sim sm:text-sm">
          DỮ LIỆU MÔ PHỎNG — mọi con số do bộ giả lập sinh ra để trình diễn, không phản ánh thị trường thật.
        </div>
      ) : null}
      {f.level === "snapshot" ? (
        <div className="bg-accent/10 px-4 py-1.5 text-center text-xs text-accent sm:text-sm">{f.detail}</div>
      ) : f.level === "red" || f.level === "error" ? (
        <div role="alert" className="bg-down/15 px-4 py-1.5 text-center text-xs text-down sm:text-sm">{f.detail}</div>
      ) : f.level === "closed" && !meta.is_simulated ? (
        <div className="bg-surface2 px-4 py-1.5 text-center text-xs text-muted sm:text-sm">{f.detail}</div>
      ) : f.level === "amber" ? (
        <div className="bg-warn/15 px-4 py-1.5 text-center text-xs text-warn sm:text-sm">{f.detail}</div>
      ) : null}
      {liveNote ? <div role="status" className="bg-warn/15 px-4 py-1.5 text-center text-xs text-warn sm:text-sm">{liveNote}</div> : null}
      {notice ? <div className="bg-surface2 px-4 py-1.5 text-center text-xs text-muted sm:text-sm">{notice}</div> : null}
      {pollError ? <div role="alert" className="bg-warn/15 px-4 py-1.5 text-center text-xs text-warn sm:text-sm">Không làm mới được: {pollError}. Đang giữ bản dữ liệu gần nhất.</div> : null}
    </div>
  );
}
