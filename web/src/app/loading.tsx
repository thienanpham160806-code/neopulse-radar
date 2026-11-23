export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="mx-auto max-w-6xl px-3 py-5 sm:px-6">
      <p className="sr-only">Đang tải dữ liệu thị trường…</p>
      <div className="skeleton h-11 rounded-2xl" aria-hidden />
      <div className="mt-4 grid grid-cols-1 gap-3.5 lg:grid-cols-12" aria-hidden>
        <div className="skeleton h-80 rounded-2xl lg:col-span-4" />
        <div className="skeleton h-80 rounded-2xl lg:col-span-4" />
        <div className="skeleton h-80 rounded-2xl lg:col-span-4" />
      </div>
      <div className="skeleton mt-6 h-80 rounded-2xl" aria-hidden />
    </div>
  );
}
