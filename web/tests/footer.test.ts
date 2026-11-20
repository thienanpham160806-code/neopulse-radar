import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { SiteFooter } from "../src/components/SiteFooter";

it("shows only the owner's confirmed contact links and real website information", () => {
  const html = renderToStaticMarkup(createElement(SiteFooter));
  expect(html).toContain("Phạm Ngọc Thiên An");
  expect(html).toContain('href="mailto:anpntk24414h@st.uel.edu.vn"');
  expect(html).toContain('href="mailto:thienanpham.160806@gmail.com"');
  expect(html).toContain('href="tel:+84828677648"');
  expect(html).toContain('href="https://github.com/thienanpham160806-code"');
  expect(html).toContain('href="https://neopulse-radar.vercel.app"');
  expect(html).toContain('href="#top"');
  expect(html).not.toMatch(/VaxiTrust|Mạnh Quyền|669 Đỗ Mười/);
});
