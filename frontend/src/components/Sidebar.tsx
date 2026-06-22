"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/store";
import { tasks as tasksApi, type Task } from "@/lib/api";

const NAV_ITEMS = [
  {
    label: "工作台",
    href: "/dashboard",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    label: "Agent 市场",
    href: "/dashboard/agents",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="10" r="3" />
        <path d="M12 2a8 8 0 0 0-8 8c0 5.4 8 12 8 12s8-6.6 8-12a8 8 0 0 0-8-8z" />
      </svg>
    ),
  },
  {
    label: "任务历史",
    href: "/dashboard/tasks",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12,6 12,12 16,14" />
      </svg>
    ),
  },
];

// 获取用户头像文字
function avatarLetter(name: string): string {
  if (!name) return "?";
  return name.charAt(0).toUpperCase();
}

// 截断文字
function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + "...";
}

// 状态颜色映射
const STATUS_COLORS: Record<string, string> = {
  completed: "#34A584",
  running: "#C9A94E",
  pending: "#8B95A5",
  failed: "#D95A4A",
};

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);

  // 加载最近任务
  useEffect(() => {
    if (!user) return;
    tasksApi
      .list()
      .then((list) => setRecentTasks(list.slice(0, 8)))
      .catch(() => {});
  }, [user]);

  // 初始化折叠状态（从 localStorage 恢复）
  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved === "true") setCollapsed(true);
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar_collapsed", String(next));
      return next;
    });
  }, []);

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  const roleLabel =
    user?.role === "admin"
      ? "管理员"
      : user?.role === "org_user"
      ? "机构用户"
      : "投资者";

  return (
    <aside
      className={`flex flex-col bg-[#0F1521] border-r border-[#1E2A3E] transition-all duration-300 ease-in-out h-screen sticky top-0 select-none ${
        collapsed ? "w-[56px]" : "w-[220px]"
      }`}
    >
      {/* ── 顶部：Logo + 折叠按钮 ── */}
      <div
        className={`flex items-center border-b border-[#1E2A3E] ${
          collapsed ? "h-12 justify-center px-0" : "h-12 px-3 gap-2"
        }`}
      >
        {/* Logo 方块 */}
        <div className="w-7 h-7 bg-[#C9A94E] rounded-sm flex items-center justify-center flex-shrink-0">
          <span className="text-[#080C14] font-bold text-sm leading-none">
            衡
          </span>
        </div>

        {/* 展开时显示名称 */}
        {!collapsed && (
          <span className="text-[#E8EDF5] font-semibold text-sm tracking-wide flex-1">
            衡策
          </span>
        )}

        {/* 折叠按钮 */}
        <button
          onClick={toggleCollapsed}
          className={`text-[#5A6577] hover:text-[#8B95A5] transition-colors flex-shrink-0 ${
            collapsed ? "hidden" : ""
          }`}
          title="折叠侧边栏"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15,18 9,12 15,6" />
          </svg>
        </button>
      </div>

      {/* 折叠状态下，Logo 下方显示展开按钮 */}
      {collapsed && (
        <button
          onClick={toggleCollapsed}
          className="flex items-center justify-center h-8 text-[#5A6577] hover:text-[#8B95A5] transition-colors"
          title="展开侧边栏"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9,18 15,12 9,6" />
          </svg>
        </button>
      )}

      {/* ── 导航菜单 ── */}
      <nav className={`py-2 ${collapsed ? "px-1" : "px-2"}`}>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={`flex items-center rounded-sm transition-all duration-150 group ${
                collapsed
                  ? "justify-center h-9 w-full"
                  : "gap-2.5 px-3 py-2"
              } ${
                active
                  ? "text-[#E8EDF5] bg-[#C9A94E]/10"
                  : "text-[#5A6577] hover:text-[#B9C2D4] hover:bg-[#141C2B]"
              }`}
            >
              <span
                className={`flex-shrink-0 ${
                  active ? "text-[#C9A94E]" : ""
                }`}
              >
                {item.icon}
              </span>
              {!collapsed && (
                <span className="text-[13px] font-medium">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── 分隔线 ── */}
      <div className="mx-3 border-t border-[#1E2A3E]" />

      {/* ── 最近任务 ── */}
      {!collapsed && (
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <div className="px-4 py-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5A6577]">
              近期分析
            </span>
          </div>

          {recentTasks.length > 0 ? (
            <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
              {recentTasks.map((task) => (
                <button
                  key={task.id}
                  onClick={() => router.push(`/dashboard/tasks/${task.id}`)}
                  className={`w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-sm transition-colors text-[13px] group ${
                    pathname === `/dashboard/tasks/${task.id}`
                      ? "text-[#E8EDF5] bg-[#141C2B]"
                      : "text-[#8B95A5] hover:text-[#B9C2D4] hover:bg-[#141C2B]"
                  }`}
                >
                  {/* 状态指示点 */}
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor:
                        STATUS_COLORS[task.status] || "#5A6577",
                    }}
                  />
                  <span className="truncate flex-1">
                    {truncate(task.title, 14)}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="px-4 py-4 text-[11px] text-[#5A6577] leading-relaxed">
              {user ? "暂无分析记录" : "登录后查看"}
            </div>
          )}
        </div>
      )}

      {/* ── 底部：用户信息 ── */}
      <div
        className={`border-t border-[#1E2A3E] ${
          collapsed ? "p-2 flex justify-center" : "p-3"
        }`}
      >
        {user ? (
          <div
            className={`flex items-center ${
              collapsed ? "flex-col gap-1" : "gap-2.5"
            }`}
          >
            {/* 头像 */}
            <div className="w-7 h-7 rounded-full bg-[#C9A94E]/20 text-[#C9A94E] flex items-center justify-center flex-shrink-0 text-xs font-semibold">
              {avatarLetter(user.name)}
            </div>

            {!collapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <div className="text-[#B9C2D4] text-[12px] font-medium truncate">
                    {user.name}
                  </div>
                  <div className="text-[#5A6577] text-[11px]">{roleLabel}</div>
                </div>

                {/* 退出按钮 */}
                <button
                  onClick={logout}
                  className="text-[#5A6577] hover:text-[#D95A4A] transition-colors flex-shrink-0"
                  title="退出登录"
                >
                  <svg
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16,17 21,12 16,7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                </button>
              </>
            )}
          </div>
        ) : (
          <div
            className={`text-[#5A6577] ${
              collapsed ? "text-[10px]" : "text-[12px]"
            }`}
          >
            {collapsed ? "?" : "未登录"}
          </div>
        )}
      </div>
    </aside>
  );
}
