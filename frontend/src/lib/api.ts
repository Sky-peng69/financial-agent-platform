const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

  // 默认 30s 超时，调用方可传 signal 覆盖（如 analyze 传 300s）
  const signal = options.signal ?? AbortSignal.timeout(30_000);
  const { signal: _, ...rest } = options;

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
  register: (data: { email: string; password: string; name: string; role: string }) =>
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
  analyze: (title: string, inputData: string) =>
    request<Task>("/api/agents/analyze", {
      method: "POST",
      body: JSON.stringify({ title, input_data: inputData }),
      signal: AbortSignal.timeout(300_000), // 5 min
    }),
};

// Tasks
export interface Task {
  id: string;
  agent_name: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  input_data: string | null;
  output_data: string | null;
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

export function setToken(t: string) {
  localStorage.setItem("token", t);
}
export function clearToken() {
  localStorage.removeItem("token");
}
export function getToken() {
  return token();
}
