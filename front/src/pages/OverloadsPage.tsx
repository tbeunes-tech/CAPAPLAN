import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useWindowStart } from "../WindowContext";
import { COLOR_STYLE, monthShort, rateLabel } from "../dash";
import ExportButton from "../components/ExportButton";

export default function OverloadsPage() {
  const { start } = useWindowStart();
  const [filter, setFilter] = useState("");
  const q = useQuery({ queryKey: ["overloads", start], queryFn: () => api.overloads(start) });

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;

  const rows = q.data!.filter(
    (o) => !filter || o.team.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div>
      <h2>Analyse des surcharges (§5.6)</h2>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Filtrer par équipe…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="muted">{rows.length} couple(s) (équipe, mois) en dépassement &gt; 100 %</span>
        <ExportButton
          name="surcharges"
          headers={["Équipe", "Mois", "Charge (j)", "Capacité (j)", "Taux", "Écart (j)"]}
          rows={rows.map((o) => [
            o.team, monthShort(o.month), o.charge, o.capacite,
            rateLabel(o.rate, o.color), o.ecart_jours,
          ])}
        />
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Équipe</th>
              <th>Mois</th>
              <th style={{ textAlign: "right" }}>Charge (j)</th>
              <th style={{ textAlign: "right" }}>Capacité (j)</th>
              <th style={{ textAlign: "right" }}>Taux</th>
              <th style={{ textAlign: "right" }}>Écart (j)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o, i) => (
              <tr key={i}>
                <td>{o.team}</td>
                <td>{monthShort(o.month)}</td>
                <td style={{ textAlign: "right" }}>{o.charge.toFixed(1)}</td>
                <td style={{ textAlign: "right" }}>{o.capacite.toFixed(1)}</td>
                <td style={{ textAlign: "right", ...COLOR_STYLE[o.color] }}>
                  {rateLabel(o.rate, o.color)}
                </td>
                <td style={{ textAlign: "right" }}>
                  <strong>+{o.ecart_jours.toFixed(1)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
