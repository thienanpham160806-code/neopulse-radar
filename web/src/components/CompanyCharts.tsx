"use client";
import { useMemo } from "react";
import { TradingViewChart } from "./TradingViewChart";
export function CompanyPriceChart({ series, symbol }: { series: [string, number, number][]; symbol: string }) {
  const stock = useMemo(() => series.map(([time, value]) => ({ time, value })), [series]);
  const index = useMemo(() => series.map(([time, , value]) => ({ time, value })), [series]);
  return <TradingViewChart symbol={symbol} data={stock} comparison={index} />;
}
