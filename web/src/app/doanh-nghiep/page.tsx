import Link from "next/link";
import { companyIndex, companyUniverse } from "@/lib/company";
import { CompanyDirectory } from "@/components/CompanyDirectory";
import { ThemeToggle } from "@/components/ThemeToggle";
export const dynamic = "force-dynamic";
export default async function Companies() {
  const [entries, universe] = await Promise.all([companyIndex(), companyUniverse()]);
  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <nav className="mb-10 flex items-center justify-between text-sm"><Link className="text-accent underline" href="/">← Nhịp thị trường</Link><ThemeToggle /></nav>
    <p className="text-xs font-semibold uppercase tracking-widest text-muted">NeoPulse · Tìm hiểu doanh nghiệp</p>
    <h1 className="mt-3 text-3xl font-bold sm:text-5xl">Đằng sau mỗi mã cổ phiếu</h1>
    <p className="mt-4 max-w-2xl text-muted">Doanh nghiệp làm gì, kinh doanh ra sao và sức khỏe tài chính thế nào? Mở hồ sơ để đọc tổng quan, phân tích báo cáo tài chính, dòng tiền và định giá.</p>
    <CompanyDirectory entries={entries} vn30={universe.symbols} universeDate={universe.date} />
    <p className="mt-10 border-t border-line pt-4 text-xs text-muted">Dữ liệu công khai qua Vietcap/vnstock. Mỗi hồ sơ ghi riêng ngày giá và kỳ báo cáo; đây là tài liệu phân tích học thuật, không phải lời khuyên đầu tư.</p>
  </main>;
}
