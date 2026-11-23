"use client";
import { useEffect, useState } from "react";
import type { CompanyReport } from "@/lib/company";
import { dmy } from "@/lib/format";
import { dmyTime } from "@/lib/fmt";
import { Card, Note } from "@/components/ui";

const safeUrl = (u?: string) => !!u && /^https:\/\/vietstock\.vn\//.test(u);

/** Hiện danh sách trong hồ sơ ngay, rồi thay bằng bản mới từ /api/news (CDN giữ 15 phút) nếu nguồn trả được. */
export function Disclosures({ symbol, events: initialEvents, news: initialNews }: { symbol: string; events: CompanyReport["events"]; news: CompanyReport["news"] }) {
  const [events, setEvents] = useState(initialEvents), [news, setNews] = useState(initialNews);
  const [updated, setUpdated] = useState<string | null>(null);
  useEffect(() => {
    const c = new AbortController();
    fetch(`/api/news?symbol=${encodeURIComponent(symbol)}`, { signal: c.signal }).then((r) => r.ok ? r.json() : null).then((d) => {
      if (!d || d.symbol !== symbol) return;
      if (Array.isArray(d.events) && d.events.length) setEvents(d.events);
      if (Array.isArray(d.news) && d.news.length) setNews(d.news);
      if (typeof d.updated_at === "string") setUpdated(d.updated_at);
    }).catch(() => { /* Giữ danh sách trong hồ sơ khi nguồn tin lỗi. */ });
    return () => c.abort();
  }, [symbol]);
  return <div className="grid gap-4 md:grid-cols-2">
    <Card title={`Sự kiện công bố · ${events.length}`}><ul className="max-h-[32rem] divide-y divide-line overflow-y-auto pr-2">{events.map((e, i) => <li key={i} className="py-3 text-sm"><span className="block text-xs text-muted"><time>{dmy(e.date)}</time>{e.type ? ` · ${e.type}` : ""}</span>{e.title}</li>)}</ul>{!events.length ? <Note>Chưa có dữ liệu.</Note> : <Note>Toàn bộ sự kiện 10 năm gần nhất theo Vietcap, mới nhất ở trên.</Note>}</Card>
    <Card title="Tin & báo cáo gần đây"><ul className="max-h-[32rem] divide-y divide-line overflow-y-auto pr-2">{news.map((n, i) => <li key={i} className="py-3 text-sm"><time className="block text-xs text-muted">{dmy(n.date)}</time>{safeUrl(n.url) ? <a href={n.url} target="_blank" rel="noopener noreferrer" className="underline-offset-4 hover:text-accent hover:underline focus-visible:underline">{n.title}<span className="ml-1 whitespace-nowrap text-xs text-muted">{n.source ?? "Nguồn"} ↗</span></a> : n.title}</li>)}</ul>{!news.length ? <Note>Chưa có dữ liệu.</Note> : <Note>Bấm tiêu đề để đọc bài gốc trên Vietstock (mở tab mới). {updated ? `Cập nhật ${dmyTime(updated)}, làm mới mỗi 15 phút.` : "Đang lấy tin mới nhất…"}</Note>}</Card>
  </div>;
}
