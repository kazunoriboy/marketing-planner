import { Inter } from "next/font/google";
import "./globals.css";

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
        {children}
      </body>
    </html>
  );
}
