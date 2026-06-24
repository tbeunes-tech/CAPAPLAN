import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Project, ProjectInput, Referentials } from "../types";

interface Props {
  refs: Referentials;
  editing: Project | null; // null = création
  onClose: () => void;
  readOnly?: boolean;
}

// Garantit que la valeur actuelle du projet figure dans les options (cas d'une valeur
// désactivée dans le référentiel mais encore portée par ce projet legacy).
function withCurrent(options: string[] | undefined, current: string | null | undefined): string[] {
  const opts = options ?? [];
  return current && !opts.includes(current) ? [current, ...opts] : opts;
}

const SELECT_FIELDS: { key: keyof ProjectInput; label: string; refKey: string }[] = [
  { key: "entite", label: "Entité", refKey: "entite" },
  { key: "domain_lead", label: "Domain lead", refKey: "domain_lead" },
  { key: "status", label: "Statut", refKey: "status" },
  { key: "priorite", label: "Priorité", refKey: "priorite" },
  { key: "pilier_strategique", label: "Pilier stratégique", refKey: "pilier_strategique" },
];

export default function ProjectForm({ refs, editing, onClose, readOnly = false }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ProjectInput>(() =>
    editing
      ? { ...editing }
      : { project_name: "", status: "Scheduled", priorite: "P2" },
  );
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof ProjectInput, v: string) =>
    setForm((f) => ({ ...f, [k]: v === "" ? null : v }));

  const mutation = useMutation({
    mutationFn: async () => {
      const body: ProjectInput = { ...form };
      return editing
        ? api.updateProject(editing.project_id, body)
        : api.createProject(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>
          {readOnly ? "Consulter" : editing ? "Éditer" : "Nouveau projet"}{" "}
          {editing?.project_id ?? ""}
        </h2>
        {readOnly && <div className="banner info">Lecture seule — votre rôle (Lecteur) n'autorise pas la modification.</div>}
        {editing && (
          <p className="muted">
            ID {editing.project_id} ·{" "}
            <span className={"badge " + (editing.in_plan ? "in-plan" : "off-plan")}>
              {editing.in_plan ? "In Plan" : "Hors plan"}
            </span>{" "}
            (calculé) · dernière maj {editing.last_update?.slice(0, 16).replace("T", " ") ?? "—"}
          </p>
        )}
        <div className="form-grid">
          <div className="field full">
            <label>Nom du projet *</label>
            <input
              value={form.project_name ?? ""}
              onChange={(e) => set("project_name", e.target.value)}
            />
          </div>

          {SELECT_FIELDS.map(({ key, label, refKey }) => (
            <div className="field" key={key}>
              <label>{label}</label>
              <select value={(form[key] as string) ?? ""} onChange={(e) => set(key, e.target.value)}>
                <option value="">—</option>
                {withCurrent(refs[refKey], form[key] as string).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          ))}

          <div className="field">
            <label>Chef de projet</label>
            <input
              list="ref-project_leader"
              value={form.project_leader ?? ""}
              onChange={(e) => set("project_leader", e.target.value)}
              placeholder="Choisir ou saisir…"
            />
            <datalist id="ref-project_leader">
              {(refs.project_leader ?? []).map((name) => <option key={name} value={name} />)}
            </datalist>
          </div>
          <div className="field">
            <label>Programme</label>
            <input
              list="ref-programme"
              value={form.programme ?? ""}
              onChange={(e) => set("programme", e.target.value)}
              placeholder="Choisir ou saisir…"
            />
            <datalist id="ref-programme">
              {(refs.programme ?? []).map((p) => <option key={p} value={p} />)}
            </datalist>
          </div>
          <div className="field">
            <label>Budget item</label>
            <input value={form.budget_item ?? ""} onChange={(e) => set("budget_item", e.target.value)} />
          </div>
          <div className="field">
            <label>Budget owner</label>
            <input value={form.budget_owner ?? ""} onChange={(e) => set("budget_owner", e.target.value)} />
          </div>
          <div className="field">
            <label>Date de début</label>
            <input
              type="date"
              value={form.start_date ?? ""}
              onChange={(e) => set("start_date", e.target.value)}
            />
          </div>
          <div className="field">
            <label>Date de fin</label>
            <input
              type="date"
              value={form.end_date ?? ""}
              onChange={(e) => set("end_date", e.target.value)}
            />
          </div>
        </div>

        {error && <p className="err">⚠ {error}</p>}

        <div className="modal-actions">
          <button onClick={onClose}>{readOnly ? "Fermer" : "Annuler"}</button>
          {!readOnly && (
            <button
              className="primary"
              disabled={!form.project_name || mutation.isPending}
              onClick={() => {
                setError(null);
                mutation.mutate();
              }}
            >
              {mutation.isPending ? "Enregistrement…" : "Enregistrer"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
