import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import type { Team } from "../types";
import ExportButton from "../components/ExportButton";

function TeamForm({ editing, onClose }: { editing: Team | null; onClose: () => void }) {
  const qc = useQueryClient();
  const isNew = editing === null;
  const [name, setName] = useState(editing?.name ?? "");
  const [manager, setManager] = useState(editing?.manager ?? "");
  const [capacite, setCapacite] = useState(editing?.capacite_etp?.toString() ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => {
      const body = {
        manager: manager || null,
        capacite_etp: capacite === "" ? null : Number(capacite),
        description: description || null,
      };
      return isNew ? api.createTeam({ name, ...body }) : api.updateTeam(editing!.name, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["teams"] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" style={{ width: 460 }} onClick={(e) => e.stopPropagation()}>
        <h2>{isNew ? "Nouvelle équipe" : `Éditer ${editing!.name}`}</h2>
        {!isNew && <p className="muted">Le nom est la clé de l'équipe → non modifiable.</p>}
        <div className="form-grid">
          <div className="field full">
            <label>Nom de l'équipe *</label>
            <input value={name} disabled={!isNew} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label>Manager</label>
            <input value={manager} onChange={(e) => setManager(e.target.value)} />
          </div>
          <div className="field">
            <label>Capacité ETP (réf.)</label>
            <input type="number" step="0.1" min="0" value={capacite}
              onChange={(e) => setCapacite(e.target.value)} />
          </div>
          <div className="field full">
            <label>Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>
        {error && <p className="err">⚠ {error}</p>}
        <div className="modal-actions">
          <button onClick={onClose}>Annuler</button>
          <button className="primary" disabled={!name || save.isPending}
            onClick={() => { setError(null); save.mutate(); }}>
            {save.isPending ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TeamsPage() {
  const qc = useQueryClient();
  const { can } = useAuth();
  const canEdit = can("admin");
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<Team | null>(null);
  const [showForm, setShowForm] = useState(false);

  const teamsQ = useQuery({ queryKey: ["teams"], queryFn: api.teams });
  const del = useMutation({
    mutationFn: (name: string) => api.deleteTeam(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
    onError: (e: Error) => alert(e.message),
  });

  const rows = useMemo(
    () => (teamsQ.data ?? []).filter((t) => t.name.toLowerCase().includes(filter.toLowerCase())),
    [teamsQ.data, filter],
  );

  if (teamsQ.isLoading) return <p>Chargement…</p>;
  if (teamsQ.isError) return <p className="err">Erreur : {(teamsQ.error as Error).message}</p>;

  return (
    <div>
      <h2>Équipes (§3.3)</h2>
      <div className="toolbar">
        <input type="search" placeholder="Filtrer par nom…" value={filter}
          onChange={(e) => setFilter(e.target.value)} />
        <span className="muted">{rows.length} équipe(s)</span>
        <ExportButton
          name="equipes"
          headers={["Équipe", "Manager", "Capacité ETP", "Description"]}
          rows={rows.map((t) => [t.name, t.manager ?? "", t.capacite_etp ?? "", t.description ?? ""])}
        />
        {canEdit && (
          <button className="primary" onClick={() => { setEditing(null); setShowForm(true); }}>
            + Nouvelle équipe
          </button>
        )}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Équipe</th>
              <th>Manager</th>
              <th style={{ textAlign: "right" }}>Capacité ETP</th>
              <th>Description</th>
              {canEdit && <th />}
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.name}>
                <td>{t.name}</td>
                <td>{t.manager ?? ""}</td>
                <td style={{ textAlign: "right" }}>{t.capacite_etp ?? ""}</td>
                <td>{t.description ?? ""}</td>
                {canEdit && (
                  <td>
                    <span style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => { setEditing(t); setShowForm(true); }}>Éditer</button>
                      <button className="danger"
                        onClick={() => { if (confirm(`Supprimer l'équipe ${t.name} ?`)) del.mutate(t.name); }}>
                        ✕
                      </button>
                    </span>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && <TeamForm editing={editing} onClose={() => setShowForm(false)} />}
    </div>
  );
}
