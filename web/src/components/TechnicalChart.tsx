"use client";
import { useEffect, useMemo, useState } from "react";
import { TradingViewChart } from "./TradingViewChart";
import { dmy } from "@/lib/format";

export interface ChartData { symbol: string; source: string; unit: string; data: { time: string; value: number }[]; studies: Record<string, { time: string; value: number }[]>; from: string | null; to: string | null }
const PERIODS = [5, 10, 20, 50, 100, 200];
export function TechnicalChart({ symbol, intraday = [], reference, fallback, intradayChart }: { symbol: string; intraday?: { time: string; value: number }[]; reference?: number | null; fallback?: ChartData; intradayChart?: ChartData }) {
  const [history, setHistory] = useState<ChartData | null>(fallback ?? null);
  const [error, setError] = useState(false);
  const [range, setRange] = useState("3T");
  const [ma, setMA] = useState(20), [ema, setEMA] = useState(50);
  const [showMA, setShowMA] = useState(true), [showEMA, setShowEMA] = useState(false), [showRef, setShowRef] = useState(false);
  useEffect(() => {
    if (fallback?.symbol === symbol && fallback.data.length) { setHistory(fallback); setError(false); return; }
    const controller = new AbortController();
    fetch(`/data/charts/${encodeURIComponent(symbol)}.json`, { signal: controller.signal }).then((r) => {
      if (!r.ok) throw new Error("missing");
      return r.json();
    }).then((p: ChartData) => { if (p.symbol !== symbol || !Array.isArray(p.data) || !p.studies) throw new Error("invalid"); setHistory(p); setError(false); }).catch((e) => { if (e.name !== "AbortError") setError(true); });
    return () => controller.abort();
  }, [symbol, fallback]);
  const isIntraday = range === "Phiên" || !history?.data.length;
  const data = isIntraday ? intraday : history!.data;
  const visible = useMemo(() => {
    if (isIntraday || range === "Tất cả") return data;
    const n = ({ "1T": 21, "3T": 63, "6T": 126, "1N": 252 } as Record<string, number>)[range];
    return data.slice(-n);
  }, [data, isIntraday, range]);
  const overlays = useMemo(() => {
    const study = isIntraday ? intradayChart : history;
    if (!study) return [];
    return [showMA ? `MA${ma}` : "", showEMA ? `EMA${ema}` : ""].filter(Boolean).map((key, i) => ({ name: key, data: study.studies[key] ?? [], color: i === 0 ? "#a182cf" : "#de8d48" }));
  }, [history, intradayChart, isIntraday, showMA, ma, showEMA, ema]);
  return <div>
    <div className="mb-4 flex flex-wrap items-center gap-2">{[...(intraday.length ? ["Phiên"] : []), "1T", "3T", "6T", "1N", "Tất cả"].map((r) => <button key={r} aria-pressed={range === r} onClick={() => setRange(r)} className={`min-h-10 rounded-full px-3 text-xs ${range === r ? "bg-accent text-on-accent" : "bg-surface2"}`}>{r}</button>)}</div>
    <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-3 text-xs">{[["MA", showMA, setShowMA, ma, setMA], ["EMA", showEMA, setShowEMA, ema, setEMA]].map(([name, checked, toggle, period, choose]) => <div key={name as string} className="flex items-center gap-2"><label className="flex min-h-10 items-center gap-2"><input type="checkbox" checked={checked as boolean} onChange={(e) => (toggle as (v: boolean) => void)(e.target.checked)} disabled={isIntraday && !intradayChart} />{name as string}</label><select aria-label={`Chu kỳ ${name}`} value={period as number} disabled={isIntraday && !intradayChart} onChange={(e) => (choose as (v: number) => void)(Number(e.target.value))} className="rounded bg-surface2 px-2 py-2">{PERIODS.map((n) => <option key={n} value={n}>{n}</option>)}</select></div>)}
      {reference != null ? <label className="flex min-h-10 items-center gap-2"><input type="checkbox" checked={showRef} onChange={(e) => setShowRef(e.target.checked)} />Tham chiếu phiên đang xem</label> : null}
    </div>
    <p className="mb-3 text-xs text-muted">{isIntraday ? "Nội phiên đã ghi · không có dữ liệu phút của các phiên chưa thu thập. MA/EMA nội phiên (nếu có) dừng ở mốc snapshot; không tính từ giá lịch sử ngày." : `${history!.source} · ${history!.unit} · ${data.length} phiên có dữ liệu (${dmy(history!.from)}–${dmy(history!.to)})`}</p>
    {error ? <p role="status" className="mb-3 text-xs text-muted">Chưa tải được lịch sử ngày; hiển thị dữ liệu sẵn có. Thử tải lại trang.</p> : null}
    {overlays.some((o) => !o.data.length) ? <p className="mb-3 text-xs text-muted">Chưa đủ phiên để vẽ một số đường đã chọn.</p> : null}
    <TradingViewChart key={`${symbol}-${range}`} symbol={symbol} data={visible} overlays={overlays} reference={showRef ? reference : null} />
    <p className="mt-3 text-xs text-muted">MA là trung bình đơn giản; EMA dùng hệ số 2/(n+1), khởi tạo bằng MA của n phiên đầu. Chu kỳ tính theo số phiên, không theo ngày lịch. Tín hiệu kỹ thuật không phải khuyến nghị mua bán.</p>
  </div>;
}
