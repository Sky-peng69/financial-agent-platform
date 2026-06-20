"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/store";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("investor");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const { user, login, register } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({ email, password, name, role });
      }
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: brand panel */}
      <div className="hidden lg:flex w-[480px] bg-[#0F1521] border-r border-[#1E2A3E] flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#C9A94E]/5 via-transparent to-[#4A90D9]/5" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-9 h-9 bg-[#C9A94E] rounded-sm flex items-center justify-center">
              <span className="text-[#080C14] font-bold text-lg">衡</span>
            </div>
            <div>
              <h1 className="text-[#E8EDF5] text-xl font-bold tracking-wide">衡策</h1>
              <p className="text-[#5A6577] text-xs">金融 Agent 平台</p>
            </div>
          </div>

          <blockquote className="text-[#8B95A5] text-sm leading-relaxed italic mb-8">
            "金融分析不应是少数人的特权。<br />
            AI 让每个决策者都能拥有<br />
            机构级别的分析能力。"
          </blockquote>

          <div className="space-y-3">
            {[
              { label: "智能 Agent", desc: "端到端自动化金融分析" },
              { label: "多角色协作", desc: "银行员工·投资者·管理者" },
              { label: "数据驱动", desc: "实时市场数据 + AI 推理" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3 text-sm">
                <div className="w-1.5 h-1.5 bg-[#C9A94E] rounded-full flex-shrink-0" />
                <span className="text-[#B9C2D4]">{item.label}</span>
                <span className="text-[#5A6577]">— {item.desc}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-[#5A6577] text-xs relative z-10">
          以上分析仅供参考，不构成投资建议
        </p>
      </div>

      {/* Right: form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-[400px] animate-fade-up">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-9 h-9 bg-[#C9A94E] rounded-sm flex items-center justify-center">
              <span className="text-[#080C14] font-bold text-lg">衡</span>
            </div>
            <h1 className="text-[#E8EDF5] text-xl font-bold">衡策</h1>
          </div>

          <h2 className="text-[#E8EDF5] text-2xl font-semibold mb-1">
            {mode === "login" ? "登录" : "注册"}
          </h2>
          <p className="text-[#5A6577] text-sm mb-8">
            {mode === "login" ? "欢迎回来，请登录你的账户" : "创建账户，开始使用智能金融分析"}
          </p>

          {error && (
            <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-4 py-3 rounded-sm mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {mode === "register" && (
              <>
                <div>
                  <label className="label">姓名</label>
                  <input
                    className="input-field"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="你的真实姓名"
                    required
                  />
                </div>
                <div>
                  <label className="label">角色</label>
                  <select
                    className="input-field"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  >
                    <option value="investor">个人投资者</option>
                    <option value="org_user">机构用户（银行员工）</option>
                    <option value="admin">平台管理员</option>
                  </select>
                </div>
              </>
            )}

            <div>
              <label className="label">邮箱</label>
              <input
                className="input-field"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
              />
            </div>

            <div>
              <label className="label">密码</label>
              <input
                className="input-field"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "至少 6 位字符" : "输入密码"}
                required
                minLength={6}
              />
            </div>

            <button className="btn-primary w-full mt-2" type="submit" disabled={busy}>
              {busy ? "处理中..." : mode === "login" ? "登录" : "创建账户"}
            </button>
          </form>

          <p className="text-[#5A6577] text-sm text-center mt-8">
            {mode === "login" ? "还没有账户？" : "已有账户？"}
            <button
              className="text-[#C9A94E] hover:text-[#D4B85A] ml-1 transition-colors"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
            >
              {mode === "login" ? "立即注册" : "去登录"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
