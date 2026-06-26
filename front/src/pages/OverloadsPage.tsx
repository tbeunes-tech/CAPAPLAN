import { Fragment, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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

function textFilter(getStr: (o: Overload) => string) {
  return (row: { original: Overload }, _id: string, value: string) =>
    getStr(row.original).toLowerCase().includes(String(value).toLowerCase());
}

/** Détail « pourquoi cette surcharge » : projets qui chargent l'équipe ce mois-là, classés. */
function OverloadReason({ o, start }: { o: Overload; start: string }) {
  const q = useQuery({
    queryKey: ["team-load-detail", o.team, start],
    queryFn: () => api.teamLoadDetail(o.team, start),
  });
  if (q.isLoading) return <span className="muted">Analyse…</span>;
  const data = q.data;
  if (!data) return <span className="muted">—</span>;

  const idx = data.months.indexOf(o.month);
  const contributors = data.rows
    .map((r) => ({ ...r, day: idx >= 0 ? r.values[idx] ?? 0 : 0 }))
    .filter((r) => r.day > 0)
    .sort((a, b) => b.day - a.day);
  const totalCharge = contributors.reduce((s, r) => s + r.day, 0);
  const nullCapa = o.color === "overload_null_capacity";

  return (
    <div className="reason">
      <p className="reason-head">
        {nullCapa ? (
          <>⚠ <strong>Aucune capacité déclarée</strong> pour {o.team} en {monthShort(o.month)} :
            {" "}{o.charge.toFixed(1)} j de charge sont posés sur une capacité de 0.</>
        ) : (
          <>Charge <strong>{o.charge.toFixed(1)} j</strong> pour une capacité de{" "}
            <strong>{o.capacite.toFixed(1)} j</strong> → dépassement de{" "}
            <strong style={COLOR_STYLE.red}>+{o.ecart_jours.toFixed(1)} j</strong>.
            {" "}En cause, ces {contributors.length} projet(s) :</>
        )}
      </p>
      <table className="sub-table">
        <thead>
          <tr>
            <th>Project ID</th><th>Projet</th><th>Prio</th><th>Prio DSI</th>
            <th style={{ textAlign: "right" }}>Charge {monthShort(o.month)} (j)</th>
            <th style={{ textAlign: "right" }}>Part</th>
          </tr>
        </thead>
        <tbody>
          {contributors.map((r) => (
            <tr key={r.project_id}>
              <td><Link to={`/portfolio/${r.project_id}/loads`}>{r.project_id}</Link></td>
              <td>{r.project_name}</td>
              <td>{r.priorite ? <span className="chip">{r.priorite}</span> : "—"}</td>
              <td>{r.prio_dsi ? <span className="chip chip-dsi">{r.prio_dsi}</span> : "—"}</td>
              <td style={{ textAlign: "right" }}>{r.day.toFixed(1)}</td>
              <td style={{ textAlign: "right" }}>
                {totalCharge ? Math.round((r.day / totalCharge) * 100) : 0}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!nullCapa && (
        <p className="muted" style={{ marginTop: 4 }}>
          Réduire/décaler les projets les moins prioritaires de cette équipe ramènerait le taux sous 100 %.
        </p>
      )}
    </div>
  );
}

export default function OverloadsPage() {
  const { start } = useWindowStart();
  const [sorting, setSorting] = useState<SortingState>([{ id: "ecart_jours", desc: true }]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const q = useQuery({ queryKey: ["overloads", start], queryFn: () => api.overloads(start) });

  const toggle = (k: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });

  const columns = useMemo<ColumnDef<Overload>[]>(
    () => [
      {
        id: "expander", header: "", enableSorting: false, enableColumnFilter: false,
        cell: ({ row, table }) => {
          const meta = table.options.meta as { expanded: Set<string>; toggle: (k: string) => void };
          const k = `${row.original.team}|${row.original.month}`;
          return (
            <button className="chevron" onClick={() => meta.toggle(k)}
              aria-label={meta.expanded.has(k) ? "Replier" : "Déplier"}>
              {meta.expanded.has(k) ? "▾" : "▸"}
            </button>
          );
        },
      },
      { id: "team", header: "Équipe", accessorFn: (o) => o.team, filterFn: textFilter((o) => o.team) },
      {
        id: "month", header: "Mois", accessorFn: (o) => o.month,
        cell: ({ row }) => monthShort(row.original.month),
        filterFn: textFilter((o) => monthShort(o.month)),
      },
      {
        id: "charge", header: "Charge (j)", accessorFn: (o) => o.charge, meta: { right: true },
        cell: ({ getValue }) => (getValue() as number).toFixed(1),
        filterFn: textFilter((o) => o.charge.toFixed(1)),
      },
      {
        id: "capacite", header: "Capacité (j)", accessorFn: (o) => o.capacite, meta: { right: true },
        cell: ({ getValue }) => (getValue() as number).toFixed(1),
        filterFn: textFilter((o) => o.capacite.toFixed(1)),
      },
      {
        id: "rate", header: "Taux", accessorFn: (o) => o.rate, meta: { right: true },
        cell: ({ row }) => (
          <span style={{ ...COLOR_STYLE[row.original.color], padding: "1px 6px", borderRadius: 6 }}>
            {rateLabel(row.original.rate, row.original.color)}
          </span>
        ),
        filterFn: textFilter((o) => rateLabel(o.rate, o.color)),
      },
      {
        id: "ecart_jours", header: "Écart (j)", accessorFn: (o) => o.ecart_jours, meta: { right: true },
        cell: ({ getValue }) => <strong>+{(getValue() as number).toFixed(1)}</strong>,
        filterFn: textFilter((o) => o.ecart_jours.toFixed(1)),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: q.data ?? [],
    columns,
    state: { sorting, columnFilters },
    meta: { expanded, toggle },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;

  const rows = table.getRowModel().rows;
  const nCols = columns.length;

  return (
    <div>
      <h2>Analyse des surcharges (§5.6)</h2>
      <div className="toolbar">
        <span className="muted">
          {rows.length} couple(s) (équipe, mois) &gt; 100 %. Triez par en-tête, filtrez par colonne,
          ou <strong>dépliez le chevron</strong> pour voir les projets responsables de la surcharge.
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
                  const sortable = h.column.getCanSort();
                  return (
                    <th key={h.id} style={{ textAlign: right ? "right" : "left" }}>
                      <span
                        style={{ cursor: sortable ? "pointer" : "default", userSelect: "none" }}
                        onClick={sortable ? h.column.getToggleSortingHandler() : undefined}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}
                      </span>
                      {h.column.getCanFilter() && (
                        <input
                          className="col-filter"
                          placeholder="filtrer…"
                          value={(h.column.getFilterValue() as string) ?? ""}
                          onChange={(e) => h.column.setFilterValue(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.map((row) => {
              const k = `${row.original.team}|${row.original.month}`;
              return (
                <Fragment key={row.id}>
                  <tr className={expanded.has(k) ? "team-row open" : "team-row"}>
                    {row.getVisibleCells().map((cell) => {
                      const right = (cell.column.columnDef.meta as { right?: boolean } | undefined)?.right;
                      return (
                        <td key={cell.id} style={{ textAlign: right ? "right" : "left" }}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      );
                    })}
                  </tr>
                  {expanded.has(k) && (
                    <tr className="detail-row">
                      <td />
                      <td colSpan={nCols - 1} style={{ padding: "8px 10px" }}>
                        <OverloadReason o={row.original} start={start} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
