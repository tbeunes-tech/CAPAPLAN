import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";

export type Role = "admin" | "contributor" | "reader";
const RANK: Record<Role, number> = { reader: 0, contributor: 1, admin: 2 };

interface AuthState {
  email: string | null;
  role: Role | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  can: (minimum: Role) => boolean;
}

const Ctx = createContext<AuthState | null>(null);
const SESSION_KEY = "portfolio_session";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<{ email: string; role: Role } | null>(() => {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw && tokenStore.get() ? JSON.parse(raw) : null;
  });

  useEffect(() => {
    const onLogout = () => {
      localStorage.removeItem(SESSION_KEY);
      setSession(null);
    };
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);

  const login = async (email: string, password: string) => {
    const r = await api.login(email, password);
    tokenStore.set(r.access_token);
    const s = { email: r.email, role: r.role };
    localStorage.setItem(SESSION_KEY, JSON.stringify(s));
    setSession(s);
  };

  const logout = () => {
    tokenStore.clear();
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
  };

  const can = (minimum: Role) => (session ? RANK[session.role] >= RANK[minimum] : false);

  return (
    <Ctx.Provider value={{ email: session?.email ?? null, role: session?.role ?? null, login, logout, can }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth hors AuthProvider");
  return ctx;
}
