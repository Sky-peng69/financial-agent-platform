"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/store";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const { user, login, demoLogin } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "登录失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleDemoLogin() {
    setError("");
    setBusy(true);
    try {
      await demoLogin();
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "暂时无法进入开发体验");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-center p-8 h-full bg-[#F8F9FB]">
      <div className="w-full max-w-[400px] animate-fade-up">
        <h2 className="text-[#111827] text-2xl font-semibold mb-1">进入衡策</h2>
        <p className="text-[#9CA3AF] text-sm mb-8">智能金融研究工作台</p>

        {error && (
          <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <button className="btn-primary w-full" type="button" onClick={handleDemoLogin} disabled={busy}>
          {busy ? "进入中..." : "进入开发体验"}
        </button>
        <p className="text-[#9CA3AF] text-xs text-center mt-3">
          无需注册，直接体验 A 股智能研究流程
        </p>

        <div className="flex items-center gap-3 my-8">
          <div className="h-px bg-[#E5E7EB] flex-1" />
          <span className="text-[#9CA3AF] text-xs">已有账户</span>
          <div className="h-px bg-[#E5E7EB] flex-1" />
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
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
              placeholder="输入密码"
              required
              minLength={6}
            />
          </div>

          <button className="btn-secondary w-full" type="submit" disabled={busy}>
            登录已有账户
          </button>
        </form>
      </div>
    </div>
  );
}
