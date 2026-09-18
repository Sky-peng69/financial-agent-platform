export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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

async function parseError(res: Response): Promise<string> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail || res.statusText;
  } catch {
    const text = await res.text();
    if (text) detail = text.slice(0, 200);
  }
  return detail;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const t = token();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (t) headers.Authorization = `Bearer ${t}`;
  const { signal, ...rest } = options;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...rest, headers, signal });
  } catch {
    throw new ApiError("无法连接后端，请确认 API 服务和数据库已启动", 0);
  }
  if (res.status === 401 || res.status === 403) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.replace("/login");
    }
    throw new ApiError("认证已过期，请重新登录", res.status);
  }
  if (!res.ok) throw new ApiError(await parseError(res), res.status);
  return res.json();
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  organization_id: string | null;
  is_active: boolean;
}

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
  demo: () =>
    request<{ access_token: string; user: User }>("/api/auth/demo", { method: "POST" }),
};

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

export interface Agent {
  name: string;
  display_name: string;
  description: string;
  category: string;
  tools: string[];
}

export interface ResearchFile {
  id: string;
  task_id: string | null;
  original_name: string;
  content_type: string;
  size_bytes: number;
  status: "uploaded" | "parsed" | "failed";
  created_at: string;
}

export interface ReportFile {
  format: "docx" | "md" | "pdf" | string;
  filename: string;
  download_url: string;
}

export interface ResearchReport {
  id: string;
  task_id: string | null;
  title: string;
  report_style: string;
  review_status: string;
  files: ReportFile[];
  created_at: string;
}

let activeStreamController: AbortController | null = null;

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
    onDone: (taskId: string, refs: SearchReference[] | null) => void,
    onError: (err: Error) => void,
  ): AbortController => {
    const controller = new AbortController();
    const t = token();
    activeStreamController?.abort();
    activeStreamController = controller;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/agents/${name}/run-stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) },
          body: JSON.stringify(data),
          signal: controller.signal,
        });
        if (!res.ok) throw new ApiError((await res.text()) || res.statusText, res.status);
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
              if (event.type === "chunk") onChunk(event.content);
              if (event.type === "done") onDone(event.task_id, event.search_references || null);
              if (event.type === "error") onError(new Error(event.message));
            } catch {
              // Ignore incomplete SSE payloads.
            }
          }
        }
        activeStreamController = null;
      } catch (err: any) {
        activeStreamController = null;
        if (err.name !== "AbortError") onError(err);
      }
    })();
    return controller;
  },
  analyze: (title: string, inputData: string) =>
    request<Task>("/api/agents/analyze", {
      method: "POST",
      body: JSON.stringify({ title, input_data: inputData }),
      signal: AbortSignal.timeout(300_000),
    }),
  analyzeStream: (
    title: string,
    inputData: string,
    options: { file_ids?: string[]; generate_report?: boolean } | null,
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
        report: ResearchReport | null;
      }) => void;
      onError: (err: Error) => void;
    },
  ): AbortController => {
    const controller = new AbortController();
    const t = token();
    activeStreamController?.abort();
    activeStreamController = controller;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/agents/analyze-stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) },
          body: JSON.stringify({ title, input_data: inputData, file_ids: options?.file_ids || [], generate_report: options?.generate_report || false }),
          signal: controller.signal,
        });
        if (!res.ok) throw new ApiError((await res.text()) || res.statusText, res.status);
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
              if (event.type === "phase") {
                if (event.plan) callbacks.onPlan(event.plan);
                callbacks.onPhase(event.phase, event.message);
              } else if (event.type === "agent_start") {
                callbacks.onAgentStart(event.agent, event.display_name, event.title || "");
              } else if (event.type === "agent_done") {
                callbacks.onAgentDone(event.agent, event.display_name, event.status);
              } else if (event.type === "synthesizing") {
                callbacks.onSynthesizing();
              } else if (event.type === "done") {
                callbacks.onDone({ task_id: event.task_id, output_data: event.output_data, plan: event.plan, subtask_results: event.subtask_results, search_references: event.search_references || null, report: event.report || null });
              } else if (event.type === "error") {
                callbacks.onError(new Error(event.message));
              }
            } catch {
              // Ignore malformed SSE frames.
            }
          }
        }
        activeStreamController = null;
      } catch (err: any) {
        activeStreamController = null;
        if (err.name !== "AbortError") callbacks.onError(err);
      }
    })();
    return controller;
  },
};

export const tasks = {
  list: () => request<Task[]>("/api/tasks"),
  get: (id: string) => request<Task>(`/api/tasks/${id}`),
};

export const reports = {
  downloadFile: async (file: ReportFile) => {
    const t = token();
    const res = await fetch(`${API_URL}${file.download_url}`, { headers: t ? { Authorization: `Bearer ${t}` } : {} });
    if (!res.ok) throw new ApiError(await parseError(res), res.status);
    const blob = await res.blob();
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = file.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(href);
  },
};

export const files = {
  list: () => request<ResearchFile[]>("/api/files"),
  upload: async (file: File, taskId?: string | null) => {
    const body = new FormData();
    body.append("file", file);
    if (taskId) body.append("task_id", taskId);
    const t = token();
    const res = await fetch(`${API_URL}/api/files`, { method: "POST", headers: t ? { Authorization: `Bearer ${t}` } : {}, body });
    if (!res.ok) throw new ApiError(await parseError(res), res.status);
    return res.json() as Promise<ResearchFile>;
  },
};

export function parseSearchReferences(raw: string | null): SearchReference[] | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : null;
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
