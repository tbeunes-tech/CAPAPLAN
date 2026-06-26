import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { COLOR_STYLE, monthShort, rateLabel } from "../dash";
import ExportButton from "../components/ExportButton";
import type { Overload } from "../types";

/** Filtre texte « contient » insensible à la casse, appliqué à une chaîne calculée par colonne. */
function textFilter(getStr: (o: Overload) => string) {
  return (row: { original: Overload }, _id: string, value: string) =>
    getStr(row.original).toLowerCase().includes(String(value).toLowerCase());
}

export default function OverloadsPage() {
  const { start } = useWindowStart();
  const [sorting, setSorting] = useState<SortingState>([{ id: "ecart_jours", desc: true }]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const q = useQuery({ queryKey: ["overloads", start], queryFn: () => api.overloads(start) });

  const columns = useMemo<ColumnDef<Overload>[]>(
    () => [
      {
        id: "team", header: "Équipe", accessorFn: (o) => o.team,
        filterFn: textFilter((o) => o.team),
      },
      {
        id: "month", header: "Mois", accessorFn: (o) => o.month, // ISO → tri chronologique
        cell: ({ row }) => monthShort(row.original.month),
        filterFn: textFilter((o) => monthShort(o.month)),
      },
      {
        id: "charge", header: "Charge (j)", accessorFn: (o) => o.charge,
        cell: ({ getValue }) => (getValue() as number).toFixed(1),
        filterFn: textFilter((o) => o.charge.toFixed(1)),
        meta: { right: true },
      },
      {
        id: "capacite", header: "Capacité (j)", accessorFn: (o) => o.capacite,
        cell: ({ getValue }) => (getValue() as number).toFixed(1),
        filterFn: textFilter((o) => o.capacite.toFixed(1)),
        meta: { right: true },
      },
      {
        id: "rate", header: "Taux", accessorFn: (o) => o.rate, // numérique → tri correct
        cell: ({ row }) => (
          <span style={{ ...COLOR_STYLE[row.original.color], padding: "1px 6px", borderRadius: 6 }}>
            {rateLabel(row.original.rate, row.original.color)}
          </span>
        ),
        filterFn: textFilter((o) => rateLabel(o.rate, o.color)),
        meta: { right: true },
      },
      {
        id: "ecart_jours", header: "Écart (j)", accessorFn: (o) => o.ecart_jours,
        cell: ({ getValue }) => <strong>+{(getValue() as number).toFixed(1)}</strong>,
        filterFn: textFilter((o) => o.ecart_jours.toFixed(1)),
        meta: { right: true },
      },
    ],
    [],
  );

  const table = useReactTable({
    data: q.data ?? [],
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;

  const rows = table.getRowModel().rows;

  return (
    <div>
      <h2>Analyse des surcharges (§5.6)</h2>
      <div className="toolbar">
        <span className="muted">
          {rows.length} couple(s) (équipe, mois) en dépassement &gt; 100 %. Cliquez un en-tête pour
          trier ; tapez sous une colonne pour filtrer.
        </span>
        {columnFilters.length > 0 && (
          <button onClick={() => setColumnFilters([])}>Réinitialiser les filtres</button>
        )}
        <ExportButton
          name="surcharges"
          headers={["Équipe", "Mois", "Charge (j)", "Capacité (j)", "Taux", "Écart (j)"]}
          rows={rows.map(({ original: o }) => [
            o.team, monthShort(o.month), o.charge, o.capacite,
            rateLabel(o.rate, o.color), o.ecart_jours,
          ])}
        />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => {
                  const right = (h.column.columnDef.meta as { right?: boolean } | undefined)?.right;
                  return (
                    <th key={h.id} style={{ textAlign: right ? "right" : "left" }}>
                      <span
                        style={{ cursor: "pointer", userSelect: "none" }}
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}
                      </span>
                      <input
                        className="col-filter"
                        placeholder="filtrer…"
                        value={(h.column.getFilterValue() as string) ?? ""}
                        onChange={(e) => h.column.setFilterValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const right = (cell.column.columnDef.meta as { right?: boolean } | undefined)?.right;
                  return (
                    <td key={cell.id} style={{ textAlign: right ? "right" : "left" }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
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
