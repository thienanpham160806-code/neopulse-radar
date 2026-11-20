import { companyIndex, companyReport } from "@/lib/company";
import { CompanyReportView } from "@/components/CompanyReportView";
import { RemoteCompany } from "@/components/RemoteCompany";
export const dynamic = "force-dynamic";
export default async function CompanyPage({ params }: { params: Promise<{ symbol: string }> }) {
  const symbol = (await params).symbol.toUpperCase();
  const report = await companyReport(symbol);
  if (report) return <CompanyReportView p={report} />;
  const entries = await companyIndex();
  return <RemoteCompany symbol={symbol} entry={entries.find((e) => e.symbol === symbol) ?? null} />;
}
