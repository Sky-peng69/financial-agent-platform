"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  files as filesApi,
  researchSubjects,
  type EvidenceSnippet,
  type ResearchAssumption,
  type ResearchClaim,
  type ResearchSubjectWorkspace,
} from "@/lib/api";

const LEVEL_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const DIRECTION_LABELS: Record<string, string> = {
  positive: "正面",
  neutral: "中性",
  negative: "负面",
};

const VERIFICATION_LABELS: Record<string, string> = {
  cited: "已引用",
  needs_review: "待核验",
  insufficient: "证据不足",
};

const ASSET_STATUS_LABELS: Record<string, string> = {
  active: "待复核",
  needs_review: "待复核",
  confirmed: "已确认",
  rejected: "已驳回",
};

type AssetKind = "claim" | "assumption";

function levelLabel(value: string | null | undefined) {
  if (!value) return "未定";
  return LEVEL_LABELS[value] || value;
}

function directionLabel(value: string) {
  return DIRECTION_LABELS[value] || value;
}

function verificationLabel(value: string) {
  return VERIFICATION_LABELS[value] || value;
}

function assetStatusLabel(value: string) {
  return ASSET_STATUS_LABELS[value] || value;
}

function assetStatusClass(value: string) {
  if (value === "confirmed") return "badge-success";
  if (value === "rejected") return "badge-error";
  return "badge-neutral";
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN");
}

function EmptyLine({ text }: { text: string }) {
  return (
    <div className="border border-dashed border-[#D1D5DB] rounded-lg px-4 py-5 text-center">
      <p className="text-[#9CA3AF] text-sm">{text}</p>
    </div>
  );
}

function EvidenceDetails({
  evidenceItems,
  verificationStatus,
}: {
  evidenceItems: EvidenceSnippet[];
  verificationStatus: string;
}) {
  if (evidenceItems.length === 0) {
    return (
      <p className="text-[#9CA3AF] text-xs mt-2">
        {verificationLabel(verificationStatus)}
      </p>
    );
  }

  return (
    <details className="mt-3 border-t border-[#F1F3F5] pt-3 group">
      <summary className="cursor-pointer list-none text-[#2563EB] text-xs font-medium">
        {verificationLabel(verificationStatus)} · 查看证据 {evidenceItems.length}
      </summary>
      <div className="space-y-2 mt-3">
        {evidenceItems.map((item) => (
          <div key={item.id} className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
            <div className="flex items-center justify-between gap-3 mb-1">
              <span className="text-[#111827] text-xs font-medium">{item.location_label}</span>
              {item.page_number && (
                <span className="text-[#9CA3AF] text-[11px]">第 {item.page_number} 页</span>
              )}
            </div>
            <p className="text-[#6B7280] text-xs leading-relaxed line-clamp-4">{item.text}</p>
          </div>
        ))}
      </div>
    </details>
  );
}

export default function ResearchSubjectWorkspacePage({ params }: { params: { id: string } }) {
  const { id } = params;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [workspace, setWorkspace] = useState<ResearchSubjectWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [editingAsset, setEditingAsset] = useState<{ kind: AssetKind; id: string; content: string } | null>(null);
  const [rejectingAsset, setRejectingAsset] = useState<{ kind: AssetKind; id: string; note: string } | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [claimForm, setClaimForm] = useState({
    content: "",
    direction: "neutral",
    confidence_level: "medium",
    evidence_strength: "medium",
  });
  const [assumptionForm, setAssumptionForm] = useState({
    content: "",
    category: "business",
    confidence_level: "medium",
  });
  const [challengeForm, setChallengeForm] = useState({
    question: "",
    risk_level: "medium",
    suggested_action: "",
  });
  const [memoForm, setMemoForm] = useState({
    current_conclusion: "",
    key_basis: "",
    biggest_uncertainty: "",
    suggested_action: "",
  });

  function loadWorkspace() {
    setLoading(true);
    setError("");
    researchSubjects
      .workspace(id)
      .then(setWorkspace)
      .catch((err: any) => setError(err.message || "加载失败"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadWorkspace();
  }, [id]);

  async function submitClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!claimForm.content.trim()) return;
    setSaving("claim");
    setError("");
    try {
      await researchSubjects.createClaim(id, claimForm);
      setClaimForm({ content: "", direction: "neutral", confidence_level: "medium", evidence_strength: "medium" });
      await researchSubjects.workspace(id).then(setWorkspace);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving("");
    }
  }

  async function submitAssumption(e: React.FormEvent) {
    e.preventDefault();
    if (!assumptionForm.content.trim()) return;
    setSaving("assumption");
    setError("");
    try {
      await researchSubjects.createAssumption(id, assumptionForm);
      setAssumptionForm({ content: "", category: "business", confidence_level: "medium" });
      await researchSubjects.workspace(id).then(setWorkspace);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving("");
    }
  }

  async function submitChallenge(e: React.FormEvent) {
    e.preventDefault();
    if (!challengeForm.question.trim()) return;
    setSaving("challenge");
    setError("");
    try {
      await researchSubjects.createChallenge(id, {
        question: challengeForm.question,
        risk_level: challengeForm.risk_level,
        suggested_action: challengeForm.suggested_action.trim() || null,
      });
      setChallengeForm({ question: "", risk_level: "medium", suggested_action: "" });
      await researchSubjects.workspace(id).then(setWorkspace);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving("");
    }
  }

  async function submitMemo(e: React.FormEvent) {
    e.preventDefault();
    if (!memoForm.current_conclusion.trim()) return;
    setSaving("memo");
    setError("");
    try {
      await researchSubjects.createDecisionMemo(id, {
        current_conclusion: memoForm.current_conclusion,
        key_basis: memoForm.key_basis.trim() || null,
        biggest_uncertainty: memoForm.biggest_uncertainty.trim() || null,
        suggested_action: memoForm.suggested_action.trim() || null,
      });
      setMemoForm({ current_conclusion: "", key_basis: "", biggest_uncertainty: "", suggested_action: "" });
      await researchSubjects.workspace(id).then(setWorkspace);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving("");
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      await filesApi.upload(file, null, id);
      setMessage("材料已归档到当前研究对象");
      await researchSubjects.workspace(id).then(setWorkspace);
    } catch (err: any) {
      setError(err.message || "上传失败");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleGenerateAssets() {
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      const updated = await researchSubjects.generateAssets(id);
      setWorkspace(updated);
      setMessage("已生成判断资产");
    } catch (err: any) {
      setError(err.message || "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function assetKey(kind: AssetKind, assetId: string) {
    return `${kind}:${assetId}`;
  }

  async function updateAsset(
    kind: AssetKind,
    assetId: string,
    data: { content?: string; status?: string; review_note?: string | null },
    successMessage: string,
  ) {
    setSaving(assetKey(kind, assetId));
    setError("");
    setMessage("");
    try {
      if (kind === "claim") {
        await researchSubjects.updateClaim(id, assetId, data);
      } else {
        await researchSubjects.updateAssumption(id, assetId, data);
      }
      const updated = await researchSubjects.workspace(id);
      setWorkspace(updated);
      setEditingAsset(null);
      setRejectingAsset(null);
      setMessage(successMessage);
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving("");
    }
  }

  function startEdit(kind: AssetKind, asset: ResearchClaim | ResearchAssumption) {
    setEditingAsset({ kind, id: asset.id, content: asset.content });
    setRejectingAsset(null);
  }

  async function submitEdit(kind: AssetKind, assetId: string) {
    if (!editingAsset || !editingAsset.content.trim()) return;
    await updateAsset(kind, assetId, { content: editingAsset.content.trim() }, "已保存修改");
  }

  async function confirmAsset(kind: AssetKind, assetId: string) {
    await updateAsset(kind, assetId, { status: "confirmed", review_note: null }, "已确认");
  }

  function startReject(kind: AssetKind, assetId: string) {
    setRejectingAsset({ kind, id: assetId, note: "" });
    setEditingAsset(null);
  }

  async function submitReject(kind: AssetKind, assetId: string) {
    if (!rejectingAsset || !rejectingAsset.note.trim()) {
      setError("请填写驳回原因");
      return;
    }
    await updateAsset(
      kind,
      assetId,
      { status: "rejected", review_note: rejectingAsset.note.trim() },
      "已驳回",
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
  const latestMemo = workspace.decision_memos[0];

  function renderAssetReview(kind: AssetKind, asset: ResearchClaim | ResearchAssumption) {
    const isEditing = editingAsset?.kind === kind && editingAsset.id === asset.id;
    const isRejecting = rejectingAsset?.kind === kind && rejectingAsset.id === asset.id;
    const busy = saving === assetKey(kind, asset.id);

    return (
      <>
        {isEditing && editingAsset ? (
          <div className="space-y-2">
            <textarea
              className="input-field min-h-[96px] resize-none"
              value={editingAsset.content}
              onChange={(e) => setEditingAsset({ ...editingAsset, content: e.target.value })}
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                className="btn-primary text-xs px-3 py-2"
                onClick={() => submitEdit(kind, asset.id)}
                disabled={busy || !editingAsset.content.trim()}
              >
                {busy ? "保存中..." : "保存修改"}
              </button>
              <button className="btn-secondary text-xs px-3 py-2" onClick={() => setEditingAsset(null)} disabled={busy}>
                取消
              </button>
            </div>
          </div>
        ) : (
          <p className="text-[#111827] text-sm leading-relaxed">{asset.content}</p>
        )}

        <EvidenceDetails
          evidenceItems={asset.evidence_items}
          verificationStatus={asset.verification_status}
        />

        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[#F1F3F5]">
          <span className={assetStatusClass(asset.status)}>{assetStatusLabel(asset.status)}</span>
          {asset.reviewed_at && (
            <span className="text-[#9CA3AF] text-xs">{formatDate(asset.reviewed_at)}</span>
          )}
          <button
            className="text-[#059669] hover:text-[#047857] text-xs font-medium disabled:text-[#9CA3AF]"
            onClick={() => confirmAsset(kind, asset.id)}
            disabled={busy || asset.status === "confirmed"}
          >
            确认
          </button>
          <button
            className="text-[#DC2626] hover:text-[#B91C1C] text-xs font-medium disabled:text-[#9CA3AF]"
            onClick={() => startReject(kind, asset.id)}
            disabled={busy || asset.status === "rejected"}
          >
            驳回
          </button>
          <button
            className="text-[#2563EB] hover:text-[#1D4ED8] text-xs font-medium disabled:text-[#9CA3AF]"
            onClick={() => startEdit(kind, asset)}
            disabled={busy}
          >
            编辑
          </button>
        </div>

        {asset.review_note && (
          <p className="text-[#6B7280] text-xs mt-2">复核备注：{asset.review_note}</p>
        )}

        {isRejecting && rejectingAsset && (
          <div className="mt-3 bg-[#FEF2F2] border border-[#DC2626]/20 rounded-lg p-3 space-y-2">
            <textarea
              className="input-field min-h-[72px] resize-none"
              value={rejectingAsset.note}
              onChange={(e) => setRejectingAsset({ ...rejectingAsset, note: e.target.value })}
              placeholder="填写驳回原因"
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                className="btn-primary text-xs px-3 py-2"
                onClick={() => submitReject(kind, asset.id)}
                disabled={busy || !rejectingAsset.note.trim()}
              >
                {busy ? "保存中..." : "保存驳回"}
              </button>
              <button className="btn-secondary text-xs px-3 py-2" onClick={() => setRejectingAsset(null)} disabled={busy}>
                取消
              </button>
            </div>
          </div>
        )}

        <p className="text-[#9CA3AF] text-xs mt-2">{formatDate(asset.updated_at)}</p>
      </>
    );
  }

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
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <h1 className="text-[#111827] text-2xl font-semibold tracking-tight">{subject.company_name}</h1>
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
            <p className="text-[#374151] text-sm leading-relaxed max-w-3xl">
              {subject.current_view || latestMemo?.current_conclusion || "尚未形成当前判断"}
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:w-[520px] gap-2 shrink-0">
            <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-3">
              <p className="text-[#9CA3AF] text-[11px]">置信度</p>
              <p className="text-[#111827] text-lg font-semibold mt-1">{levelLabel(subject.confidence_level)}</p>
            </div>
            <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-3">
              <p className="text-[#9CA3AF] text-[11px]">证据强度</p>
              <p className="text-[#111827] text-lg font-semibold mt-1">{levelLabel(subject.evidence_strength)}</p>
            </div>
            <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-3">
              <p className="text-[#9CA3AF] text-[11px]">证据</p>
              <p className="text-[#111827] text-lg font-semibold mt-1">{workspace.evidence_count}</p>
            </div>
            <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-3">
              <p className="text-[#9CA3AF] text-[11px]">更新</p>
              <p className="text-[#111827] text-sm font-semibold mt-1">{formatDate(subject.updated_at)}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-6 items-start">
        <main className="space-y-6">
          <section className="card p-6 animate-fade-up stagger-1">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h2 className="text-[#111827] text-sm font-semibold">判断图谱</h2>
              <span className="badge-neutral">{workspace.claims.length} 条</span>
            </div>
            {workspace.claims.length === 0 ? (
              <EmptyLine text="暂无判断" />
            ) : (
              <div className="space-y-3">
                {workspace.claims.map((claim) => (
                  <div key={claim.id} className="border border-[#E5E7EB] rounded-lg px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="badge-info">{directionLabel(claim.direction)}</span>
                      <span className="badge-neutral">置信度 {levelLabel(claim.confidence_level)}</span>
                      <span className="badge-neutral">证据 {levelLabel(claim.evidence_strength)}</span>
                      <span className={claim.verification_status === "cited" ? "badge-info" : "badge-neutral"}>
                        {verificationLabel(claim.verification_status)}
                      </span>
                    </div>
                    {renderAssetReview("claim", claim)}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card p-6 animate-fade-up stagger-2">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h2 className="text-[#111827] text-sm font-semibold">核心假设</h2>
              <span className="badge-neutral">{workspace.assumptions.length} 条</span>
            </div>
            {workspace.assumptions.length === 0 ? (
              <EmptyLine text="暂无假设" />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {workspace.assumptions.map((assumption) => (
                  <div key={assumption.id} className="border border-[#E5E7EB] rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="badge-neutral">{assumption.category}</span>
                      <span className="badge-info">置信度 {levelLabel(assumption.confidence_level)}</span>
                      <span className={assumption.verification_status === "cited" ? "badge-info" : "badge-neutral"}>
                        {verificationLabel(assumption.verification_status)}
                      </span>
                    </div>
                    {renderAssetReview("assumption", assumption)}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card p-6 animate-fade-up stagger-3">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h2 className="text-[#111827] text-sm font-semibold">反方挑战</h2>
              <span className="badge-neutral">{workspace.challenges.length} 条</span>
            </div>
            {workspace.challenges.length === 0 ? (
              <EmptyLine text="暂无反方挑战" />
            ) : (
              <div className="space-y-3">
                {workspace.challenges.map((challenge) => (
                  <div key={challenge.id} className="border border-[#E5E7EB] rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={challenge.risk_level === "high" ? "badge-error" : "badge-neutral"}>
                        风险 {levelLabel(challenge.risk_level)}
                      </span>
                    </div>
                    <p className="text-[#111827] text-sm leading-relaxed">{challenge.question}</p>
                    {challenge.suggested_action && (
                      <p className="text-[#6B7280] text-sm mt-2">动作：{challenge.suggested_action}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card p-6 animate-fade-up stagger-4">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h2 className="text-[#111827] text-sm font-semibold">决策备忘录</h2>
              <span className="badge-neutral">{workspace.decision_memos.length} 条</span>
            </div>
            {workspace.decision_memos.length === 0 ? (
              <EmptyLine text="暂无备忘录" />
            ) : (
              <div className="space-y-3">
                {workspace.decision_memos.map((memo) => (
                  <div key={memo.id} className="border border-[#E5E7EB] rounded-lg px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="badge-info">{memo.review_status === "ai_draft" ? "AI 草稿" : memo.review_status}</span>
                      <span className="text-[#9CA3AF] text-xs">{formatDate(memo.created_at)}</span>
                    </div>
                    <p className="text-[#111827] text-sm font-medium leading-relaxed">{memo.current_conclusion}</p>
                    {memo.key_basis && <p className="text-[#6B7280] text-sm mt-2">依据：{memo.key_basis}</p>}
                    {memo.biggest_uncertainty && (
                      <p className="text-[#6B7280] text-sm mt-1">不确定性：{memo.biggest_uncertainty}</p>
                    )}
                    {memo.suggested_action && (
                      <p className="text-[#6B7280] text-sm mt-1">动作：{memo.suggested_action}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>

        <aside className="space-y-4">
          <section className="card p-5 animate-fade-up stagger-1">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">研究动作</h2>
            <button className="btn-primary w-full text-sm" onClick={handleGenerateAssets} disabled={generating}>
              {generating ? "生成中..." : "生成判断资产"}
            </button>
          </section>

          <section className="card p-5 animate-fade-up stagger-1">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">材料归档</h2>
            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
            />
            <button
              className="btn-secondary w-full text-sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "上传中..." : "上传 PDF 材料"}
            </button>
            <div className="grid grid-cols-2 gap-2 mt-3">
              <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
                <p className="text-[#9CA3AF] text-[11px]">证据片段</p>
                <p className="text-[#111827] text-base font-semibold mt-1">{workspace.evidence_count}</p>
              </div>
              <div className="bg-[#F8F9FB] border border-[#E5E7EB] rounded-lg px-3 py-2">
                <p className="text-[#9CA3AF] text-[11px]">状态</p>
                <p className="text-[#111827] text-sm font-semibold mt-1">可追溯</p>
              </div>
            </div>
          </section>

          <section className="card p-5 animate-fade-up stagger-2">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">添加判断</h2>
            <form className="space-y-3" onSubmit={submitClaim}>
              <textarea
                className="input-field min-h-[92px] resize-none"
                value={claimForm.content}
                onChange={(e) => setClaimForm({ ...claimForm, content: e.target.value })}
                placeholder="例如：储能业务可能成为第二增长曲线"
              />
              <div className="grid grid-cols-3 gap-2">
                <select
                  className="input-field"
                  value={claimForm.direction}
                  onChange={(e) => setClaimForm({ ...claimForm, direction: e.target.value })}
                >
                  <option value="positive">正面</option>
                  <option value="neutral">中性</option>
                  <option value="negative">负面</option>
                </select>
                <select
                  className="input-field"
                  value={claimForm.confidence_level}
                  onChange={(e) => setClaimForm({ ...claimForm, confidence_level: e.target.value })}
                >
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
                <select
                  className="input-field"
                  value={claimForm.evidence_strength}
                  onChange={(e) => setClaimForm({ ...claimForm, evidence_strength: e.target.value })}
                >
                  <option value="high">强</option>
                  <option value="medium">中</option>
                  <option value="low">弱</option>
                </select>
              </div>
              <button className="btn-primary w-full text-sm" disabled={saving === "claim" || !claimForm.content.trim()}>
                {saving === "claim" ? "保存中..." : "保存判断"}
              </button>
            </form>
          </section>

          <section className="card p-5 animate-fade-up stagger-3">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">添加假设</h2>
            <form className="space-y-3" onSubmit={submitAssumption}>
              <textarea
                className="input-field min-h-[84px] resize-none"
                value={assumptionForm.content}
                onChange={(e) => setAssumptionForm({ ...assumptionForm, content: e.target.value })}
                placeholder="例如：储能收入增速能抵消动力电池价格压力"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="input-field"
                  value={assumptionForm.category}
                  onChange={(e) => setAssumptionForm({ ...assumptionForm, category: e.target.value })}
                >
                  <option value="revenue">收入</option>
                  <option value="margin">利润率</option>
                  <option value="cashflow">现金流</option>
                  <option value="valuation">估值</option>
                  <option value="business">商业模式</option>
                </select>
                <select
                  className="input-field"
                  value={assumptionForm.confidence_level}
                  onChange={(e) => setAssumptionForm({ ...assumptionForm, confidence_level: e.target.value })}
                >
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
              </div>
              <button
                className="btn-primary w-full text-sm"
                disabled={saving === "assumption" || !assumptionForm.content.trim()}
              >
                {saving === "assumption" ? "保存中..." : "保存假设"}
              </button>
            </form>
          </section>

          <section className="card p-5 animate-fade-up stagger-4">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">添加挑战</h2>
            <form className="space-y-3" onSubmit={submitChallenge}>
              <textarea
                className="input-field min-h-[84px] resize-none"
                value={challengeForm.question}
                onChange={(e) => setChallengeForm({ ...challengeForm, question: e.target.value })}
                placeholder="例如：如果海外项目交付延迟，这个判断是否失效？"
              />
              <select
                className="input-field"
                value={challengeForm.risk_level}
                onChange={(e) => setChallengeForm({ ...challengeForm, risk_level: e.target.value })}
              >
                <option value="high">高风险</option>
                <option value="medium">中风险</option>
                <option value="low">低风险</option>
              </select>
              <input
                className="input-field"
                value={challengeForm.suggested_action}
                onChange={(e) => setChallengeForm({ ...challengeForm, suggested_action: e.target.value })}
                placeholder="建议动作"
              />
              <button
                className="btn-primary w-full text-sm"
                disabled={saving === "challenge" || !challengeForm.question.trim()}
              >
                {saving === "challenge" ? "保存中..." : "保存挑战"}
              </button>
            </form>
          </section>

          <section className="card p-5 animate-fade-up stagger-5">
            <h2 className="text-[#111827] text-sm font-semibold mb-4">添加备忘录</h2>
            <form className="space-y-3" onSubmit={submitMemo}>
              <textarea
                className="input-field min-h-[80px] resize-none"
                value={memoForm.current_conclusion}
                onChange={(e) => setMemoForm({ ...memoForm, current_conclusion: e.target.value })}
                placeholder="当前结论"
              />
              <input
                className="input-field"
                value={memoForm.key_basis}
                onChange={(e) => setMemoForm({ ...memoForm, key_basis: e.target.value })}
                placeholder="关键依据"
              />
              <input
                className="input-field"
                value={memoForm.biggest_uncertainty}
                onChange={(e) => setMemoForm({ ...memoForm, biggest_uncertainty: e.target.value })}
                placeholder="最大不确定性"
              />
              <input
                className="input-field"
                value={memoForm.suggested_action}
                onChange={(e) => setMemoForm({ ...memoForm, suggested_action: e.target.value })}
                placeholder="建议动作"
              />
              <button className="btn-primary w-full text-sm" disabled={saving === "memo" || !memoForm.current_conclusion.trim()}>
                {saving === "memo" ? "保存中..." : "保存备忘录"}
              </button>
            </form>
          </section>
        </aside>
      </div>
    </div>
  );
}
