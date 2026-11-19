export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="mx-auto max-w-7xl px-4 py-6">
      <p className="text-sm text-muted">Đang tải dữ liệu…</p>
      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-5" aria-hidden>
        <div className="h-64 animate-pulse rounded-xl bg-surface2 lg:col-span-2" />
        <div className="h-64 animate-pulse rounded-xl bg-surface2 lg:col-span-3" />
      </div>
    </div>
  );
}
