import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { monthShort } from "../dash";
import ExportButton from "../components/ExportButton";

const fmt = (v: number) => (v === 0 ? "" : v.toFixed(1));

/** Sous-lignes : un projet par ligne, charge par mois (drill-down §5.3). */
function TeamDetail({ team, start, months }: { team: string; start: string; months: string[] }) {
  const q = useQuery({
    queryKey: ["team-load-detail", team, start],
    queryFn: () => api.teamLoadDetail(team, start),
  });

  if (q.isLoading)
    return (
      <tr className="detail-row">
        <td className="sticky-col" />
        <td colSpan={months.length + 1} className="muted">Chargement du détail…</td>
      </tr>
    );
  const rows = q.data?.rows ?? [];
  if (!rows.length)
    return (
      <tr className="detail-row">
        <td className="sticky-col" />
        <td colSpan={months.length + 1} className="muted">Aucune charge in plan sur la fenêtre.</td>
      </tr>
    );

  return (
    <>
      {rows.map((r) => (
        <tr className="detail-row" key={r.project_id}>
          <td className="sticky-col detail-label" title={r.project_name}>
            <Link to={`/portfolio/${r.project_id}/loads`}>{r.project_id}</Link> · {r.project_name}
            {r.priorite && <span className="chip">{r.priorite}</span>}
            {r.prio_dsi && <span className="chip chip-dsi">{r.prio_dsi}</span>}
          </td>
          {r.values.map((v, i) => (
            <td key={i} style={{ textAlign: "right" }}>{fmt(v)}</td>
          ))}
        </tr>
      ))}
    </>
  );
}

export default function TeamLoadPage() {
  const { start } = useWindowStart();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const q = useQuery({ queryKey: ["team-load", start], queryFn: () => api.teamLoad(start) });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;

  const { months, rows } = q.data!;
  const visible = rows.filter((r) => r.values.some((v) => v !== 0));
  const totals = months.map((_, i) => visible.reduce((s, r) => s + (r.values[i] ?? 0), 0));

  const toggle = (team: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(team) ? next.delete(team) : next.add(team);
      return next;
    });

  return (
    <div>
      <h2>Charge équipe (§5.3)</h2>
      <div className="toolbar">
        <span className="muted">
          Somme des jours-homme des projets <strong>in&nbsp;plan</strong>, par équipe et par mois
          (§6.3). <strong>Cliquez le chevron</strong> pour le détail par projet.
        </span>
        <ExportButton
          name="charge-equipe"
          headers={["Équipe", ...months.map(monthShort), "Total"]}
          rows={visible.map((r) => [r.team, ...r.values, r.values.reduce((s, v) => s + v, 0)])}
        />
      </div>
      <div className="table-wrap">
        <table className="pivot">
          <thead>
            <tr>
              <th className="sticky-col">Équipe</th>
              {months.map((m) => (
                <th key={m} style={{ textAlign: "right" }}>{monthShort(m)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => {
              const open = expanded.has(r.team);
              return (
                <RowGroup
                  key={r.team}
                  open={open}
                  onToggle={() => toggle(r.team)}
                  team={r.team}
                  values={r.values}
                  months={months}
                  start={start}
                />
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td className="sticky-col"><strong>Total</strong></td>
              {totals.map((t, i) => (
                <td key={i} style={{ textAlign: "right" }}><strong>{t.toFixed(1)}</strong></td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function RowGroup({
  open, onToggle, team, values, months, start,
}: {
  open: boolean; onToggle: () => void; team: string; values: number[]; months: string[]; start: string;
}) {
  return (
    <>
      <tr className={open ? "team-row open" : "team-row"}>
        <td className="sticky-col">
          <button className="chevron" onClick={onToggle} aria-label={open ? "Replier" : "Déplier"}>
            {open ? "▾" : "▸"}
          </button>
          {team}
        </td>
        {values.map((v, i) => (
          <td key={i} style={{ textAlign: "right" }}>{fmt(v)}</td>
        ))}
      </tr>
      {open && <TeamDetail team={team} start={start} months={months} />}
    </>
  );
}
