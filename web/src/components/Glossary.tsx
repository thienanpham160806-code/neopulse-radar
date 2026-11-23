"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { GLOSSARY, METHOD_URL, searchGlossary } from "@/lib/glossary";

const GlossaryContext = createContext<((key?: string) => void) | null>(null);

/** Native modal supplies focus containment, Escape and inert background; no UI dependency. */
export function GlossaryProvider({ children, onNavigate }: { children: ReactNode; onNavigate: (tab: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("pulse");
  const results = searchGlossary(query);
  const entry = GLOSSARY[selected];
  const show = (key = "pulse") => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelected(GLOSSARY[key] ? key : "pulse");
    setQuery("");
    setOpen(true);
  };
  const close = () => setOpen(false);

  useEffect(() => {
    const node = dialog.current;
    if (!open || !node) return;
    node.showModal();
    search.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      node.close();
      document.body.style.overflow = overflow;
      if (opener.current?.isConnected) opener.current.focus();
    };
  }, [open]);

  return <GlossaryContext.Provider value={show}>
    {children}
    <dialog ref={dialog} aria-labelledby="glossary-title" className="glossary-dialog" onCancel={close}
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        const items = [...e.currentTarget.querySelectorAll<HTMLElement>("button, input, a[href], summary")]
          .filter((el) => el.getClientRects().length && !el.hasAttribute("disabled"));
        const first = items[0], last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }}
      onClick={(e) => { if (e.target === dialog.current) close(); }}>
      {open ? <div className="flex min-h-full flex-col bg-surface">
        <header className="sticky top-0 z-10 border-b border-line bg-surface px-5 pb-4 pt-5 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <h2 id="glossary-title" className="text-xl font-bold">Tra cứu chỉ số</h2>
            <button type="button" onClick={close} className="min-h-11 rounded-lg bg-surface2 px-3 text-sm">Đóng <span aria-hidden>×</span></button>
          </div>
          <label className="mt-3 block text-sm" htmlFor="glossary-search">Tìm tên chỉ số hoặc viết tắt</label>
          <input ref={search} id="glossary-search" value={query} onChange={(e) => setQuery(e.target.value)} type="search"
            placeholder="Ví dụ: do rong, OBI, IC…" className="mt-1 min-h-11 w-full rounded-lg border border-line bg-bg px-3 text-base" />
          <p role="status" className="mt-2 text-xs text-muted">{results.length} mục phù hợp · Tìm được cả tiếng Việt không dấu</p>
        </header>
        <nav aria-label="Kết quả tra cứu" className="max-h-44 shrink-0 overflow-y-auto border-b border-line bg-bg p-3">
          {results.length ? <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">{results.map(([key, g]) => <li key={key}>
            <button type="button" aria-current={selected === key ? "true" : undefined}
              onClick={() => setSelected(key)}
              className={`min-h-11 w-full rounded-lg px-3 py-2 text-left text-sm ${selected === key ? "bg-accent font-semibold text-on-accent" : "hover:bg-surface2"}`}>
              {g.title}
            </button>
          </li>)}</ul> : <p className="p-2 text-sm">Không tìm thấy. Thử tên ngắn hơn hoặc viết tắt như OBI, RVOL, IC.</p>}
        </nav>
        {entry ? <article id="glossary-entry" aria-labelledby="glossary-entry-title" className="flex-1 px-5 py-5 sm:px-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Hiểu chỉ số để đọc đúng dữ liệu</p>
          <h3 id="glossary-entry-title" className="mt-2 text-2xl font-bold">{entry.title}</h3>
          <p className="mt-1 text-xs text-muted">{entry.aliases.join(" · ")}</p>
          <p className="mt-3 text-sm"><b>Đơn vị:</b> {entry.unit}</p>
          <p className="mt-3 leading-relaxed">{entry.body}</p>
          <h4 className="mt-5 font-bold">Đọc con số thế nào?</h4>
          <p className="mt-1 text-sm leading-relaxed">{entry.reading}</p>
          <div className="mt-4 rounded-xl bg-surface2 p-4 text-sm leading-relaxed"><b className="mb-1 block">Ví dụ minh họa · không phải số liệu hiện tại</b>{entry.example}</div>
          <h4 className="mt-5 font-bold">Vì sao có trong đồ án?</h4>
          <p className="mt-1 text-sm leading-relaxed">{entry.role}</p>
          <h4 className="mt-5 font-bold">Giới hạn khi sử dụng</h4>
          <p className="mt-1 text-sm leading-relaxed text-muted">{entry.limit}</p>
          <details className="mt-5 rounded-xl border border-line p-3">
            <summary className="min-h-8 cursor-pointer text-sm font-semibold">Công thức và nguồn tham khảo</summary>
            <p className="mt-2 break-words text-sm leading-relaxed">{entry.formula}</p>
            <a href={METHOD_URL} target="_blank" rel="noreferrer" className="mt-3 block text-sm text-accent underline underline-offset-4">Phương pháp và giả định của NeoPulse ↗</a>
            {entry.source ? <a href={entry.source.url} target="_blank" rel="noreferrer" className="mt-2 block text-sm text-accent underline underline-offset-4">{entry.source.title} ↗</a> : null}
          </details>
          <button type="button" onClick={() => {
            close(); onNavigate(entry.tab);
            requestAnimationFrame(() => document.getElementById("tabpanel")?.focus());
          }} className="mt-5 min-h-11 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-on-accent">Xem nơi sử dụng chỉ số →</button>
        </article> : null}
      </div> : null}
    </dialog>
  </GlossaryContext.Provider>;
}

export function GlossaryButton() {
  const show = useContext(GlossaryContext);
  return <button type="button" onClick={() => show?.()} aria-haspopup="dialog"
    className="min-h-11 shrink-0 rounded-xl bg-accent px-4 text-sm font-semibold text-on-accent">Tra cứu chỉ số <span aria-hidden>↗</span></button>;
}

export function Term({ k, children }: { k: string; children?: ReactNode }) {
  const show = useContext(GlossaryContext);
  const entry = GLOSSARY[k];
  if (!entry) return <>{children}</>;
  return <button type="button" data-term={k} aria-haspopup="dialog" aria-label={`Giải thích: ${entry.title}`} onClick={() => show?.(k)}
    className="inline-flex min-h-8 items-center gap-1 rounded-md text-left hover:bg-surface2">
    {children}<span aria-hidden className="inline-flex h-8 w-8 shrink-0 items-center justify-center text-sm font-semibold text-accent">ⓘ</span>
  </button>;
}
