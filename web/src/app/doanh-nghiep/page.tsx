import { SiteHeader } from "@/components/SiteHeader";
import { companyIndex, companyUniverse, companyVN100 } from "@/lib/company";
import { CompanyDirectory } from "@/components/CompanyDirectory";

export const dynamic = "force-dynamic";
export default async function Companies() {
  const [entries, universe, vn100] = await Promise.all([companyIndex(), companyUniverse(), companyVN100()]);
  return <><SiteHeader area="company" crumbs={[{ label: "Doanh nghiệp" }]} /><main className="mx-auto max-w-6xl px-4 pb-8 sm:px-6">
    <section className="feature-hero rounded-3xl p-6 sm:p-9"><p className="hero-kicker">NeoPulse · Tìm hiểu doanh nghiệp</p>
    <h1 className="mt-3 text-3xl font-bold sm:text-5xl">Đằng sau mỗi mã cổ phiếu</h1>
    <p className="hero-description mt-4 max-w-2xl text-sm leading-relaxed">Doanh nghiệp làm gì, kinh doanh ra sao và sức khỏe tài chính thế nào? Mở hồ sơ để đọc tổng quan, phân tích báo cáo tài chính, dòng tiền và định giá.</p>
    </section>
    <CompanyDirectory entries={entries} vn30={universe.symbols} universeDate={universe.date} vn100={vn100.symbols} vn100Date={vn100.date} />
    <p className="mt-10 border-t border-line pt-4 text-xs text-muted">Dữ liệu công khai qua Vietcap/vnstock. Mỗi hồ sơ ghi riêng ngày giá và kỳ báo cáo; đây là tài liệu phân tích học thuật, không phải lời khuyên đầu tư.</p>
  </main></>;
}
