"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { agents as agentsApi, tasks as tasksApi, type Agent, type Task } from "@/lib/api";
import { useAuth } from "@/lib/store";

const SUGGESTED_PROMPTS = [
  "分析茅台(600519)的投资价值，涵盖行业竞争、财务表现和风险因素",
  "白酒行业竞争格局与关键趋势分析",
  "当前宏观经济形势研判及对A股市场影响",
];

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Commander analyze state
  const [analyzeInput, setAnalyzeInput] = useState("");
  const [analyzeResult, setAnalyzeResult] = useState<Task | null>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [analyzePhase, setAnalyzePhase] = useState("");

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

  async function handleAnalyze() {
    if (!analyzeInput.trim()) return;
    setAnalyzeError("");
    setAnalyzeResult(null);
    setAnalyzeLoading(true);
    setAnalyzePhase("planning");

    const phaseTimer = setTimeout(() => setAnalyzePhase("executing"), 4000);

    try {
      const result = await agentsApi.analyze(analyzeInput.trim(), analyzeInput.trim());
      clearTimeout(phaseTimer);
      setAnalyzeResult(result);
      setAnalyzePhase("");
      tasksApi.list().then(setTasks).catch(() => {});
    } catch (err: any) {
      clearTimeout(phaseTimer);
      setAnalyzeError(err.message || "分析失败，请重试");
      setAnalyzePhase("");
    } finally {
      setAnalyzeLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  }

  // Parse Commander plan from input_data JSON
  const parsedPlan =
    analyzeResult?.agent_name === "commander" && analyzeResult.input_data
      ? (() => {
          try { return JSON.parse(analyzeResult.input_data); }
          catch { return null; }
        })()
      : null;

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
          输入金融分析问题，AI Commander 自动调度专家 Agent 协作
        </p>
      </div>

      {/* ======== Commander 智能分析入口 ======== */}
      <section className="mb-12 animate-fade-up stagger-1">
        <div className="card relative overflow-hidden">
          {/* Gold accent line at top — "activated" visual cue */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#C9A94E]/60 to-transparent" />

          <div className="p-6 sm:p-8">
            {/* Section label with pulse indicator */}
            <div className="flex items-center gap-2.5 mb-5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#C9A94E] opacity-60" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#C9A94E]" />
              </span>
              <h2 className="text-[#8B95A5] text-xs font-semibold tracking-widest uppercase">
                Commander 智能分析
              </h2>
            </div>

            {/* Input + button row */}
            <div className="flex flex-col sm:flex-row gap-3">
              <textarea
                className="input-field flex-1 min-h-[56px] resize-none text-sm"
                placeholder="输入你的金融分析问题，AI 自动分配专家协作..."
                value={analyzeInput}
                onChange={(e) => setAnalyzeInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={analyzeLoading}
                rows={2}
              />
              <button
                className="btn-primary self-end sm:self-stretch flex items-center gap-2 whitespace-nowrap text-sm"
                onClick={handleAnalyze}
                disabled={analyzeLoading || !analyzeInput.trim()}
              >
                {analyzeLoading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-[#080C14]/30 border-t-[#080C14] rounded-full animate-spin" />
                    分析中...
                  </>
                ) : (
                  <>
                    <span className="text-base">◆</span>
                    智能分析
                  </>
                )}
              </button>
            </div>

            {/* Suggested prompts — only show in idle state */}
            {!analyzeResult && !analyzeLoading && !analyzeError && (
              <div className="flex flex-wrap gap-2 mt-4">
                <span className="text-[10px] text-[#5A6577] self-center mr-1">试试：</span>
                {SUGGESTED_PROMPTS.map((hint) => (
                  <button
                    key={hint}
                    className="text-xs text-[#5A6577] bg-[#0A0F18] border border-[#1E2A3E] px-3 py-1.5 rounded-sm hover:text-[#C9A94E] hover:border-[#C9A94E]/30 transition-all duration-200"
                    onClick={() => setAnalyzeInput(hint)}
                  >
                    {hint.length > 24 ? hint.slice(0, 24) + "..." : hint}
                  </button>
                ))}
              </div>
            )}

            {/* ---- Loading state ---- */}
            {analyzeLoading && (
              <div className="mt-6 border-t border-[#1E2A3E] pt-6 animate-fade-in">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-5 h-5 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
                  <span className="text-sm text-[#8B95A5]">
                    {analyzePhase === "planning" && "AI Commander 正在理解问题、规划分析任务..."}
                    {analyzePhase === "executing" && "专家 Agent 正在并行分析中，预计需 1-2 分钟..."}
                    {!analyzePhase && "正在处理..."}
                  </span>
                </div>
                {/* Skeleton blocks */}
                <div className="space-y-2.5">
                  <div className="h-3 bg-[#1E2A3E] rounded-sm animate-pulse w-full" />
                  <div className="h-3 bg-[#1E2A3E] rounded-sm animate-pulse w-3/4" />
                  <div className="h-3 bg-[#1E2A3E] rounded-sm animate-pulse w-5/6" />
                  <div className="h-3 bg-[#1E2A3E] rounded-sm animate-pulse w-1/2" />
                </div>
              </div>
            )}

            {/* ---- Error state ---- */}
            {analyzeError && (
              <div className="mt-6 bg-[#3D1A1A] border border-[#D95A4A]/30 rounded-sm px-5 py-4 animate-fade-in">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[#D95A4A] text-sm font-semibold mb-1">分析未能完成</p>
                    <p className="text-[#D95A4A]/70 text-sm">{analyzeError}</p>
                  </div>
                  <button
                    className="text-[#C9A94E] text-sm hover:text-[#D4B85A] transition-colors shrink-0 mt-0.5"
                    onClick={handleAnalyze}
                  >
                    重试
                  </button>
                </div>
              </div>
            )}

            {/* ---- Result area ---- */}
            {analyzeResult && (
              <div className="mt-6 border-t border-[#1E2A3E] pt-6 animate-fade-up">
                {/* Status */}
                <div className="flex items-center gap-2 mb-5">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-sm font-medium ${
                      analyzeResult.status === "completed"
                        ? "bg-[#1A3D2A] text-[#34A584]"
                        : "bg-[#3D1A1A] text-[#D95A4A]"
                    }`}
                  >
                    {analyzeResult.status === "completed" ? "✓ 分析完成" : "✗ 失败"}
                  </span>
                  {analyzeResult.error_message && (
                    <span className="text-xs text-[#D95A4A]">{analyzeResult.error_message}</span>
                  )}
                </div>

                {/* Plan visualization */}
                {parsedPlan?.plan && (
                  <div className="mb-6">
                    <h3 className="text-[#E8EDF5] text-sm font-semibold mb-3 flex items-center gap-2">
                      <span className="text-[#C9A94E] text-xs">◇</span>
                      编排计划
                    </h3>
                    <div className="flex flex-wrap gap-2">
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
                  </div>
                )}

                {/* Sub-task results (collapsible per specialist) */}
                {parsedPlan?.subtask_results?.length > 0 && (
                  <div className="mb-6 space-y-2">
                    <h3 className="text-[#E8EDF5] text-sm font-semibold mb-3 flex items-center gap-2">
                      <span className="text-[#C9A94E] text-xs">◇</span>
                      专家分析详情
                    </h3>
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
                )}

                {/* Synthesis report */}
                {analyzeResult.output_data && (
                  <div className="bg-[#0A0F18] border border-[#1E2A3E] rounded-sm p-5">
                    <h3 className="text-[#E8EDF5] text-sm font-semibold mb-4 flex items-center gap-2">
                      <span className="text-[#C9A94E] text-xs">◆</span>
                      综合报告
                    </h3>
                    <div className="markdown-content">
                      <ReactMarkdown>{analyzeResult.output_data}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Footer actions */}
                <div className="mt-4 flex items-center gap-4">
                  <Link
                    href={`/dashboard/tasks/${analyzeResult.id}`}
                    className="text-[#C9A94E] text-xs hover:text-[#D4B85A] transition-colors"
                  >
                    查看任务详情 →
                  </Link>
                  <button
                    className="text-[#5A6577] text-xs hover:text-[#8B95A5] transition-colors"
                    onClick={() => {
                      setAnalyzeResult(null);
                      setAnalyzeInput("");
                    }}
                  >
                    新建分析
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

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
