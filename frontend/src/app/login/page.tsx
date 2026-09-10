"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/store";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
        await register({ email, password });
      }
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "操作失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-center p-8 h-full bg-[#F8F9FB]">
      <div className="w-full max-w-[400px] animate-fade-up">
        <h2 className="text-[#111827] text-2xl font-semibold mb-1">
          {mode === "login" ? "登录" : "注册"}
        </h2>
        <p className="text-[#9CA3AF] text-sm mb-8">
          {mode === "login" ? "欢迎回来，请登录你的账户" : "创建账户，开始使用智能金融分析"}
        </p>

        {error && (
          <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
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

        <p className="text-[#9CA3AF] text-sm text-center mt-8">
          {mode === "login" ? "还没有账户？" : "已有账户？"}
          <button
            className="text-[#2563EB] hover:text-[#1D4ED8] ml-1 transition-colors font-medium"
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
          >
            {mode === "login" ? "立即注册" : "去登录"}
          </button>
        </p>
      </div>
    </div>
  );
}
