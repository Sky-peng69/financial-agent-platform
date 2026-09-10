const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const t = token();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const { signal, ...rest } = options;

  const res = await fetch(`${API_URL}${path}`, { ...rest, headers, signal });

  // 401/403 统一处理：清除 token，跳转登录页
  if (res.status === 401 || res.status === 403) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.replace("/login");
    }
    throw new ApiError("认证已过期，请重新登录", res.status);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || res.statusText;
    } catch {
      const text = await res.text();
      if (text) detail = text.slice(0, 200);
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

// Auth
export const auth = {
  register: (data: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// 全局活跃的流式请求控制器，确保同一时间只有一个流
let _activeStreamController: AbortController | null = null;

// Agents
export interface Agent {
  name: string;
  display_name: string;
  description: string;
  category: string;
  tools: string[];
}

export const agents = {
  list: (category?: string) =>
    request<Agent[]>(`/api/agents${category ? `?category=${category}` : ""}`),
  get: (name: string) => request<Agent>(`/api/agents/${name}`),
  run: (name: string, data: { agent_name: string; title: string; input_data: string }) =>
    request<Task>(`/api/agents/${name}/run`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  runStream: (
    name: string,
    data: { agent_name: string; title: string; input_data: string },
    onChunk: (text: string) => void,
    onDone: (taskId: string, searchReferences: SearchReference[] | null) => void,
    onError: (err: Error) => void,
  ): AbortController => {
    const controller = new AbortController();
    const t = token();

    // 先中止上一个（避免重复点击启动两个并发流）
    _activeStreamController?.abort();
    _activeStreamController = controller;

    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/agents/${name}/run-stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(t ? { Authorization: `Bearer ${t}` } : {}),
          },
          body: JSON.stringify(data),
          signal: controller.signal,
        });

        // 401/403 统一处理：清除 token，跳转登录页
        if (res.status === 401 || res.status === 403) {
          if (typeof window !== "undefined") {
            localStorage.removeItem("token");
            window.location.replace("/login");
          }
          throw new ApiError("认证已过期，请重新登录", res.status);
        }

        if (!res.ok) {
          const text = await res.text();
          throw new ApiError(text || res.statusText, res.status);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // 解析 SSE 帧（以 \n\n 分隔）
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || ""; // 保留不完整的最后一帧

          for (const part of parts) {
            const line = part.replace(/^data: /, "").trim();
            if (!line) continue;
            try {
              const event = JSON.parse(line);
              if (event.type === "chunk") {
                onChunk(event.content);
              } else if (event.type === "done") {
                onDone(event.task_id, event.search_references || null);
              } else if (event.type === "error") {
                onError(new Error(event.message));
              }
            } catch { /* 跳过解析失败的帧 */ }
          }
        }

        // 流正常结束但无 done 事件（异常情况）：手动通知完成
        _activeStreamController = null;
      } catch (err: any) {
        if (err.name === "AbortError") {
          // 用户主动取消 / 新请求中止旧请求，不报错
          _activeStreamController = null;
          return;
        }
        _activeStreamController = null;
        onError(err);
      }
    })();

    return controller; // 调用方可以 controller.abort() 取消
  },
  analyze: (title: string, inputData: string) =>
    request<Task>("/api/agents/analyze", {
      method: "POST",
      body: JSON.stringify({ title, input_data: inputData }),
      signal: AbortSignal.timeout(300_000), // 5 min
    }),

  /** SSE 流式版 Commander 分析 —— 实时推送进度事件 */
  analyzeStream: (
    title: string,
    inputData: string,
    callbacks: {
      onPhase: (phase: string, message: string) => void;
      onPlan: (plan: any) => void;
      onAgentStart: (agent: string, displayName: string, agentTitle: string) => void;
      onAgentDone: (agent: string, displayName: string, status: string) => void;
      onSynthesizing: () => void;
      onDone: (result: {
        task_id: string;
        output_data: string;
        plan: any;
        subtask_results: any[];
        search_references: SearchReference[] | null;
      }) => void;
      onError: (err: Error) => void;
    },
  ): AbortController => {
    const controller = new AbortController();
    const t = token();

    // 先中止上一个
    _activeStreamController?.abort();
    _activeStreamController = controller;

    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/agents/analyze-stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(t ? { Authorization: `Bearer ${t}` } : {}),
          },
          body: JSON.stringify({ title, input_data: inputData }),
          signal: controller.signal,
        });

        if (res.status === 401 || res.status === 403) {
          if (typeof window !== "undefined") {
            localStorage.removeItem("token");
            window.location.replace("/login");
          }
          throw new ApiError("认证已过期，请重新登录", res.status);
        }

        if (!res.ok) {
          const text = await res.text();
          throw new ApiError(text || res.statusText, res.status);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const line = part.replace(/^data: /, "").trim();
            if (!line) continue;
            try {
              const event = JSON.parse(line);
              switch (event.type) {
                case "phase":
                  if (event.plan) callbacks.onPlan(event.plan);
                  callbacks.onPhase(event.phase, event.message);
                  break;
                case "agent_start":
                  callbacks.onAgentStart(event.agent, event.display_name, event.title || "");
                  break;
                case "agent_done":
                  callbacks.onAgentDone(event.agent, event.display_name, event.status);
                  break;
                case "done":
                  callbacks.onDone({
                    task_id: event.task_id,
                    output_data: event.output_data,
                    plan: event.plan,
                    subtask_results: event.subtask_results,
                    search_references: event.search_references || null,
                  });
                  break;
                case "error":
                  callbacks.onError(new Error(event.message));
                  break;
              }
            } catch { /* skip parse errors */ }
          }
        }

        _activeStreamController = null;
      } catch (err: any) {
        if (err.name === "AbortError") {
          _activeStreamController = null;
          return;
        }
        _activeStreamController = null;
        callbacks.onError(err);
      }
    })();

    return controller;
  },
};

// Tasks
export interface SearchReference {
  name?: string;
  title?: string;
  url?: string;
  link?: string;
  snippet?: string;
  content?: string;
}

export interface Task {
  id: string;
  agent_name: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  input_data: string | null;
  output_data: string | null;
  search_references: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export const tasks = {
  list: () => request<Task[]>("/api/tasks"),
  get: (id: string) => request<Task>(`/api/tasks/${id}`),
};

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  organization_id: string | null;
  is_active: boolean;
}

export function parseSearchReferences(raw: string | null): SearchReference[] | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    return null;
  } catch {
    return null;
  }
}

export function setToken(t: string) {
  localStorage.setItem("token", t);
}
export function clearToken() {
  localStorage.removeItem("token");
}
export function getToken() {
  return token();
}
