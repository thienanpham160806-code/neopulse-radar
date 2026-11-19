import type { Meta, Phase } from "./types";

export type Level = "green" | "amber" | "red" | "closed" | "sim" | "error" | "snapshot";

export interface Freshness {
  level: Level;
  label: string;
  detail: string;
  /** tuổi dữ liệu (giây) tính từ lần cập nhật cuối; null nếu không áp dụng */
  ageSeconds: number | null;
}

const GREEN_UNDER_S = 60;
const AMBER_UNDER_S = 300;

/** Pha phiên theo giờ Việt Nam (UTC+7, không có giờ mùa hè). Khớp `webexport.session_phase` bên Python. */
export function sessionPhase(nowMs: number): Phase {
  const vn = new Date(nowMs + 7 * 3600_000);
  const dow = vn.getUTCDay(); // 0 = CN, 6 = T7
  if (dow === 0 || dow === 6) return "closed";
  const m = vn.getUTCHours() * 60 + vn.getUTCMinutes();
  if (m < 9 * 60) return "pre";
  if (m < 11 * 60 + 30) return "open";
  if (m < 13 * 60) return "lunch";
  if (m <= 15 * 60 + 5) return "open";
  return "closed";
}

export function ageSince(iso: string | null, nowMs: number): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : Math.max(0, (nowMs - t) / 1000);
}

export function formatAge(sec: number | null): string {
  if (sec === null) return "—";
  if (sec < 90) return `${Math.round(sec)} giây`;
  if (sec < 5400) return `${Math.round(sec / 60)} phút`;
  return `${(sec / 3600).toFixed(1)} giờ`;
}

/**
 * Trạng thái hiển thị. JSON chỉ là ảnh chụp tại `generated_at` nên độ tươi luôn tính lại từ đồng hồ hiện tại:
 * xanh < 60 s, cam < 5 phút, đỏ còn lại. Ngoài giờ giao dịch là "phiên đã kết thúc", KHÔNG phải lỗi.
 */
export function freshness(meta: Meta, nowMs: number): Freshness {
  const st = meta.data_status;
  const ageData = ageSince(meta.last_update, nowMs);
  const ageGen = ageSince(meta.generated_at, nowMs);
  if (st.state === "error") {
    return { level: "error", label: "Lỗi dữ liệu", detail: st.reason, ageSeconds: ageData };
  }
  if (meta.snapshot_at && !meta.is_simulated) return snapshotFreshness(meta, nowMs);
  if (meta.is_simulated) {
    return { level: "sim", label: "MÔ PHỎNG", detail: "Dữ liệu mô phỏng — không phải dữ liệu thị trường.", ageSeconds: null };
  }
  const phaseNow = sessionPhase(nowMs);
  if (phaseNow !== "open") {
    const label = phaseNow === "lunch" ? "Nghỉ trưa" : phaseNow === "pre" ? "Chưa mở cửa" : "Phiên đã kết thúc";
    const why = phaseNow === "lunch" ? "Nghỉ trưa (11:30–13:00)." : phaseNow === "pre" ? "Phiên chưa mở cửa." : "Phiên đã kết thúc.";
    return { level: "closed", label, detail: `${why} Hiển thị dữ liệu của lần cập nhật cuối.`, ageSeconds: ageData };
  }
  // đang trong giờ giao dịch
  if (st.state === "closed" && (ageGen === null || ageGen > AMBER_UNDER_S)) {
    return {
      level: "red",
      label: "Dữ liệu cũ",
      detail: "Đang trong giờ giao dịch nhưng bản đẩy lên web đã cũ — máy ghi hoặc `neopulse publish` có thể đã dừng.",
      ageSeconds: ageGen,
    };
  }
  if (st.state === "closed") {
    return { level: "closed", label: "Phiên đã kết thúc", detail: st.reason, ageSeconds: ageData };
  }
  const age = ageData ?? ageGen;
  if (age === null) return { level: "red", label: "Không rõ tuổi dữ liệu", detail: "Thiếu mốc thời gian cập nhật.", ageSeconds: null };
  if (age < GREEN_UNDER_S) return { level: "green", label: "Dữ liệu mới", detail: "Đang nhận dữ liệu.", ageSeconds: age };
  if (age < AMBER_UNDER_S) return { level: "amber", label: "Hơi trễ", detail: "Dữ liệu chưa được làm mới gần đây.", ageSeconds: age };
  return { level: "red", label: "Dữ liệu cũ", detail: "Bộ ghi hoặc đường đẩy dữ liệu có thể đã dừng, hoặc mất kết nối.", ageSeconds: age };
}

/**
 * Snapshot tĩnh (không phải thời gian thực). Tuổi của snapshot KHÔNG làm đổi màu thành đỏ: dữ liệu vốn đứng yên.
 *  - cuối phiên: chấm xanh dương "snapshot", không cảnh báo dù đã cũ nhiều ngày;
 *  - giữa phiên: chấm cam, nhắc rằng thị trường đã đi tiếp sau thời điểm snapshot.
 */
export function snapshotFreshness(meta: Meta, nowMs: number): Freshness {
  const age = ageSince(meta.snapshot_at ?? null, nowMs);
  const base = "Không phải thời gian thực: số liệu cố định tại thời điểm snapshot.";
  if (meta.snapshot_kind === "intraday") {
    return {
      level: "amber",
      label: "Snapshot giữa phiên",
      detail: `${base} Thị trường có thể đã thay đổi sau lúc snapshot.`,
      ageSeconds: age,
    };
  }
  return { level: "snapshot", label: "Snapshot cuối phiên", detail: base, ageSeconds: age };
}
