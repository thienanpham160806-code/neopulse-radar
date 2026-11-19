import { NextResponse } from "next/server";
import { sitePassword } from "@/lib/auth";

export const dynamic = "force-dynamic";

const CHANNEL = "neopulse:live";
const TTL_MS = 15 * 60 * 1000; // ngắn: ably-js tự gọi lại route này để gia hạn

/**
 * Cấp token Ably CHỈ subscribe kênh `neopulse:live`, hạn 15 phút. Khóa gốc ABLY_API_KEY chỉ dùng ở máy chủ, không bao giờ
 * gửi xuống trình duyệt. Route nằm sau middleware mật khẩu; chưa đặt SITE_PASSWORD thì từ chối (dữ liệu trực tiếp là thật).
 */
export async function GET() {
  if (!sitePassword()) {
    return NextResponse.json({ error: "Kênh trực tiếp bị khóa: chưa đặt SITE_PASSWORD." }, { status: 403 });
  }
  const key = (process.env.ABLY_API_KEY ?? "").trim();
  const keyName = key.split(":")[0];
  if (!key.includes(":") || !keyName.includes(".")) {
    return NextResponse.json({ error: "Chưa cấu hình kênh trực tiếp." }, { status: 503 });
  }
  try {
    const res = await fetch(`https://rest.ably.io/keys/${encodeURIComponent(keyName)}/requestToken`, {
      method: "POST",
      headers: { Authorization: `Basic ${Buffer.from(key).toString("base64")}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        keyName,
        timestamp: Date.now(),
        ttl: TTL_MS,
        capability: JSON.stringify({ [CHANNEL]: ["subscribe"] }),
      }),
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ error: `Ably từ chối cấp token (HTTP ${res.status}).` }, { status: 502 });
    }
    const t = (await res.json()) as { token: string; expires: number; issued: number; capability: string; keyName: string };
    // chỉ trả trường TokenDetails cần cho ably-js; không có khóa gốc
    return NextResponse.json(
      { token: t.token, expires: t.expires, issued: t.issued, capability: t.capability, keyName: t.keyName },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return NextResponse.json({ error: "Không liên lạc được Ably." }, { status: 502 });
  }
}
