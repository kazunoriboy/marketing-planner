"use client";

import { Inter } from "next/font/google";
import { usePathname } from "next/navigation";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  
  // システムアドミン、施設管理者、マーケティングのパスでは既存のSidebarを表示しない
  const isAdminPath = pathname?.startsWith("/admin");
  const isFacilityPath = pathname?.startsWith("/facility");
  const isMarketingPath = pathname?.startsWith("/marketing");
  const isRootPath = pathname === "/";
  const showSidebar = !isAdminPath && !isFacilityPath && !isMarketingPath && !isRootPath;

  return (
    <html lang="ja" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`} suppressHydrationWarning>
        {showSidebar ? (
          <main className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 p-8 overflow-y-auto">
              {children}
            </div>
          </main>
        ) : (
          <main>
            {children}
          </main>
        )}
      </body>
    </html>
  );
}
