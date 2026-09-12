"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { researchSubjects, type ResearchSubject } from "@/lib/api";

const CONFIDENCE_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

function confidenceLabel(value: string | null) {
  if (!value) return "未定";
  return CONFIDENCE_LABELS[value] || value;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("zh-CN");
}

export default function ResearchSubjectsPage() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<ResearchSubject[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    company_name: "",
    ticker: "",
    industry: "",
    current_view: "",
    confidence_level: "medium",
    evidence_strength: "medium",
  });

  function loadSubjects() {
    setLoading(true);
    setError("");
    researchSubjects
      .list()
      .then(setSubjects)
      .catch((err: any) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadSubjects();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setSaving(true);
    setError("");
    try {
      const subject = await researchSubjects.create({
        company_name: form.company_name.trim(),
        ticker: form.ticker.trim() || null,
        industry: form.industry.trim() || null,
        current_view: form.current_view.trim() || null,
        confidence_level: form.confidence_level,
        evidence_strength: form.evidence_strength,
      });
      router.push(`/dashboard/research/${subject.id}`);
    } catch (err: any) {
      setError(err.message || "创建失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8 animate-fade-up">
        <p className="text-[#9CA3AF] text-xs mb-2 tracking-widest uppercase">Research</p>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <h1 className="text-[#111827] text-2xl font-semibold tracking-tight">公司研究</h1>
            <p className="text-[#6B7280] text-sm mt-2">围绕公司沉淀判断、假设、证据和反方挑战。</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-[#6B7280]">
            <span className="badge-neutral">研究对象 {subjects.length}</span>
            <span className="badge-info">判断工作台</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-5">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-6 items-start">
        <section className="space-y-3 animate-fade-up stagger-1">
          {subjects.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-[#111827] text-sm font-semibold">暂无公司研究对象</p>
              <p className="text-[#9CA3AF] text-sm mt-2">先创建一个公司研究档案。</p>
            </div>
          ) : (
            subjects.map((subject) => (
              <Link
                key={subject.id}
                href={`/dashboard/research/${subject.id}`}
                className="card-hover block p-5"
              >
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-[#111827] text-base font-semibold">{subject.company_name}</h2>
                      {subject.ticker && (
                        <span className="text-[#2563EB] text-xs font-mono bg-[#EFF6FF] px-2 py-1 rounded-md">
                          {subject.ticker}
                        </span>
                      )}
                      {subject.industry && (
                        <span className="text-[#6B7280] text-xs bg-[#F1F3F5] px-2 py-1 rounded-md">
                          {subject.industry}
                        </span>
                      )}
                    </div>
                    <p className="text-[#374151] text-sm leading-relaxed mt-3 line-clamp-2">
                      {subject.current_view || "尚未形成当前判断"}
                    </p>
                  </div>
                  <div className="grid grid-cols-3 gap-2 md:w-[230px] shrink-0">
                    <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
                      <p className="text-[#9CA3AF] text-[11px]">置信度</p>
                      <p className="text-[#111827] text-sm font-semibold mt-1">
                        {confidenceLabel(subject.confidence_level)}
                      </p>
                    </div>
                    <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
                      <p className="text-[#9CA3AF] text-[11px]">证据</p>
                      <p className="text-[#111827] text-sm font-semibold mt-1">
                        {confidenceLabel(subject.evidence_strength)}
                      </p>
                    </div>
                    <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
                      <p className="text-[#9CA3AF] text-[11px]">更新</p>
                      <p className="text-[#111827] text-sm font-semibold mt-1">
                        {formatDate(subject.updated_at)}
                      </p>
                    </div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </section>

        <aside className="card p-5 animate-fade-up stagger-2">
          <h2 className="text-[#111827] text-sm font-semibold mb-4">新建研究对象</h2>
          <form className="space-y-4" onSubmit={handleCreate}>
            <div>
              <label className="label">公司名称</label>
              <input
                className="input-field"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                placeholder="例如：宁德时代"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">股票代码</label>
                <input
                  className="input-field"
                  value={form.ticker}
                  onChange={(e) => setForm({ ...form, ticker: e.target.value })}
                  placeholder="300750.SZ"
                />
              </div>
              <div>
                <label className="label">行业</label>
                <input
                  className="input-field"
                  value={form.industry}
                  onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  placeholder="电力设备"
                />
              </div>
            </div>
            <div>
              <label className="label">当前判断</label>
              <textarea
                className="input-field min-h-[96px] resize-none"
                value={form.current_view}
                onChange={(e) => setForm({ ...form, current_view: e.target.value })}
                placeholder="例如：中性偏积极，等待储能回款质量进一步验证"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">置信度</label>
                <select
                  className="input-field"
                  value={form.confidence_level}
                  onChange={(e) => setForm({ ...form, confidence_level: e.target.value })}
                >
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
              </div>
              <div>
                <label className="label">证据强度</label>
                <select
                  className="input-field"
                  value={form.evidence_strength}
                  onChange={(e) => setForm({ ...form, evidence_strength: e.target.value })}
                >
                  <option value="high">强</option>
                  <option value="medium">中</option>
                  <option value="low">弱</option>
                </select>
              </div>
            </div>
            <button
              className="btn-primary w-full text-sm"
              disabled={saving || !form.company_name.trim()}
            >
              {saving ? "创建中..." : "创建研究对象"}
            </button>
          </form>
        </aside>
      </div>
    </div>
  );
}
