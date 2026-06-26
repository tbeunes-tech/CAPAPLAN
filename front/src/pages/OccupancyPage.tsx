import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { COLOR_STYLE, monthShort, rateLabel } from "../dash";
import ExportButton from "../components/ExportButton";

function Legend5() {
  return (
    <div className="legend">
      <span style={COLOR_STYLE.green}>&lt; 80 % marge</span>
      <span style={COLOR_STYLE.amber}>80–100 % cible</span>
      <span style={COLOR_STYLE.red}>&gt; 100 % surcharge</span>
      <span style={COLOR_STYLE.overload_null_capacity}>charge sans capacité</span>
    </div>
  );
}

const fmtDays = (v: number) => (v === 0 ? "" : v.toFixed(1));

/** Détail de la charge d'une équipe : projets contributeurs × mois (numérateur du taux). */
function TeamDetail({ team, start, nMonths }: { team: string; start: string; nMonths: number }) {
  const q = useQuery({
    queryKey: ["team-load-detail", team, start],
    queryFn: () => api.teamLoadDetail(team, start),
  });
  if (q.isLoading)
    return (
      <tr className="detail-row">
        <td className="sticky-col" /><td colSpan={nMonths} className="muted">Chargement…</td>
      </tr>
    );
  const rows = q.data?.rows ?? [];
  if (!rows.length)
    return (
      <tr className="detail-row">
        <td className="sticky-col" /><td colSpan={nMonths} className="muted">Aucune charge in plan.</td>
      </tr>
    );
  return (
    <>
      <tr className="detail-row">
        <td className="sticky-col detail-label muted">charge (j) par projet ↓</td>
        {Array.from({ length: nMonths }).map((_, i) => <td key={i} />)}
      </tr>
      {rows.map((r) => (
        <tr className="detail-row" key={r.project_id}>
          <td className="sticky-col detail-label" title={r.project_name}>
            <Link to={`/portfolio/${r.project_id}/loads`}>{r.project_id}</Link> · {r.project_name}
            {r.priorite && <span className="chip">{r.priorite}</span>}
            {r.prio_dsi && <span className="chip chip-dsi">{r.prio_dsi}</span>}
          </td>
          {r.values.map((v, i) => (
            <td key={i} style={{ textAlign: "right" }}>{fmtDays(v)}</td>
          ))}
        </tr>
      ))}
    </>
  );
}

export default function OccupancyPage() {
  const { start } = useWindowStart();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const occQ = useQuery({ queryKey: ["occupancy", start], queryFn: () => api.occupancy(start) });
  const loadQ = useQuery({ queryKey: ["team-load", start], queryFn: () => api.teamLoad(start) });
  const capaQ = useQuery({ queryKey: ["capacity", start], queryFn: () => api.capacityPivot(start) });

  if (occQ.isLoading || loadQ.isLoading || capaQ.isLoading) return <p>Chargement…</p>;
  if (occQ.isError) return <p className="err">Erreur : {(occQ.error as Error).message}</p>;

  const occ = occQ.data!;
  const months = occ.months;

  const chart = months.map((m, i) => {
    const charge = (loadQ.data?.rows ?? []).reduce((s, r) => s + (r.values[i] ?? 0), 0);
    const capa = (capaQ.data?.rows ?? []).reduce((s, r) => s + (r.values[i] ?? 0), 0);
    return {
      month: monthShort(m),
      charge: Math.round(charge * 10) / 10,
      capacite: Math.round(capa * 10) / 10,
      taux: capa > 0 ? Math.round((charge / capa) * 100) : 0,
    };
  });

  const rows = occ.rows.filter((r) =>
    r.cells.some((c) => c.rate !== 0 || c.color === "overload_null_capacity"),
  );

  const toggle = (team: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(team) ? next.delete(team) : next.add(team);
      return next;
    });

  return (
    <div>
      <h2>Taux d'occupation (§5.5)</h2>
      <div className="toolbar">
        <span className="muted">
          Charge / capacité par équipe et par mois. <strong>Cliquez le chevron</strong> pour voir les
          projets qui composent la charge d'une équipe.
        </span>
        <ExportButton
          name="taux-occupation"
          headers={["Équipe", ...months.map(monthShort)]}
          rows={rows.map((r) => [
            r.team,
            ...r.cells.map((c) =>
              c.color === "overload_null_capacity" ? "∞" : c.rate === 0 ? "" : `${Math.round(c.rate * 100)}%`,
            ),
          ])}
        />
      </div>

      <div className="chart-card">
        <strong>Vue d'ensemble portefeuille — charge vs capacité totale</strong>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={chart} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" fontSize={12} />
            <YAxis yAxisId="j" fontSize={12} label={{ value: "jours", angle: -90, position: "insideLeft", fontSize: 11 }} />
            <YAxis yAxisId="p" orientation="right" fontSize={12} unit="%" />
            <Tooltip />
            <Legend />
            <Bar yAxisId="j" dataKey="capacite" name="Capacité" fill="#cfe0ff" />
            <Bar yAxisId="j" dataKey="charge" name="Charge in plan" fill="#2f6df6" />
            <Line yAxisId="p" type="monotone" dataKey="taux" name="Taux %" stroke="#d23b3b" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <Legend5 />

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
            {rows.map((r) => {
              const open = expanded.has(r.team);
              return (
                <Fragment key={r.team}>
                  <tr className={open ? "team-row open" : "team-row"}>
                    <td className="sticky-col">
                      <button className="chevron" onClick={() => toggle(r.team)} aria-label={open ? "Replier" : "Déplier"}>
                        {open ? "▾" : "▸"}
                      </button>
                      {r.team}
                    </td>
                    {r.cells.map((c, i) => (
                      <td
                        key={i}
                        style={{ textAlign: "right", ...(c.rate === 0 && c.color !== "overload_null_capacity" ? {} : COLOR_STYLE[c.color]) }}
                      >
                        {c.rate === 0 && c.color !== "overload_null_capacity" ? "" : rateLabel(c.rate, c.color)}
                      </td>
                    ))}
                  </tr>
                  {open && <TeamDetail team={r.team} start={start} nMonths={months.length} />}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
