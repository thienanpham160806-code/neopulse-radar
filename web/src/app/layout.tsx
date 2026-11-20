import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { SiteFooter } from "@/components/SiteFooter";
import "./globals.css";

// Be Vietnam Pro (SIL OFL 1.1, xem fonts/OFL.txt) - dấu tiếng Việt chuẩn, số đều nhau khi bật tabular-nums
const beVietnam = localFont({
  src: [
    { path: "./fonts/BeVietnamPro-Regular.ttf", weight: "400", style: "normal" },
    { path: "./fonts/BeVietnamPro-Medium.ttf", weight: "500", style: "normal" },
    { path: "./fonts/BeVietnamPro-SemiBold.ttf", weight: "600", style: "normal" },
    { path: "./fonts/BeVietnamPro-Bold.ttf", weight: "700", style: "normal" },
  ],
  variable: "--font-bvp",
  display: "swap",
});

export const metadata: Metadata = {
  title: "NeoPulse Radar",
  description: "Radar nhịp thị trường, áp lực sổ lệnh và cảnh báo bất thường nội phiên. Không phải lời khuyên đầu tư.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={beVietnam.variable} suppressHydrationWarning>
      <body id="top" className="flex min-h-dvh flex-col antialiased"><div className="flex-1">{children}</div><SiteFooter /></body>
    </html>
  );
}
