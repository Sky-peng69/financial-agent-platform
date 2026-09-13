"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SearchReferences from "@/components/SearchReferences";
import {
  reports as reportsApi,
  researchSubjects,
  type ResearchReport,
  type ResearchSubjectWorkspace,
  type SearchReference,
} from "@/lib/api";

const REPORT_STYLES = [
  {
    value: "institutional",
    label: "机构投研深度版",
    description: "面向券商、基金投研人员，结构完整，强调基本面、估值、风险和待核验事项。",
  },
  {
    value: "executive",
    label: "管理层摘要版",
    description: "面向评委、管理层或投委会快速阅读，结论先行，篇幅更克制。",
  },
  {
    value: "risk_review",
    label: "风险审查版",
    description: "突出来源可靠性、反方挑战、风险等级、证据缺口和人工复核边界。",
  },
];

const REPORT_FORMATS = [
  { value: "docx", label: "Word" },
  { value: "md", label: "Markdown" },
  { value: "pdf", label: "PDF" },
];

interface AgentProgress {
  agent: string;
  displayName: string;
  title: string;
  status: "running" | "completed" | "timeout" | "error";
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN");
}

function fileTypeLabel(format: string) {
  if (format === "docx") return "Word";
  if (format === "md") return "Markdown";
  if (format === "pdf") return "PDF";
  return format.toUpperCase();
}

function ReportDownloads({ report }: { report: ResearchReport }) {
  const handleDownload = (file: ResearchReport["files"][number]) => {
    reportsApi.downloadFile(file).catch((err) => {
      alert(err instanceof Error ? err.message : "下载失败，请稍后重试");
    });
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
      {report.files.map((file) => (
        <button
          key={file.format}
          type="button"
          onClick={() => handleDownload(file)}
          className="text-left bg-white border border-[#E5E7EB] rounded-lg px-3 py-3 hover:border-[#2563EB]/40 hover:bg-[#EFF6FF] transition-colors"
        >
          <span className="text-[#2563EB] text-xs font-semibold">{fileTypeLabel(file.format)}</span>
          <p className="text-[#374151] text-xs mt-1 truncate">{file.filename}</p>
        </button>
      ))}
    </div>
  );
}

export default function ResearchSubjectReportPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [workspace, setWorkspace] = useState<ResearchSubjectWorkspace | null>(null);
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reportStyle, setReportStyle] = useState("institutional");
  const [formats, setFormats] = useState(["docx", "md", "pdf"]);
  const [phaseMessage, setPhaseMessage] = useState("");
  const [agentProgress, setAgentProgress] = useState<AgentProgress[]>([]);
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [searchRefs, setSearchRefs] = useState<SearchReference[]>([]);
  const [latestReport, setLatestReport] = useState<ResearchReport | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  function loadPage() {
    setLoading(true);
    setError("");
    Promise.all([
      researchSubjects.workspace(id),
      researchSubjects.listReports(id),
    ])
      .then(([nextWorkspace, nextReports]) => {
        setWorkspace(nextWorkspace);
        setReports(nextReports);
        setLatestReport(nextReports[0] || null);
      })
      .catch((err: any) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPage();
    return () => abortRef.current?.abort();
  }, [id]);

  function toggleFormat(format: string) {
    setFormats((items) => {
      if (items.includes(format)) {
        const next = items.filter((item) => item !== format);
        return next.length > 0 ? next : items;
      }
      return [...items, format];
    });
  }

  function handleStartResearch() {
    setRunning(true);
    setError("");
    setMessage("");
    setPhaseMessage("预计耗时 2-5 分钟，AI 正在准备研究任务...");
    setAgentProgress([]);
    setReportMarkdown("");
    setSearchRefs([]);
    setLatestReport(null);

    const states: AgentProgress[] = [];
    abortRef.current = researchSubjects.startResearchStream(
      id,
      { report_style: reportStyle, formats },
      {
        onPhase: (_phase, phase) => {
          setPhaseMessage(phase);
        },
        onPlan: () => {},
        onAgentStart: (agent, displayName, title) => {
          states.push({ agent, displayName, title, status: "running" });
          setAgentProgress([...states]);
        },
        onAgentDone: (agent, _displayName, status) => {
          const found = states.find((item) => item.agent === agent);
          if (found) {
            found.status = status === "completed" ? "completed" : status === "timeout" ? "timeout" : "error";
          }
          setAgentProgress([...states]);
        },
        onDone: (result) => {
          setRunning(false);
          setPhaseMessage("");
          setReportMarkdown(result.output_data);
          setSearchRefs(result.search_references || []);
          setLatestReport(result.report);
          if (result.report) setReports((items) => [result.report!, ...items]);
          setMessage("研究报告已生成");
        },
        onError: (err) => {
          setRunning(false);
          setPhaseMessage("");
          setError(err.message || "研究失败，请重试");
        },
      },
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="card p-10 text-center">
          <p className="text-[#6B7280] text-sm">研究对象不存在</p>
          <Link href="/dashboard/research" className="text-[#2563EB] text-sm mt-2 inline-block font-medium">
            返回公司研究
          </Link>
        </div>
      </div>
    );
  }

  const { subject } = workspace;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center gap-2 text-xs mb-6 animate-fade-up">
        <Link href="/dashboard/research" className="text-[#9CA3AF] hover:text-[#2563EB] transition-colors">
          公司研究
        </Link>
        <span className="text-[#D1D5DB]">/</span>
        <span className="text-[#2563EB] font-medium truncate">{subject.company_name}</span>
      </div>

      {error && (
        <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-5">
          {error}
        </div>
      )}
      {message && (
        <div className="bg-[#ECFDF5] border border-[#059669]/20 text-[#059669] text-sm px-4 py-3 rounded-lg mb-5">
          {message}
        </div>
      )}

      <section className="card p-6 mb-6 animate-fade-up">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5">
          <div className="min-w-0">
            <p className="text-[#9CA3AF] text-xs mb-2 tracking-widest uppercase">Company Research</p>
            <h1 className="text-[#111827] text-2xl font-semibold tracking-tight">{subject.company_name}</h1>
            <p className="text-[#6B7280] text-sm mt-2 max-w-3xl">
              AI 将自动检索公开资料，调度专业 Agent 生成可下载的公司研究报告。
            </p>
          </div>
          <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-4 py-3 shrink-0">
            <p className="text-[#9CA3AF] text-[11px]">报告版本</p>
            <p className="text-[#111827] text-lg font-semibold mt-1">{reports.length}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-6 items-start">
        <aside className="space-y-4">
          <section className="card p-5 animate-fade-up stagger-1">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">报告风格</h2>
            <div className="space-y-2">
              {REPORT_STYLES.map((style) => (
                <button
                  key={style.value}
                  type="button"
                  onClick={() => setReportStyle(style.value)}
                  disabled={running}
                  className={`w-full text-left border rounded-lg px-3 py-3 transition-colors ${
                    reportStyle === style.value
                      ? "border-[#2563EB] bg-[#EFF6FF]"
                      : "border-[#E5E7EB] bg-white hover:bg-[#F8F9FB]"
                  }`}
                >
                  <p className="text-[#111827] text-sm font-semibold">{style.label}</p>
                  <p className="text-[#6B7280] text-xs leading-relaxed mt-1">{style.description}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="card p-5 animate-fade-up stagger-2">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">下载格式</h2>
            <div className="grid grid-cols-3 gap-2">
              {REPORT_FORMATS.map((format) => (
                <button
                  key={format.value}
                  type="button"
                  onClick={() => toggleFormat(format.value)}
                  disabled={running}
                  className={`border rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    formats.includes(format.value)
                      ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                      : "border-[#E5E7EB] bg-white text-[#6B7280] hover:bg-[#F8F9FB]"
                  }`}
                >
                  {format.label}
                </button>
              ))}
            </div>
            <button
              className="btn-primary w-full text-sm mt-4 h-[44px]"
              onClick={handleStartResearch}
              disabled={running || formats.length === 0}
            >
              {running ? "研究中..." : "开始研究"}
            </button>
            <p className="text-[#9CA3AF] text-xs mt-3">预计耗时 2-5 分钟，实际取决于联网检索和模型响应速度。</p>
          </section>
        </aside>

        <main className="space-y-6">
          {running && (
            <section className="card p-6 animate-fade-up">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-5 h-5 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
                <span className="text-sm text-[#6B7280]">{phaseMessage || "正在研究..."}</span>
              </div>
              {agentProgress.length > 0 ? (
                <div className="space-y-2">
                  {agentProgress.map((item) => (
                    <div
                      key={item.agent}
                      className="flex items-center justify-between bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="text-[#111827] text-sm font-medium">{item.displayName}</p>
                        {item.title && <p className="text-[#9CA3AF] text-xs mt-1 truncate">{item.title}</p>}
                      </div>
                      <span
                        className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                          item.status === "completed"
                            ? "bg-[#ECFDF5] text-[#059669]"
                            : item.status === "running"
                            ? "bg-[#EFF6FF] text-[#2563EB]"
                            : "bg-[#FEF2F2] text-[#DC2626]"
                        }`}
                      >
                        {item.status === "completed" ? "完成" : item.status === "running" ? "分析中" : "异常"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2.5">
                  <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-full" />
                  <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-3/4" />
                  <div className="h-3 bg-[#F1F3F5] rounded-lg animate-pulse w-5/6" />
                </div>
              )}
            </section>
          )}

          {latestReport && (
            <section className="card p-6 animate-fade-up">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
                <div>
                  <h2 className="text-[#111827] text-sm font-semibold">报告文件</h2>
                  <p className="text-[#9CA3AF] text-xs mt-1">
                    {latestReport.review_status === "ai_draft" ? "AI 生成草稿" : latestReport.review_status}
                    {" · "}
                    {formatDate(latestReport.created_at)}
                  </p>
                </div>
              </div>
              <ReportDownloads report={latestReport} />
            </section>
          )}

          {reportMarkdown && (
            <section className="card p-6 animate-fade-up">
              <h2 className="text-[#111827] text-sm font-semibold mb-4">报告预览</h2>
              <MarkdownRenderer content={reportMarkdown} />
              <SearchReferences references={searchRefs} />
            </section>
          )}

          {!running && !reportMarkdown && !latestReport && (
            <section className="card p-10 text-center animate-fade-up">
              <p className="text-[#111827] text-sm font-semibold">尚未生成研究报告</p>
              <p className="text-[#9CA3AF] text-sm mt-2">选择报告风格和下载格式后，点击开始研究。</p>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
