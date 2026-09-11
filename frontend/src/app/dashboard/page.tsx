"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SearchReferences from "@/components/SearchReferences";
import { agents as agentsApi, files as filesApi, tasks as tasksApi, type Agent, type ResearchFile, type Task, type SearchReference, parseSearchReferences } from "@/lib/api";
import { useAuth } from "@/lib/store";

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    ta.style.top = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); return true; }
    catch { return false; }
    finally { document.body.removeChild(ta); }
  }
}

const SUGGESTED_PROMPTS = [
  "分析茅台(600519)的投资价值，涵盖行业竞争、财务表现和风险因素",
  "白酒行业竞争格局与关键趋势分析",
  "当前宏观经济形势研判及对A股市场影响",
];

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface AgentProgress {
  agent: string;
  displayName: string;
  title: string;
  status: "pending" | "running" | "completed" | "timeout" | "error";
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [researchFiles, setResearchFiles] = useState<ResearchFile[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [fileError, setFileError] = useState("");
  const [fileMessage, setFileMessage] = useState("");

  // Commander analyze state
  const [analyzeInput, setAnalyzeInput] = useState("");
  const [analyzeResult, setAnalyzeResult] = useState<Task | null>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [analyzePhase, setAnalyzePhase] = useState("");  // planning | executing | synthesizing
  const [phaseMessage, setPhaseMessage] = useState("");
  const [agentProgress, setAgentProgress] = useState<AgentProgress[]>([]);
  const [parsedPlan, setParsedPlan] = useState<any>(null);
  const [dashboardSearchRefs, setDashboardSearchRefs] = useState<SearchReference[] | null>(null);
  const [copied, setCopied] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  function handleCopy(text: string) {
    copyToClipboard(text).then((ok) => {
      if (ok) { setCopied(true); setTimeout(() => setCopied(false), 2000); }
    });
  }

  function handleExportPDF() {
    window.print();
  }

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;

    Promise.all([
      agentsApi.list(),
      tasksApi.list(),
      filesApi.list(),
    ]).then(([a, t, f]) => {
      setAgents(a);
      setTasks(t);
      setResearchFiles(f);
    }).catch(console.error).finally(() => setLoadingData(false));
  }, [user, loading, router]);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setFileError("");
    setFileMessage("");

    if (file.type && file.type !== "application/pdf") {
      setFileError("当前仅支持 PDF 文件");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setFileError("当前仅支持 PDF 文件");
      return;
    }

    setUploadingFile(true);
    try {
      const uploaded = await filesApi.upload(file);
      setResearchFiles((items) => [uploaded, ...items.filter((item) => item.id !== uploaded.id)]);
      setFileMessage("PDF 已上传并解析完成");
    } catch (err: any) {
      setFileError(err.message || "文件上传失败");
    } finally {
      setUploadingFile(false);
    }
  }

  function resetAnalysis() {
    abortRef.current?.abort();
    setAnalyzeResult(null);
    setAnalyzeError("");
    setAnalyzePhase("");
    setPhaseMessage("");
    setAgentProgress([]);
    setParsedPlan(null);
    setDashboardSearchRefs(null);
  }

  async function handleAnalyze() {
    if (!analyzeInput.trim()) return;
    resetAnalysis();
    setAnalyzeLoading(true);

    const agentStates: AgentProgress[] = [];

    abortRef.current = agentsApi.analyzeStream(
      analyzeInput.trim(),
      analyzeInput.trim(),
      {
        onPhase: (phase, message) => {
          setAnalyzePhase(phase);
          setPhaseMessage(message);
        },
        onPlan: (plan) => {
          setParsedPlan({ plan });
        },
        onAgentStart: (agent, displayName, agentTitle) => {
          agentStates.push({ agent, displayName, title: agentTitle, status: "running" });
          setAgentProgress([...agentStates]);
        },
        onAgentDone: (agent, _displayName, status) => {
          const found = agentStates.find((a) => a.agent === agent);
          if (found) {
            found.status = status === "completed" ? "completed" : status === "timeout" ? "timeout" : "error";
          }
          setAgentProgress([...agentStates]);
        },
        onSynthesizing: () => {
          // handled by onPhase("synthesizing", ...)
        },
        onDone: (result) => {
          setAnalyzeLoading(false);
          setAnalyzePhase("");
          setDashboardSearchRefs(result.search_references);
          setAnalyzeResult({
            id: result.task_id,
            agent_name: "commander",
            title: analyzeInput.trim(),
            status: "completed",
            input_data: JSON.stringify({ plan: result.plan, subtask_results: result.subtask_results }),
            output_data: result.output_data,
            search_references: null,
            error_message: null,
            created_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          });
          // 设置 parsedPlan（如果还没设置）
          if (!parsedPlan && result.plan) {
            setParsedPlan({ plan: result.plan, subtask_results: result.subtask_results });
          }
          tasksApi.list().then(setTasks).catch(() => {});
        },
        onError: (err) => {
          setAnalyzeLoading(false);
          setAnalyzeError(err.message || "分析失败，请重试");
          setAnalyzePhase("");
        },
      },
    );
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  }

  const phaseLabels: Record<string, string> = {
    planning: "AI Commander 正在理解问题、规划分析任务...",
    executing: "专家 Agent 正在并行分析中...",
    synthesizing: "正在汇总各专家分析结果，生成综合报告...",
  };

  if (loading || loadingData) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  const recentTasks = tasks.slice(0, 5);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-10 animate-fade-up">
        <p className="text-[#9CA3AF] text-xs mb-2 tracking-widest uppercase">Dashboard</p>
        <h1 className="text-[#111827] text-2xl font-semibold">
          {user?.name ? `${user.name}，下午好` : '欢迎回来'}
        </h1>
        <p className="text-[#6B7280] text-sm mt-1">
          输入金融分析问题，AI Commander 自动调度专家 Agent 协作
        </p>
      </div>

      {/* PDF 材料 */}
      <section className="mb-12 animate-fade-up stagger-1">
        <div className="card p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
            <div>
              <p className="text-[#9CA3AF] text-xs mb-1 tracking-widest uppercase">Research Files</p>
              <h2 className="text-[#111827] text-lg font-semibold">研究材料</h2>
            </div>
            <label className="btn-secondary cursor-pointer inline-flex items-center justify-center gap-2 text-sm">
              {uploadingFile ? (
                <>
                  <span className="w-4 h-4 border-2 border-[#6B7280]/20 border-t-[#6B7280] rounded-full animate-spin" />
                  解析中...
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  上传 PDF
                </>
              )}
              <input
                className="hidden"
                type="file"
                accept="application/pdf,.pdf"
                disabled={uploadingFile}
                onChange={handleFileUpload}
              />
            </label>
          </div>

          {fileError && (
            <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-4">
              {fileError}
            </div>
          )}
          {fileMessage && (
            <div className="bg-[#ECFDF5] border border-[#059669]/20 text-[#059669] text-sm px-4 py-3 rounded-lg mb-4">
              {fileMessage}
            </div>
          )}

          {researchFiles.length === 0 ? (
            <div className="bg-[#F8F9FB] border border-dashed border-[#D1D5DB] rounded-lg px-5 py-6 text-center">
              <p className="text-[#6B7280] text-sm">暂无 PDF 材料</p>
            </div>
          ) : (
            <div className="space-y-2">
              {researchFiles.slice(0, 5).map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between gap-4 bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-[#111827] text-sm font-medium truncate">{file.original_name}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span className="text-[#9CA3AF] text-xs">{formatBytes(file.size_bytes)}</span>
                      <span className="text-[#D1D5DB]">·</span>
                      <span className="text-[#9CA3AF] text-xs">
                        {new Date(file.created_at).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium shrink-0 ${
                      file.status === "parsed"
                        ? "bg-[#ECFDF5] text-[#059669]"
                        : file.status === "failed"
                        ? "bg-[#FEF2F2] text-[#DC2626]"
                        : "bg-[#F1F3F5] text-[#6B7280]"
                    }`}
                  >
                    {file.status === "parsed" ? "已解析" : file.status === "failed" ? "失败" : "已上传"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ======== Commander 智能分析入口 ======== */}
      <section className="mb-12 animate-fade-up stagger-2">
        <div className="card relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#2563EB]" />

          <div className="p-6 sm:p-8">
            {/* Section label with pulse indicator */}
            <div className="flex items-center gap-2.5 mb-5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2563EB] opacity-40" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2563EB]" />
              </span>
              <h2 className="text-[#6B7280] text-xs font-semibold tracking-widest uppercase">
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
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    分析中...
                  </>
                ) : (
                  "智能分析"
                )}
              </button>
            </div>

            {/* Suggested prompts */}
            {!analyzeResult && !analyzeLoading && !analyzeError && (
              <div className="flex flex-wrap gap-2 mt-4">
                <span className="text-[11px] text-[#9CA3AF] self-center mr-1">试试：</span>
                {SUGGESTED_PROMPTS.map((hint) => (
                  <button
                    key={hint}
                    className="text-xs text-[#6B7280] bg-[#F1F3F5] border border-[#E5E7EB] px-3 py-1.5 rounded-lg hover:text-[#2563EB] hover:border-[#2563EB]/30 hover:bg-[#EFF6FF] transition-all duration-200"
                    onClick={() => setAnalyzeInput(hint)}
                  >
                    {hint.length > 24 ? hint.slice(0, 24) + "..." : hint}
                  </button>
                ))}
              </div>
            )}

            {/* ---- Loading state with real-time agent progress ---- */}
            {analyzeLoading && (
              <div className="mt-6 border-t border-[#E5E7EB] pt-6 animate-fade-in">
                {/* Phase indicator */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-5 h-5 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
                  <span className="text-sm text-[#6B7280]">
                    {phaseMessage || phaseLabels[analyzePhase] || "正在处理..."}
                  </span>
                </div>

                {/* Agent progress cards */}
                {agentProgress.length > 0 && (
                  <div className="space-y-2 mb-4">
                    <p className="text-[11px] text-[#9CA3AF] uppercase tracking-wider font-medium">
                      专家执行进度
                    </p>
                    {agentProgress.map((ap) => (
                      <div
                        key={ap.agent}
                        className="flex items-center justify-between bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-4 py-3 transition-all duration-300"
                      >
                        <div className="flex items-center gap-3">
                          {/* Status dot */}
                          {ap.status === "running" ? (
                            <span className="relative flex h-2.5 w-2.5">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2563EB] opacity-40" />
                              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#2563EB]" />
                            </span>
                          ) : ap.status === "completed" ? (
                            <span className="w-2.5 h-2.5 rounded-full bg-[#059669]" />
                          ) : ap.status === "timeout" ? (
                            <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                          ) : (
                            <span className="w-2.5 h-2.5 rounded-full bg-[#DC2626]" />
                          )}
                          <div>
                            <span className="text-[#111827] text-sm font-medium">
                              {ap.displayName}
                            </span>
                            {ap.title && (
                              <span className="text-[#9CA3AF] text-xs ml-2">
                                — {ap.title}
                              </span>
                            )}
                          </div>
                        </div>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            ap.status === "running"
                              ? "bg-[#EFF6FF] text-[#2563EB]"
                              : ap.status === "completed"
                              ? "bg-[#ECFDF5] text-[#059669]"
                              : ap.status === "timeout"
                              ? "bg-[#FFFBEB] text-[#F59E0B]"
                              : "bg-[#FEF2F2] text-[#DC2626]"
                          }`}
                        >
                          {ap.status === "running"
                            ? "分析中"
                            : ap.status === "completed"
                            ? "✓ 完成"
                            : ap.status === "timeout"
                            ? "超时"
                            : "失败"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Skeleton while no agents started yet */}
                {agentProgress.length === 0 && (
                  <div className="space-y-2.5">
                    <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-full" />
                    <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-3/4" />
                    <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-5/6" />
                  </div>
                )}
              </div>
            )}

            {/* ---- Error state ---- */}
            {analyzeError && (
              <div className="mt-6 bg-[#FEF2F2] border border-[#DC2626]/20 rounded-lg px-5 py-4 animate-fade-in">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[#DC2626] text-sm font-semibold mb-1">分析未能完成</p>
                    <p className="text-[#DC2626]/70 text-sm">{analyzeError}</p>
                  </div>
                  <button
                    className="text-[#2563EB] text-sm hover:text-[#1D4ED8] transition-colors shrink-0 mt-0.5 font-medium"
                    onClick={handleAnalyze}
                  >
                    重试
                  </button>
                </div>
              </div>
            )}

            {/* ---- Result area ---- */}
            {analyzeResult && (
              <div className="mt-6 border-t border-[#E5E7EB] pt-6 animate-fade-up">
                {/* Status */}
                <div className="flex items-center gap-2 mb-5">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      analyzeResult.status === "completed"
                        ? "bg-[#ECFDF5] text-[#059669]"
                        : "bg-[#FEF2F2] text-[#DC2626]"
                    }`}
                  >
                    {analyzeResult.status === "completed" ? "✓ 分析完成" : "✗ 失败"}
                  </span>
                  {analyzeResult.error_message && (
                    <span className="text-xs text-[#DC2626]">{analyzeResult.error_message}</span>
                  )}
                </div>

                {/* Plan visualization */}
                {parsedPlan?.plan && (
                  <div className="mb-6">
                    <h3 className="text-[#111827] text-sm font-semibold mb-3 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
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
                  </div>
                )}

                {/* Sub-task results (collapsible per specialist) */}
                {parsedPlan?.subtask_results?.length > 0 && (
                  <div className="mb-6 space-y-2">
                    <h3 className="text-[#111827] text-sm font-semibold mb-3 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                      专家分析详情
                    </h3>
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
                )}

                {/* Synthesis report */}
                {analyzeResult.output_data && (
                  <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg p-5">
                    <h3 className="text-[#111827] text-sm font-semibold mb-4 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                      综合报告
                    </h3>
                    <MarkdownRenderer content={analyzeResult.output_data} />
                    {/* Search references */}
                    <SearchReferences references={dashboardSearchRefs || []} />
                    <div className="flex items-center gap-2 mt-5 pt-4 border-t border-[#E5E7EB]">
                      <button
                        onClick={() => handleCopy(analyzeResult.output_data || "")}
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
                        onClick={handleExportPDF}
                        className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                        导出 PDF
                      </button>
                      <button
                        onClick={handleAnalyze}
                        className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                        重新生成
                      </button>
                    </div>
                  </div>
                )}

                {/* Footer actions */}
                <div className="mt-4 flex items-center gap-4">
                  <Link
                    href={`/dashboard/tasks/${analyzeResult.id}`}
                    className="text-[#2563EB] text-xs hover:text-[#1D4ED8] transition-colors font-medium"
                  >
                    查看任务详情 →
                  </Link>
                  <button
                    className="text-[#9CA3AF] text-xs hover:text-[#6B7280] transition-colors"
                    onClick={() => {
                      setAnalyzeResult(null);
                      setAnalyzeInput("");
                      setParsedPlan(null);
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
          <h2 className="text-[#111827] text-sm font-semibold tracking-wider uppercase">可用 Agent</h2>
          <Link href="/dashboard/agents" className="text-[#2563EB] text-xs hover:text-[#1D4ED8] transition-colors font-medium">
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
                <h3 className="text-[#111827] font-semibold text-sm">{agent.display_name}</h3>
                <span className="text-[#6B7280] text-xs px-2 py-0.5 rounded-full bg-[#F1F3F5]">
                  {agent.category}
                </span>
              </div>
              <p className="text-[#6B7280] text-xs leading-relaxed mb-3 line-clamp-2">
                {agent.description}
              </p>
              <div className="flex items-center gap-1.5">
                {agent.tools.map((t) => (
                  <span key={t} className="text-[#6B7280] text-[10px] px-1.5 py-0.5 rounded-full bg-[#F1F3F5]">
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
          <h2 className="text-[#111827] text-sm font-semibold tracking-wider uppercase">最近任务</h2>
          <Link href="/dashboard/tasks" className="text-[#2563EB] text-xs hover:text-[#1D4ED8] transition-colors font-medium">
            查看全部 →
          </Link>
        </div>

        {recentTasks.length === 0 ? (
          <div className="card p-8 text-center">
            <p className="text-[#9CA3AF] text-sm">还没有任务，去 Agent 市场运行第一个分析吧</p>
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
                  <h4 className="text-[#111827] text-sm font-medium">{task.title}</h4>
                  <span className="text-[#9CA3AF] text-xs">{task.agent_name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[#9CA3AF] text-xs">
                    {new Date(task.created_at).toLocaleDateString("zh-CN")}
                  </span>
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
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
