import type {
  CapacityCell, CapacityInput, ChangeEntry, LoadGrid, NumberPivot, OccupancyPivot, Overload,
  PrioritizationPlan, Project, ProjectInput, Referentials, RoadmapItem, Team, TeamInput,
  TeamLoadDetail,
} from "./types";

const q = (start?: string) => (start ? `?start=${start}` : "");

// Dev / LAN : "/api" (proxifié vers le backend par Vite, même origine).
// Cloud : VITE_API_BASE = URL publique de l'API (ex. https://portfolio-api.onrender.com).
const BASE = import.meta.env.VITE_API_BASE || "/api";

const TOKEN_KEY = "portfolio_token";
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Notifie l'app d'une session expirée/invalide (intercepté par AuthContext).
function onUnauthorized() {
  tokenStore.clear();
  window.dispatchEvent(new CustomEvent("auth:logout"));
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = tokenStore.get();
  const res = await fetch(BASE + path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (res.status === 401 && !path.startsWith("/auth/login")) onUnauthorized();
  if (!res.ok) {
    let body: unknown = null;
    let detail = res.statusText;
    try {
      body = await res.json();
      const d = (body as { detail?: unknown }).detail;
      detail = typeof d === "string" ? d
        : d && typeof d === "object" && "message" in d ? String((d as { message: unknown }).message)
        : JSON.stringify(d);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, `${res.status} — ${detail}`, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface LoginResult {
  access_token: string;
  email: string;
  role: "admin" | "contributor" | "reader";
}

export const api = {
  login: (email: string, password: string) =>
    req<LoginResult>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req<{ email: string; role: string; full_name: string | null }>("/auth/me"),
  referentials: () => req<Referentials>("/referentials"),
  teams: () => req<Team[]>("/teams"),
  createTeam: (body: TeamInput) =>
    req<Team>("/teams", { method: "POST", body: JSON.stringify(body) }),
  updateTeam: (name: string, body: Omit<TeamInput, "name">) =>
    req<Team>(`/teams/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteTeam: (name: string) =>
    req<void>(`/teams/${encodeURIComponent(name)}`, { method: "DELETE" }),
  listProjects: () => req<Project[]>("/projects"),
  getProject: (id: string) => req<Project>(`/projects/${id}`),
  projectHistory: (id: string) => req<ChangeEntry[]>(`/projects/${id}/history`),
  createProject: (body: ProjectInput) =>
    req<Project>("/projects", { method: "POST", body: JSON.stringify(body) }),
  updateProject: (id: string, body: ProjectInput) =>
    req<Project>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteProject: (id: string) => req<void>(`/projects/${id}`, { method: "DELETE" }),
  getLoadGrid: (id: string) => req<LoadGrid>(`/projects/${id}/loads`),
  saveLoadGrid: (
    id: string,
    cells: { team: string; month: string; days: number; base_updated_at: string | null }[],
  ) => req<Project>(`/projects/${id}/loads`, { method: "PUT", body: JSON.stringify({ cells }) }),

  // Dashboards §5.3–5.8
  teamLoad: (start?: string) => req<NumberPivot>(`/dashboards/team-load${q(start)}`),
  teamLoadDetail: (team: string, start?: string) =>
    req<TeamLoadDetail>(
      `/dashboards/team-load/detail?team=${encodeURIComponent(team)}${start ? `&start=${start}` : ""}`,
    ),
  capacityPivot: (start?: string) => req<NumberPivot>(`/capacity/pivot${q(start)}`),
  capacityCell: (team: string, month: string) =>
    req<CapacityCell>(`/capacity/cell?team=${encodeURIComponent(team)}&month=${month}`),
  saveCapacity: (body: CapacityInput) =>
    req<CapacityCell>("/capacity", { method: "PUT", body: JSON.stringify(body) }),
  occupancy: (start?: string) => req<OccupancyPivot>(`/dashboards/occupancy${q(start)}`),
  overloads: (start?: string) => req<Overload[]>(`/dashboards/overloads${q(start)}`),
  roadmap: () => req<RoadmapItem[]>("/dashboards/roadmap"),
  prioritization: (start?: string) => req<PrioritizationPlan>(`/dashboards/prioritization${q(start)}`),
};
