import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

export function SiteHeader({
  area,
  crumbs = [],
  compact = false,
}: {
  area?: "market" | "company" | "notifications";
  crumbs?: { label: string; href?: string; onClick?: () => void }[];
  compact?: boolean;
}) {
  const items: { label: string; href?: string; onClick?: () => void }[] = [{ label: "Trang chủ", href: "/trang-chu" }, ...crumbs];
  const navLink = (href: string, label: string, active: boolean) => (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`ui-transition whitespace-nowrap rounded-full px-2 py-1 text-xs sm:px-3 sm:py-1.5 sm:text-sm ${
        active ? "bg-surface2 font-semibold text-fg" : "text-muted hover:bg-surface2/60 hover:text-fg"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="border-b border-line/80 bg-surface/90 backdrop-blur">
      <div className="mx-auto max-w-6xl px-3 sm:px-6">
        <header className="flex items-center justify-between gap-1.5 py-2 sm:gap-2 sm:py-2.5">
          <Link href="/trang-chu" className="flex shrink-0 items-center gap-2">
            <span className="brand-mark" aria-hidden>n<span>p</span></span>
            <span className="text-sm font-bold tracking-tight sm:text-lg">
              NeoPulse<span className="ml-1.5 hidden text-[11px] font-medium tracking-wider text-muted sm:inline">RADAR</span>
            </span>
          </Link>
          <div className="flex min-w-0 items-center gap-1 sm:gap-3">
            <nav aria-label="Khu vực" className="no-scrollbar scroll-x flex items-center gap-0.5 sm:gap-1">
              {navLink("/", "Thị trường", area === "market")}
              {navLink("/doanh-nghiep", "Doanh nghiệp", area === "company")}
              {navLink("/thong-bao", "Nhận tin", area === "notifications")}
            </nav>
            <ThemeToggle />
          </div>
        </header>
        {!compact && crumbs.length > 0 ? (
          <nav aria-label="Đường dẫn" className="pb-2.5 text-xs text-muted">
            <ol className="flex flex-wrap items-center gap-1.5">
              {items.map((c, i) => (
                <li key={`${c.label}-${i}`} className="flex items-center gap-1.5">
                  {i ? <span aria-hidden className="opacity-50">›</span> : null}
                  {c.href ? (
                    <Link href={c.href} onClick={c.onClick} className="hover:text-fg hover:underline">{c.label}</Link>
                  ) : (
                    <span aria-current="page" className="font-medium text-fg">{c.label}</span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        ) : null}
      </div>
    </div>
  );
}
