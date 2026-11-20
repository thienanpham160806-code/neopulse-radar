"use client";
import { useState } from "react";
import type { CompanyEntry } from "@/lib/company";
import { CompanyLink } from "./CompanyLink";
import { dmy } from "@/lib/format";
const searchText = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
export function CompanyDirectory({ entries, vn30 = [], universeDate = null, vn100 = [], vn100Date = null }: { entries: CompanyEntry[]; vn30?: string[]; universeDate?: string | null; vn100?: string[]; vn100Date?: string | null }) {
  const [query, setQuery] = useState(""), [group, setGroup] = useState("market"), [exchange, setExchange] = useState("");
  const [page, setPage] = useState(1);
  const ready = vn100.filter((s) => entries.some((e) => e.symbol === s && e.has_report)).length;
  const covered = vn30.filter((s) => entries.some((e) => e.symbol === s && e.has_report)).length;
  const q = searchText(query.trim());
  const rows = entries.filter((e) => (group !== "vn30" || vn30.includes(e.symbol)) && (group !== "vn100" || vn100.includes(e.symbol))
    && (!exchange || e.exchange === exchange) && searchText(`${e.symbol} ${e.name ?? ""} ${e.industry ?? ""}`).includes(q));
  const maxPage = Math.max(1, Math.ceil(rows.length / 24)), current = Math.min(page, maxPage);
  return <>
    <div className="mt-6 flex flex-wrap gap-2" aria-label="Nhóm doanh nghiệp">{[["market", `Toàn thị trường (${entries.length})`], ["vn30", `VN30 (${covered}/30)`], ["vn100", `VN100 · báo cáo sẵn (${ready}/100)`]].map(([key, text]) => <button key={key} onClick={() => { setGroup(key); setPage(1); }} aria-pressed={group === key} className={`min-h-11 rounded-full px-4 text-sm ${group === key ? "bg-accent text-on-accent" : "bg-surface"}`}>{text}</button>)}</div>
    <p className="mt-3 max-w-3xl text-xs leading-relaxed text-muted">Danh mục cổ phiếu HOSE/HNX/UPCoM từ Vietcap; không bao gồm toàn bộ doanh nghiệp tư nhân tại Việt Nam. {ready}/100 mã VN100 có báo cáo sẵn; những mã chưa lưu sẽ tải BCTC khi mở hồ sơ. Rổ VN100 đối chiếu ngày {dmy(vn100Date)}; rổ VN30 theo dữ liệu phiên {dmy(universeDate)}.</p>
    <div className="mt-6 flex flex-wrap items-end gap-3"><label className="block w-full max-w-xl"><span className="mb-2 block text-sm font-medium">Tìm mã, tên doanh nghiệp hoặc ngành</span><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Ví dụ: VND, Hòa Phát, ngân hàng…" className="min-h-12 w-full rounded-xl border border-line bg-surface px-4" /></label>
      <label className="block text-sm"><span className="mb-2 block">Sàn giao dịch</span><select aria-label="Sàn giao dịch" value={exchange} onChange={(e) => { setExchange(e.target.value); setPage(1); }} className="min-h-12 rounded-xl border border-line bg-surface px-4"><option value="">Tất cả sàn</option>{["HOSE", "HNX", "UPCOM"].map((e) => <option key={e}>{e}</option>)}</select></label></div>
    <p role="status" className="my-4 text-sm text-muted">{rows.length} cổ phiếu khớp bộ lọc{rows.length ? ` · hiển thị ${(current - 1) * 24 + 1}–${Math.min(current * 24, rows.length)}` : ""}</p>
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{rows.slice((current - 1) * 24, current * 24).map((e) => <li key={e.symbol} className="rounded-2xl bg-surface p-4 shadow-sm"><div className="flex items-center justify-between"><span className="text-xl"><CompanyLink symbol={e.symbol} /></span><span className="text-xs text-muted">{e.exchange}{vn30.includes(e.symbol) ? " · VN30" : ""}</span></div><h2 className="mt-3 font-semibold">{e.name ?? e.symbol}</h2><p className="mt-2 text-xs text-muted">{e.industry ?? "Chưa có phân ngành"}</p><p className="mt-3 text-xs font-medium text-accent">{e.has_report ? "Báo cáo có sẵn" : "Tải báo cáo khi mở →"}</p></li>)}</ul>
    {!rows.length ? <p className="rounded-xl bg-surface p-6 text-muted">Không tìm thấy cổ phiếu khớp bộ lọc. Thử đổi sàn hoặc nhóm doanh nghiệp.</p> : null}
    <nav aria-label="Phân trang doanh nghiệp" className="mt-6 flex flex-wrap items-center justify-center gap-3"><button disabled={current === 1} onClick={() => setPage(current - 1)} className="min-h-11 rounded-full bg-surface px-5 text-sm disabled:opacity-40">Trước</button><label className="flex items-center gap-2 text-sm text-muted"><span>Trang</span><select aria-label="Đi đến trang doanh nghiệp" value={current} onChange={(e) => setPage(Number(e.target.value))} className="min-h-11 rounded-full bg-surface px-3 text-sm text-fg">{Array.from({ length: maxPage }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{String(n).padStart(2, "0")}/{String(maxPage).padStart(2, "0")}</option>)}</select></label><button disabled={current === maxPage} onClick={() => setPage(current + 1)} className="min-h-11 rounded-full bg-surface px-5 text-sm disabled:opacity-40">Sau</button></nav>
  </>;
}
