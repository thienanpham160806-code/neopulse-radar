"use client";

import { clock, dmy } from "@/lib/format";
import { ageSince, formatAge, freshness, type Level } from "@/lib/status";
import type { Meta } from "@/lib/types";

const DOT: Record<Level, string> = {
  // không mượn màu giá (xanh/đỏ/vàng): trạng thái dữ liệu dùng accent, độ đậm của mực và chữ
  green: "bg-accent",
  amber: "border-2 border-fg bg-transparent",
  red: "bg-fg",
  error: "bg-fg",
  closed: "bg-muted",
  sim: "bg-sim",
  snapshot: "bg-accent",
};

const BADGE: Record<Level, string> = {
  green: "bg-accent text-on-accent",
  snapshot: "bg-surface2 text-fg border border-line",
  amber: "bg-surface2 text-fg border border-fg/50",
  red: "bg-fg text-bg",
  error: "bg-fg text-bg",
  closed: "bg-surface2 text-muted border border-line",
  sim: "bg-sim text-bg",
};

/** Thanh trạng thái luôn hiện: nguồn · giờ cập nhật · tuổi dữ liệu · phạm vi & cảnh báo thiếu dữ liệu. */
export interface LiveInfo {
  ts: string | null;
  latencyMs: number | null;
  simulated: boolean;
}

export function StatusBar({ meta, nowMs, notice, pollError, live = null, liveNote = null }: {
  meta: Meta; nowMs: number; notice: string | null; pollError: string | null; live?: LiveInfo | null; liveNote?: string | null;
}) {
  const f = live
    ? { level: "green" as Level, label: "Trực tiếp", detail: "", ageSeconds: null }
    : freshness(meta, nowMs);
  const excluded = meta.n_symbols_excluded;
  const showSource = meta.source_label && meta.source_label.toUpperCase() !== f.label.toUpperCase();
  const isSim = Boolean(meta.is_simulated || live?.simulated);

  return (
    <div className="border-b border-line bg-surface/75 text-muted">
      <div className="mx-auto max-w-6xl px-3 sm:px-6">
        <details className="group">
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2.5 gap-y-1.5 py-2 text-xs">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-semibold ${BADGE[f.level]}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${f.level === "green" || f.level === "sim" || f.level === "red" || f.level === "error" ? "bg-current" : DOT[f.level]}`} aria-hidden />
              {f.label}
            </span>
            {showSource ? <span className="font-medium text-fg">{meta.source_label}</span> : null}
            <span className="tnum text-fg/90">
              {clock(live?.ts ?? meta.last_update)} · {dmy(meta.trading_date)}
            </span>
            <span className="tnum hidden text-muted sm:inline">
              · {meta.n_symbols_computed} mã{excluded > 0 ? ` (${excluded} mã bị loại)` : ""}
            </span>
            {meta.snapshot_at && !live ? (
              <span className="rounded-full bg-surface2 px-2 py-0.5 text-[11px] font-medium text-fg">
                Không phải thời gian thực
              </span>
            ) : null}
            {isSim ? (
              <span className="hidden text-sim md:inline">· Số liệu giả lập minh họa</span>
            ) : null}
            <span className="ml-auto inline-flex items-center gap-1 font-medium text-accent">
              <span className="hidden sm:inline">Chi tiết dữ liệu</span>
              <span aria-hidden className="ui-transition inline-block group-open:rotate-180">▾</span>
            </span>
          </summary>

          <div
            className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-line/70 py-2.5 text-xs"
            role="status"
            aria-live="polite"
          >
            <span>
              <span className="text-muted">Nguồn: </span>
              <b className={meta.is_simulated ? "text-sim" : "text-fg"}>{meta.source_label}</b>
            </span>
            {live ? (
              <>
                <span className="tnum">
                  <span className="text-muted">Tin lúc: </span>
                  <b className="text-fg">{clock(live.ts)}</b> (giờ VN)
                </span>
                <span className="tnum">
                  <span className="text-muted">Độ trễ: </span>
                  <b className="text-fg">
                    {live.latencyMs === null ? "—" : `${(live.latencyMs / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`}
                  </b>
                </span>
              </>
            ) : meta.snapshot_at ? (
              <>
                <span className="tnum">
                  <span className="text-muted">Bản dữ liệu lúc: </span>
                  <b className="text-fg">{clock(meta.snapshot_at)} · {dmy(meta.snapshot_at.slice(0, 10))}</b> (giờ VN)
                </span>
                <span className="tnum">
                  <span className="text-muted">Cách đây: </span>
                  <b className="text-fg">{formatAge(ageSince(meta.snapshot_at, nowMs))}</b>
                </span>
                <span className="tnum">
                  <span className="text-muted">Số liệu đến: </span>
                  <b className="text-fg">{clock(meta.last_update)} · {dmy(meta.trading_date)}</b>
                </span>
              </>
            ) : (
              <>
                <span className="tnum">
                  <span className="text-muted">Cập nhật: </span>
                  <b className="text-fg">{clock(meta.last_update)} · {dmy(meta.trading_date)}</b> (giờ VN)
                </span>
                {f.ageSeconds !== null ? (
                  <span className="tnum">
                    <span className="text-muted">Cách đây: </span>
                    <b className="text-fg">{formatAge(f.ageSeconds)}</b>
                  </span>
                ) : null}
              </>
            )}
            <span className="tnum">
              <span className="text-muted">Số mã đã tính / bị loại: </span>
              <b className="text-fg">{meta.n_symbols_computed} / {excluded}</b>
              {meta.excluded_reason ? <span className="text-muted"> ({meta.excluded_reason})</span> : null}
            </span>
            <span className="tnum">
              <span className="text-muted">Số phiên đã lưu: </span>
              <b className="text-fg">{meta.n_sessions}</b>
            </span>
          </div>
        </details>
      </div>

      {/* Dải cảnh báo tình trạng dữ liệu — luôn hiện rõ khi MÔ PHỎNG / thiếu dữ liệu / giữa phiên / ngoài giờ / lỗi */}
      {isSim ? (
        <div className="border-t border-dashed border-sim/60 bg-surface2/90 px-3 py-1 text-center text-xs text-sim">
          <b>DỮ LIỆU MÔ PHỎNG</b> — số do bộ giả lập sinh ra để trình diễn, không phản ánh thị trường thật.
        </div>
      ) : null}
      {f.level === "red" || f.level === "error" ? (
        <div role="alert" className="border-t border-fg bg-surface2 px-3 py-1.5 text-center text-xs font-semibold text-fg">
          {f.detail}
        </div>
      ) : f.level === "closed" && !meta.is_simulated ? (
        <div className="border-t border-line bg-surface2 px-3 py-1 text-center text-xs text-fg">
          {f.detail}
        </div>
      ) : f.level === "amber" ? (
        <div className="border-t border-line bg-surface2 px-3 py-1.5 text-center text-xs font-medium text-fg">
          {f.detail}
        </div>
      ) : null}
      {excluded > 0 && meta.excluded_reason ? (
        <div className="border-t border-line bg-surface2/70 px-3 py-1 text-center text-xs text-muted">
          <b className="text-fg">Phạm vi rổ:</b> {excluded} mã bị loại khỏi tính toán ({meta.excluded_reason}).
        </div>
      ) : null}
      {liveNote ? (
        <div role="status" className="border-t border-line bg-surface2 px-3 py-1 text-center text-xs text-fg">
          {liveNote}
        </div>
      ) : null}
      {notice && !meta.is_simulated ? (
        <div className="border-t border-line bg-surface2 px-3 py-1 text-center text-xs text-muted">
          {notice}
        </div>
      ) : null}
      {pollError ? (
        <div role="alert" className="border-t border-line bg-surface2 px-3 py-1 text-center text-xs font-medium text-fg">
          Không làm mới được: {pollError}. Đang giữ bản dữ liệu gần nhất.
        </div>
      ) : null}
    </div>
  );
}
