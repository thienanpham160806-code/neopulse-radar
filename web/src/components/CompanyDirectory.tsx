"use client";
import { useState } from "react";
import type { CompanyEntry } from "@/lib/company";
import { CompanyLink } from "./CompanyLink";
import { dmy } from "@/lib/format";

export function CompanyDirectory({ entries, vn30 = [], universeDate = null }: { entries: CompanyEntry[]; vn30?: string[]; universeDate?: string | null }) {
  const [query, setQuery] = useState("");
  const [onlyVN30, setOnlyVN30] = useState(vn30.length > 0);
  const q = query.trim().toLocaleLowerCase("vi");
  const covered = vn30.filter((s) => entries.some((e) => e.symbol === s)).length;
  const rows = entries.filter((e) => (!onlyVN30 || vn30.includes(e.symbol)) && `${e.symbol} ${e.name ?? ""} ${e.industry ?? ""}`.toLocaleLowerCase("vi").includes(q));
  return <>
    {vn30.length ? <div className="mt-6"><div aria-label="Nhóm doanh nghiệp" className="flex gap-2">
      <button onClick={() => setOnlyVN30(true)} aria-pressed={onlyVN30} className={`min-h-11 rounded-lg border border-line px-4 text-sm ${onlyVN30 ? "bg-fg text-bg" : "bg-surface"}`}>VN30 ({covered}/30)</button>
      <button onClick={() => setOnlyVN30(false)} aria-pressed={!onlyVN30} className={`min-h-11 rounded-lg border border-line px-4 text-sm ${!onlyVN30 ? "bg-fg text-bg" : "bg-surface"}`}>Tất cả hồ sơ ({entries.length})</button>
    </div><p className="mt-3 text-xs text-muted">Rổ VN30 theo dữ liệu phiên {dmy(universeDate)} · {covered}/30 mã có hồ sơ. Thành phần rổ có thể thay đổi theo kỳ.</p></div> : null}
    <label className="mt-6 block max-w-xl"><span className="mb-2 block text-sm font-medium">Tìm mã, tên doanh nghiệp hoặc ngành</span>
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ví dụ: MWG, Thế Giới Di Động, ngân hàng…"
        className="min-h-12 w-full rounded-lg border border-line bg-surface px-4" /></label>
    <p role="status" className="my-4 text-sm text-muted">{rows.length} doanh nghiệp có hồ sơ</p>
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{rows.map((e) => <li key={e.symbol} className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-center justify-between text-xl"><CompanyLink symbol={e.symbol} />{vn30.includes(e.symbol) ? <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">VN30</span> : null}</div><h2 className="mt-2 font-semibold">{e.name ?? e.symbol}</h2>
      <p className="mt-1 text-sm text-muted">{e.industry ?? "Chưa có phân ngành"}</p>
    </li>)}</ul>
    {!rows.length ? <p className="rounded-lg border border-dashed border-line p-6 text-muted">Không có hồ sơ khớp tìm kiếm. Thử mã khác hoặc tên ngắn hơn.</p> : null}
  </>;
}
