import type { CompanyReport } from "@/lib/company";
import { dmy, num, ratioPct } from "@/lib/format";
import { dmyTime } from "@/lib/fmt";
import { CompanyLink } from "@/components/CompanyLink";
import { CompanyPriceChart } from "@/components/CompanyCharts";
import { SiteHeader } from "@/components/SiteHeader";

import { Card, Note, Stat } from "@/components/ui";
import { Disclosures } from "@/components/Disclosures";
const sections = [["tong-quan", "01", "Doanh nghiệp & ngành"], ["tai-chinh", "02", "Tài chính & kinh doanh"], ["tom-tat", "03", "Tóm tắt & rủi ro"], ["dinh-gia", "04", "Định giá & giả định"]];
const ratioRows: [string, string, string][] = [
  ["revenue_growth", "Tăng trưởng doanh thu", "%"], ["toi_growth", "Tăng trưởng thu nhập hoạt động", "%"],
  ["npat_growth", "Tăng trưởng LNST công ty mẹ", "%"], ["gross_margin", "Biên lợi nhuận gộp", "%"],
  ["core_margin", "Biên hoạt động cốt lõi", "%"], ["net_margin", "Biên lợi nhuận ròng", "%"],
  ["roe", "ROE · lợi nhuận/vốn chủ bình quân", "%"], ["roa", "ROA · lợi nhuận/tài sản bình quân", "%"],
  ["current_ratio", "Thanh toán hiện hành", "lần"], ["quick_ratio", "Thanh toán nhanh", "lần"],
  ["debt_to_equity", "Nợ vay/vốn chủ", "lần"], ["interest_cover", "Khả năng trả lãi", "lần"],
  ["inventory_days", "Số ngày tồn kho", "ngày"], ["receivable_days", "Số ngày phải thu", "ngày"],
  ["payable_days", "Số ngày phải trả", "ngày"], ["ccc", "Chu kỳ chuyển đổi tiền mặt", "ngày"],
  ["cfo_to_npat", "Dòng tiền kinh doanh/LNST", "lần"], ["cir", "Chi phí hoạt động/thu nhập (CIR)", "%"],
  ["ldr", "Cho vay/tiền gửi khách hàng", "%"], ["loan_growth", "Tăng trưởng cho vay", "%"], ["deposit_growth", "Tăng trưởng tiền gửi", "%"],
];
const fmt = (v: number | null | undefined, unit = "") => v == null ? "—" : unit === "%" ? ratioPct(v, 1) : `${num(v, 1)}${unit ? ` ${unit}` : ""}`;
function DataTable({ years, rows, caption }: { years: string[]; rows: { label: string; values: (number | null)[] }[]; caption: string }) {
  return <div className="scroll-x"><table className="w-full text-sm"><caption className="mb-3 text-left text-xs text-muted">{caption}</caption>
    <thead><tr className="border-b border-line"><th scope="col" className="min-w-48 py-2 text-left">Chỉ tiêu</th>{years.map((y) => <th key={y} scope="col" className="min-w-24 px-3 py-2 text-right">{y}</th>)}</tr></thead>
    <tbody>{rows.map((r) => <tr key={r.label} className="border-b border-line"><th scope="row" className="py-3 text-left font-normal">{r.label}</th>{r.values.map((v, i) => <td key={i} className="tnum px-3 py-3 text-right">{num(v, 1)}</td>)}</tr>)}</tbody>
  </table>{!rows.length ? <p className="py-4 text-muted">Chưa có số liệu cho phần này.</p> : null}</div>;
}

export function CompanyReportView({ p }: { p: CompanyReport }) {
  const symbol = p.symbol;
  const latest = p.years.at(-1), r = latest ? p.ratios[latest] ?? {} : {};
  const ratios = ratioRows.filter(([key]) => p.years.some((y) => p.ratios[y]?.[key] != null));
  return <><SiteHeader area="company" crumbs={[{ label: "Doanh nghiệp", href: "/doanh-nghiep" }, { label: p.symbol }]} /><div className="mx-auto max-w-6xl px-4 pb-8 sm:px-6">
    <header className="rounded-3xl bg-surface p-6 shadow-sm sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted">NeoPulse · Hồ sơ phân tích doanh nghiệp</p>
      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-4"><div><p className="text-sm text-muted">{p.profile.exchange ?? "—"} · {p.profile.industry ?? "Chưa có phân ngành"}</p><h1 className="mt-1 text-4xl font-bold sm:text-6xl">{p.symbol}</h1><p className="mt-2 text-xl">{p.profile.name ?? p.symbol}</p></div>
        <div className="text-right"><p className="tnum text-3xl font-semibold">{num(p.price.last, 0)} <span className="text-sm font-normal text-muted">đồng/CP</span></p><p className="mt-1 text-xs text-muted">Giá ngày {dmy(p.price.date)} · không phải giá trực tiếp</p></div></div>
      <p className="mt-5 text-xs text-muted">Nguồn: {p.source ?? "Chưa rõ"} · Lấy dữ liệu: {dmyTime(p.fetched_at)} · BCTC năm {p.years.join("–") || "chưa có"}. Giá và báo cáo tài chính có thể thuộc các kỳ khác nhau.</p>
    </header>
    <div className="mt-6 grid items-start gap-8 lg:grid-cols-[200px_minmax(0,1fr)]">
      <aside className="lg:sticky lg:top-6"><nav aria-label="Mục lục hồ sơ" className="grid grid-cols-2 gap-2 lg:grid-cols-1">{sections.map(([id, n, title]) => <a key={id} href={`#${id}`} className="rounded-lg border border-line px-3 py-3 text-sm hover:bg-surface2"><span className="mr-2 text-muted">{n}</span>{title}</a>)}</nav>
        <p className="mt-4 text-xs leading-relaxed text-muted">Đọc theo trình tự: hiểu hoạt động → xem hiệu quả → nhận diện rủi ro → đối chiếu định giá.</p></aside>
      <main className="min-w-0 space-y-12">
        <section id="tong-quan" className="scroll-mt-6 space-y-5"><h2 className="text-2xl font-bold">01 · Doanh nghiệp & ngành</h2>
          <p className="max-w-[72ch] whitespace-pre-line leading-relaxed">{p.profile.about ?? "Nguồn dữ liệu chưa cung cấp mô tả hoạt động doanh nghiệp."}</p>
          <div className="grid grid-cols-2 gap-3"><Stat label="Vốn hóa theo giá trên" value={`${num(p.valuation.market_cap, 0)} tỷ`} /><Stat label="Cổ phiếu lưu hành" value={num(p.profile.shares, 0)} /><Stat label="Ngày niêm yết" value={dmy(p.profile.listing_date)} /><Stat label="Sở hữu nước ngoài" value={ratioPct(p.profile.foreign_pct, 1)} /></div>
          <div className="grid gap-4 md:grid-cols-2"><Card title="Cổ đông được nguồn công bố"><ul className="divide-y divide-line">{p.shareholders.map((s, i) => <li key={i} className="flex justify-between gap-4 py-2 text-sm"><span>{s.name}</span><span className="tnum shrink-0">{ratioPct(s.pct, 2)}</span></li>)}</ul>{!p.shareholders.length ? <Note>Chưa có dữ liệu cổ đông.</Note> : null}</Card>
            <Card title="Ban lãnh đạo"><ul className="space-y-3">{p.officers.map((o, i) => <li key={i} className="text-sm"><b>{o.name}</b><span className="block text-muted">{o.position}</span></li>)}</ul>{!p.officers.length ? <Note>Chưa có dữ liệu lãnh đạo.</Note> : null}</Card></div>
          <Card title="Diễn biến giá so với thị trường">{(p.price.series.length > 1 || (p.technical?.data.length ?? 0) > 1) ? <CompanyPriceChart series={p.price.series} symbol={symbol} technical={p.technical} /> : <Note>Chưa đủ dữ liệu giá so sánh.</Note>}
            <Note>Chế độ Giá & chỉ báo dùng giá đóng cửa (đồng/CP); chế độ So với VN-Index quy hai đường về 100 tại ngày đầu có dữ liệu chung. Vùng giá đóng cửa của {p.price.n_sessions ?? "tối đa 250"} phiên có dữ liệu: {num(p.price.low_52w, 0)}–{num(p.price.high_52w, 0)} đồng/CP; không phải mức cao/thấp trong ngày.</Note>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries(p.price.returns).map(([period, ret]) => <div key={period} className="rounded-lg bg-surface2 p-3 text-sm"><b>{period}</b><p>{symbol}: {fmt(ret.stock, "%")}</p><p className="text-muted">VN-Index: {fmt(ret.index, "%")}</p></div>)}</div></Card>
        </section>

        <section id="tai-chinh" className="scroll-mt-6 space-y-5"><h2 className="text-2xl font-bold">02 · Tài chính & kết quả kinh doanh</h2>
          <p className="text-sm text-muted">BCTC năm hợp nhất · tỷ đồng. “—” là chưa có dữ liệu, không phải bằng 0.</p>
          {!p.years.length ? <Card>Chưa có đủ báo cáo tài chính để phân tích.</Card> : null}
          {[["income", "Kết quả kinh doanh"], ["balance", "Tài sản & nguồn vốn"], ["cashflow", "Dòng tiền"]].map(([key, title]) => <Card key={key} title={title}><DataTable years={p.years} rows={p.tables[key] ?? []} caption={`${title} · tỷ đồng`} /></Card>)}
          <Card title="Khả năng sinh lời, thanh khoản & hiệu quả"><div className="scroll-x"><table className="w-full text-sm"><thead><tr className="border-b border-line"><th className="min-w-56 py-2 text-left" scope="col">Tỷ số</th>{p.years.map((y) => <th scope="col" key={y} className="min-w-24 px-3 text-right">{y}</th>)}</tr></thead><tbody>{ratios.map(([key, label, unit]) => <tr key={key} className="border-b border-line"><th scope="row" className="py-3 text-left font-normal">{label}</th>{p.years.map((y) => <td key={y} className="tnum px-3 text-right">{fmt(p.ratios[y]?.[key], unit)}</td>)}</tr>)}</tbody></table></div></Card>
          {p.kind !== "bank" ? <Card title={`Phân rã ROE · DuPont ${latest ?? ""}`}><div className="grid gap-3 sm:grid-cols-3"><Stat label="Biên ròng" value={fmt(r.net_margin, "%")} /><Stat label="× Vòng quay tài sản" value={fmt(r.asset_turnover, "lần")} /><Stat label="× Đòn bẩy tài sản/vốn chủ" value={fmt(r.leverage, "lần")} /></div><Note>Tích ba thành phần bằng ROE {fmt(r.roe, "%")}, trước sai số làm tròn. Tỷ số không tự chứng minh chất lượng lợi nhuận.</Note></Card> : null}
          <Card title="Đối chiếu doanh nghiệp"><p className="mb-3 text-xs text-muted">{p.peers.basis}. Chỉ là nhóm dữ liệu hiện có, không phải toàn ngành. Mỗi dòng ghi riêng năm BCTC.</p><div className="scroll-x"><table className="w-full text-sm"><thead><tr className="border-b border-line">{["Mã", "Năm", "Tăng trưởng", "ROE", "P/E", "P/B"].map((h) => <th key={h} className="min-w-20 py-2 text-left" scope="col">{h}</th>)}</tr></thead><tbody>{p.peers.rows.map((a) => <tr key={a.symbol} className="border-b border-line"><th scope="row" className="py-3 text-left"><CompanyLink symbol={a.symbol} /></th><td>{a.year ?? "—"}</td><td>{fmt(a.revenue_growth as number | null, "%")}</td><td>{fmt(a.roe as number | null, "%")}</td><td>{fmt(a.pe as number | null)}</td><td>{fmt(a.pb as number | null)}</td></tr>)}</tbody></table></div></Card>
        </section>
        <section id="tom-tat" className="scroll-mt-6 space-y-5"><h2 className="text-2xl font-bold">03 · Tóm tắt & điều cần theo dõi</h2>
          <ol className="space-y-4">{p.summary.map((s, i) => <li key={i} className="flex gap-4 rounded-xl border border-line bg-surface p-4"><span className="tnum text-xl text-muted">{String(i + 1).padStart(2, "0")}</span><p className="leading-relaxed">{s}</p></li>)}</ol>
          <Card title="Rủi ro & giới hạn khi đọc"><ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed"><li>BCTC năm mô tả quá khứ; chưa bao gồm kết quả quý mới hơn hay kế hoạch kinh doanh mới.</li><li>{p.kind === "bank" ? "Cho vay/tiền gửi và CIR không thay thế phân tích nợ xấu, dự phòng, an toàn vốn và cơ cấu kỳ hạn." : "Biên lợi nhuận, tồn kho và dòng tiền có thể thay đổi theo chu kỳ ngành; cần đọc thuyết minh trước khi kết luận."}</li><li>Nhận định được dựng từ số liệu; chưa có phân tích chiến lược, thị phần hoặc lợi thế cạnh tranh được kiểm chứng riêng.</li><li>Ngày giá và năm BCTC khác nhau; bội số dưới đây dùng lợi nhuận năm gần nhất đã tải, không phải lợi nhuận 12 tháng gần nhất.</li></ul></Card>
          <Disclosures symbol={p.symbol} events={p.events} news={p.news} />
        </section>
        <section id="dinh-gia" className="scroll-mt-6 space-y-5"><h2 className="text-2xl font-bold">04 · Định giá & giả định</h2>
          <p className="text-sm text-muted">Giá {dmy(p.price.date)}, BCTC năm {latest ?? "chưa có"}. Bội số không phải giá mục tiêu hay khuyến nghị.</p>
          <div className="grid gap-3 sm:grid-cols-3"><Stat label="P/E · LNST công ty mẹ" value={fmt(p.valuation.pe, "lần")} /><Stat label="P/B · vốn chủ công ty mẹ" value={fmt(p.valuation.pb, "lần")} /><Stat label="EV/EBITDA ước tính" value={fmt(p.valuation.ev_ebitda, "lần")} /></div>
          <Card title="Chiết khấu dòng tiền · bảng độ nhạy minh họa">
            {p.dcf?.cases.length ? <><p className="mb-4 text-sm leading-relaxed">FCFF nền ước tính: {num(p.dcf.base_fcff, 1)} tỷ đồng. Giữ FCFF nền cho 5 năm; sau đó tăng trưởng dài hạn theo từng cột. Thuế giả định {ratioPct(p.dcf.tax_rate, 0)}. WACC và tăng trưởng dưới đây là giả định minh họa, chưa được ước lượng riêng cho doanh nghiệp.</p>
              <div className="scroll-x"><table className="w-full text-sm"><caption className="mb-2 text-left text-xs text-muted">Giá trị vốn chủ/CP · đồng · FCFF trừ nợ vay ròng và lợi ích không kiểm soát</caption><thead><tr><th scope="col" className="p-3 text-left">WACC / g</th>{[0.02, 0.03, 0.04].map((g) => <th scope="col" key={g}>{ratioPct(g)}</th>)}</tr></thead><tbody>{[0.10, 0.12, 0.14].map((w) => <tr key={w} className="border-t border-line"><th scope="row" className="p-3 text-left">{ratioPct(w)}</th>{p.dcf!.cases.filter((c) => c.wacc === w).map((c) => <td className="tnum text-center" key={c.growth}>{num(c.value, 0)}</td>)}</tr>)}</tbody></table></div>
              <Note>FCFF = EBIT hoạt động × (1 − thuế) + khấu hao − chi TSCĐ − thay đổi vốn lưu động hoạt động. EBIT hoạt động = lãi gộp − chi bán hàng − chi quản lý, loại thu nhập tài chính. Vốn lưu động ở đây = phải thu + tồn kho − phải trả nhà cung cấp. Không dùng CFO − CapEx thay cho FCFF. Mô hình giản lược chưa dự phóng riêng doanh thu/biên lợi nhuận; không xem các con số này là định giá chính thức.</Note></> : <p className="text-sm text-muted">{p.dcf?.reason ?? "Chưa có đủ đầu vào dòng tiền và giả định để dựng DCF có thể kiểm chứng."}</p>}
          </Card>
        </section>
        <footer className="border-t border-line pt-6"><h2 className="text-sm font-semibold">Nguồn & phương pháp</h2><ul className="mt-2 list-disc space-y-2 pl-5 text-xs text-muted">{p.notes.map((s, i) => <li key={i}>{s}</li>)}</ul><p className="mt-5 text-sm font-medium">Công cụ phân tích học thuật. Không phải lời khuyên đầu tư.</p></footer>
      </main>
    </div>
  </div></>;
}
