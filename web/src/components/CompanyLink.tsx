import Link from "next/link";

/** Giữ đường dẫn thật để mở tab mới, quay lại và dùng được bằng bàn phím. */
export function CompanyLink({ symbol, children }: { symbol: string; children?: React.ReactNode }) {
  return <Link href={`/doanh-nghiep/${encodeURIComponent(symbol)}`} title={`Xem hồ sơ doanh nghiệp ${symbol}`}
    className="font-semibold text-accent underline decoration-accent/30 underline-offset-4 hover:decoration-accent">{children ?? symbol}</Link>;
}
