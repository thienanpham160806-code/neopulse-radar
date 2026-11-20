"use client";
import { useEffect, useState } from "react";
import type { CompanyEntry, CompanyReport } from "@/lib/company";
import { CompanyReportView } from "./CompanyReportView";
import { SiteHeader } from "./SiteHeader";
export function RemoteCompany({ symbol, entry }: { symbol: string; entry: CompanyEntry | null }) {
  const [report, setReport] = useState<CompanyReport | null>(null), [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!entry) return;
    const c = new AbortController();
    fetch(`/api/company?symbol=${encodeURIComponent(symbol)}`, { signal: c.signal }).then(async (r) => {
      const p = await r.json();
      if (!r.ok) throw new Error(p.error ?? "Không tải được dữ liệu.");
      if (p.symbol !== symbol || !p.tables || !p.profile) throw new Error("Dữ liệu không hợp lệ.");
      setReport(p);
    }).catch((e) => { if (e.name !== "AbortError") setError(e.message); });
    return () => c.abort();
  }, [entry, symbol, attempt]);
  if (report) return <CompanyReportView p={report} />;
  return <><SiteHeader area="company" crumbs={[{ label: "Doanh nghiệp", href: "/doanh-nghiep" }, { label: symbol }]} /><main className="mx-auto max-w-4xl px-4 pb-12"><section className="rounded-3xl bg-surface p-6 sm:p-9"><p className="text-sm text-muted">{entry?.exchange ?? "Danh mục cổ phiếu Việt Nam"} · {entry?.industry ?? "Chưa có phân ngành"}</p><h1 className="mt-3 text-4xl font-bold">{symbol}</h1><p className="mt-3 text-xl">{entry?.name ?? "Không tìm thấy mã trong danh mục"}</p>
    <p role="status" className="mt-6 text-sm leading-relaxed text-muted">{!entry ? "Mã này chưa có trong danh mục HOSE/HNX/UPCoM hiện tại." : error || "Đang tải BCTC công khai và tính báo cáo bằng Python. Thông tin cơ bản đã sẵn có; lần mở đầu có thể mất vài chục giây."}</p>
    {entry && error ? <button onClick={() => { setError(""); setAttempt((n) => n + 1); }} className="mt-5 min-h-11 rounded-full bg-accent px-5 text-sm text-on-accent">Thử tải lại báo cáo</button> : null}
    <p className="mt-6 text-xs text-muted">Không thay dữ liệu thiếu bằng 0 hoặc tự tạo nhận định. Công cụ học thuật, không phải lời khuyên đầu tư.</p></section></main></>;
}
