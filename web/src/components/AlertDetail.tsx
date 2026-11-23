import { isNum } from "@/lib/fmt";
import { num } from "@/lib/format";
import type { AlertItem } from "@/lib/types";
import { Term } from "./Glossary";

const TERM: Record<string, string> = { volume_spike: "rvol", spread_blowout: "spread", price_jump: "anomaly", foreign_flow: "foreign", book_pressure: "book", near_limit: "band" };

/** Show the supplied rule result; never reverse-engineer live measurements from message text. */
export function AlertDetail({ a }: { a: AlertItem }) {
  return <div className="mt-2 space-y-2 text-sm leading-relaxed">
    <p>{a.message}</p>
    {isNum(a.value) && isNum(a.threshold)
      ? <p className="text-muted">Giá trị kiểm tra: <b className="tnum text-fg">{num(a.value, 2)}</b> · Ngưỡng quy tắc: <b className="tnum text-fg">{num(a.threshold, 2)}</b>. Đơn vị và cách đối chiếu xem trong mô tả cảnh báo.</p>
      : <p className="text-muted">Bản tin nhanh chưa kèm giá trị và ngưỡng đo. Chờ bản dữ liệu đầy đủ để đối chiếu; không suy ra mức nền từ câu thông báo.</p>}
    <p className="text-muted"><Term k={TERM[a.rule] ?? "anomaly"}>Hiểu chỉ số của quy tắc</Term> · Đây là biến động cần xem lại, chưa cho biết nguyên nhân hay hướng giá tiếp theo.</p>
  </div>;
}
