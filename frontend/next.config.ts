import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker本番環境用：スタンドアロンビルドを有効化
  output: "standalone",
  
  // 画像最適化の設定（外部画像を使用する場合）
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
      },
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

export default nextConfig;
