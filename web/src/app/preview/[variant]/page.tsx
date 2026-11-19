import { notFound } from "next/navigation";
import { PreviewApp } from "@/components/preview/PreviewApp";
import { PreviewNews } from "@/components/preview/PreviewNews";
import { PreviewTerminal } from "@/components/preview/PreviewTerminal";
import type { PreviewState } from "@/components/preview/usePreview";
import { loadSample } from "@/components/preview/loadSample";

export const dynamic = "force-dynamic";
export const metadata = { title: "Bản xem trước giao diện · NeoPulse Radar", robots: { index: false } };

type SP = Promise<{ state?: string; tab?: string }>;

/** Ba hướng giao diện để chọn: cùng lớp dữ liệu (loadData + usePreview), chỉ khác lớp trình bày. */
export default async function PreviewPage({ params, searchParams }: { params: Promise<{ variant: string }>; searchParams: SP }) {
  const { variant } = await params;
  const sp = await searchParams;
  const state: PreviewState = sp.state === "snapshot" || sp.state === "error" ? sp.state : "live";
  const loaded = await loadSample(); // luôn MÔ PHỎNG: cùng dữ liệu cho cả ba hướng, không lộ dữ liệu thật
  const props = { initial: loaded, state, tab: sp.tab ?? null };
  if (variant === "a") return <PreviewTerminal {...props} />;
  if (variant === "b") return <PreviewNews {...props} />;
  if (variant === "c") return <PreviewApp {...props} />;
  notFound();
}
