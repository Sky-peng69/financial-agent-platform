"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { agents as agentsApi, tasks as tasksApi, type Agent, type Task } from "@/lib/api";
import { useAuth } from "@/lib/store";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;

    Promise.all([
      agentsApi.list(),
      tasksApi.list(),
    ]).then(([a, t]) => {
      setAgents(a);
      setTasks(t);
    }).catch(console.error).finally(() => setLoadingData(false));
  }, [user, loading, router]);

  if (loading || loadingData) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  const recentTasks = tasks.slice(0, 5);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-10 animate-fade-up">
        <p className="text-[#5A6577] text-xs mb-2 tracking-widest uppercase">Dashboard</p>
        <h1 className="text-[#E8EDF5] text-2xl font-semibold">
          {user?.name ? `${user.name}，下午好` : '欢迎回来'}
        </h1>
        <p className="text-[#8B95A5] text-sm mt-1">
          选择一个 Agent 开始你的金融分析工作
        </p>
      </div>

      {/* Agent 快捷入口 */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[#E8EDF5] text-sm font-semibold tracking-wider uppercase">可用 Agent</h2>
          <Link href="/dashboard/agents" className="text-[#C9A94E] text-xs hover:text-[#D4B85A] transition-colors">
            查看全部 →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent, i) => (
            <Link
              key={agent.name}
              href={`/dashboard/agents/${agent.name}`}
              className={`card-hover p-5 block animate-fade-up stagger-${i + 1}`}
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-[#E8EDF5] font-semibold text-sm">{agent.display_name}</h3>
                <span className="text-[#5A6577] text-xs px-2 py-0.5 rounded border border-[#1E2A3E]">
                  {agent.category}
                </span>
              </div>
              <p className="text-[#8B95A5] text-xs leading-relaxed mb-3 line-clamp-2">
                {agent.description}
              </p>
              <div className="flex items-center gap-1.5">
                {agent.tools.map((t) => (
                  <span key={t} className="text-[#5A6577] text-[10px] px-1.5 py-0.5 rounded bg-[#0A0F18] border border-[#1E2A3E]">
                    {t}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 最近任务 */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[#E8EDF5] text-sm font-semibold tracking-wider uppercase">最近任务</h2>
          <Link href="/dashboard/tasks" className="text-[#C9A94E] text-xs hover:text-[#D4B85A] transition-colors">
            查看全部 →
          </Link>
        </div>

        {recentTasks.length === 0 ? (
          <div className="card p-8 text-center">
            <p className="text-[#5A6577] text-sm">还没有任务，去 Agent 市场运行第一个分析吧</p>
          </div>
        ) : (
          <div className="space-y-2">
            {recentTasks.map((task) => (
              <Link
                key={task.id}
                href={`/dashboard/tasks/${task.id}`}
                className="card-hover flex items-center justify-between px-5 py-3.5 block"
              >
                <div>
                  <h4 className="text-[#E8EDF5] text-sm font-medium">{task.title}</h4>
                  <span className="text-[#5A6577] text-xs">{task.agent_name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[#5A6577] text-xs">
                    {new Date(task.created_at).toLocaleDateString("zh-CN")}
                  </span>
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
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
