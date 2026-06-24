import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import type { Referential } from "../types";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { can } = useAuth();
  const isAdmin = can("admin");
  const [category, setCategory] = useState<string>("project_leader");
  const [newValue, setNewValue] = useState("");
  const [editing, setEditing] = useState<{ id: number; value: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const catsQ = useQuery({ queryKey: ["ref-categories"], queryFn: api.referentialCategories });
  const listQ = useQuery({
    queryKey: ["ref-manage", category],
    queryFn: () => api.referentialsManage(category),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["ref-manage", category] });
    qc.invalidateQueries({ queryKey: ["referentials"] });       // listes des formulaires
    qc.invalidateQueries({ queryKey: ["projects"] });           // cascade éventuelle
  };

  const create = useMutation({
    mutationFn: (value: string) => api.createReferential(category, value),
    onSuccess: () => { setNewValue(""); setError(null); invalidate(); },
    onError: (e: Error) => setError(e.message),
  });
  const update = useMutation({
    mutationFn: (v: { id: number; body: { value?: string; active?: boolean } }) => api.updateReferential(v.id, v.body),
    onSuccess: (r) => {
      setEditing(null); setError(null);
      if (r.projects_updated) setNotice(`Renommé — ${r.projects_updated} projet(s) mis à jour automatiquement.`);
      invalidate();
    },
    onError: (e: Error) => setError(e.message),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.deleteReferential(id),
    onSuccess: invalidate,
    onError: (e: Error) => alert(e.message),
  });
  const seed = useMutation({
    mutationFn: () => api.seedReferentials(),
    onSuccess: (r) => { setNotice(`${r.added} valeur(s) ajoutée(s) depuis les défauts et les projets.`); invalidate(); },
  });

  if (!isAdmin) return <p className="err">Réservé aux administrateurs.</p>;

  const label = catsQ.data?.find((c) => c.key === category)?.label ?? category;

  return (
    <div>
      <h2>Paramétrage — référentiels</h2>
      <p className="muted">
        Toutes les listes des formulaires sont gérées ici. <strong>Renommer</strong> une valeur la
        met à jour automatiquement sur tous les projets qui l'utilisent (cascade).
      </p>

      <div className="toolbar">
        <label>
          Liste :{" "}
          <select value={category} onChange={(e) => { setCategory(e.target.value); setEditing(null); setError(null); }}>
            {(catsQ.data ?? []).map((c) => (
              <option key={c.key} value={c.key}>{c.label}</option>
            ))}
          </select>
        </label>
        <button disabled={seed.isPending} onClick={() => seed.mutate()}
          title="Ajouter les valeurs par défaut (§4) + celles déjà présentes sur les projets">
          Réamorcer depuis défauts + projets
        </button>
      </div>

      <section className="settings-card">
        <h3>{label}</h3>
        <div className="toolbar">
          <input type="text" placeholder={`Nouvelle valeur — ${label}`} value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && newValue.trim() && create.mutate(newValue.trim())} />
          <button className="primary" disabled={!newValue.trim() || create.isPending}
            onClick={() => create.mutate(newValue.trim())}>+ Ajouter</button>
          <span className="muted">{listQ.data?.length ?? 0} valeur(s)</span>
        </div>
        {error && <p className="err">⚠ {error}</p>}
        {notice && <p className="muted">✓ {notice}</p>}

        {listQ.isLoading ? <p>Chargement…</p> : (
          <div className="table-wrap" style={{ maxHeight: "60vh" }}>
            <table>
              <thead><tr><th>Valeur</th><th>Active</th><th /></tr></thead>
              <tbody>
                {(listQ.data ?? []).map((r: Referential) => (
                  <tr key={r.id}>
                    <td>
                      {editing?.id === r.id ? (
                        <input value={editing.value} autoFocus style={{ minWidth: 220 }}
                          onChange={(e) => setEditing({ id: r.id, value: e.target.value })}
                          onKeyDown={(e) => e.key === "Enter" && update.mutate({ id: r.id, body: { value: editing.value } })} />
                      ) : r.value}
                    </td>
                    <td>
                      <input type="checkbox" checked={r.active}
                        onChange={() => update.mutate({ id: r.id, body: { active: !r.active } })} />
                    </td>
                    <td>
                      <span style={{ display: "flex", gap: 6 }}>
                        {editing?.id === r.id ? (
                          <>
                            <button className="primary" onClick={() => update.mutate({ id: r.id, body: { value: editing.value } })}>OK</button>
                            <button onClick={() => setEditing(null)}>Annuler</button>
                          </>
                        ) : (
                          <button onClick={() => { setNotice(null); setEditing({ id: r.id, value: r.value }); }}>Renommer</button>
                        )}
                        <button className="danger" onClick={() => { if (confirm(`Supprimer « ${r.value} » ?`)) del.mutate(r.id); }}>✕</button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
