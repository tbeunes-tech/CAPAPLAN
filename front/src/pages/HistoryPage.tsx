import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { monthShort } from "../dash";
import ExportButton from "../components/ExportButton";
import type { ChangeEntry } from "../types";

const FIELD_LABELS: Record<string, string> = {
  status: "Statut", priorite: "Priorité", project_name: "Nom", project_leader: "Chef de projet",
  entite: "Entité", domain_lead: "Domain lead", pilier_strategique: "Pilier", programme: "Programme",
  budget_item: "Budget item", budget_owner: "Budget owner", start_date: "Début", end_date: "Fin",
  in_plan: "In Plan", days: "Charge (j)", total_project_load: "Charge totale", last_update: "Dernière maj",
};
// Colonnes dérivées/techniques : recalculées automatiquement à chaque saisie → on les masque
// pour ne montrer que les vraies actions métier (statut, dates, charges…).
const HIDDEN = new Set(["updated_at", "last_update", "total_project_load"]);
const ACTION_LABEL = { insert: "Création", update: "Modification", delete: "Suppression" } as const;

function fmtVal(v: unknown): string {
  if (v === null || v === undefined || v === "") return "∅";
  if (typeof v === "boolean") return v ? "oui" : "non";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) return v.slice(0, 16).replace("T", " ");
  return String(v);
}

function target(e: ChangeEntry): string {
  if (e.table_name === "monthly_loads") {
    const [, team, month] = e.row_pk.split("|");
    return `Charge · ${team} · ${month ? monthShort(month) : ""}`;
  }
  return "Projet";
}

/** Changements lisibles (champs modifiés hors bruit technique). Vide = entrée à masquer. */
function changes(e: ChangeEntry): string[] {
  if (e.action === "delete") return ["Élément supprimé"];
  if (e.action === "insert") {
    const a = e.after ?? {};
    if (e.table_name === "monthly_loads") return [`Charge = ${fmtVal(a.days)} j`];
    return [`Créé (${fmtVal(a.project_name)}, ${fmtVal(a.status)})`];
  }
  const before = e.before ?? {}, after = e.after ?? {};
  return Object.keys(after)
    .filter((k) => !HIDDEN.has(k))
    .map((k) => `${FIELD_LABELS[k] ?? k} : ${fmtVal(before[k])} → ${fmtVal(after[k])}`);
}

/** Une entrée n'a d'intérêt que si elle décrit au moins un changement métier. */
function isMeaningful(e: ChangeEntry): boolean {
  return e.action !== "update" || changes(e).length > 0;
}

export default function HistoryPage() {
  const { projectId = "" } = useParams();
  const projQ = useQuery({ queryKey: ["project", projectId], queryFn: () => api.getProject(projectId) });
  const histQ = useQuery({ queryKey: ["history", projectId], queryFn: () => api.projectHistory(projectId) });

  if (histQ.isLoading) return <p>Chargement de l'historique…</p>;
  if (histQ.isError) return <p className="err">Erreur : {(histQ.error as Error).message}</p>;
  const entries = histQ.data!.filter(isMeaningful);

  return (
    <div>
      <div className="toolbar">
        <Link to="/portfolio">← Portefeuille</Link>
        <strong>Historique · {projectId} — {projQ.data?.project_name ?? ""}</strong>
        <span className="muted">{entries.length} modification(s)</span>
        <ExportButton
          name={`historique-${projectId}`}
          headers={["Date", "Utilisateur", "Cible", "Action", "Détail"]}
          rows={entries.map((e) => [
            fmtVal(e.ts), e.user_email, target(e), ACTION_LABEL[e.action], changes(e).join(" ; "),
          ])}
        />
      </div>

      <p className="muted">
        Journal d'audit (§8.2) : qui a changé quoi, quand, avant → après. Couvre le projet et ses
        charges. Conservation intégrale, rien n'est écrasé sans trace.
      </p>

      {entries.length === 0 ? (
        <p className="muted">Aucune modification enregistrée depuis la mise en service (l'import initial n'est pas journalisé).</p>
      ) : (
        <ul className="timeline">
          {entries.map((e) => (
            <li key={e.id} className={`tl-${e.action}`}>
              <div className="tl-head">
                <span className="tl-when">{fmtVal(e.ts)}</span>
                <span className={`badge tl-action ${e.action}`}>{ACTION_LABEL[e.action]}</span>
                <span className="tl-target">{target(e)}</span>
                <span className="muted">par {e.user_email}</span>
              </div>
              <ul className="tl-changes">
                {changes(e).map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
