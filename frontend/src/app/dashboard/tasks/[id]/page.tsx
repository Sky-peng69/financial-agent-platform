"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SearchReferences from "@/components/SearchReferences";
import { tasks as tasksApi, type Task, parseSearchReferences } from "@/lib/api";

/** 复制文本到剪贴板，回退方案用 execCommand */
async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // 降级：创建临时 textarea + execCommand
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    ta.style.top = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      return true;
    } catch {
      return false;
    } finally {
      document.body.removeChild(ta);
    }
  }
}

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  function handleCopy(text: string) {
    copyToClipboard(text).then((ok) => {
      if (ok) { setCopied(true); setTimeout(() => setCopied(false), 2000); }
    });
  }

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
          <div className="h-3 w-16 bg-[#F1F3F5] rounded-lg animate-pulse" />
          <div className="h-3 w-3 bg-[#F1F3F5] rounded-lg animate-pulse" />
          <div className="h-3 w-32 bg-[#F1F3F5] rounded-lg animate-pulse" />
        </div>
        {/* Meta card skeleton */}
        <div className="card p-6 mb-6 space-y-3">
          <div className="h-6 bg-[#F1F3F5] rounded-lg animate-pulse w-3/4" />
          <div className="h-4 bg-[#F1F3F5] rounded-lg animate-pulse w-1/2" />
        </div>
        {/* Content skeleton */}
        <div className="card p-6 space-y-3">
          <div className="h-5 bg-[#F1F3F5] rounded-lg animate-pulse w-1/3" />
          <div className="h-4 bg-[#F1F3F5] rounded-lg animate-pulse w-full" />
          <div className="h-4 bg-[#F1F3F5] rounded-lg animate-pulse w-5/6" />
          <div className="h-4 bg-[#F1F3F5] rounded-lg animate-pulse w-2/3" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
        <div className="bg-[#FEF2F2] border border-[#DC2626]/20 rounded-lg px-6 py-8 text-center">
          <p className="text-[#DC2626] text-sm font-semibold mb-2">加载失败</p>
          <p className="text-[#DC2626]/70 text-sm mb-4">{error}</p>
          <button
            className="text-[#2563EB] text-sm hover:text-[#1D4ED8] transition-colors font-medium"
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
          <p className="text-[#6B7280] text-sm">任务不存在</p>
          <Link href="/dashboard/tasks" className="text-[#2563EB] text-sm mt-2 inline-block font-medium">返回列表</Link>
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
        <Link href="/dashboard/tasks" className="text-[#9CA3AF] hover:text-[#2563EB] transition-colors">
          任务历史
        </Link>
        <span className="text-[#D1D5DB]">/</span>
        <span className="text-[#2563EB] font-medium truncate">{task.title}</span>
      </div>

      {/* Meta */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-[#111827] text-lg font-semibold">{task.title}</h1>
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              task.status === "completed"
                ? "bg-[#ECFDF5] text-[#059669]"
                : task.status === "failed"
                ? "bg-[#FEF2F2] text-[#DC2626]"
                : "bg-[#F1F3F5] text-[#6B7280]"
            }`}
          >
            {task.status === "completed" ? "✓ 完成" : task.status === "failed" ? "✗ 失败" : task.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#9CA3AF]">
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
              <h2 className="text-[#111827] text-sm font-semibold mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
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
                        className="flex items-center gap-2 bg-[#F1F3F5] border border-[#E5E7EB] rounded-lg px-3 py-2"
                      >
                        <span className="text-[11px] text-[#2563EB] font-mono tabular-nums font-medium">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="text-[#374151] text-xs">{name}</span>
                      </div>
                    );
                  }
                )}
              </div>
              {parsedPlan.plan.analysis_type && (
                <p className="text-[#9CA3AF] text-xs">分析类型: {parsedPlan.plan.analysis_type}</p>
              )}
            </div>
          )}

          {/* Sub-task results (collapsible per specialist) */}
          {parsedPlan.subtask_results?.length > 0 && (
            <div className="card p-6 mb-6">
              <h2 className="text-[#111827] text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                专家分析详情
              </h2>
              <div className="space-y-2">
                {parsedPlan.subtask_results.map((r: any, i: number) => (
                  <details key={i} className="group bg-[#F1F3F5] border border-[#E5E7EB] rounded-lg">
                    <summary className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-[#E5E7EB] transition-colors list-none">
                      <div className="flex items-center gap-3">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            r.status === "completed"
                              ? "bg-[#059669]"
                              : r.status === "timeout"
                              ? "bg-[#DC2626]"
                              : r.status === "error"
                              ? "bg-[#DC2626]"
                              : "bg-[#9CA3AF]"
                          }`}
                        />
                        <span className="text-[#111827] text-sm font-medium">{r.agent}</span>
                        <span className="text-[#9CA3AF] text-[11px]">{r.status}</span>
                      </div>
                      <span className="text-[#9CA3AF] text-xs group-open:hidden">展开</span>
                      <span className="text-[#9CA3AF] text-xs hidden group-open:inline">收起</span>
                    </summary>
                    <div className="px-4 pb-4 border-t border-[#E5E7EB] pt-4">
                      <MarkdownRenderer content={r.content || "（无内容）"} />
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {task.error_message && (
            <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-5 py-4 rounded-lg mb-6">
              <p className="font-semibold mb-1">错误信息</p>
              {task.error_message}
            </div>
          )}

          {/* Synthesis report */}
          {task.output_data && (
            <div className="card p-6">
              <h2 className="text-[#111827] text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                综合报告
              </h2>
              <MarkdownRenderer content={task.output_data} />
              <SearchReferences references={parseSearchReferences(task.search_references) || []} />
              {/* 操作按钮：复制 + 导出 PDF */}
              <div className="flex items-center gap-2 mt-6 pt-4 border-t border-[#E5E7EB]">
                <button
                  onClick={() => handleCopy(task.output_data || "")}
                  className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                >
                  {copied ? (
                    <>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      已复制
                    </>
                  ) : (
                    <>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                      复制报告
                    </>
                  )}
                </button>
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  导出 PDF
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Non-Commander: simple input/output display */}
          {task.input_data && (
            <div className="card p-6 mb-6">
              <h2 className="text-[#111827] text-sm font-semibold mb-3">任务输入</h2>
              <p className="text-[#6B7280] text-sm whitespace-pre-wrap">{task.input_data}</p>
            </div>
          )}

          {task.error_message && (
            <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-5 py-4 rounded-lg mb-6">
              <p className="font-semibold mb-1">错误信息</p>
              {task.error_message}
            </div>
          )}

          {task.output_data && (
            <div className="card p-6">
              <h2 className="text-[#111827] text-sm font-semibold mb-4">分析结果</h2>
              <MarkdownRenderer content={task.output_data} />
              <SearchReferences references={parseSearchReferences(task.search_references) || []} />
              {/* 复制 + PDF 导出按钮 */}
              <div className="flex items-center gap-2 mt-6 pt-4 border-t border-[#E5E7EB]">
                <button
                  onClick={() => handleCopy(task.output_data || "")}
                  className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                >
                  {copied ? (
                    <>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      已复制
                    </>
                  ) : (
                    <>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                      复制报告
                    </>
                  )}
                </button>
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  导出 PDF
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
