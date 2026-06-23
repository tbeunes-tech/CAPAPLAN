import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { useAuth } from "../AuthContext";
import PivotTable from "../components/PivotTable";
import CapacityEditor from "../components/CapacityEditor";
import ExportButton from "../components/ExportButton";
import { monthShort } from "../dash";

export default function CapacityPage() {
  const { start } = useWindowStart();
  const { can } = useAuth();
  const canEdit = can("admin");
  const [cell, setCell] = useState<{ team: string; month: string } | null>(null);

  const q = useQuery({ queryKey: ["capacity", start], queryFn: () => api.capacityPivot(start) });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;

  return (
    <div>
      <h2>Capacité équipe (§5.4)</h2>
      <div className="toolbar">
        <span className="muted">
          Capacité projet mensuelle <code>capa_projet</code> (§6.7), en jours.{" "}
          {canEdit ? (
            <strong>Cliquez une cellule pour éditer les ETP / indispos (Admin).</strong>
          ) : (
            "L'édition est réservée aux Admin."
          )}
        </span>
        <ExportButton
          name="capacite-equipe"
          headers={["Équipe", ...q.data!.months.map(monthShort)]}
          rows={q.data!.rows.map((r) => [r.team, ...r.values])}
        />
      </div>
      <PivotTable
        data={q.data!}
        hideEmpty={!canEdit}
        onCellClick={canEdit ? (team, month) => setCell({ team, month }) : undefined}
      />
      {cell && (
        <CapacityEditor team={cell.team} month={cell.month} onClose={() => setCell(null)} />
      )}
    </div>
  );
}
