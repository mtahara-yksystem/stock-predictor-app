import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,

  // リダイレクト設定を追加
  async redirects() {
    return [
      {
        source: "/",
        destination: "/home",
        permanent: true, // 301リダイレクト（恒久的）
      },
    ];
  },
};

export default nextConfig;