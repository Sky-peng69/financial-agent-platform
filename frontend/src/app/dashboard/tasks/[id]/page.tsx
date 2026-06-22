"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { tasks as tasksApi, type Task } from "@/lib/api";

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function fetchTask() {
    setLoading(true);
    setError("");
    tasksApi
      .get(id)
      .then(setTask)
      .catch((err: any) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchTask();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
        {/* Breadcrumb skeleton */}
        <div className="flex items-center gap-2 text-xs mb-6">
          <div className="h-3 w-16 bg-[#1E2A3E] rounded-sm animate-pulse" />
          <div className="h-3 w-3 bg-[#1E2A3E] rounded-sm animate-pulse" />
          <div className="h-3 w-32 bg-[#1E2A3E] rounded-sm animate-pulse" />
        </div>
        {/* Meta card skeleton */}
        <div className="card p-6 mb-6 space-y-3">
          <div className="h-6 bg-[#1E2A3E] rounded-sm animate-pulse w-3/4" />
          <div className="h-4 bg-[#1E2A3E] rounded-sm animate-pulse w-1/2" />
        </div>
        {/* Content skeleton */}
        <div className="card p-6 space-y-3">
          <div className="h-5 bg-[#1E2A3E] rounded-sm animate-pulse w-1/3" />
          <div className="h-4 bg-[#1E2A3E] rounded-sm animate-pulse w-full" />
          <div className="h-4 bg-[#1E2A3E] rounded-sm animate-pulse w-5/6" />
          <div className="h-4 bg-[#1E2A3E] rounded-sm animate-pulse w-2/3" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
        <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 rounded-sm px-6 py-8 text-center">
          <p className="text-[#D95A4A] text-sm font-semibold mb-2">加载失败</p>
          <p className="text-[#D95A4A]/70 text-sm mb-4">{error}</p>
          <button
            className="text-[#C9A94E] text-sm hover:text-[#D4B85A] transition-colors"
            onClick={fetchTask}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="card p-12 text-center">
          <p className="text-[#8B95A5] text-sm">任务不存在</p>
          <Link href="/dashboard/tasks" className="text-[#C9A94E] text-sm mt-2 inline-block">返回列表</Link>
        </div>
      </div>
    );
  }

  // Parse Commander plan from input_data JSON
  const isCommander = task.agent_name === "commander";
  const parsedPlan =
    isCommander && task.input_data
      ? (() => {
          try {
            const parsed = JSON.parse(task.input_data);
            return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
          } catch { return null; }
        })()
      : null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs mb-6">
        <Link href="/dashboard/tasks" className="text-[#5A6577] hover:text-[#C9A94E] transition-colors">
          任务历史
        </Link>
        <span className="text-[#1E2A3E]">/</span>
        <span className="text-[#C9A94E] truncate">{task.title}</span>
      </div>

      {/* Meta */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-[#E8EDF5] text-lg font-semibold">{task.title}</h1>
          <span
            className={`text-xs px-2 py-0.5 rounded-sm ${
              task.status === "completed"
                ? "bg-[#1A3D2A] text-[#34A584]"
                : task.status === "failed"
                ? "bg-[#3D1A1A] text-[#D95A4A]"
                : "bg-[#1E2A3E] text-[#8B95A5]"
            }`}
          >
            {task.status === "completed" ? "✓ 完成" : task.status === "failed" ? "✗ 失败" : task.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#5A6577]">
          <span>Agent: {task.agent_name}</span>
          <span>创建: {new Date(task.created_at).toLocaleString("zh-CN")}</span>
          {task.completed_at && <span>完成: {new Date(task.completed_at).toLocaleString("zh-CN")}</span>}
        </div>
      </div>

      {/* Commander: parsed plan + subtask results + report */}
      {isCommander && parsedPlan ? (
        <>
          {/* Plan visualization */}
          {parsedPlan.plan && (
            <div className="card p-6 mb-6">
              <h2 className="text-[#E8EDF5] text-sm font-semibold mb-3 flex items-center gap-2">
                <span className="text-[#C9A94E] text-xs">◇</span>
                编排计划
              </h2>
              <div className="flex flex-wrap gap-2 mb-4">
                {(parsedPlan.plan.subtasks?.length ? parsedPlan.plan.subtasks : (parsedPlan.plan.specialists_needed || [])).map(
                  (item: any, i: number) => {
                    const name = typeof item === "string" ? item : item.agent;
                    if (!name) return null;
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 bg-[#0A0F18] border border-[#1E2A3E] rounded-sm px-3 py-2"
                      >
                        <span className="text-[10px] text-[#C9A94E] font-mono tabular-nums">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="text-[#B9C2D4] text-xs">{name}</span>
                      </div>
                    );
                  }
                )}
              </div>
              {parsedPlan.plan.analysis_type && (
                <p className="text-[#5A6577] text-xs">分析类型: {parsedPlan.plan.analysis_type}</p>
              )}
            </div>
          )}

          {/* Sub-task results (collapsible per specialist) */}
          {parsedPlan.subtask_results?.length > 0 && (
            <div className="card p-6 mb-6">
              <h2 className="text-[#E8EDF5] text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="text-[#C9A94E] text-xs">◇</span>
                专家分析详情
              </h2>
              <div className="space-y-2">
                {parsedPlan.subtask_results.map((r: any, i: number) => (
                  <details key={i} className="group bg-[#0A0F18] border border-[#1E2A3E] rounded-sm">
                    <summary className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-[#141C2B] transition-colors list-none">
                      <div className="flex items-center gap-3">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            r.status === "completed"
                              ? "bg-[#34A584]"
                              : r.status === "timeout"
                              ? "bg-[#D95A4A]"
                              : r.status === "error"
                              ? "bg-[#D95A4A]"
                              : "bg-[#5A6577]"
                          }`}
                        />
                        <span className="text-[#E8EDF5] text-sm font-medium">{r.agent}</span>
                        <span className="text-[#5A6577] text-[10px]">{r.status}</span>
                      </div>
                      <span className="text-[#5A6577] text-xs group-open:hidden">展开</span>
                      <span className="text-[#5A6577] text-xs hidden group-open:inline">收起</span>
                    </summary>
                    <div className="px-4 pb-4 border-t border-[#1E2A3E] pt-4 markdown-content">
                      <ReactMarkdown>{r.content || "（无内容）"}</ReactMarkdown>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {task.error_message && (
            <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-5 py-4 rounded-sm mb-6">
              <p className="font-semibold mb-1">错误信息</p>
              {task.error_message}
            </div>
          )}

          {/* Synthesis report */}
          {task.output_data && (
            <div className="card p-6">
              <h2 className="text-[#E8EDF5] text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="text-[#C9A94E] text-xs">◆</span>
                综合报告
              </h2>
              <div className="markdown-content">
                <ReactMarkdown>{task.output_data}</ReactMarkdown>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Non-Commander: simple input/output display */}
          {task.input_data && (
            <div className="card p-6 mb-6">
              <h2 className="text-[#E8EDF5] text-sm font-semibold mb-3">任务输入</h2>
              <p className="text-[#8B95A5] text-sm whitespace-pre-wrap">{task.input_data}</p>
            </div>
          )}

          {task.error_message && (
            <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-5 py-4 rounded-sm mb-6">
              <p className="font-semibold mb-1">错误信息</p>
              {task.error_message}
            </div>
          )}

          {task.output_data && (
            <div className="card p-6">
              <h2 className="text-[#E8EDF5] text-sm font-semibold mb-4">分析结果</h2>
              <div className="markdown-content">
                <ReactMarkdown>{task.output_data}</ReactMarkdown>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
