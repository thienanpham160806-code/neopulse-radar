"use client";
import { useState } from "react";
export function TelegramSignup() {
  const [alerts, setAlerts] = useState(true), [news, setNews] = useState(false), [laws, setLaws] = useState(false);
  const topics = [alerts ? "alerts" : "", news ? "news" : "", laws ? "laws" : ""].filter(Boolean).join("_");
  return <section className="rounded-2xl bg-surface p-5 shadow-sm sm:p-8"><h2 className="text-xl font-semibold">Bro muốn nhận nội dung nào?</h2><div className="my-5 grid gap-3">{[["Cảnh báo thị trường mức CAO", "Tín hiệu bất thường từ dữ liệu NeoPulse, kèm mã và thời điểm.", alerts, setAlerts], ["Tin doanh nghiệp đáng chú ý", "Tiêu đề có nhắc mã theo dõi từ RSS CafeF, kèm link bài gốc.", news, setNews], ["Tin chính sách & văn bản", "Nguồn Báo Chính phủ. Phân biệt bài viết/đề xuất và văn bản có hiệu lực.", laws, setLaws]].map(([title, text, checked, setter]) => <label key={title as string} className="flex cursor-pointer gap-3 rounded-xl bg-surface2 p-4"><input className="mt-1 h-4 w-4 shrink-0" type="checkbox" checked={checked as boolean} onChange={(e) => (setter as (v: boolean) => void)(e.target.checked)} /><span><b className="text-sm">{title as string}</b><span className="mt-1 block text-xs leading-relaxed text-muted">{text as string}</span></span></label>)}</div>
    {topics ? <a href={`https://t.me/neopulse_warningbot?start=${topics}`} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-12 items-center rounded-full bg-accent px-6 text-sm font-semibold text-on-accent">Mở Telegram và nhấn Start ↗</a> : <p className="text-sm text-muted">Chọn ít nhất một nhóm tin để đăng ký.</p>}
    <p className="mt-4 text-xs leading-relaxed text-muted">Chỉ đăng ký sau khi bạn nhấn Start trong Telegram. Website không yêu cầu tài khoản hay thu thập số điện thoại của bạn. Không đăng ký cũng sử dụng được toàn bộ website.</p>
  </section>;
}
