import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { useAuth } from "../AuthContext";
import type { LoadConflict } from "../types";

function monthLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { month: "short", year: "2-digit" });
}
const key = (team: string, month: string) => `${team}|${month}`;

interface Edit {
  days: number;
  baseUpdatedAt: string | null; // horodatage de la cellule au moment où on a commencé à l'éditer
}

export default function LoadGridPage() {
  const { projectId = "" } = useParams();
  const { can } = useAuth();
  const canWrite = can("contributor");
  const qc = useQueryClient();

  const gridQ = useQuery({
    queryKey: ["loads", projectId],
    queryFn: () => api.getLoadGrid(projectId),
    refetchInterval: 15_000, // rafraîchissement live : voir les saisies des collègues (objectif n°1)
  });
  const projectQ = useQuery({ queryKey: ["project", projectId], queryFn: () => api.getProject(projectId) });

  const [edits, setEdits] = useState<Record<string, Edit>>({});
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<LoadConflict[] | null>(null);

  useEffect(() => {
    setEdits({});
    setConflicts(null);
  }, [projectId]);

  // base : valeur + horodatage serveur courant par cellule.
  const base = useMemo(() => {
    const m: Record<string, { days: number; updatedAt: string | null }> = {};
    gridQ.data?.cells.forEach((c) => (m[key(c.team, c.month)] = { days: c.days, updatedAt: c.updated_at }));
    return m;
  }, [gridQ.data]);

  // Cellules que j'édite mais qu'un collègue a modifiées entre-temps (conflit potentiel).
  const stale = useMemo(() => {
    const s = new Set<string>();
    for (const k of Object.keys(edits)) {
      if ((base[k]?.updatedAt ?? null) !== edits[k].baseUpdatedAt) s.add(k);
    }
    return s;
  }, [edits, base]);

  const save = useMutation({
    mutationFn: () => {
      const cells = Object.entries(edits).map(([k, e]) => {
        const [team, month] = k.split("|");
        return { team, month, days: e.days, base_updated_at: e.baseUpdatedAt };
      });
      return api.saveLoadGrid(projectId, cells);
    },
    onSuccess: () => {
      setEdits({});
      setConflicts(null);
      setSavedAt(new Date().toLocaleTimeString("fr-FR"));
      qc.invalidateQueries({ queryKey: ["loads", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) {
        const detail = (err.body as { detail?: { conflicts?: LoadConflict[] } })?.detail;
        setConflicts(detail?.conflicts ?? []);
        gridQ.refetch(); // recharge les valeurs serveur pour les afficher
      } else {
        alert((err as Error).message);
      }
    },
  });

  if (gridQ.isLoading) return <p>Chargement de la grille…</p>;
  if (gridQ.isError) return <p className="err">Erreur : {(gridQ.error as Error).message}</p>;
  const grid = gridQ.data!;
  const dirtyCount = Object.keys(edits).length;

  const cellValue = (team: string, month: string): number => {
    const k = key(team, month);
    return k in edits ? edits[k].days : base[k]?.days ?? 0;
  };

  const setCell = (team: string, month: string, v: number) => {
    const k = key(team, month);
    setEdits((prev) => {
      const next = { ...prev };
      const baseDays = base[k]?.days ?? 0;
      if (v === baseDays) {
        delete next[k]; // retour à la valeur serveur → plus une modif
      } else {
        next[k] = { days: v, baseUpdatedAt: k in prev ? prev[k].baseUpdatedAt : base[k]?.updatedAt ?? null };
      }
      return next;
    });
  };

  // Résolution de conflit : écraser avec mes valeurs (on adopte l'horodatage serveur courant).
  const overwriteConflicts = () => {
    if (!conflicts) return;
    setEdits((prev) => {
      const next = { ...prev };
      for (const c of conflicts) {
        const k = key(c.team, c.month);
        if (k in next) next[k] = { ...next[k], baseUpdatedAt: c.server_updated_at };
      }
      return next;
    });
    setConflicts(null);
    setTimeout(() => save.mutate(), 0);
  };
  const discardConflicts = () => {
    if (!conflicts) return;
    setEdits((prev) => {
      const next = { ...prev };
      for (const c of conflicts) delete next[key(c.team, c.month)];
      return next;
    });
    setConflicts(null);
  };

  return (
    <div>
      <div className="toolbar">
        <Link to="/portfolio">← Portefeuille</Link>
        <strong>{projectId} — {projectQ.data?.project_name ?? ""}</strong>
        <span className="muted">{grid.teams.length} équipes × {grid.months.length} mois</span>
        {canWrite && (
          <button className="primary" disabled={dirtyCount === 0 || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Enregistrement…" : `Enregistrer (${dirtyCount})`}
          </button>
        )}
        {!canWrite && <span className="muted">Lecture seule (rôle Lecteur)</span>}
        {savedAt && dirtyCount === 0 && <span className="muted">✓ enregistré à {savedAt}</span>}
        <span className="muted" style={{ marginLeft: "auto" }}>
          {gridQ.isFetching ? "↻ synchro…" : "à jour"} · rafraîchi auto toutes les 15 s
        </span>
      </div>

      {conflicts && (
        <div className="banner conflict">
          <strong>⚠ Conflit de saisie</strong> — {conflicts.length} cellule(s) ont été modifiées par
          un autre utilisateur. Rien n'a été enregistré.
          <ul>
            {conflicts.map((c) => (
              <li key={key(c.team, c.month)}>
                {c.team} · {monthLabel(c.month)} : serveur = <strong>{c.server_days}</strong> j,
                vous = <strong>{c.your_days}</strong> j
              </li>
            ))}
          </ul>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="primary" onClick={overwriteConflicts}>Écraser avec mes valeurs</button>
            <button onClick={discardConflicts}>Garder les valeurs du serveur</button>
          </div>
        </div>
      )}

      {stale.size > 0 && !conflicts && (
        <div className="banner warn">
          ⚠ {stale.size} cellule(s) que vous éditez (en orange) ont été modifiées par un collègue.
          À l'enregistrement, vous pourrez choisir d'écraser ou de garder leur version.
        </div>
      )}

      <div className="banner info">
        Grille de saisie (jours-homme). Seules les cellules
        <span className="grid-cell dirty" style={{ display: "inline-block", width: "auto", padding: "0 6px", margin: "0 4px" }}>modifiées</span>
        sont envoyées. Sauvegarde concurrente protégée : si un collègue a changé une cellule entre
        temps, vous êtes prévenu plutôt que de l'écraser silencieusement.
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="sticky-col">Équipe</th>
              {grid.months.map((m) => (
                <th key={m} style={{ textAlign: "right" }}>{monthLabel(m)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.teams.map((team) => (
              <tr key={team}>
                <td className="sticky-col">{team}</td>
                {grid.months.map((m) => {
                  const k = key(team, m);
                  const dirty = k in edits;
                  const isStale = stale.has(k);
                  return (
                    <td key={m} style={{ padding: 2 }}>
                      <input
                        className={"grid-cell" + (isStale ? " stale" : dirty ? " dirty" : "")}
                        type="number"
                        step="0.5"
                        min="0"
                        disabled={!canWrite}
                        title={isStale ? "Modifiée par un collègue depuis votre édition" : undefined}
                        value={cellValue(team, m)}
                        onChange={(e) => setCell(team, m, e.target.value === "" ? 0 : Number(e.target.value))}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
