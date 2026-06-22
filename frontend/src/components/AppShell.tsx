"use client";

import { useAuth } from "@/lib/store";
import Sidebar from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080C14]">
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 overflow-auto relative z-10">{children}</main>
    </div>
  );
}
