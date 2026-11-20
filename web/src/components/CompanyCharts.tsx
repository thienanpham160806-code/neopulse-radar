"use client";
import { useMemo } from "react";
import { TradingViewChart } from "./TradingViewChart";
import { TechnicalChart, type ChartData } from "./TechnicalChart";
import { useState } from "react";
export function CompanyPriceChart({ series, symbol, technical }: { series: [string, number, number][]; symbol: string; technical?: ChartData }) {
  const stock = useMemo(() => series.map(([time, value]) => ({ time, value })), [series]);
  const index = useMemo(() => series.map(([time, , value]) => ({ time, value })), [series]);
  const [compare, setCompare] = useState(false);
  return <div><div className="mb-4 flex gap-2 text-sm"><button aria-pressed={!compare} onClick={() => setCompare(false)} className="rounded-full bg-surface2 px-4 py-2">Giá & chỉ báo</button><button disabled={series.length < 2} aria-pressed={compare} onClick={() => setCompare(true)} className="rounded-full bg-surface2 px-4 py-2">So với VN-Index</button></div>{compare ? <TradingViewChart symbol={symbol} data={stock} comparison={index} /> : <TechnicalChart key={symbol} symbol={symbol} fallback={technical} />}</div>;
}
