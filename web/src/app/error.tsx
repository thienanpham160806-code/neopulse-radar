"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main role="alert" className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-3 px-4">
      <h1 className="text-xl font-semibold">Không hiển thị được trang</h1>
      <p className="text-sm text-muted">
        Đã xảy ra lỗi khi dựng giao diện từ dữ liệu. Thử tải lại; nếu vẫn lỗi, bản snapshot có thể bị hỏng và cần xuất lại bằng
        <code> neopulse publish-static</code>.
      </p>
      <button onClick={reset} className="self-start rounded-md bg-accent px-3 py-2 font-medium text-on-accent">Thử lại</button>
      <p className="text-xs text-muted">Công cụ phân tích học thuật. Không phải lời khuyên đầu tư.</p>
    </main>
  );
}
