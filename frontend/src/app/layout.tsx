import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata = {
  title: "旅館AIアシスタント",
  description: "旅館のマーケティングをAIでサポートするツール",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`} suppressHydrationWarning>
        <main className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 p-8 overflow-y-auto">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
