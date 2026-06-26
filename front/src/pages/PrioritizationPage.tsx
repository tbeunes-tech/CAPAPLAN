import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { COLOR_STYLE, monthShort, rateLabel } from "../dash";
import ExportButton from "../components/ExportButton";

export default function PrioritizationPage() {
  const { start } = useWindowStart();
  const [open, setOpen] = useState<Set<string>>(new Set());
  const q = useQuery({ queryKey: ["prioritization", start], queryFn: () => api.prioritization(start) });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;
  const plan = q.data!;
  const nCols = 4 + plan.months.length;

  const toggle = (s: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });

  return (
    <div>
      <h2>Plan de priorisation (§5.8)</h2>
      <div className="toolbar">
        <span className="muted">
          Tenue de capacité par paliers de priorité cumulés. <strong>Cliquez le chevron</strong> d'un
          scénario pour voir les projets concernés (avec Prio et Prio DSI).
        </span>
        <ExportButton
          name="priorisation"
          headers={["Scénario", "Nb projets", "Charge cumulée (j)", "Taux global",
                    ...plan.months.map(monthShort)]}
          rows={plan.scenarios.map((s) => [
            s.scenario, s.project_count, s.charge_cumulee, rateLabel(s.global_rate, s.global_color),
            ...s.monthly.map((c) => rateLabel(c.rate, c.color)),
          ])}
        />
      </div>

      <div className="table-wrap">
        <table className="pivot">
          <thead>
            <tr>
              <th className="sticky-col">Scénario</th>
              <th style={{ textAlign: "right" }}>Projets</th>
              <th style={{ textAlign: "right" }}>Charge cumulée (j)</th>
              <th style={{ textAlign: "right" }}>Taux global</th>
              {plan.months.map((m) => (
                <th key={m} style={{ textAlign: "right" }}>{monthShort(m)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {plan.scenarios.map((s) => {
              const isOpen = open.has(s.scenario);
              return (
                <Fragment key={s.scenario}>
                  <tr className={isOpen ? "team-row open" : "team-row"}>
                    <td className="sticky-col">
                      <button className="chevron" onClick={() => toggle(s.scenario)}
                        aria-label={isOpen ? "Replier" : "Déplier"}>
                        {isOpen ? "▾" : "▸"}
                      </button>
                      <strong>{s.scenario}</strong>
                    </td>
                    <td style={{ textAlign: "right" }}>{s.project_count}</td>
                    <td style={{ textAlign: "right" }}>{s.charge_cumulee.toFixed(1)}</td>
                    <td style={{ textAlign: "right", ...COLOR_STYLE[s.global_color] }}>
                      {rateLabel(s.global_rate, s.global_color)}
                    </td>
                    {s.monthly.map((c, i) => (
                      <td key={i} style={{ textAlign: "right", ...COLOR_STYLE[c.color] }}>
                        {rateLabel(c.rate, c.color)}
                      </td>
                    ))}
                  </tr>
                  {isOpen && (
                    <tr className="detail-row">
                      <td className="sticky-col" />
                      <td colSpan={nCols - 1} style={{ padding: "6px 10px" }}>
                        {s.projects.length === 0 ? (
                          <span className="muted">Aucun projet.</span>
                        ) : (
                          <table className="sub-table">
                            <thead>
                              <tr>
                                <th>Project ID</th><th>Projet</th>
                                <th>Prio</th><th>Prio DSI</th>
                                <th style={{ textAlign: "right" }}>Charge (j)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {s.projects.map((p) => (
                                <tr key={p.project_id}>
                                  <td><Link to={`/portfolio/${p.project_id}/loads`}>{p.project_id}</Link></td>
                                  <td>{p.project_name}</td>
                                  <td>{p.priorite ? <span className="chip">{p.priorite}</span> : "—"}</td>
                                  <td>{p.prio_dsi ? <span className="chip chip-dsi">{p.prio_dsi}</span> : "—"}</td>
                                  <td style={{ textAlign: "right" }}>{p.charge.toFixed(1)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
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
