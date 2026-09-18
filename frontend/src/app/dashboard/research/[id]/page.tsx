"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SearchReferences from "@/components/SearchReferences";
import {
  files as filesApi,
  reports as reportsApi,
  researchSubjects,
  type ActionRecommendation,
  type BusinessEventImpact,
  type BusinessEventImpactPreview,
  type FinancingNeed,
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

function financingNeedTypeLabel(value: string) {
  const labels: Record<string, string> = {
    working_capital: "经营周转",
    equipment: "设备投入",
    supply_chain: "供应链金融",
    overseas: "跨境经营",
    other: "其他需求",
  };
  return labels[value] || value;
}

function reviewStatusLabel(status: string) {
  if (status === "confirmed") return "已确认";
  if (status === "rejected") return "已驳回";
  return "待复核";
}

function reviewStatusClass(status: string) {
  if (status === "confirmed") return "bg-[#ECFDF5] text-[#059669]";
  if (status === "rejected") return "bg-[#FEF2F2] text-[#DC2626]";
  return "bg-[#FFF7ED] text-[#C2410C]";
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

function ActionRecommendationCard({
  recommendation,
  onReview,
}: {
  recommendation: ActionRecommendation;
  onReview: (recommendation: ActionRecommendation, status: "confirmed" | "rejected") => void;
}) {
  const statusLabel =
    recommendation.status === "confirmed"
      ? "已确认"
      : recommendation.status === "rejected"
      ? "已驳回"
      : "待复核";
  const statusClass =
    recommendation.status === "confirmed"
      ? "bg-[#ECFDF5] text-[#059669]"
      : recommendation.status === "rejected"
      ? "bg-[#FEF2F2] text-[#DC2626]"
      : "bg-[#FFF7ED] text-[#C2410C]";

  return (
    <div className="border border-[#E5E7EB] rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[#2563EB] text-[11px] font-semibold uppercase tracking-wide">
              {recommendation.action_type}
            </span>
            <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${statusClass}`}>
              {statusLabel}
            </span>
          </div>
          <h3 className="text-[#111827] text-sm font-semibold mt-2">{recommendation.title}</h3>
        </div>
        <span className="text-[#6B7280] text-xs shrink-0">风险 {recommendation.risk_level}</span>
      </div>
      <p className="text-[#4B5563] text-sm leading-relaxed mt-2">{recommendation.rationale}</p>
      <div className="flex flex-wrap items-center justify-between gap-2 mt-3">
        <span className="text-[#9CA3AF] text-xs">
          {recommendation.evidence_items.length > 0
            ? `已关联 ${recommendation.evidence_items.length} 条证据`
            : "暂无直接证据，需人工补充"}
        </span>
        {recommendation.status === "needs_review" && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="text-xs text-[#059669] border border-[#A7F3D0] rounded-md px-2.5 py-1.5 hover:bg-[#ECFDF5]"
              onClick={() => onReview(recommendation, "confirmed")}
            >
              确认动作
            </button>
            <button
              type="button"
              className="text-xs text-[#DC2626] border border-[#FECACA] rounded-md px-2.5 py-1.5 hover:bg-[#FEF2F2]"
              onClick={() => onReview(recommendation, "rejected")}
            >
              驳回
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function FinancingNeedCard({
  need,
  onReview,
}: {
  need: FinancingNeed;
  onReview: (need: FinancingNeed, status: "confirmed" | "rejected") => void;
}) {
  return (
    <div className="border border-[#E5E7EB] rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[#2563EB] text-[11px] font-semibold uppercase tracking-wide">
              {financingNeedTypeLabel(need.need_type)}
            </span>
            <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${reviewStatusClass(need.status)}`}>
              {reviewStatusLabel(need.status)}
            </span>
          </div>
          <h3 className="text-[#111827] text-sm font-semibold mt-2">{need.title}</h3>
        </div>
        <span className="text-[#6B7280] text-xs shrink-0">紧迫性 {need.urgency}</span>
      </div>
      <p className="text-[#4B5563] text-sm leading-relaxed mt-2">{need.description}</p>
      <div className="flex flex-wrap items-center justify-between gap-2 mt-3">
        <span className="text-[#9CA3AF] text-xs">
          {need.amount_text ? `金额：${need.amount_text}` : "金额待核验"}
          {need.evidence_items.length > 0 ? ` · 已关联 ${need.evidence_items.length} 条证据` : " · 暂无直接证据"}
        </span>
        {need.status === "needs_review" && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="text-xs text-[#059669] border border-[#A7F3D0] rounded-md px-2.5 py-1.5 hover:bg-[#ECFDF5]"
              onClick={() => onReview(need, "confirmed")}
            >
              确认需求
            </button>
            <button
              type="button"
              className="text-xs text-[#DC2626] border border-[#FECACA] rounded-md px-2.5 py-1.5 hover:bg-[#FEF2F2]"
              onClick={() => onReview(need, "rejected")}
            >
              驳回
            </button>
          </div>
        )}
      </div>
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
  const [uploading, setUploading] = useState(false);
  const [generatingAssets, setGeneratingAssets] = useState(false);
  const [eventTitle, setEventTitle] = useState("");
  const [eventDescription, setEventDescription] = useState("");
  const [impactPreview, setImpactPreview] = useState<BusinessEventImpactPreview | null>(null);
  const [impactHistory, setImpactHistory] = useState<BusinessEventImpact[]>([]);
  const [impactLoading, setImpactLoading] = useState(false);
  const [promotingImpact, setPromotingImpact] = useState(false);
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

  async function handleUpload(file: File) {
    setUploading(true);
    setError("");
    try {
      await filesApi.upload(file, null, id);
      setMessage("材料已上传并进入解析队列");
      loadPage();
    } catch (err: any) {
      setError(err.message || "材料上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleGenerateAssets() {
    setGeneratingAssets(true);
    setError("");
    try {
      const nextWorkspace = await researchSubjects.generateAssets(id);
      setWorkspace(nextWorkspace);
      setMessage("尽调资产已生成，请先复核行动建议");
    } catch (err: any) {
      setError(err.message || "尽调资产生成失败");
    } finally {
      setGeneratingAssets(false);
    }
  }

  async function handleCreateEvent(e: React.FormEvent) {
    e.preventDefault();
    if (!eventTitle.trim() || !eventDescription.trim()) return;
    try {
      await researchSubjects.createEvent(id, {
        title: eventTitle.trim(),
        description: eventDescription.trim(),
      });
      setEventTitle("");
      setEventDescription("");
      setMessage("企业事件已记录，下一步可用于影响分析");
      loadPage();
    } catch (err: any) {
      setError(err.message || "事件记录失败");
    }
  }

  async function handlePreviewImpact(eventId: string) {
    setImpactLoading(true);
    setError("");
    try {
      const preview = await researchSubjects.previewEventImpact(id, eventId);
      setImpactPreview(preview);
      setImpactHistory((current) => [preview, ...current.filter((item) => item.id !== preview.id)]);
    } catch (err: any) {
      setError(err.message || "事件影响分析失败");
    } finally {
      setImpactLoading(false);
    }
  }

  async function handleLoadImpactHistory(eventId: string) {
    setImpactLoading(true);
    setError("");
    try {
      const history = await researchSubjects.listEventImpactPreviews(id, eventId);
      setImpactHistory(history);
      setImpactPreview(history[0] || null);
      setMessage(history.length > 0 ? `已加载 ${history.length} 条影响分析记录` : "该事件暂无影响分析记录");
    } catch (err: any) {
      setError(err.message || "影响分析历史加载失败");
    } finally {
      setImpactLoading(false);
    }
  }

  async function handlePromoteImpactActions() {
    if (!impactPreview || impactPreview.proposed_actions.length === 0) return;
    setPromotingImpact(true);
    setError("");
    try {
      const created = await Promise.all(
        impactPreview.proposed_actions.map((action) =>
          researchSubjects.createActionRecommendation(id, {
            ...action,
            status: "needs_review",
          }),
        ),
      );
      setWorkspace((current) =>
        current
          ? { ...current, action_recommendations: [...created, ...current.action_recommendations] }
          : current,
      );
      setImpactPreview(null);
      setMessage("事件影响已转为待复核行动建议");
    } catch (err: any) {
      setError(err.message || "转为行动建议失败");
    } finally {
      setPromotingImpact(false);
    }
  }

  async function handleReviewAction(
    recommendation: ActionRecommendation,
    status: "confirmed" | "rejected",
  ) {
    const reviewNote = status === "rejected" ? window.prompt("请填写驳回原因") : null;
    if (status === "rejected" && !reviewNote?.trim()) return;
    try {
      const updated = await researchSubjects.reviewActionRecommendation(id, recommendation.id, {
        status,
        review_note: reviewNote,
      });
      setWorkspace((current) =>
        current
          ? {
              ...current,
              action_recommendations: current.action_recommendations.map((item) =>
                item.id === updated.id ? updated : item,
              ),
            }
          : current,
      );
      setMessage(status === "confirmed" ? "行动建议已确认" : "行动建议已驳回");
    } catch (err: any) {
      setError(err.message || "复核失败");
    }
  }

  async function handleReviewFinancingNeed(
    need: FinancingNeed,
    status: "confirmed" | "rejected",
  ) {
    const reviewNote = status === "rejected" ? window.prompt("请填写驳回原因") : null;
    if (status === "rejected" && !reviewNote?.trim()) return;
    try {
      const updated = await researchSubjects.reviewFinancingNeed(id, need.id, {
        status,
        review_note: reviewNote,
      });
      setWorkspace((current) =>
        current
          ? {
              ...current,
              financing_needs: current.financing_needs.map((item) =>
                item.id === updated.id ? updated : item,
              ),
            }
          : current,
      );
      setMessage(status === "confirmed" ? "融资需求已确认" : "融资需求已驳回");
    } catch (err: any) {
      setError(err.message || "融资需求复核失败");
    }
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
            <p className="text-[#9CA3AF] text-xs mb-2 tracking-widest uppercase">Enterprise Finance Due Diligence</p>
            <h1 className="text-[#111827] text-2xl font-semibold tracking-tight">{subject.company_name}</h1>
            <p className="text-[#6B7280] text-sm mt-2 max-w-3xl">
              从企业材料与业务变化出发，形成可追溯的风险判断和金融行动建议；报告只是最后的导出物。
            </p>
          </div>
          <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-4 py-3 shrink-0">
            <p className="text-[#9CA3AF] text-[11px]">报告版本</p>
            <p className="text-[#111827] text-lg font-semibold mt-1">{reports.length}</p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)] gap-6 mb-6">
        <div className="card p-6 animate-fade-up">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-5">
            <div>
              <p className="text-[#2563EB] text-xs font-semibold tracking-widest uppercase">Decision Workspace</p>
              <h2 className="text-[#111827] text-lg font-semibold mt-2">企业金融尽调闭环</h2>
              <p className="text-[#6B7280] text-sm mt-1">材料 → 事实判断 → 金融动作 → 人工复核</p>
            </div>
            <label className="btn-secondary text-sm cursor-pointer text-center">
              {uploading ? "上传中..." : "上传 PDF 材料"}
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                disabled={uploading || generatingAssets}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleUpload(file);
                  e.currentTarget.value = "";
                }}
              />
            </label>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              className="btn-primary text-sm h-[42px] px-4"
              onClick={handleGenerateAssets}
              disabled={generatingAssets || uploading}
            >
              {generatingAssets ? "智能体分析中..." : "生成尽调资产"}
            </button>
            <div className="text-xs text-[#9CA3AF] self-center">
              已沉淀证据 {workspace.evidence_count} 条 · 融资需求 {workspace.financing_needs.length} 条 · 行动建议 {workspace.action_recommendations.length} 条
            </div>
          </div>

          {workspace.financing_needs.length > 0 && (
            <div className="mt-6 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-[#111827] text-sm font-semibold">融资需求</h3>
                <span className="text-[#9CA3AF] text-xs">金额与需求均需人工核验</span>
              </div>
              {workspace.financing_needs.map((need) => (
                <FinancingNeedCard
                  key={need.id}
                  need={need}
                  onReview={handleReviewFinancingNeed}
                />
              ))}
            </div>
          )}

          {workspace.action_recommendations.length > 0 ? (
            <div className="mt-6 space-y-3">
              {workspace.action_recommendations.map((recommendation) => (
                <ActionRecommendationCard
                  key={recommendation.id}
                  recommendation={recommendation}
                  onReview={handleReviewAction}
                />
              ))}
            </div>
          ) : (
            <div className="mt-6 rounded-lg border border-dashed border-[#D1D5DB] px-4 py-5 text-sm text-[#6B7280]">
              上传年报、合同、订单或经营材料后，智能体会把研究结论转换成银行下一步可执行动作。
            </div>
          )}
        </div>

        <div className="card p-6 animate-fade-up">
          <p className="text-[#2563EB] text-xs font-semibold tracking-widest uppercase">Business Events</p>
          <h2 className="text-[#111827] text-lg font-semibold mt-2">记录企业变化</h2>
          <p className="text-[#6B7280] text-sm mt-1">把订单、回款、客户或经营变化作为未来影响分析的触发器。</p>
          <form className="space-y-3 mt-5" onSubmit={handleCreateEvent}>
            <input
              className="input-field"
              value={eventTitle}
              onChange={(e) => setEventTitle(e.target.value)}
              placeholder="例如：核心客户订单下降 30%"
            />
            <textarea
              className="input-field min-h-[92px] resize-y"
              value={eventDescription}
              onChange={(e) => setEventDescription(e.target.value)}
              placeholder="描述事件、来源和已知影响"
            />
            <button
              type="submit"
              className="btn-secondary w-full text-sm h-[42px]"
              disabled={!eventTitle.trim() || !eventDescription.trim()}
            >
              记录企业事件
            </button>
          </form>
          {workspace.business_events.length > 0 && (
            <div className="mt-5 pt-5 border-t border-[#E5E7EB] space-y-3">
              {workspace.business_events.slice(0, 3).map((event) => (
                <div key={event.id} className="border-l-2 border-[#F59E0B] pl-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[#111827] text-sm font-medium">{event.title}</p>
                    <button
                      type="button"
                      className="text-[#2563EB] text-xs whitespace-nowrap hover:underline"
                      disabled={impactLoading}
                      onClick={() => void handlePreviewImpact(event.id)}
                    >
                      {impactLoading ? "分析中" : "分析影响"}
                    </button>
                    <button
                      type="button"
                      className="text-[#6B7280] text-xs whitespace-nowrap hover:underline"
                      disabled={impactLoading}
                      onClick={() => void handleLoadImpactHistory(event.id)}
                    >
                      历史记录
                    </button>
                  </div>
                  <p className="text-[#6B7280] text-xs leading-relaxed mt-1">{event.description}</p>
                </div>
              ))}
            </div>
          )}
      {impactPreview && (
            <div className="mt-5 pt-5 border-t border-[#E5E7EB]">
              <p className="text-[#111827] text-sm font-semibold">事件影响预览</p>
              <p className="text-[#9CA3AF] text-xs mt-1">
                本次分析已保存 · 历史记录 {impactHistory.length} 条
              </p>
              <p className="text-[#4B5563] text-sm leading-relaxed mt-2">{impactPreview.impact_summary}</p>
              <div className="flex flex-wrap gap-2 mt-3 text-xs">
                <span className="badge-neutral">受影响判断 {impactPreview.affected_claim_ids.length}</span>
                <span className="badge-neutral">受影响建议 {impactPreview.affected_recommendation_ids.length}</span>
                <span className="text-xs px-2 py-1 rounded-full bg-[#FFF7ED] text-[#C2410C]">待人工复核</span>
              </div>
              {impactPreview.evidence_gaps.length > 0 && (
                <div className="mt-3 rounded-md bg-[#FFF7ED] px-3 py-2 text-xs text-[#9A3412]">
                  证据缺口：{impactPreview.evidence_gaps.join("；")}
                </div>
              )}
              {impactPreview.proposed_actions.length > 0 && (
                <div className="mt-3">
                  <p className="text-[#6B7280] text-xs mb-2">建议新增动作</p>
                  <div className="space-y-2">
                    {impactPreview.proposed_actions.map((action, index) => (
                      <div key={`${action.title}-${index}`} className="bg-[#F8F9FB] rounded-md px-3 py-2">
                        <p className="text-[#111827] text-xs font-medium">{action.title}</p>
                        <p className="text-[#6B7280] text-xs mt-1">{action.rationale}</p>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="btn-secondary w-full text-xs h-[38px] mt-3"
                    disabled={promotingImpact}
                    onClick={() => void handlePromoteImpactActions()}
                  >
                    {promotingImpact ? "转化中..." : "转为待复核行动建议"}
                  </button>
                </div>
              )}
            </div>
          )}
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
