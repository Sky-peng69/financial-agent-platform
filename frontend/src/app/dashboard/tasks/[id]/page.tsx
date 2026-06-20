"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { tasks as tasksApi, type Task } from "@/lib/api";

export default function TaskDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tasksApi
      .get(id)
      .then(setTask)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <div className="w-7 h-7 border-2 border-[#C9A94E]/30 border-t-[#C9A94E] rounded-full animate-spin" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="card p-12 text-center">
          <p className="text-[#8B95A5] text-sm">任务不存在</p>
          <Link href="/dashboard/tasks" className="text-[#C9A94E] text-sm mt-2 inline-block">返回列表</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 animate-fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs mb-6">
        <Link href="/dashboard/tasks" className="text-[#5A6577] hover:text-[#C9A94E] transition-colors">
          任务历史
        </Link>
        <span className="text-[#1E2A3E]">/</span>
        <span className="text-[#C9A94E] truncate">{task.title}</span>
      </div>

      {/* Meta */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-[#E8EDF5] text-lg font-semibold">{task.title}</h1>
          <span
            className={`text-xs px-2 py-0.5 rounded-sm ${
              task.status === "completed"
                ? "bg-[#1A3D2A] text-[#34A584]"
                : task.status === "failed"
                ? "bg-[#3D1A1A] text-[#D95A4A]"
                : "bg-[#1E2A3E] text-[#8B95A5]"
            }`}
          >
            {task.status === "completed" ? "✓ 完成" : task.status === "failed" ? "✗ 失败" : task.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#5A6577]">
          <span>Agent: {task.agent_name}</span>
          <span>创建: {new Date(task.created_at).toLocaleString("zh-CN")}</span>
          {task.completed_at && <span>完成: {new Date(task.completed_at).toLocaleString("zh-CN")}</span>}
        </div>
      </div>

      {/* Input */}
      {task.input_data && (
        <div className="card p-6 mb-6">
          <h2 className="text-[#E8EDF5] text-sm font-semibold mb-3">任务输入</h2>
          <p className="text-[#8B95A5] text-sm whitespace-pre-wrap">{task.input_data}</p>
        </div>
      )}

      {/* Error */}
      {task.error_message && (
        <div className="bg-[#3D1A1A] border border-[#D95A4A]/30 text-[#D95A4A] text-sm px-5 py-4 rounded-sm mb-6">
          <p className="font-semibold mb-1">错误信息</p>
          {task.error_message}
        </div>
      )}

      {/* Output */}
      {task.output_data && (
        <div className="card p-6">
          <h2 className="text-[#E8EDF5] text-sm font-semibold mb-4">分析结果</h2>
          <div className="markdown-content">
            <ReactMarkdown>{task.output_data}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
