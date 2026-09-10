"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { agents as agentsApi, type Agent } from "@/lib/api";

const CATEGORIES: Record<string, string> = {
  "wealth-management": "财富管理",
  research: "研究分析",
  "investment-banking": "投资银行",
  "fund-admin": "基金运营",
  operations: "运营管理",
  modeling: "建模工具",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [category, setCategory] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    agentsApi
      .list(category || undefined)
      .then(setAgents)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [category]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 animate-fade-up">
      <div className="mb-8">
        <p className="text-[#9CA3AF] text-xs mb-1 tracking-widest uppercase">Agent Marketplace</p>
        <h1 className="text-[#111827] text-2xl font-semibold mb-2">Agent 市场</h1>
        <p className="text-[#6B7280] text-sm">选择一个 Agent，输入任务描述，AI 将自动完成分析</p>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-8 flex-wrap">
        <button
          onClick={() => setCategory("")}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-all duration-200 font-medium ${
            !category
              ? "bg-[#2563EB] text-white border-[#2563EB]"
              : "bg-white border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:bg-[#F8F9FB]"
          }`}
        >
          全部
        </button>
        {Object.entries(CATEGORIES).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setCategory(key)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all duration-200 font-medium ${
              category === key
                ? "bg-[#2563EB] text-white border-[#2563EB]"
                : "bg-white border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:bg-[#F8F9FB]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Agent grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map((agent, i) => (
          <Link
            key={agent.name}
            href={`/dashboard/agents/${agent.name}`}
            className={`card-hover p-6 block animate-fade-up stagger-${(i % 6) + 1}`}
          >
            <div className="flex items-start justify-between mb-3">
              <h2 className="text-[#111827] text-base font-semibold">{agent.display_name}</h2>
              <span className="text-[#6B7280] text-[11px] px-2 py-0.5 rounded-full bg-[#F1F3F5] whitespace-nowrap ml-2">
                {CATEGORIES[agent.category] || agent.category}
              </span>
            </div>
            <p className="text-[#6B7280] text-sm leading-relaxed mb-4">
              {agent.description}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {agent.tools.map((t) => (
                  <span key={t} className="text-[#6B7280] text-[10px] px-1.5 py-0.5 rounded-full bg-[#F1F3F5]">
                    {t}
                  </span>
                ))}
              </div>
              <span className="text-[#2563EB] text-xs font-medium">运行 →</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
