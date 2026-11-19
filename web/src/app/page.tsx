import { Dashboard } from "@/components/Dashboard";
import { loadData } from "@/lib/data";
import { ParseError } from "@/lib/parse";

export const dynamic = "force-dynamic";

type SP = Promise<{ date?: string; index?: string; tab?: string }>;

function Message({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-3 px-4">
      <h1 className="text-xl font-semibold">{title}</h1>
      <div className="text-sm text-muted">{children}</div>
      <p className="text-xs text-muted">Công cụ phân tích học thuật. Không phải lời khuyên đầu tư.</p>
    </main>
  );
}

export default async function Page({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  let loaded;
  try {
    loaded = await loadData(sp.date, sp.index);
  } catch (e) {
    const msg = e instanceof ParseError ? e.message : "Không đọc được dữ liệu mẫu hay dữ liệu trực tiếp.";
    return <Message title="Không tải được dữ liệu">{msg}</Message>;
  }
  return <Dashboard key={`${sp.date ?? ""}|${sp.index ?? ""}`} initial={loaded} requestedDate={sp.date ?? null} requestedIndex={sp.index ?? null} initialTab={sp.tab ?? null} />;
}
