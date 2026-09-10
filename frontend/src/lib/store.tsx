"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User } from "./api";
import { auth, setToken, clearToken, getToken } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string }) => Promise<void>;
  demoLogin: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  demoLogin: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 恢复 session：从 token 解析用户信息，校验过期时间
    const t = getToken();
    if (t) {
      try {
        const payload = JSON.parse(atob(t.split(".")[1]));
        // token 已过期则清除，强制重新登录
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          clearToken();
        } else {
          setUser({
            id: payload.sub,
            email: "",
            name: "",
            role: "",
            organization_id: null,
            is_active: true,
          });
        }
      } catch {
        clearToken();
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await auth.login({ email, password });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (data: { email: string; password: string }) => {
    const res = await auth.register(data);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const demoLogin = useCallback(async () => {
    const res = await auth.demo();
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, demoLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
