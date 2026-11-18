import { NextResponse } from "next/server";
import { COOKIE_NAME, cookieValue, safeEqual, sitePassword } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const pw = sitePassword();
  if (!pw) return NextResponse.json({ ok: true, open: true });
  let given = "";
  try {
    const form = await req.formData();
    given = String(form.get("password") ?? "");
  } catch {
    return NextResponse.json({ error: "Yêu cầu không hợp lệ." }, { status: 400 });
  }
  if (!safeEqual(given, pw)) {
    await new Promise((r) => setTimeout(r, 600)); // làm chậm dò mật khẩu
    return NextResponse.redirect(new URL("/login?error=1", req.url), 303);
  }
  const res = NextResponse.redirect(new URL("/", req.url), 303);
  res.cookies.set(COOKIE_NAME, await cookieValue(pw), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}
