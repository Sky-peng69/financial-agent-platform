"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { agents as agentsApi, type Agent, type Task } from "@/lib/api";

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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
    setResult(null);
    try {
      const task = await agentsApi.run(name, {
        agent_name: name,
        title: title.trim(),
        input_data: inputData.trim(),
      });
      setResult(task);
    } catch (err: any) {
      setError(err.message || "运行失败");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  if (!agent) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs mb-6">
        <Link href="/dashboard/agents" className="text-[#5A6577] hover:text-[#C9A94E] transition-colors">
          Agent 市场
        </Link>
        <span className="text-[#1E2A3E]">/</span>
        <span className="text-[#C9A94E]">{agent.display_name}</span>
      </div>

      {/* Agent info */}
      <div className="card p-6 mb-8">
        <div className="flex items-start justify-between mb-2">
          <h1 className="text-[#E8EDF5] text-xl font-semibold">{agent.display_name}</h1>
          <span className="text-[#5A6577] text-xs px-2 py-0.5 rounded border border-[#1E2A3E]">
            {CATEGORIES[agent.category] || agent.category}
          </span>
        </div>
        <p className="text-[#8B95A5] text-sm mb-3">{agent.description}</p>
        <div className="flex items-center gap-1.5">
          {agent.tools.map((t) => (
            <span key={t} className="text-[#5A6577] text-[10px] px-1.5 py-0.5 rounded bg-[#0A0F18] border border-[#1E2A3E]">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Input form */}
      <div className="card p-6 mb-8">
        <h2 className="text-[#E8EDF5] text-sm font-semibold mb-4">任务配置</h2>

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
          <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-4 py-3 rounded-sm mb-4">
            {error}
          </div>
        )}

        <button className="btn-primary w-full sm:w-auto" onClick={handleRun} disabled={busy}>
          {busy ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-[#080C14]/30 border-t-[#080C14] rounded-full animate-spin" />
              AI 分析中...
            </span>
          ) : (
            "开始分析"
          )}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="card p-6 animate-fade-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[#E8EDF5] text-sm font-semibold">分析结果</h2>
            <span
              className={`text-xs px-2 py-0.5 rounded-sm ${
                result.status === "completed"
                  ? "bg-[#1A3D2A] text-[#34A584]"
                  : result.status === "failed"
                  ? "bg-[#3D1A1A] text-[#D95A4A]"
                  : "bg-[#1E2A3E] text-[#8B95A5]"
              }`}
            >
              {result.status === "completed" ? "✓ 完成" : result.status === "failed" ? "✗ 失败" : result.status}
            </span>
          </div>

          {result.error_message && (
            <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-4 py-3 rounded-sm mb-4">
              {result.error_message}
            </div>
          )}

          {result.output_data && (
            <div className="markdown-content">
              <ReactMarkdown>{result.output_data}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
