import { NextResponse } from "next/server";
import { gateAllows, loadData } from "@/lib/data";
import { sitePassword } from "@/lib/auth";
import { ParseError } from "@/lib/parse";

export const dynamic = "force-dynamic";

/** Làm mới dữ liệu cho trình duyệt (poll ~20 s). Middleware đã kiểm tra mật khẩu; ở đây thêm cổng "chưa đặt mật khẩu". */
export async function GET(req: Request) {
  const sp = new URL(req.url).searchParams;
  try {
    const d = await loadData(sp.get("date"), sp.get("index"));
    if (!gateAllows(d.payload, Boolean(sitePassword()))) {
      return NextResponse.json({ error: "Dữ liệu thật bị khóa: chưa đặt SITE_PASSWORD." }, { status: 403 });
    }
    return NextResponse.json(d, { headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    const msg = e instanceof ParseError ? e.message : "Không đọc được dữ liệu.";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
