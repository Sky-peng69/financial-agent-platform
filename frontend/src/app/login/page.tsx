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
    <div className="flex items-center justify-center p-8 h-full">
      <div className="w-full max-w-[400px] animate-fade-up">

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
  );
}
