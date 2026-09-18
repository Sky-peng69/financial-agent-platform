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
  if (!value) return "";
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
        ticker: null,
        industry: null,
        current_view: null,
        confidence_level: null,
        evidence_strength: null,
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
        <p className="text-[#9CA3AF] text-xs mb-2 tracking-widest uppercase">Enterprise Finance</p>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <h1 className="text-[#111827] text-2xl font-semibold tracking-tight">企业金融尽调</h1>
            <p className="text-[#6B7280] text-sm mt-2">围绕企业事实、风险判断、经营事件和可执行金融动作形成闭环。</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-[#6B7280]">
            <span className="badge-neutral">研究对象 {subjects.length}</span>
            <span className="badge-info">决策工作台</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-5">
          {error}
        </div>
      )}

      <div className="space-y-5">
        <section className="card p-5 animate-fade-up stagger-1">
          <h2 className="text-[#111827] text-sm font-semibold mb-4">新建企业尽调档案</h2>
          <form className="flex flex-col sm:flex-row gap-3" onSubmit={handleCreate}>
            <div className="flex-1">
              <label className="label">公司名称</label>
              <input
                className="input-field"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                placeholder="例如：某汽车零部件供应商"
              />
            </div>
            <button
              className="btn-primary w-full sm:w-auto sm:self-end text-sm h-[44px] px-5"
              disabled={saving || !form.company_name.trim()}
            >
              {saving ? "创建中..." : "开始企业尽调"}
            </button>
          </form>
        </section>

        <section className="space-y-3 animate-fade-up stagger-2">
          {subjects.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-[#111827] text-sm font-semibold">暂无企业尽调档案</p>
              <p className="text-[#9CA3AF] text-sm mt-2">先创建一个企业档案，再上传材料和记录经营事件。</p>
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
                  <div className="flex flex-wrap md:justify-end gap-2 shrink-0">
                    {subject.confidence_level && (
                      <span className="badge-neutral">置信度 {confidenceLabel(subject.confidence_level)}</span>
                    )}
                    {subject.evidence_strength && (
                      <span className="badge-neutral">证据 {confidenceLabel(subject.evidence_strength)}</span>
                    )}
                    <span className="text-[#9CA3AF] text-xs leading-7">
                      更新 {formatDate(subject.updated_at)}
                    </span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </section>
      </div>
    </div>
  );
}
