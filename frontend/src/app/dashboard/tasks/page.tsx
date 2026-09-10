"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { tasks as tasksApi, type Task } from "@/lib/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tasksApi
      .list()
      .then(setTasks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 animate-fade-up">
      <div className="mb-8">
        <p className="text-[#9CA3AF] text-xs mb-1 tracking-widest uppercase">Task History</p>
        <h1 className="text-[#111827] text-2xl font-semibold">任务历史</h1>
      </div>

      {tasks.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-[#D1D5DB] text-4xl mb-4">☰</div>
          <p className="text-[#6B7280] text-sm mb-2">暂无任务</p>
          <Link href="/dashboard/agents" className="text-[#2563EB] text-sm hover:text-[#1D4ED8] transition-colors font-medium">
            去 Agent 市场运行第一个分析 →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <Link
              key={task.id}
              href={`/dashboard/tasks/${task.id}`}
              className="card-hover flex items-center justify-between px-5 py-4 block"
            >
              <div className="flex-1 min-w-0 mr-4">
                <h3 className="text-[#111827] text-sm font-medium truncate">{task.title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[#9CA3AF] text-xs">{task.agent_name}</span>
                  <span className="text-[#D1D5DB]">·</span>
                  <span className="text-[#9CA3AF] text-xs">
                    {new Date(task.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-4 flex-shrink-0">
                <span
                  className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    task.status === "completed"
                      ? "bg-[#ECFDF5] text-[#059669]"
                      : task.status === "failed"
                      ? "bg-[#FEF2F2] text-[#DC2626]"
                      : "bg-[#F1F3F5] text-[#6B7280]"
                  }`}
                >
                  {task.status === "completed" ? "完成" : task.status === "failed" ? "失败" : task.status}
                </span>
                <span className="text-[#9CA3AF] text-xs">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
