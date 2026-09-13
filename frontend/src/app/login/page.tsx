"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/store";

export default function LoginPage() {
  const [error, setError] = useState("");
  const { user, loading, demoLogin } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (user) {
      router.replace("/dashboard");
      return;
    }
    demoLogin()
      .then(() => router.replace("/dashboard"))
      .catch((err: any) => setError(err.message || "暂时无法进入体验"));
  }, [user, loading, demoLogin, router]);

  return (
    <div className="flex items-center justify-center p-8 h-full bg-[#F8F9FB]">
      <div className="w-full max-w-[420px] text-center animate-fade-up">
        <div className="w-8 h-8 border-2 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin mx-auto mb-5" />
        <h1 className="text-[#111827] text-2xl font-semibold mb-2">正在进入弈金</h1>
        <p className="text-[#6B7280] text-sm">无需注册，直接进入 A 股智能研究工作台。</p>
        {error && (
          <div className="bg-[#FEF2F2] border border-[#DC2626]/20 text-[#DC2626] text-sm px-4 py-3 rounded-lg mt-6">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
