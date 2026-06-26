import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { api } from "../api";
import type { Project } from "../types";
import ProjectForm from "../components/ProjectForm";
import ExportButton from "../components/ExportButton";
import { useAuth } from "../AuthContext";

function qcSummary(p: Project): string {
  return [p.qc.date_error, p.qc.status_error, p.qc.obsolete_forecast, p.qc.leader_error]
    .filter(Boolean)
    .join(" · ");
}

export default function PortfolioPage() {
  const qc = useQueryClient();
  const { can } = useAuth();
  const canWrite = can("contributor");
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "project_id", desc: false }]);
  const [editing, setEditing] = useState<Project | null>(null);
  const [showForm, setShowForm] = useState(false);

  const refsQ = useQuery({ queryKey: ["referentials"], queryFn: api.referentials });
  const projectsQ = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  const columns = useMemo<ColumnDef<Project>[]>(
    () => [
      {
        id: "qc",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.qc.has_error ? (
            <span className="qc-dot" title={qcSummary(row.original)}>
              ●
            </span>
          ) : null,
      },
      { accessorKey: "project_id", header: "ID" },
      { accessorKey: "entite", header: "Entité" },
      { accessorKey: "project_name", header: "Projet" },
      { accessorKey: "domain_lead", header: "Domain lead" },
      { accessorKey: "project_leader", header: "Chef de projet" },
      { accessorKey: "status", header: "Statut" },
      { accessorKey: "priorite", header: "Prio" },
      { accessorKey: "prio_dsi", header: "Prio DSI" },
      { accessorKey: "pilier_strategique", header: "Pilier" },
      { accessorKey: "programme", header: "Programme" },
      { accessorKey: "start_date", header: "Début" },
      { accessorKey: "end_date", header: "Fin" },
      {
        accessorKey: "total_project_load",
        header: "Charge (j)",
        cell: ({ getValue }) => (getValue() as number | null) ?? 0,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <span style={{ display: "flex", gap: 6 }}>
            <button
              onClick={() => {
                setEditing(row.original);
                setShowForm(true);
              }}
            >
              {canWrite ? "Éditer" : "Voir"}
            </button>
            <Link to={`/portfolio/${row.original.project_id}/loads`}>
              <button>Charge</button>
            </Link>
            <Link to={`/portfolio/${row.original.project_id}/history`}>
              <button title="Historique des modifications">Hist.</button>
            </Link>
            {canWrite && (
              <button
                className="danger"
                onClick={() => {
                  if (confirm(`Supprimer ${row.original.project_id} ?`)) del.mutate(row.original.project_id);
                }}
              >
                ✕
              </button>
            )}
          </span>
        ),
      },
    ],
    [del, canWrite],
  );

  const table = useReactTable({
    data: projectsQ.data ?? [],
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (projectsQ.isError)
    return <p className="err">Erreur de chargement : {(projectsQ.error as Error).message}. Le backend (port 8000) est-il lancé ?</p>;

  const rows = table.getRowModel().rows;
  const errorCount = (projectsQ.data ?? []).filter((p) => p.qc.has_error).length;

  return (
    <div>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Filtrer (nom, entité, statut, chef…)"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
        <span className="muted">
          {rows.length} projet(s) · <span className="qc-dot">●</span> {errorCount} en erreur QC
        </span>
        <ExportButton
          name="portefeuille-projets"
          headers={["ID", "Entité", "Projet", "Domain lead", "Chef de projet", "Statut",
                    "Priorité", "Prio DSI", "Pilier", "Programme", "Début", "Fin",
                    "Charge (j)", "Erreurs QC"]}
          rows={rows.map(({ original: p }) => [
            p.project_id, p.entite, p.project_name, p.domain_lead, p.project_leader, p.status,
            p.priorite, p.prio_dsi, p.pilier_strategique, p.programme,
            p.start_date, p.end_date, p.total_project_load ?? 0, qcSummary(p),
          ])}
        />
        {canWrite && (
          <button
            className="primary"
            disabled={!refsQ.data}
            onClick={() => {
              setEditing(null);
              setShowForm(true);
            }}
          >
            + Nouveau projet
          </button>
        )}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} onClick={h.column.getToggleSortingHandler()}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className={row.original.qc.has_error ? "qc-error" : ""}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && refsQ.data && (
        <ProjectForm
          refs={refsQ.data}
          editing={editing}
          readOnly={!canWrite}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
