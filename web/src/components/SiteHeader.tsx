import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

export function SiteHeader({ area, crumbs = [] }: { area?: "market" | "company" | "notifications"; crumbs?: { label: string; href?: string; onClick?: () => void }[] }) {
  const items: { label: string; href?: string; onClick?: () => void }[] = [{ label: "Trang chủ", href: "/trang-chu" }, ...crumbs];
  return <div className="mx-auto max-w-6xl px-4 pt-5 sm:px-6">
    <header className="flex flex-wrap items-center justify-between gap-4">
      <Link href="/trang-chu" aria-label="NeoPulse · Trang chủ" className="flex items-center gap-3"><span className="brand-mark" aria-hidden>n<span>p</span></span><span className="text-lg font-bold tracking-tight">NeoPulse<span className="ml-2 text-xs font-normal text-muted">RADAR</span></span></Link>
      <div className="flex items-center gap-2 sm:gap-4"><nav aria-label="Khu vực" className="flex gap-1 text-sm"><Link href="/" aria-current={area === "market" ? "page" : undefined} className={`rounded-full px-3 py-2 ${area === "market" ? "bg-surface2 font-semibold" : "text-muted"}`}>Thị trường</Link><Link href="/doanh-nghiep" aria-current={area === "company" ? "page" : undefined} className={`rounded-full px-3 py-2 ${area === "company" ? "bg-surface2 font-semibold" : "text-muted"}`}>Doanh nghiệp</Link><Link href="/thong-bao" aria-current={area === "notifications" ? "page" : undefined} className={`rounded-full px-3 py-2 ${area === "notifications" ? "bg-surface2 font-semibold" : "text-muted"}`}>Nhận tin</Link></nav><ThemeToggle /></div>
    </header>
    <nav aria-label="Đường dẫn" className="py-5 text-xs text-muted"><ol className="flex flex-wrap items-center gap-2">{items.map((c, i) => <li key={`${c.label}-${i}`} className="flex items-center gap-2">{i ? <span aria-hidden className="opacity-50">›</span> : null}{c.href ? <Link href={c.href} onClick={c.onClick} className="hover:text-fg hover:underline">{c.label}</Link> : <span aria-current="page" className="font-medium text-fg">{c.label}</span>}</li>)}</ol></nav>
  </div>;
}
