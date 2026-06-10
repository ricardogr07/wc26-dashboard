import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // Rewrites only work with `next dev` (dev server). `next build` with output:export
  // runs with NODE_ENV=production so this block is excluded, avoiding the build error
  // that rewrites + output:export would otherwise trigger.
  ...(process.env.NODE_ENV !== "production" && {
    async rewrites() {
      return [{ source: "/api/:path*", destination: "http://localhost:7071/api/:path*" }];
    },
  }),
};

export default nextConfig;
