import { expect, it } from "vitest";
import { chartPoints } from "../src/lib/chart";
it("chuẩn hóa múi giờ, loại điểm lỗi/trùng và sắp thời gian tăng", () => {
  const p = chartPoints([{ time: "2026-11-19T10:00:00+07:00", value: 1 }, { time: "bad", value: 3 }, { time: "2026-11-19T03:00:00Z", value: 2 }, { time: "2026-11-18", value: 4 }, { time: "2026-11-17", value: NaN }]);
  expect(p).toHaveLength(2);
  expect(p[0].value).toBe(4);
  expect(p[1].value).toBe(2);
  expect(p[1].time).toBe(Date.parse("2026-11-19T03:00:00Z") / 1000);
});
