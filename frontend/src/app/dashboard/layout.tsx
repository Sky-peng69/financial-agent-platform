"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/store";

const NAV_ITEMS = [
  { label: "工作台", href: "/dashboard", icon: "⌂" },
  { label: "Agent 市场", href: "/dashboard/agents", icon: "◆" },
  { label: "任务历史", href: "/dashboard/tasks", icon: "☰" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080C14]">
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside
        className={`bg-[#0F1521] border-r border-[#1E2A3E] flex flex-col transition-all duration-300 ${
          collapsed ? "w-[60px]" : "w-[220px]"
        }`}
      >
        {/* Logo */}
        <div className="h-14 flex items-center gap-2 px-4 border-b border-[#1E2A3E]">
          <button onClick={() => setCollapsed(!collapsed)} className="text-[#C9A94E] hover:text-[#D4B85A] transition-colors">
            <div className="w-7 h-7 bg-[#C9A94E] rounded-sm flex items-center justify-center text-[#080C14] font-bold text-sm">衡</div>
          </button>
          {!collapsed && (
            <span className="text-[#E8EDF5] font-semibold text-sm tracking-wide">衡策</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm text-[#8B95A5] hover:text-[#E8EDF5] hover:bg-[#141C2B] transition-all duration-200"
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* User */}
        {!collapsed && user && (
          <div className="p-3 border-t border-[#1E2A3E]">
            <div className="text-[#E8EDF5] text-sm font-medium truncate">{user.name}</div>
            <div className="text-[#5A6577] text-xs mb-2">
              {user.role === "admin" ? "管理员" : user.role === "org_user" ? "机构用户" : "投资者"}
            </div>
            <button
              onClick={logout}
              className="text-[#D95A4A] text-xs hover:text-red-400 transition-colors"
            >
              退出登录
            </button>
          </div>
        )}
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto relative z-10">{children}</main>
    </div>
  );
}
