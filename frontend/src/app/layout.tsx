import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/store";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "衡策 · 金融 Agent 平台",
  description: "AI 驱动的金融分析平台 — 银行员工和个人投资者的智能助手",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-white text-[#374151] antialiased min-h-screen">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
