import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_NAME, decide, isAuthorized, sitePassword } from "@/lib/auth";

/**
 * Chặn mọi trang/API/tệp snapshot khi đã đặt SITE_PASSWORD mà chưa có cookie hợp lệ.
 * Chưa đặt mật khẩu: /data/* (dữ liệu thật) bị chặn hẳn. Không log mật khẩu hay cookie.
 */
export async function middleware(req: NextRequest) {
  const hasPassword = Boolean(sitePassword());
  const authorized = hasPassword ? await isAuthorized(req.cookies.get(COOKIE_NAME)?.value) : false;
  switch (decide(req.nextUrl.pathname, hasPassword, authorized)) {
    case "next":
      return NextResponse.next();
    case "forbidden":
      return NextResponse.json({ error: "Dữ liệu thật bị khóa: chưa đặt SITE_PASSWORD." }, { status: 403 });
    case "unauthorized":
      return NextResponse.json({ error: "Cần đăng nhập." }, { status: 401 });
    default: {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.search = "";
      return NextResponse.redirect(url);
    }
  }
}

export const config = {
  matcher: ["/((?!_next/|favicon.ico|icon.svg|login|api/login).*)"],
};
