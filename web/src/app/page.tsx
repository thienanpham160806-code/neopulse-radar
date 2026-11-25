import { redirect } from "next/navigation";
import { legacyMarketDestination, type RouteQuery } from "@/lib/routes";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
function Home() {
  return <><SiteHeader /><main className="mx-auto max-w-6xl px-4 pb-16 sm:px-6"><section className="feature-hero rounded-3xl p-7 sm:p-12"><p className="hero-kicker">NeoPulse · Góc nhìn thị trường</p><h1 className="mt-5 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">Hiểu nhịp thị trường.<br /><span className="hero-highlight">Nhìn sâu doanh nghiệp.</span></h1><p className="hero-description mt-6 max-w-xl leading-relaxed">Một không gian để theo dõi diễn biến trong phiên và đọc câu chuyện đằng sau từng mã cổ phiếu VN30.</p><Link href="/thi-truong" className="hero-button mt-8 inline-flex min-h-12 items-center rounded-full px-6 font-semibold">Khám phá thị trường ↗</Link></section><div className="mt-6 grid gap-5 md:grid-cols-2">{[["01", "Nhịp thị trường", "Chỉ số, độ rộng, dòng tiền và những tín hiệu đáng chú ý trong phiên.", "/thi-truong"], ["02", "Hồ sơ doanh nghiệp", "Từ doanh nghiệp làm gì đến kết quả kinh doanh, dòng tiền và định giá.", "/doanh-nghiep"]].map(([n, title, text, href]) => <Link key={href} href={href} className="group rounded-2xl bg-surface p-6 shadow-sm transition-transform hover:-translate-y-1"><span className="text-xs font-semibold text-muted">Khám phá · {n}</span><h2 className="mt-4 flex justify-between text-2xl font-semibold">{title}<span className="text-accent">↗</span></h2><p className="mt-3 max-w-md text-sm leading-relaxed text-muted">{text}</p></Link>)}</div><p className="mt-8 text-xs text-muted">Công cụ phân tích học thuật. Không phải lời khuyên đầu tư. Nguồn và thời điểm dữ liệu được ghi tại từng trang.</p></main></>;
}

export default async function Page({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const destination = legacyMarketDestination(await searchParams);
  if (destination) redirect(destination);
  return <Home />;
}
