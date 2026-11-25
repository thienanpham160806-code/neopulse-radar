import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [{ source: "/trang-chu", destination: "/", permanent: true }];
  },
  async rewrites() {
    return process.env.NODE_ENV === "development" ? [{ source: "/api/company", destination: "http://127.0.0.1:3201/api/company" }, { source: "/api/news", destination: "http://127.0.0.1:3201/api/news" }] : [];
  },
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default nextConfig;
