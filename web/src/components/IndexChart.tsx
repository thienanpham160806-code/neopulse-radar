"use client";

/** Đồ thị chỉ số trong phiên + đường tham chiếu. Tách riêng để tải lười (Recharts nặng, không chặn lần vẽ đầu). */
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { isNum } from "@/lib/fmt";
import { num } from "@/lib/format";
import type { Num } from "@/lib/types";
import { TOOLTIP_STYLE } from "./ui";

export default function IndexChart({ data, code, refValue }: { data: { t: string; v: number }[]; code: string; refValue: Num }) {
  return (
    <div className="h-64" role="img" aria-label={`Diễn biến ${code} trong phiên`}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="t" minTickGap={48} tickLine={false} axisLine={false} />
          <YAxis domain={["auto", "auto"]} width={50} tickLine={false} axisLine={false} tickFormatter={(v: number) => num(v, 0)} />
          <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [num(v), code]} />
          {isNum(refValue) ? <ReferenceLine y={refValue} stroke="var(--refc)" strokeDasharray="5 4" ifOverflow="extendDomain"
            label={{ value: `Tham chiếu ${num(refValue)}`, position: "insideTopLeft", fill: "var(--refc)", fontSize: 11 }} /> : null}
          <Line dataKey="v" stroke="var(--fg)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
