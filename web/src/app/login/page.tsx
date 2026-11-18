export const metadata = { title: "Đăng nhập · NeoPulse Radar" };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const sp = await searchParams;
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-4 px-4">
      <h1 className="text-xl font-semibold">NeoPulse Radar</h1>
      <p className="text-sm text-muted">Trang này cần mật khẩu. Công cụ phân tích học thuật, không phải lời khuyên đầu tư.</p>
      <form method="post" action="/api/login" className="flex flex-col gap-3">
        <label className="text-sm" htmlFor="password">Mật khẩu</label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoFocus
          autoComplete="current-password"
          className="rounded-md border border-line bg-surface px-3 py-2 text-base"
        />
        {sp.error ? <p role="alert" className="text-sm text-down">Mật khẩu không đúng.</p> : null}
        <button type="submit" className="rounded-md bg-accent px-3 py-2 font-medium text-white">Vào xem</button>
      </form>
    </main>
  );
}
