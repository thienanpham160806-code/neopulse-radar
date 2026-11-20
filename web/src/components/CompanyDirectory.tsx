"use client";
import { useState } from "react";
import type { CompanyEntry } from "@/lib/company";
import { CompanyLink } from "./CompanyLink";
import { dmy } from "@/lib/format";
const searchText = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
export function CompanyDirectory({ entries, vn30 = [], universeDate = null }: { entries: CompanyEntry[]; vn30?: string[]; universeDate?: string | null }) {
  const [query, setQuery] = useState(""), [group, setGroup] = useState("market"), [exchange, setExchange] = useState("");
  const [page, setPage] = useState(1);
  const ready = entries.filter((e) => e.has_report).length;
  const covered = vn30.filter((s) => entries.some((e) => e.symbol === s && e.has_report)).length;
  const q = searchText(query.trim());
  const rows = entries.filter((e) => (group !== "vn30" || vn30.includes(e.symbol)) && (group !== "ready" || e.has_report)
    && (!exchange || e.exchange === exchange) && searchText(`${e.symbol} ${e.name ?? ""} ${e.industry ?? ""}`).includes(q));
  const maxPage = Math.max(1, Math.ceil(rows.length / 24)), current = Math.min(page, maxPage);
  return <>
    <div className="mt-6 flex flex-wrap gap-2" aria-label="Nhóm doanh nghiệp">{[["market", `Toàn thị trường (${entries.length})`], ["vn30", `VN30 (${covered}/30)`], ["ready", `Báo cáo có sẵn (${ready})`]].map(([key, text]) => <button key={key} onClick={() => { setGroup(key); setPage(1); }} aria-pressed={group === key} className={`min-h-11 rounded-full px-4 text-sm ${group === key ? "bg-accent text-on-accent" : "bg-surface"}`}>{text}</button>)}</div>
    <p className="mt-3 max-w-3xl text-xs leading-relaxed text-muted">Danh mục cổ phiếu HOSE/HNX/UPCoM từ Vietcap; không bao gồm toàn bộ doanh nghiệp tư nhân tại Việt Nam. {ready} báo cáo đã chuẩn bị sẵn; các mã khác tải BCTC khi mở hồ sơ. Rổ VN30 theo dữ liệu phiên {dmy(universeDate)}.</p>
    <div className="mt-6 flex flex-wrap items-end gap-3"><label className="block w-full max-w-xl"><span className="mb-2 block text-sm font-medium">Tìm mã, tên doanh nghiệp hoặc ngành</span><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Ví dụ: VND, Hòa Phát, ngân hàng…" className="min-h-12 w-full rounded-xl border border-line bg-surface px-4" /></label>
      <label className="block text-sm"><span className="mb-2 block">Sàn giao dịch</span><select aria-label="Sàn giao dịch" value={exchange} onChange={(e) => { setExchange(e.target.value); setPage(1); }} className="min-h-12 rounded-xl border border-line bg-surface px-4"><option value="">Tất cả sàn</option>{["HOSE", "HNX", "UPCOM"].map((e) => <option key={e}>{e}</option>)}</select></label></div>
    <p role="status" className="my-4 text-sm text-muted">{rows.length} cổ phiếu khớp bộ lọc{rows.length ? ` · hiển thị ${(current - 1) * 24 + 1}–${Math.min(current * 24, rows.length)}` : ""}</p>
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{rows.slice((current - 1) * 24, current * 24).map((e) => <li key={e.symbol} className="rounded-2xl bg-surface p-4 shadow-sm"><div className="flex items-center justify-between"><span className="text-xl"><CompanyLink symbol={e.symbol} /></span><span className="text-xs text-muted">{e.exchange}{vn30.includes(e.symbol) ? " · VN30" : ""}</span></div><h2 className="mt-3 font-semibold">{e.name ?? e.symbol}</h2><p className="mt-2 text-xs text-muted">{e.industry ?? "Chưa có phân ngành"}</p><p className="mt-3 text-xs font-medium text-accent">{e.has_report ? "Báo cáo có sẵn" : "Tải báo cáo khi mở →"}</p></li>)}</ul>
    {!rows.length ? <p className="rounded-xl bg-surface p-6 text-muted">Không tìm thấy cổ phiếu khớp bộ lọc. Thử đổi sàn hoặc nhóm doanh nghiệp.</p> : null}
    <nav aria-label="Phân trang doanh nghiệp" className="mt-6 flex items-center justify-center gap-4"><button disabled={current === 1} onClick={() => setPage(current - 1)} className="min-h-11 rounded-full bg-surface px-5 text-sm disabled:opacity-40">Trước</button><span className="text-sm text-muted">Trang {current}/{maxPage}</span><button disabled={current === maxPage} onClick={() => setPage(current + 1)} className="min-h-11 rounded-full bg-surface px-5 text-sm disabled:opacity-40">Sau</button></nav>
  </>;
}
