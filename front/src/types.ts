export interface QC {
  date_error: string | null;
  status_error: string | null;
  obsolete_forecast: string | null;
  leader_error: string | null;
  has_error: boolean;
}

export interface Project {
  project_id: string;
  entite: string | null;
  domain_lead: string | null;
  project_name: string | null;
  project_leader: string | null;
  status: string | null;
  priorite: string | null;
  pilier_strategique: string | null;
  budget_item: string | null;
  budget_owner: string | null;
  programme: string | null;
  in_plan: boolean;
  start_date: string | null;
  end_date: string | null;
  last_update: string | null;
  total_project_load: number | null;
  qc: QC;
}

export type ProjectInput = Partial<Omit<Project, "project_id" | "in_plan" | "last_update" | "total_project_load" | "qc">>;

export type Referentials = Record<string, string[]>;

export interface Team {
  name: string;
  manager: string | null;
  capacite_etp: number | null;
  description: string | null;
}

export interface TeamInput {
  name: string;
  manager: string | null;
  capacite_etp: number | null;
  description: string | null;
}

export interface ProjectLeader {
  id: number;
  name: string;
  active: boolean;
}

export interface LoadGrid {
  project_id: string;
  months: string[];
  teams: string[];
  cells: { team: string; month: string; days: number; updated_at: string | null }[];
}

export interface LoadConflict {
  team: string;
  month: string;
  server_days: number;
  server_updated_at: string | null;
  your_days: number;
}

// --- Dashboards (§5.3–5.8) ---
export type ColorName = "green" | "amber" | "red" | "overload_null_capacity";

export interface NumberPivot {
  months: string[];
  rows: { team: string; values: number[] }[];
}

export interface TeamLoadDetail {
  team: string;
  months: string[];
  rows: { project_id: string; project_name: string; values: number[] }[];
}

export interface OccupancyPivot {
  months: string[];
  rows: { team: string; cells: { rate: number; color: ColorName }[] }[];
}

export interface Overload {
  team: string;
  month: string;
  charge: number;
  capacite: number;
  rate: number;
  ecart_jours: number;
  color: ColorName;
}

export interface RoadmapItem {
  project_id: string;
  project_name: string;
  pilier_strategique: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface ScenarioMonth {
  month: string;
  charge: number;
  capacite: number;
  rate: number;
  color: ColorName;
}

export interface Scenario {
  scenario: string;
  project_count: number;
  project_ids: string[];
  charge_cumulee: number;
  global_rate: number;
  global_color: ColorName;
  monthly: ScenarioMonth[];
}

export interface PrioritizationPlan {
  months: string[];
  scenarios: Scenario[];
}

export interface CapacityCell {
  team: string;
  month: string;
  etp_team: number | null;
  etp_projet: number | null;
  part_projet: number | null;
  jours_indispo: number | null;
  capa_projet: number | null;
  exists: boolean;
}

export interface CapacityInput {
  team: string;
  month: string;
  etp_team: number | null;
  etp_projet: number | null;
  jours_indispo: number | null;
}

export interface ChangeEntry {
  id: number;
  ts: string;
  user_email: string;
  table_name: string;
  row_pk: string;
  action: "insert" | "update" | "delete";
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}
