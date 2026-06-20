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
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 animate-fade-up">
      <div className="mb-8">
        <p className="text-[#5A6577] text-xs mb-1 tracking-widest uppercase">Task History</p>
        <h1 className="text-[#E8EDF5] text-2xl font-semibold">任务历史</h1>
      </div>

      {tasks.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-[#5A6577] text-4xl mb-4">☰</div>
          <p className="text-[#8B95A5] text-sm mb-2">暂无任务</p>
          <Link href="/dashboard/agents" className="text-[#C9A94E] text-sm hover:text-[#D4B85A] transition-colors">
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
                <h3 className="text-[#E8EDF5] text-sm font-medium truncate">{task.title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[#5A6577] text-xs">{task.agent_name}</span>
                  <span className="text-[#1E2A3E]">·</span>
                  <span className="text-[#5A6577] text-xs">
                    {new Date(task.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-4 flex-shrink-0">
                <span
                  className={`text-xs px-2 py-0.5 rounded-sm ${
                    task.status === "completed"
                      ? "bg-[#1A3D2A] text-[#34A584]"
                      : task.status === "failed"
                      ? "bg-[#3D1A1A] text-[#D95A4A]"
                      : "bg-[#1E2A3E] text-[#8B95A5]"
                  }`}
                >
                  {task.status === "completed" ? "完成" : task.status === "failed" ? "失败" : task.status}
                </span>
                <span className="text-[#5A6577] text-xs">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
