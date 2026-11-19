/** Chuẩn hóa dữ liệu cho thư viện vẽ, không tính chỉ báo tài chính. */
export function chartPoints(rows: { time: string; value: number }[]) {
  const points = new Map<number, number>();
  for (const r of rows) {
    const t = Math.floor(Date.parse(r.time) / 1000);
    if (Number.isFinite(t) && Number.isFinite(r.value)) points.set(t, r.value);
  }
  return [...points.entries()].sort(([a], [b]) => a - b).map(([time, value]) => ({ time, value }));
}
