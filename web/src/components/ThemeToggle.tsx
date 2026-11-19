"use client";

/**
 * Nút đổi sáng/tối. Tái sử dụng từ invest-system-phase2/components/ThemeToggle.tsx (cùng tác giả):
 * giữ aria-pressed, nhãn chữ, icon SVG, đồng bộ giữa các tab qua sự kiện storage.
 * Sửa: khóa lưu "np-theme"; trạng thái ban đầu theo prefers-color-scheme khi chưa chọn; không phát sự kiện riêng.
 */
import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "np-theme";

function systemTheme(): Theme {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readTheme(): Theme {
  try {
    const t = localStorage.getItem(STORAGE_KEY);
    return t === "dark" || t === "light" ? t : systemTheme();
  } catch {
    return systemTheme();
  }
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const apply = (next: Theme) => {
      setTheme(next);
      document.documentElement.dataset.theme = next;
    };
    apply(readTheme());
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) apply(e.newValue === "dark" ? "dark" : "light");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* vẫn đổi được trong trang này */
    }
    document.documentElement.dataset.theme = next;
    setTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === "dark"}
      aria-label={`Chuyển sang giao diện ${theme === "dark" ? "sáng" : "tối"}`}
      className={`inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-1 text-sm ${className}`}
    >
      {theme === "dark" ? (
        <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
        </svg>
      ) : (
        <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M20.2 15.1A8.5 8.5 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z" />
        </svg>
      )}
      <span>{theme === "dark" ? "Tối" : "Sáng"}</span>
    </button>
  );
}
