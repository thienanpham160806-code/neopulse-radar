"use client";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { num } from "@/lib/format";
import { TOOLTIP_STYLE } from "./ui";
export function CompanyPriceChart({ series, symbol }: { series: [string, number, number][]; symbol: string }) {
  const data = series.map(([date, stock, index]) => ({ date, stock, index }));
  return <div className="h-64" role="img" aria-label={`Giá ${symbol} và VN-Index, cùng quy về 100 tại ngày đầu`}>
    <ResponsiveContainer><LineChart data={data} margin={{ left: 0, right: 12, top: 12 }}>
      <CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="date" minTickGap={60} tickFormatter={(s: string) => s.slice(0, 7)} />
      <YAxis width={46} domain={["auto", "auto"]} tickFormatter={(v: number) => num(v, 0)} />
      <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => num(v)} /><Legend />
      <Line name={symbol} dataKey="stock" stroke="var(--accent)" dot={false} isAnimationActive={false} strokeWidth={2} />
      <Line name="VN-Index" dataKey="index" stroke="var(--muted)" strokeDasharray="5 3" dot={false} isAnimationActive={false} />
    </LineChart></ResponsiveContainer>
  </div>;
}
