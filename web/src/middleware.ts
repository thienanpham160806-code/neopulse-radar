import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_NAME, isAuthorized, sitePassword } from "@/lib/auth";

/** Chặn mọi trang/API khi đã đặt SITE_PASSWORD mà chưa có cookie hợp lệ. Không log mật khẩu hay cookie. */
export async function middleware(req: NextRequest) {
  if (!sitePassword()) return NextResponse.next();
  if (await isAuthorized(req.cookies.get(COOKIE_NAME)?.value)) return NextResponse.next();
  if (req.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Cần đăng nhập." }, { status: 401 });
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/|favicon.ico|login|api/login).*)"],
};
