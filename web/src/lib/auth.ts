/** Xác thực mật khẩu đơn giản bằng cookie httpOnly. Chạy được ở Edge (middleware) lẫn Node (route handler). */
export const COOKIE_NAME = "np_auth";

export function sitePassword(): string {
  return (process.env.SITE_PASSWORD ?? "").trim();
}

async function sha256Hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Giá trị cookie = băm của mật khẩu (không bao giờ là chính mật khẩu); đổi mật khẩu thì cookie cũ vô hiệu. */
export async function cookieValue(password: string): Promise<string> {
  return sha256Hex(`neopulse-radar:v1:${password}`);
}

export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function isAuthorized(cookie: string | undefined): Promise<boolean> {
  const pw = sitePassword();
  if (!pw) return true; // không đặt mật khẩu: dữ liệu thật bị khóa ở tầng `gateAllows`
  if (!cookie) return false;
  return safeEqual(cookie, await cookieValue(pw));
}
