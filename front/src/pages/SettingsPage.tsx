import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import type { ProjectLeader } from "../types";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { can } = useAuth();
  const isAdmin = can("admin");
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const q = useQuery({ queryKey: ["project-leaders"], queryFn: api.projectLeaders });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["project-leaders"] });

  const create = useMutation({
    mutationFn: (name: string) => api.createLeader(name),
    onSuccess: () => { setNewName(""); setError(null); invalidate(); },
    onError: (e: Error) => setError(e.message),
  });
  const update = useMutation({
    mutationFn: (v: { id: number; body: { name?: string; active?: boolean } }) => api.updateLeader(v.id, v.body),
    onSuccess: () => { setEditing(null); invalidate(); },
    onError: (e: Error) => setError(e.message),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.deleteLeader(id),
    onSuccess: invalidate,
    onError: (e: Error) => alert(e.message),
  });
  const importer = useMutation({
    mutationFn: () => api.importLeadersFromProjects(),
    onSuccess: (r) => { alert(`${r.added} chef(s) ajouté(s) depuis les projets (total ${r.total}).`); invalidate(); },
  });

  if (!isAdmin) return <p className="err">Réservé aux administrateurs.</p>;
  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;
  const leaders = q.data!;

  return (
    <div>
      <h2>Paramétrage</h2>

      <section className="settings-card">
        <h3>Chefs de projet</h3>
        <p className="muted">
          Liste proposée dans le champ « Chef de projet » des projets. Tu peux en ajouter,
          renommer, désactiver (masqué des suggestions) ou supprimer.
        </p>

        <div className="toolbar">
          <input
            type="text"
            placeholder="Nom du chef de projet"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && newName.trim() && create.mutate(newName.trim())}
          />
          <button className="primary" disabled={!newName.trim() || create.isPending}
            onClick={() => create.mutate(newName.trim())}>
            + Ajouter
          </button>
          <button disabled={importer.isPending} onClick={() => importer.mutate()}
            title="Alimenter la liste à partir des chefs déjà saisis sur les projets">
            Importer depuis les projets
          </button>
          <span className="muted">{leaders.length} chef(s)</span>
        </div>
        {error && <p className="err">⚠ {error}</p>}

        <div className="table-wrap" style={{ maxHeight: "60vh" }}>
          <table>
            <thead>
              <tr><th>Nom</th><th>Actif</th><th /></tr>
            </thead>
            <tbody>
              {leaders.map((l: ProjectLeader) => (
                <tr key={l.id}>
                  <td>
                    {editing?.id === l.id ? (
                      <input value={editing.name} autoFocus
                        onChange={(e) => setEditing({ id: l.id, name: e.target.value })}
                        onKeyDown={(e) => e.key === "Enter" && update.mutate({ id: l.id, body: { name: editing.name } })} />
                    ) : l.name}
                  </td>
                  <td>
                    <input type="checkbox" checked={l.active}
                      onChange={() => update.mutate({ id: l.id, body: { active: !l.active } })} />
                  </td>
                  <td>
                    <span style={{ display: "flex", gap: 6 }}>
                      {editing?.id === l.id ? (
                        <>
                          <button className="primary" onClick={() => update.mutate({ id: l.id, body: { name: editing.name } })}>OK</button>
                          <button onClick={() => setEditing(null)}>Annuler</button>
                        </>
                      ) : (
                        <button onClick={() => setEditing({ id: l.id, name: l.name })}>Renommer</button>
                      )}
                      <button className="danger" onClick={() => { if (confirm(`Supprimer « ${l.name} » ?`)) del.mutate(l.id); }}>✕</button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
