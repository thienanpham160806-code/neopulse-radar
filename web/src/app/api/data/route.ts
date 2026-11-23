import { NextResponse } from "next/server";
import { loadData } from "@/lib/data";
import { ParseError } from "@/lib/parse";

export const dynamic = "force-dynamic";

/** API công khai chỉ trả dữ liệu chỉ báo tổng hợp. */
export async function GET(req: Request) {
  const sp = new URL(req.url).searchParams;
  try {
    const d = await loadData(sp.get("date"), sp.get("index"));
    return NextResponse.json(d, { headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    const msg = e instanceof ParseError ? e.message : "Không đọc được dữ liệu phiên. Vui lòng tải lại trang sau ít phút.";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
