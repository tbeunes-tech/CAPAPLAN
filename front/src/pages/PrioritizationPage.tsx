import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { COLOR_STYLE, monthShort, rateLabel } from "../dash";
import ExportButton from "../components/ExportButton";

export default function PrioritizationPage() {
  const { start } = useWindowStart();
  const q = useQuery({ queryKey: ["prioritization", start], queryFn: () => api.prioritization(start) });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;
  const plan = q.data!;

  return (
    <div>
      <h2>Plan de priorisation (§5.8)</h2>
      <div className="toolbar">
        <span className="muted">
          Tenue de capacité par paliers de priorité cumulés. Taux mensuel = charge des projets du
          scénario / capacité totale du mois.
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
                <th key={m} style={{ textAlign: "right" }}>
                  {monthShort(m)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {plan.scenarios.map((s) => (
              <tr key={s.scenario}>
                <td className="sticky-col">
                  <strong>{s.scenario}</strong>
                </td>
                <td
                  style={{ textAlign: "right", cursor: "help" }}
                  title={s.project_ids.join(", ")}
                >
                  {s.project_count}
                </td>
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
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">Survolez le nombre de projets pour voir la liste des Project ID inclus.</p>
    </div>
  );
}
