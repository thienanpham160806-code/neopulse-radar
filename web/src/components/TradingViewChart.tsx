"use client";
import { useEffect, useRef, useState } from "react";
import { AreaSeries, LineSeries, ColorType, createChart, type Time, type UTCTimestamp, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { num } from "@/lib/format";
import { chartPoints } from "@/lib/chart";

export function TradingViewChart({ symbol, data, comparison, exchange = "HOSE" }: {
  symbol: string; data: { time: string; value: number }[]; comparison?: { time: string; value: number }[]; exchange?: string | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<IChartApi | null>(null);
  const mainSeries = useRef<ISeriesApi<"Area"> | null>(null);
  const comparisonSeries = useRef<ISeriesApi<"Line"> | null>(null);
  const fitted = useRef(false);
  const ready = data.length > 1;
  const hasComparison = Boolean(comparison);
  const intraday = Boolean(data[0]?.time.includes("T"));
  const [selected, setSelected] = useState<string | null>(null);
  const url = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(`${exchange ?? "HOSE"}:${symbol}`)}`;
  useEffect(() => {
    if (!host.current || !ready) return;
    const el = host.current;
    const color = (key: string) => getComputedStyle(document.documentElement).getPropertyValue(key).trim();
    const chart = createChart(el, { autoSize: true, layout: { background: { type: ColorType.Solid, color: color("--surface") }, textColor: color("--muted"), attributionLogo: true }, grid: { vertLines: { visible: false }, horzLines: { color: color("--line") } }, rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, timeVisible: intraday, tickMarkFormatter: (t: Time) => typeof t === "number" ? new Date(t * 1000).toLocaleString("vi-VN", intraday ? { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit" } : { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit" }) : null }, localization: { locale: "vi-VN", priceFormatter: (v: number) => num(v), timeFormatter: (t: Time) => typeof t === "number" ? new Date(t * 1000).toLocaleString("vi-VN", intraday ? { timeZone: "Asia/Ho_Chi_Minh" } : { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric" }) : String(t) } });
    const area = chart.addSeries(AreaSeries, { lineColor: color("--accent"), topColor: color("--surface-2"), bottomColor: color("--surface"), lineWidth: 2 });
    api.current = chart; mainSeries.current = area; fitted.current = false;
    const index = hasComparison ? chart.addSeries(LineSeries, { color: color("--muted"), lineStyle: 2, lineWidth: 1 }) : null;
    comparisonSeries.current = index;
    chart.subscribeCrosshairMove((p) => {
      const row = p.seriesData.get(area);
      setSelected(row && "value" in row ? `${symbol}: ${num(row.value)}` : null);
    });
    const updateTheme = () => {
      chart.applyOptions({ layout: { background: { type: ColorType.Solid, color: color("--surface") }, textColor: color("--muted") }, grid: { horzLines: { color: color("--line") } } });
      area.applyOptions({ lineColor: color("--accent"), topColor: color("--surface-2"), bottomColor: color("--surface") });
      index?.applyOptions({ color: color("--muted") });
    };
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { observer.disconnect(); chart.remove(); api.current = null; mainSeries.current = null; comparisonSeries.current = null; };
  }, [ready, hasComparison, intraday, symbol]);
  useEffect(() => {
    mainSeries.current?.setData(chartPoints(data).map((p) => ({ ...p, time: p.time as UTCTimestamp })));
    comparisonSeries.current?.setData(chartPoints(comparison ?? []).map((p) => ({ ...p, time: p.time as UTCTimestamp })));
    if (api.current && !fitted.current) { api.current.timeScale().fitContent(); fitted.current = true; }
  }, [data, comparison, ready, hasComparison, intraday, symbol]);
  return <div>
    <div className="mb-3 flex flex-wrap justify-between gap-2 text-xs"><span className="tnum font-medium">{selected ?? `${symbol}${comparison ? " / VN-Index · ngày đầu = 100" : " · chỉ số"}`}</span><a href={url} target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-4">Mở trên TradingView ↗</a></div>
    {data.length > 1 ? <div ref={host} data-testid="tradingview-chart" className="h-72 min-w-0 sm:h-96" role="img" aria-label={`Biểu đồ tương tác ${symbol}`} /> : <p className="py-10 text-center text-sm text-muted">Chưa đủ điểm dữ liệu để vẽ biểu đồ.</p>}
    <p className="mt-3 text-xs leading-relaxed text-muted">Cuộn để thu phóng, kéo để di chuyển, chạm để đọc giá trị. Dữ liệu NeoPulse theo nguồn và thời điểm ghi trên trang; không phải luồng giá từ TradingView. Thời gian hiển thị theo giờ Việt Nam.</p>
    <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-[10px] text-muted">TradingView Lightweight Charts™ · Copyright (с) 2025 TradingView, Inc.</a>
  </div>;
}
