import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DefaultTooltipContent } from "recharts";
import { expect, it } from "vitest";
import { TOOLTIP_STYLE } from "../src/components/ui";

it("tooltip overrides the series black text with the theme foreground", () => {
  const html = renderToStaticMarkup(createElement(DefaultTooltipContent, {
    ...TOOLTIP_STYLE, label: "11:18", payload: [{ name: "OBI", value: -0.731, color: "#000000" }],
  }));
  const item = html.match(/<li[^>]*style="([^"]*)"/)?.[1];
  expect(item).toContain("color:var(--fg)");
  expect(item).not.toContain("#000000");
});
