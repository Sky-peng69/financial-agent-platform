"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import SearchReferences from "@/components/SearchReferences";
import { agents as agentsApi, type Agent, type Task, type SearchReference } from "@/lib/api";

const CATEGORIES: Record<string, string> = {
  "wealth-management": "财富管理",
  research: "研究分析",
  "investment-banking": "投资银行",
  "fund-admin": "基金运营",
  operations: "运营管理",
  modeling: "建模工具",
};

// 每个 Agent 专属的 placeholder 示例
const AGENT_PLACEHOLDERS: Record<string, { title: string; description: string }> = {
  "macro-economy-analyst": {
    title: "例如：分析当前宏观经济形势及对A股的影响",
    description:
      "输入更多上下文：关注指标（PMI/CPI/M2）、政策方向（货币/财政）、时间范围...",
  },
  "industry-analyst": {
    title: "例如：白酒行业竞争格局与关键趋势分析",
    description:
      "输入更多上下文：目标行业、关注维度（价值链/集中度/龙头对标）、政策影响...",
  },
  "fundamental-analyst": {
    title: "例如：对茅台(600519)进行财务分析和估值",
    description:
      "输入更多上下文：目标公司、关注指标（ROE/毛利率/现金流）、估值方法偏好...",
  },
  "news-sentiment-analyst": {
    title: "例如：近期降准政策对银行板块的影响评估",
    description:
      "输入更多上下文：关注事件类型（政策/财报/行业）、时间范围、情绪侧重...",
  },
  "wealth-advisor": {
    title: "例如：35岁互联网从业者的资产配置方案",
    description:
      "输入更多上下文：年龄、收入、资产负债、风险偏好（保守/平衡/进取）、理财目标...",
  },
  "report-synthesizer": {
    title: "例如：汇总各专家分析，生成贵州茅台综合投资报告",
    description:
      "输入更多上下文：涉及的标的、已完成的各项分析结果、报告侧重点...",
  },
};

// 默认 placeholder
const DEFAULT_PLACEHOLDER = {
  title: "例如：描述你的分析需求...",
  description: "输入更多上下文：分析对象、关注维度、期望输出格式...",
};

export default function AgentRunPage({ params }: { params: { name: string } }) {
  const { name } = params;
  const router = useRouter();

  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [inputData, setInputData] = useState("");
  const [result, setResult] = useState<Task | null>(null);
  const [searchRefs, setSearchRefs] = useState<SearchReference[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const controllerRef = useRef<AbortController | null>(null);
  const [copied, setCopied] = useState(false);

  // 组件卸载时中止进行中的流式请求
  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    agentsApi
      .get(name)
      .then(setAgent)
      .catch(() => router.push("/dashboard/agents"))
      .finally(() => setLoading(false));
  }, [name, router]);

  async function handleRun() {
    if (!title.trim()) {
      setError("请输入任务标题");
      return;
    }
    setError("");
    setBusy(true);
    setStreaming(true);
    setStreamText("");
    setResult(null);
    setSearchRefs(null);

    // 用 local var 累积完整文本，避免闭包捕获旧的 streamText
    let fullText = "";

    const controller = agentsApi.runStream(
      name,
      { agent_name: name, title: title.trim(), input_data: inputData.trim() },
      // onChunk
      (text) => {
        fullText += text;
        setStreamText(fullText);
      },
      // onDone
      (taskId, searchRefs) => {
        setBusy(false);
        setStreaming(false);
        setSearchRefs(searchRefs);
        setResult({
          id: taskId,
          agent_name: name,
          title: title.trim(),
          status: "completed" as const,
          input_data: inputData.trim(),
          output_data: fullText,
          search_references: null,
          error_message: null,
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        });
      },
      // onError
      (err) => {
        setError(err.message || "运行失败");
        setBusy(false);
        setStreaming(false);
      },
    );
    controllerRef.current = controller;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  if (!agent) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs mb-6">
        <Link href="/dashboard/agents" className="text-[#9CA3AF] hover:text-[#2563EB] transition-colors">
          Agent 市场
        </Link>
        <span className="text-[#D1D5DB]">/</span>
        <span className="text-[#2563EB] font-medium">{agent.display_name}</span>
      </div>

      {/* Agent info */}
      <div className="card p-6 mb-8">
        <div className="flex items-start justify-between mb-2">
          <h1 className="text-[#111827] text-xl font-semibold">{agent.display_name}</h1>
          <span className="text-[#6B7280] text-xs px-2.5 py-1 rounded-full bg-[#F1F3F5] font-medium">
            {CATEGORIES[agent.category] || agent.category}
          </span>
        </div>
        <p className="text-[#6B7280] text-sm mb-3">{agent.description}</p>
        <div className="flex items-center gap-1.5">
          {agent.tools.map((t) => (
            <span key={t} className="text-[#6B7280] text-[10px] px-1.5 py-0.5 rounded-full bg-[#F1F3F5]">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Input form */}
      <div className="card p-6 mb-8">
        <h2 className="text-[#111827] text-sm font-semibold mb-4">任务配置</h2>

        <div className="mb-4">
          <label className="label">任务标题 *</label>
          <input
            className="input-field"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={
              (AGENT_PLACEHOLDERS[name] || DEFAULT_PLACEHOLDER).title
            }
          />
        </div>

        <div className="mb-4">
          <label className="label">详细描述（可选）</label>
          <textarea
            className="input-field min-h-[120px]"
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            placeholder={
              (AGENT_PLACEHOLDERS[name] || DEFAULT_PLACEHOLDER).description
            }
          />
        </div>

        {error && (
          <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <button className="btn-primary w-full sm:w-auto" onClick={handleRun} disabled={busy}>
          {busy ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              AI 分析中...
            </span>
          ) : (
            "开始分析"
          )}
        </button>
      </div>

      {/* 流式输出区（边跑边写） */}
      {streaming && (
        <div className="card p-6 mb-8 animate-fade-up">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-[#2563EB] animate-pulse-accent" />
            <span className="text-[#2563EB] text-sm font-medium">AI 分析中...</span>
            <button
              onClick={() => {
                controllerRef.current?.abort();
                setBusy(false);
                setStreaming(false);
              }}
              className="ml-auto text-[#9CA3AF] text-xs hover:text-[#DC2626] transition-colors"
            >
              停止生成
            </button>
          </div>
          {streamText ? (
            <MarkdownRenderer content={streamText} />
          ) : (
            <div className="flex items-center gap-2 text-[#9CA3AF] text-sm">
              <span className="w-4 h-4 border-2 border-[#9CA3AF]/30 border-t-[#2563EB] rounded-full animate-spin" />
              正在连接 AI...
            </div>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="card p-6 animate-fade-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[#111827] text-sm font-semibold">分析结果</h2>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                result.status === "completed"
                  ? "bg-[#ECFDF5] text-[#059669]"
                  : result.status === "failed"
                  ? "bg-[#FEF2F2] text-[#DC2626]"
                  : "bg-[#F1F3F5] text-[#6B7280]"
              }`}
            >
              {result.status === "completed" ? "✓ 完成" : result.status === "failed" ? "✗ 失败" : result.status}
            </span>
          </div>

          {result.error_message && (
            <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-4">
              {result.error_message}
            </div>
          )}

          {result.output_data && (
            <>
              <MarkdownRenderer content={result.output_data} />

              {/* 搜索引用 */}
              <SearchReferences references={searchRefs || []} />

              {/* 操作按钮：复制 + 导出 PDF + 重新生成 */}
              <div className="flex items-center gap-2 mt-6 pt-4 border-t border-[#E5E7EB]">
                <button
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(result.output_data || "");
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    } catch {
                      // 降级方案：选中文本
                      const sel = window.getSelection();
                      const range = document.createRange();
                      const el = document.getElementById("result-content");
                      if (el && sel) {
                        range.selectNodeContents(el);
                        sel.removeAllRanges();
                        sel.addRange(range);
                      }
                    }
                  }}
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
                      复制
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
                <button
                  onClick={handleRun}
                  className="flex items-center gap-1.5 text-xs text-[#6B7280] hover:text-[#2563EB] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#F1F3F5]"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                  重新生成
                </button>
                <Link
                  href={`/dashboard/tasks/${result.id}`}
                  className="ml-auto text-xs text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
                >
                  查看任务详情 →
                </Link>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
