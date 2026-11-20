import Link from "next/link";

export const SITE_CONTACT = {
  name: "Phạm Ngọc Thiên An",
  email: "anpntk24414h@st.uel.edu.vn",
  personalEmail: "thienanpham.160806@gmail.com",
  phone: "+84 828 677 648",
  github: "https://github.com/thienanpham160806-code",
};

export function SiteFooter() {
  return <footer aria-label="Thông tin website và liên hệ" className="mt-12 bg-surface pb-24 pt-8 md:pb-8">
    <div className="w-full px-4 sm:px-6 xl:px-10">
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1.3fr)]">
        <section aria-label="Về NeoPulse Radar" className="min-w-0 pr-4">
          <Link href="/trang-chu" className="inline-flex items-center gap-3"><span className="brand-mark" aria-hidden>n<span>p</span></span><span><span className="block text-xl font-bold tracking-tight">NeoPulse Radar</span><span className="text-xs font-medium uppercase tracking-widest text-accent">Hiểu nhịp thị trường</span></span></Link>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">Theo dõi thị trường chứng khoán Việt Nam, nhận diện những biến động đáng chú ý và tìm hiểu sức khỏe tài chính của doanh nghiệp.</p>
          <nav aria-label="Khám phá NeoPulse" className="mt-5 flex flex-wrap gap-x-4 gap-y-3 text-sm"><Link href="/" className="hover:text-accent hover:underline">Thị trường</Link><Link href="/doanh-nghiep" className="hover:text-accent hover:underline">Doanh nghiệp</Link><Link href="/thong-bao" className="hover:text-accent hover:underline">Nhận thông báo</Link></nav>
        </section>
        <section aria-labelledby="footer-contact" className="min-w-0 rounded-2xl bg-surface2 p-5">
          <h2 id="footer-contact" className="text-base font-semibold">Liên hệ người phát triển</h2>
          <p className="mt-3 font-semibold">{SITE_CONTACT.name}</p>
          <p className="mt-1 text-sm leading-relaxed text-muted">Phát triển và vận hành NeoPulse Radar. Liên hệ để góp ý, báo lỗi hoặc trao đổi về website.</p>
          <dl className="mt-4 grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
            <div><dt className="font-medium">Email trường</dt><dd className="mt-1"><a href={`mailto:${SITE_CONTACT.email}`} className="break-all text-accent underline-offset-4 hover:underline">{SITE_CONTACT.email}</a></dd></div>
            <div><dt className="font-medium">Email cá nhân</dt><dd className="mt-1"><a href={`mailto:${SITE_CONTACT.personalEmail}`} className="break-all text-accent underline-offset-4 hover:underline">{SITE_CONTACT.personalEmail}</a></dd></div>
            {SITE_CONTACT.phone ? <div><dt className="font-medium">Điện thoại</dt><dd className="mt-1"><a href={`tel:${SITE_CONTACT.phone.replace(/[\s().-]/g, "")}`} className="text-accent underline-offset-4 hover:underline">{SITE_CONTACT.phone}</a></dd></div> : null}
            <div><dt className="font-medium">GitHub</dt><dd className="mt-1"><a href={SITE_CONTACT.github} target="_blank" rel="noopener noreferrer" className="break-all text-accent underline-offset-4 hover:underline">thienanpham160806-code ↗</a></dd></div>
          </dl>
        </section>
        <section aria-labelledby="footer-website" className="min-w-0 rounded-2xl bg-surface2 p-5">
          <h2 id="footer-website" className="text-base font-semibold">Thông tin website</h2>
          <dl className="mt-4 space-y-4 text-sm"><div><dt className="font-medium">Địa chỉ truy cập</dt><dd className="mt-1"><a href="https://neopulse-radar.vercel.app" className="break-all text-accent underline-offset-4 hover:underline">neopulse-radar.vercel.app</a></dd></div><div><dt className="font-medium">Nguồn dữ liệu</dt><dd className="mt-1 leading-relaxed text-muted">SSI FastConnect cho thị trường; Vietcap cho hồ sơ doanh nghiệp và lịch sử giá. Thời điểm cập nhật được ghi tại từng trang.</dd></div></dl>
          <Link href="/?tab=phuong-phap" className="mt-4 inline-flex min-h-10 items-center text-sm font-medium text-accent underline-offset-4 hover:underline">Cách tính chỉ báo & giới hạn dữ liệu →</Link>
        </section>
      </div>
      <div className="mt-7 flex flex-wrap items-end justify-between gap-4 border-t border-line pt-5">
        <div className="max-w-3xl text-xs leading-relaxed text-muted"><p>© {new Date().getFullYear()} NeoPulse Radar · Phát triển bởi {SITE_CONTACT.name}.</p><p className="mt-1">Công cụ phân tích học thuật. Thông tin tham khảo, không phải khuyến nghị đầu tư.</p></div>
        <a href="#top" aria-label="Quay về đầu trang" className="inline-flex min-h-11 items-center gap-2 rounded-full bg-surface2 px-4 text-sm font-medium hover:text-accent">Về đầu trang <span aria-hidden>↑</span></a>
      </div>
    </div>
  </footer>;
}
